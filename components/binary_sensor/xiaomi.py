"""
Support for Xiaomi binary sensors.

Developed by Rave from Lazcad.com
"""
import logging
import asyncio

from homeassistant.helpers.entity import Entity
from homeassistant.components.binary_sensor import (BinarySensorDevice)
from homeassistant.const import ATTR_BATTERY_LEVEL

_LOGGER = logging.getLogger(__name__)

def setup_platform(hass, config, add_devices, discovery_info=None):
    """Perform the setup for Xiaomi devices."""

    devices = []
    XIAOMI_GATEWAYS = hass.data['XIAOMI_GATEWAYS']
    for (ip, gateway) in XIAOMI_GATEWAYS.items():
        for device in gateway.XIAOMI_DEVICES['binary_sensor']:
            model = device['model']
            if (model == 'motion'):
                devices.append(XiaomiMotionSensor(device, gateway, hass))
            elif (model == 'magnet'):
                devices.append(XiaomiDoorSensor(device, gateway))
            elif (model == 'switch'):
                devices.append(XiaomiButton(device, 'Switch', 'status', hass, gateway))
            elif (model == 'cube'):
                devices.append(XiaomiCube(device, hass, gateway))
            elif (model == '86sw1'):
                devices.append(XiaomiButton(device, 'Wall Switch', 'channel_0', hass, gateway))
            elif (model == '86sw2'):
                devices.append(XiaomiButton(device, 'Wall Switch (Left)', 'channel_0', hass, gateway),
                    XiaomiButton(device, 'Wall Switch (Right)', 'channel_1', hass, gateway))
    add_devices(devices)

class XiaomiDevice(Entity):
    """Representation a base Xiaomi device."""

    def __init__(self, device, name, xiaomi_hub):
        """Initialize the xiaomi device."""
        self._sid = device['sid']
        self._name = '{}_{}'.format(name, self._sid)
        self.parse_data(device['data'])
        self.xiaomi_hub = xiaomi_hub
        self._device_state_attributes = {}
        xiaomi_hub.XIAOMI_HA_DEVICES[self._sid].append(self)

    @property
    def name(self):
        """Return the name of the device."""
        return self._name

    @property
    def should_poll(self):
        return False

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        return self._device_state_attributes

    def push_data(self, data):
        raise NotImplementedError()

    def parse_data(self, data):
        raise NotImplementedError()

        
class XiaomiMotionSensor(XiaomiDevice, BinarySensorDevice):
    """Representation of a XiaomiMotionSensor."""

    def __init__(self, device, xiaomi_hub, hass):
        """Initialize the XiaomiMotionSensor."""
        self._state = False
        self._hass = hass
        XiaomiDevice.__init__(self, device, 'Motion Sensor', xiaomi_hub)

    @property
    def sensor_class(self):
        return 'motion'

    @property
    def is_on(self):
        """Return true if sensor is on."""
        return self._state

    def parse_data(self, data):
        if 'status' in data:
            value = data['status']
            if value == 'motion':
                self._hass.loop.create_task(self.async_poll_status())
                if self._state:
                    return False
                else:
                    self._state = True
                    return True
            elif value == 'no_motion':
                if not self._state:
                    return False
                else:
                    self._state = False
                    return True

        if 'no_motion' in data:
            if self._state:
                self._state = False
                return True
            else:
                return False

    def push_data(self, data):
        """Push from Hub"""
        if self.parse_data(data):
            self.schedule_update_ha_state()

        if 'battery' in data:
            self._device_state_attributes[ATTR_BATTERY_LEVEL] = data['battery']

    #For Polling
    def update(self):
        data = self.xiaomi_hub.get_from_hub(self._sid)
        if data is None:
            if self._state:
                self._state = False
                self.schedule_update_ha_state()
            return
        self.push_data(data)

    @asyncio.coroutine
    def async_poll_status(self):
        yield from asyncio.sleep(10)
        self.update()


class XiaomiDoorSensor(XiaomiDevice, BinarySensorDevice):
    """Representation of a XiaomiDoorSensor."""

    def __init__(self, device, xiaomi_hub):
        """Initialize the XiaomiDoorSensor."""
        self._state = False
        XiaomiDevice.__init__(self, device, 'Door Window Sensor', xiaomi_hub)

    @property
    def sensor_class(self):
        return 'opening'

    @property
    def is_on(self):
        """Return true if sensor is on."""
        return self._state

    def parse_data(self, data):
        if not 'status' in data:
            return False

        value = data['status']
        if value == 'open' or value == 'no_close':
            if self._state:
                return False
            else:
                self._state = True
                return True

        if value == 'close':
            if self._state:
                self._state = False
                return True
            else:
                return False

    def push_data(self, data):
        """Push from Hub"""
        if self.parse_data(data):
            self.schedule_update_ha_state()

        if 'battery' in data:
            self._device_state_attributes[ATTR_BATTERY_LEVEL] = data['battery']


class XiaomiButton(XiaomiDevice, BinarySensorDevice):

    def __init__(self, device, name, data_key, hass, xiaomi_hub):
        """Initialize the XiaomiButton."""
        self._is_down = False
        self._hass = hass
        self._data_key = data_key
        XiaomiDevice.__init__(self, device, name, xiaomi_hub)

    @property
    def is_on(self):
        """Return true if sensor is on."""
        return self._is_down

    def push_data(self, data):
        """Push from Hub"""
        if not self._data_key in data:
            return False

        state = data[self._data_key]
        if state == 'long_click_press':
            self._is_down = True
            self.schedule_update_ha_state()
            click_type = 'long_click_press'
        elif state == 'long_click_release':
            self._is_down = False
            self.schedule_update_ha_state()
            click_type = 'hold'
        elif state == 'click':
            click_type = 'single'
        elif state == 'double_click':
            click_type = 'double'

        self._hass.bus.fire('click', {
            'entity_id': self.entity_id,
            'click_type': click_type
        })


class XiaomiCube(XiaomiDevice, BinarySensorDevice):

    STATUS = 'status'
    ROTATE = 'rotate'

    def __init__(self, device, hass, xiaomi_hub):
        """Initialize the XiaomiButton."""
        self._hass = hass
        XiaomiDevice.__init__(self, device, 'Cube', xiaomi_hub)

    @property
    def is_on(self):
        """Return true if sensor is on."""
        return False

    def push_data(self, data):
        """Push from Hub"""
        if self.STATUS in data:
            self._hass.bus.fire('cube_action', {
                'entity_id': self.entity_id,
                'action_type': data[self.STATUS]
            })

        if self.ROTATE in data:
            self._hass.bus.fire('cube_action', {
                'entity_id': self.entity_id,
                'action_type': self.ROTATE,
                'action_value': data[self.ROTATE]
            })
