"""
Support for Xiaomi sensors.

Developed by Rave from Lazcad.com
"""
import logging

try:
    from homeassistant.components.xiaomi import (PY_XIAOMI_GATEWAY, XiaomiDevice)
except ImportError:
    from custom_components.xiaomi import (PY_XIAOMI_GATEWAY, XiaomiDevice)
from homeassistant.const import TEMP_CELSIUS

_LOGGER = logging.getLogger(__name__)

def setup_platform(hass, config, add_devices, discovery_info=None):
    """Perform the setup for Xiaomi devices."""
    devices = []
    gateways = PY_XIAOMI_GATEWAY.gateways
    for (ip_add, gateway) in gateways.items():
        for device in gateway.devices['sensor']:
            if device['model'] == 'sensor_ht':
                devices.append(XiaomiSensor(device, 'Temperature', 'temperature', gateway))
                devices.append(XiaomiSensor(device, 'Humidity', 'humidity', gateway))
            if device['model'] == 'natgas':
                devices.append(XiaomiSensor(device, 'Gas', 'density', gateway))
    add_devices(devices)


class XiaomiSensor(XiaomiDevice):
    """Representation of a XiaomiSensor."""

    def __init__(self, device, name, data_key, xiaomi_hub):
        """Initialize the XiaomiSensor."""
        self.current_value = None
        self._data_key = data_key
        self._battery = None
        XiaomiDevice.__init__(self, device, name, xiaomi_hub)

    @property
    def _is_humidity(self):
        return self._data_key == 'humidity'

    @property
    def _is_temperature(self):
        return self._data_key == 'temperature'

    @property
    def _is_gas(self):
        return self._data_key == 'density'

    @property
    def available(self):
        """Return True if entity is available."""
        if self._is_temperature and self.current_value != 100:
            return True
        elif self._is_humidity and self.current_value != 0:
            return True

        return False

    @property
    def state(self):
        """Return the name of the sensor."""
        return self.current_value

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement of this entity, if any."""
        if self._data_key == 'temperature':
            return TEMP_CELSIUS
        elif self._data_key == 'humidity':
            return '%'
        elif self._data_key == 'density':
            return '%'

    def parse_data(self, data):
        """Parse data sent by gateway"""
        value = data.get(self._data_key)
        if value is None:
            return False
        if self._data_key == 'density':
            self.current_value = int(value)
        else:
            self.current_value = int(value) / 100
        return True
