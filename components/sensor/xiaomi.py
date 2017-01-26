"""
Support for Xiaomi sensors.

Developed by Rave from Lazcad.com
"""
import logging

from homeassistant.components.xiaomi import XiaomiDevice
from homeassistant.const import TEMP_CELSIUS

_LOGGER = logging.getLogger(__name__)

def setup_platform(hass, config, add_devices, discovery_info=None):
    """Perform the setup for Xiaomi devices."""
    devices = []
    for (ip, gateway) in hass.data['XIAOMI_GATEWAYS']:
        for device in gateway.XIAOMI_DEVICES['sensor']:
            model = device['model']
            if (model == 'sensor_ht'):
                devices.append(XiaomiSensor(device, 'Temperature', 'temperature', gateway))
                devices.append(XiaomiSensor(device, 'Humidity', 'humidity', gateway))
    add_devices(devices)


class XiaomiSensor(XiaomiDevice, Entity):
    """Representation of a XiaomiGenericSwitch."""

    def __init__(self, device, name, data_key, xiaomi_hub):
        """Initialize the XiaomiSensor."""
        self.current_value = 0
        self._data_key = data_key
        self._battery = None
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
