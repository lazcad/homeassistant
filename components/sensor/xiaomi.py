"""
Support for Xiaomi sensors.

"""
import logging

from homeassistant.const import (ATTR_BATTERY_LEVEL, TEMP_CELSIUS)
from homeassistant.helpers.entity import Entity
from homeassistant.components.xiaomi import (XiaomiDevice, XIAOMI_HUB)

_LOGGER = logging.getLogger(__name__)

def setup_platform(hass, config, add_devices, discovery_info=None):
    """Perform the setup for Xiaomi devices."""

    for resp in XIAOMI_HUB.XIAOMI_DEVICES['sensor']:
        model = resp['model']
        if (model == 'sensor_ht'):
            add_devices([
                XiaomiSensor(resp, 'Temperature', 'temperature', XIAOMI_HUB), 
                XiaomiSensor(resp, 'Humidity', 'humidity', XIAOMI_HUB)])

class XiaomiSensor(XiaomiDevice, Entity):
    """Representation of a XiaomiGenericSwitch."""

    def __init__(self, resp, name, dataKey, xiaomiHub):
        """Initialize the XiaomiSensor."""
        self.current_value = 0
        self._dataKey = dataKey
        self._battery = -1
        XiaomiDevice.__init__(self, resp, name, xiaomiHub)

    @property
    def state(self):
        """Return the name of the sensor."""
        return self.current_value

    @property
    def unit_of_measurement(self):
        if self._dataKey == 'temperature':
            return TEMP_CELSIUS 
        elif self._dataKey == 'humidity':
            return '%'

    def parse_data(self, data):
        value = data[self._dataKey]
        self.current_value = int(value) / 100
        return True

    def push_data(self, data):
        """Push from Hub"""
        if self._dataKey in data and self.parse_data(data) == True:
            self.schedule_update_ha_state()

        if 'battery' in data:
            self._battery = data['battery']

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        return {
            ATTR_BATTERY_LEVEL: self._battery,
        }

    def update(self):
        data = self.xiaomiHub.get_from_hub(self._sid)
        self.push_data(data)

