"""
Support for Xiaomi binary sensors.

"""
import logging

from homeassistant.components.binary_sensor import (BinarySensorDevice)
from homeassistant.components.xiaomi import (XiaomiDevice, XIAOMI_HUB)
from homeassistant.const import ATTR_BATTERY_LEVEL

_LOGGER = logging.getLogger(__name__)

def setup_platform(hass, config, add_devices, discovery_info=None):
    """Perform the setup for Xiaomi devices."""

    for resp in XIAOMI_HUB.XIAOMI_DEVICES['binary_sensor']:
            model = resp['model']
            if (model == 'motion'):
                add_devices([XiaomiGenericBinarySensor(resp, 'Motion Sensor','status', 'motion', XIAOMI_HUB)])
            elif (model == 'magnet'):
                add_devices([XiaomiGenericBinarySensor(resp, 'Door Window Sensor', 'status', 'open', XIAOMI_HUB)])
            elif (model == 'switch'):
                add_devices([XiaomiButton(resp, 'Switch', 'status', hass, XIAOMI_HUB)])
            elif (model == '86sw1'):
                add_devices([XiaomiButton(resp, 'Wall Switch', 'channel_0', hass, XIAOMI_HUB)])
            elif (model == '86sw2'):
                add_devices([
                    XiaomiButton(resp, 'Wall Switch (Left)', 'channel_0', hass, XIAOMI_HUB), 
                    XiaomiButton(resp, 'Wall Switch (Right)', 'channel_1', hass, XIAOMI_HUB)])

class XiaomiGenericBinarySensor(XiaomiDevice, BinarySensorDevice):
    """Representation of a XiaomiMotionSensor."""

    def __init__(self, resp, name, dataKey, dataOpenValue, xiaomiHub):
        """Initialize the XiaomiMotionSensor."""
        self._state = False
        self._dataKey = dataKey
        self._dataOpenValue = dataOpenValue
        self._battery = -1
        XiaomiDevice.__init__(self, resp, name, xiaomiHub)

    @property
    def sensor_class(self):
        if self._dataKey == 'motion':
            return 'motion'
        elif self._dataKey == 'open':
            return 'opening'
        return None

    @property
    def is_on(self):
        """Return true if sensor is on."""
        return self._state

    def parse_data(self, data):
        state = True if data[self._dataKey] == self._dataOpenValue else False
        if self._state == state:
            return False
        else:
            self._state = state
            return True

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        return {
            ATTR_BATTERY_LEVEL: self._battery,
        }

    def push_data(self, data):
        """Push from Hub"""
        if self._dataKey in data and self.parse_data(data) == True:
            self.schedule_update_ha_state()

        if 'battery' in data:
            self._battery = data['battery']

class XiaomiButton(XiaomiDevice, BinarySensorDevice):

    def __init__(self, resp, name, dataKey, hass, xiaomiHub):
        """Initialize the XiaomiButton."""
        self._is_down = False
        self._hass = hass
        self._dataKey = dataKey
        XiaomiDevice.__init__(self, resp, name, xiaomiHub)

    @property
    def is_on(self):
        """Return true if sensor is on."""
        return self._is_down

    def push_data(self, data):
        """Push from Hub"""
        if self._dataKey in data:
            state = data[self._dataKey]
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