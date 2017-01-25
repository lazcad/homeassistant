"""
Support for Xiaomi sensors.

Developed by Rave from Lazcad.com
"""
import logging

from homeassistant.helpers.entity import Entity
from homeassistant.const import (ATTR_BATTERY_LEVEL, TEMP_CELSIUS)

_LOGGER = logging.getLogger(__name__)

def setup_platform(hass, config, add_devices, discovery_info=None):
    """Perform the setup for Xiaomi devices."""

    XIAOMI_GATEWAYS = hass.data['XIAOMI_GATEWAYS']
    for (ip, gateway) in XIAOMI_GATEWAYS.items():
        for device in gateway.XIAOMI_DEVICES['sensor']:
            model = device['model']
            if (model == 'sensor_ht'):
                add_devices([
                    XiaomiSensor(device, 'Temperature', 'temperature', gateway),
                    XiaomiSensor(device, 'Humidity', 'humidity', gateway)])

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

class XiaomiSensor(XiaomiDevice, Entity):
    """Representation of a XiaomiGenericSwitch."""

    def __init__(self, device, name, data_key, xiaomi_hub):
        """Initialize the XiaomiSensor."""
        self.current_value = 0
        self._data_key = data_key
        self._battery = -1
        XiaomiDevice.__init__(self, device, name, xiaomi_hub)

    @property
    def state(self):
        """Return the name of the sensor."""
        return self.current_value

    @property
    def unit_of_measurement(self):
        if self._data_key == 'temperature':
            return TEMP_CELSIUS
        elif self._data_key == 'humidity':
            return '%'

    def parse_data(self, data):
        if not self._data_key in data:
            return False

        value = data[self._data_key]
        self.current_value = int(value) / 100
        return True

    def push_data(self, data):
        """Push from Hub"""
        if self.parse_data(data):
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
        data = self.xiaomi_hub.get_from_hub(self._sid)
        if data is None:
            return
        self.push_data(data)

