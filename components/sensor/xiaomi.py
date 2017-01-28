"""
Support for Xiaomi sensors.

Developed by Rave from Lazcad.com
"""
import logging

try:
    from homeassistant.components.xiaomi import XiaomiDevice
except ImportError:
    from custom_components.xiaomi import XiaomiDevice
from homeassistant.const import TEMP_CELSIUS

_LOGGER = logging.getLogger(__name__)

def setup_platform(hass, config, add_devices, discovery_info=None):
    """Perform the setup for Xiaomi devices."""
    devices = []
    XIAOMI_GATEWAYS = hass.data['XIAOMI_GATEWAYS']
    for (ip, gateway) in XIAOMI_GATEWAYS.items():
        for device in gateway.XIAOMI_DEVICES['sensor']:
            if device['model'] == 'sensor_ht':
                devices.append(XiaomiSensor(device, 'Temperature', 'temperature', gateway))
                devices.append(XiaomiSensor(device, 'Humidity', 'humidity', gateway))
    add_devices(devices)


class XiaomiSensor(XiaomiDevice):
    """Representation of a XiaomiGenericSwitch."""

    def __init__(self, device, name, data_key, xiaomi_hub):
        """Initialize the XiaomiSensor."""
        self.current_value = None
        self._data_key = data_key
        self._battery = None
        XiaomiDevice.__init__(self, device, name, xiaomi_hub)

    @property
    def should_poll(self):
        return False

    @property
    def is_humidity(self):
        return self._data_key == 'humidity'

    @property
    def is_temperature(self):
        return self._data_key == 'temperature'

    @property
    def available(self):
        if self.is_temperature and self.current_value != 100:
            return True
        elif self.is_humidity and self.current_value != 0:
            return True

        return False

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
        value = data.get(self._data_key)
        if value is None:
            return False
        self.current_value = int(value) / 100
        return True
