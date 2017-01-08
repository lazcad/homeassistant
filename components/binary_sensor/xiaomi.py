"""
Support for Xiaomi binary sensors.

Developed by Rave from Lazcad.com
"""
import logging

from homeassistant.helpers.entity import Entity
from homeassistant.components.binary_sensor import (BinarySensorDevice)
from homeassistant.const import ATTR_BATTERY_LEVEL

_LOGGER = logging.getLogger(__name__)

def setup_platform(hass, config, add_devices, discovery_info=None):
    """Perform the setup for Xiaomi devices."""

    XIAOMI_HUB = hass.data['XIAOMI_HUB']
    for device in XIAOMI_HUB.XIAOMI_DEVICES['binary_sensor']:
            model = device['model']
            if (model == 'motion'):
                add_devices([XiaomiBinarySensor(device, 'Motion Sensor','status', 'motion', 'motion', 'no_motion', XIAOMI_HUB)])
            elif (model == 'magnet'):
                add_devices([XiaomiBinarySensor(device, 'Door Window Sensor', 'status', 'open', 'no_close', 'close', XIAOMI_HUB)])
            elif (model == 'switch'):
                add_devices([XiaomiButton(device, 'Switch', 'status', hass, XIAOMI_HUB)])
            elif (model == 'cube'):
                add_devices([XiaomiCube(device, 'Cube', 'status', hass, XIAOMI_HUB)])
            elif (model == '86sw1'):
                add_devices([XiaomiButton(device, 'Wall Switch', 'channel_0', hass, XIAOMI_HUB)])
            elif (model == '86sw2'):
                add_devices([XiaomiButton(device, 'Wall Switch (Left)', 'channel_0', hass, XIAOMI_HUB), 
                    XiaomiButton(device, 'Wall Switch (Right)', 'channel_1', hass, XIAOMI_HUB)])

class XiaomiDevice(Entity):
    """Representation a base Xiaomi device."""

    def __init__(self, device, name, xiaomi_hub):
        """Initialize the xiaomi device."""
        self._sid = device['sid']
        self._name = '{}_{}'.format(name, self._sid)
        self.parse_data(device['data'])
        self.xiaomi_hub = xiaomi_hub
        xiaomi_hub.XIAOMI_HA_DEVICES[self._sid].append(self)

    @property
    def name(self):
        """Return the name of the device."""
        return self._name

    @property
    def should_poll(self):
        return False

    def push_data(self, data):
        return True

    def parse_data(self, data):
        return True

class XiaomiBinarySensor(XiaomiDevice, BinarySensorDevice):
    """Representation of a XiaomiBinarySensor."""

    def __init__(self, device, name, data_key, data_open_value, data_maintain_value, data_close_value, xiaomi_hub):
        """Initialize the XiaomiBinarySensor."""
        self._state = False
        self._data_key = data_key
        self._data_open_value = data_open_value
        self._data_maintain_value = data_maintain_value
        self._data_close_value = data_close_value
        self._battery = -1
        XiaomiDevice.__init__(self, device, name, xiaomi_hub)

    @property
    def sensor_class(self):
        if self._data_open_value == 'motion':
            return 'motion'
        elif self._data_open_value == 'open':
            return 'opening'
        return None

    @property
    def is_on(self):
        """Return true if sensor is on."""
        return self._state

    def parse_data(self, data):
        if not self._data_key in data:
            return False

        key_value = data[self._data_key]
        if key_value == self._data_open_value or key_value == self._data_maintain_value:
            if self._state == True:
                return False
            else:
                self._state = True
                return True

        if key_value == self._data_close_value:
            if self._state == True:
                self._state = False
                return True
            else:
                return False     

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        return {
            ATTR_BATTERY_LEVEL: self._battery,
        }

    def push_data(self, data):
        """Push from Hub"""
        if self.parse_data(data) == True:
            self.schedule_update_ha_state()

        if 'battery' in data:
            self._battery = data['battery']

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
            return

        if state == 'long_click_release':
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

    def __init__(self, device, name, data_key, hass, xiaomi_hub):
        """Initialize the XiaomiButton."""
        self._hass = hass
        self._data_key = data_key
        XiaomiDevice.__init__(self, device, name, xiaomi_hub)

    @property
    def is_on(self):
        """Return true if sensor is on."""
        return False

    def push_data(self, data):
        """Push from Hub"""
        if not self._data_key in data:
            return False

        self._hass.bus.fire('cube_action', {
            'entity_id': self.entity_id,
            'action_type': data[self._data_key]
        })
