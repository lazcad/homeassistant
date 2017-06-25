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
                temp_info = SensorInfo('Temperature', 'temperature', TEMP_CELSIUS, 100, 0, 0.01)
                humi_info = SensorInfo('Humidity', 'humidity', '%', 100, 0, 0.01)
                devices.append(XiaomiSensor(device, temp_info, gateway))
                devices.append(XiaomiSensor(device, humi_info, gateway))
            elif device['model'] == 'gateway':
                illu_info = SensorInfo('Illuminance', 'illumination', 'lx', 100000, 0, 1)
                devices.append(XiaomiSensor(device, illu_info, gateway))
    add_devices(devices)

class SensorInfo(object):
    """Xiaomi Sensor info"""
    def __init__(self, name, data_key, units, max_value, min_value, value_modifier):
        self.name = name
        self.data_key = data_key
        self.units = units
        self.max = max_value
        self.min = min_value
        self.value_modifier = value_modifier

class XiaomiSensor(XiaomiDevice):
    """Representation of a XiaomiSensor."""

    def __init__(self, device, sensor_info, xiaomi_hub):
        """Initialize the XiaomiSensor."""
        self.current_value = None
        self._data_key = sensor_info.data_key
        self._battery = None
        self._units = sensor_info.units
        self._max = sensor_info.max
        self._min = sensor_info.min
        self._value_modifier = sensor_info.value_modifier

        XiaomiDevice.__init__(self, device, sensor_info.name, xiaomi_hub)

    @property
    def available(self):
        """Return True if entity is available."""
        return self.current_value > self._min and self.current_value < self._max

    @property
    def state(self):
        """Return the name of the sensor."""
        return self.current_value

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement of this entity, if any."""
        return self._units

    def parse_data(self, data):
        """Parse data sent by gateway"""
        value = data.get(self._data_key)
        if value is None:
            return False

        self.current_value = int(value) * self._value_modifier
        return True
