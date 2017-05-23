"""
Support for Xiaomi binary sensors.

Developed by Rave from Lazcad.com
"""
import logging

from homeassistant.components.switch import SwitchDevice
try:
    from homeassistant.components.xiaomi import (PY_XIAOMI_GATEWAY, XiaomiDevice)
except ImportError:
    from custom_components.xiaomi import (PY_XIAOMI_GATEWAY, XiaomiDevice)

_LOGGER = logging.getLogger(__name__)

ATTR_LOAD_POWER = 'Load power' # Load power in watts (W)
ATTR_POWER_CONSUMED = 'Power consumed' #Load power consumption in kilowatt hours (kWh)
ATTR_IN_USE = 'In use'
LOAD_POWER = 'load_power'
POWER_CONSUMED = 'power_consumed'
IN_USE = 'inuse'

def setup_platform(hass, config, add_devices, discovery_info=None):
    """Perform the setup for Xiaomi devices."""
    devices = []
    gateways = PY_XIAOMI_GATEWAY.gateways
    for (ip_add, gateway) in gateways.items():
        for device in gateway.devices['switch']:
            model = device['model']
            if model == 'plug':
                devices.append(XiaomiGenericSwitch(device, "Plug", 'status', gateway))
            elif model == 'ctrl_neutral1':
                devices.append(XiaomiGenericSwitch(device, 'Wall Switch', 'channel_0', gateway))
            elif model == 'ctrl_neutral2':
                devices.append(XiaomiGenericSwitch(device, 'Wall Switch Left', 'channel_0', gateway))
                devices.append(XiaomiGenericSwitch(device, 'Wall Switch Right', 'channel_1', gateway))
            elif (model == '86plug'):
                devices.append(XiaomiGenericSwitch(device, 'Wall Plug', 'status', gateway))
    add_devices(devices)


class XiaomiGenericSwitch(XiaomiDevice, SwitchDevice):
    """Representation of a XiaomiPlug."""

    def __init__(self, device, name, data_key, xiaomi_hub):
        """Initialize the XiaomiPlug."""
        self._state = False
        self._data_key = data_key
        self._in_use = False
        self._load_power = 0
        self._power_consumed = 0
        XiaomiDevice.__init__(self, device, name, xiaomi_hub)

    @property
    def icon(self):
        """Return the icon to use in the frontend, if any."""
        if self._data_key == 'status':
            return 'mdi:power-plug'
        else:
            return 'mdi:power-socket'

    @property
    def is_on(self):
        """Return true if plug is on."""
        return self._state

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        attrs = {ATTR_IN_USE: self._in_use,
                 ATTR_LOAD_POWER: self._load_power,
                 ATTR_POWER_CONSUMED: self._power_consumed}
        attrs.update(super().device_state_attributes)
        return attrs
    def turn_on(self, **kwargs):
        """Turn the switch on."""
        self.xiaomi_hub.write_to_hub(self._sid, self._data_key, 'on')

    def turn_off(self):
        """Turn the switch off."""
        self.xiaomi_hub.write_to_hub(self._sid, self._data_key, 'off')

    def parse_data(self, data):
        """Parse data sent by gateway"""
        if IN_USE in data:
            self._in_use = int(data[IN_USE])
            if not self._in_use:
                self._load_power = 0

        if POWER_CONSUMED in data:
            self._power_consumed = int(data[POWER_CONSUMED])

        if LOAD_POWER in data:
            self._load_power = int(data[LOAD_POWER])

        value = data.get(self._data_key)
        if value is None:
            return False

        state = value == 'on'
        if self._state == state:
            return False
        else:
            self._state = state
            return True
