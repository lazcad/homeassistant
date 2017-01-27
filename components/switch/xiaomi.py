"""
Support for Xiaomi binary sensors.

Developed by Rave from Lazcad.com
"""
import logging

from homeassistant.components.switch import SwitchDevice
try:
    from homeassistant.components.xiaomi import XiaomiDevice
except ImportError:
    from custom_components.xiaomi import XiaomiDevice

_LOGGER = logging.getLogger(__name__)

def setup_platform(hass, config, add_devices, discovery_info=None):
    """Perform the setup for Xiaomi devices."""

    devices = []
    for ip, gateway in hass.data['XIAOMI_GATEWAYS']:
        for device in gateway.XIAOMI_DEVICES['switch']:
            model = device['model']
            if (model == 'plug'):
                devices.append(XiaomiGenericSwitch(device, "Plug", 'status', gateway))
            elif (model == 'ctrl_neutral1'):
                devices.append(XiaomiGenericSwitch(device, 'Wall Switch', 'channel_0', gateway))
            elif (model == 'ctrl_neutral2'):
                devices.append(XiaomiGenericSwitch(device, 'Wall Switch Left','channel_0', gateway))
                devices.append(XiaomiGenericSwitch(device, 'Wall Switch Right', 'channel_1', gateway))
    add_devices(devices)


class XiaomiGenericSwitch(XiaomiDevice, SwitchDevice):
    """Representation of a XiaomiPlug."""

    def __init__(self, device, name, data_key, xiaomi_hub):
        """Initialize the XiaomiPlug."""
        self._state = False
        self._data_key = data_key
        XiaomiDevice.__init__(self, device, name, xiaomi_hub)

    @property
    def icon(self):
        if self._data_key == 'status':
            return 'mdi:power-plug'
        else:
            return 'mdi:power-socket'

    @property
    def is_on(self):
        """Return true if plug is on."""
        return self._state

    def turn_on(self, **kwargs):
        """Turn the switch on."""
        if self.xiaomi_hub.write_to_hub(self._sid, self._data_key, 'on'):
            self._state = True

    def turn_off(self):
        """Turn the switch off."""
        if self.xiaomi_hub.write_to_hub(self._sid, self._data_key, 'off'):
            self._state = False

    def parse_data(self, data):
        if self._data_key not in data:
            return False

        state = data[self._data_key] == 'on'
        if self._state == state:
            return False
        else:
            self._state = state
            return True
