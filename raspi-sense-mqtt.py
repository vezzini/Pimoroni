# -*- coding: utf-8 -*-
"""
Created on Sat May 16 22:52:06 2020

@author: via1
"""


#!/usr/bin/env python

import time
from veml6075 import VEML6075
from bmp280 import BMP280
from ltr559 import LTR559
from smbus import SMBus
from subprocess import PIPE, Popen
import paho.mqtt.client as mqtt

# setting up the variables for the MQTT broker!
mqtt_username = "openhab"
mqtt_password = "DsPW4us@RW4"
mqtt_topic = "raspi-openhab"
mqtt_broker_address = "raspi-panel.home"
mqtt_client_id = "raspi-zero"

client = mqtt.Client(mqtt_client_id)
# Set the username and password for the MQTT client
client.username_pw_set(mqtt_username, mqtt_password)

#connect to the mqqt broker
client.connect(mqtt_broker_address)

bus = SMBus(1)

# Create ltr559 instance and setup
ltr559 = LTR559()

# Create VEML6075 instance and set up
uv_sensor = VEML6075(i2c_dev=bus)
uv_sensor.set_shutdown(False)
uv_sensor.set_high_dynamic_range(False)
uv_sensor.set_integration_time('100ms')

# Create BMP280 instance and set up
bmp280 = BMP280(i2c_dev=bus)
baseline_values = []
baseline_size = 100

print("Collecting baseline values for {:d} seconds. Do not move the sensor!\n".format(baseline_size))

for i in range(baseline_size):
    pressure = bmp280.get_pressure()
    baseline_values.append(pressure)
    time.sleep(1)

baseline = sum(baseline_values[:-25]) / len(baseline_values[:-25])


# Gets the CPU temperature in degrees C
def get_cpu_temperature():
    process = Popen(['vcgencmd', 'measure_temp'], stdout=PIPE)
    output, _error = process.communicate()
    return float(output[5:9])

factor = 2.4  # Smaller numbers adjust temp down, vice ver$
smooth_size = 10  # Dampens jitter due to rapid CPU temp c$

cpu_temps = []



while True:
    
    cpu_temp = get_cpu_temperature()
    cpu_temps.append(cpu_temp)

    if len(cpu_temps) > smooth_size:
        cpu_temps = cpu_temps[1:]

    smoothed_cpu_temp = sum(cpu_temps) / float(len(cpu_temps))
 
    raw_temp = bmp280.get_temperature()
    pressure = bmp280.get_pressure()
    print('{:05.2f}*C {:05.2f}hPa'.format(raw_temp, pressure))
    
    
    comp_temp = raw_temp - ((smoothed_cpu_temp - raw_temp) / factor)

    print("Compensated temperature: {:05.2f} °C".format(comp_temp))
    
    altitude = bmp280.get_altitude(qnh=baseline)
    print('Relative altitude: {:05.2f} metres'.format(altitude))
    
    
    uva, uvb = uv_sensor.get_measurements()
    uv_comp1, uv_comp2 = uv_sensor.get_comparitor_readings()
    uv_indices = uv_sensor.convert_to_index(uva, uvb, uv_comp1, uv_comp2)

    print('UVA : {0} UVB : {1} COMP 1 : {2} COMP 2 : {3}'.format(uva, uvb, uv_comp1, uv_comp2))
    print('UVA INDEX: {0[0]} UVB INDEX : {0[1]} AVG UV INDEX : {0[2]}\n'.format(uv_indices))



    payload = "Compensated temperature: {:05.2f} °C".format(comp_temp)
    #publish to mqtt broker
    client.publish(mqtt_topic, payload)

    time.sleep(1.0)