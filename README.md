# homeassistant

Credit to the following Github project
https://github.com/fooxy/homeassistant-aqara
https://github.com/louisZL/lumi-gateway-local-api

This is an almost completed Home Assistant component for Xiaomi Hub. It allows you to integrate the following devices into HA

- Motion Sensor
- Door and Window Sensor
- Button
- Plug
- Wall Switch (Single)
- Wall Switch (Double)
- Wireless Switch (Single)
- Wireless Switch (Double)
- Cube (TODO, i don't have one yet)

Power consumption for the plug and battery reporting is coming soon

1) First, copy all the files into the Home Assistant root location. Yes, it only works in the location below
/srv/homeassistant/homeassistant_venv/lib/python3.4/site-packages/homeassistant/components

2) Add the following line to the Configuration.yaml. You will need to get the Hub's key in order to issue command to the hub like turning on and off plug. Follow the steps here http://bbs.xiaomi.cn/t-13198850

xiaomi :
  key: xxxxxxxxxxxxxxxx

3) Start HA. if you get an error about pycrypto, most probably, it couldn't install itself. In this case, install pycrypto manually

4) Add friendly names to the Configuration.yaml like below

  customize:
    binary_sensor.158d000xxxxxc3_switch:
        friendly_name: Ktichen Switch
    binary_sensor.158d000xxxxxc2_switch:
        friendly_name: Table Switch
    binary_sensor.158d000xxxxx7a_door_window_sensor:
        friendly_name: Door Sensor
        
5) Add automation. For the Button and Switch, use the following event

automation:
- alias: Turn on Dining Light when click
  initial_state: True
  hide_entity: False
  trigger:
    platform: event
    event_type: click
    event_data:
        button_name: 158d000xxxxxc2_switch
        click_type: click
          action:
    service: switch.toggle
    entity_id: switch.158d000xxxxx01_wall_switch_left
