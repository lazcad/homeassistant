# HomeAssistant Xiaomi Hub Component by Rave (Lazcad)

Credits
---------------
Credits to the following Github project
- https://github.com/fooxy/homeassistant-aqara
- https://github.com/louisZL/lumi-gateway-local-api

Description
---------------
This is an almost completed Home Assistant component for Xiaomi Hub. It allows you to integrate the following devices into HA

- Motion Sensor
- Door and Window Sensor
- Button
- Plug
- Aqara Wall Switch (Single)
- Aqara Wall Switch (Double)
- Aqara Wireless Switch (Single)
- Aqara Wireless Switch (Double)
- Cube (TODO, i don't have one yet)

Power consumption for the plug and battery reporting is coming soon

![alt tag](http://lazcad.com/content/images/beer.png)
[Buy me a beer](https://www.paypal.com/cgi-bin/webscr?cmd=_s-xclick&hosted_button_id=R3P4SPQ7LHXMN)  if you like what you're seeing!

Installation (Raspberry Pi)
---------------------------

1. First, copy all the files into the Home Assistant location. It can now be installed either to the custom_components folder 
```
/home/homeassistant/.homeassistant/custom_components
```
or the root folder (using virtual environment)
```
/srv/homeassistant/homeassistant_venv/lib/python3.4/site-packages/homeassistant/components
```

2. Add the following line to the Configuration.yaml. You will need to get the Hub's key in order to issue command to the hub like turning on and off plug. Follow the steps here http://bbs.xiaomi.cn/t-13198850
  ```yaml
  xiaomi :
    key: xxxxxxxxxxxxxxxx
  ```
3. Start HA. Pycrypto should install automatically. If not, install pycrypto manually. if you are using virtual environment, remember to install from virtual environment like below
```
(homeassistant_venv) pi@raspberrypi:~ $ pip3 install pycrypto
```

4. Add friendly names to the Configuration.yaml like below
  ```yaml
    customize:
      binary_sensor.switch_158d000xxxxxc3:
          friendly_name: Ktichen Switch
      binary_sensor.switch_158d000xxxxxc2:
          friendly_name: Table Switch
      binary_sensor.door_window_sensor_158d000xxxxx7a:
          friendly_name: Door Sensor
  ```
        
5. Add automation. For the Button and Switch, use the following event. Available click types are 'single', 'double' and 'hold'
  ```yaml
  automation:
  - alias: Turn on Dining Light when click
    trigger:
      platform: event
      event_type: click
      event_data:
          entity_id: binary_sensor.switch_158d000xxxxxc2
          click_type: single
    action:
      service: switch.toggle
      entity_id: switch.wall_switch_left_158d000xxxxx01
  ```
6. To display custom data such as battery, add the following to configuration.yaml (I have not tested whether the battery code works)
```yaml
sensor:
    platform: template
    sensors:
        battery_door:
          friendly_name: 'Door Sensor Battery'
          value_template: '{{ states.binary_sensor.door_window_sensor_158d000xxxxx0a.attributes.battery_level }}'
          unit_of_measurement: '%'
        battery_temp:
          friendly_name: 'Temp Sensor Battery'
          value_template: '{{ states.sensor.temperature_158d000xxxxx03.attributes.battery_level }}'
          unit_of_measurement: '%'
```
