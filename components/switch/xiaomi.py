"""
Support for Xiaomi binary sensors.

Developed by Rave from Lazcad.com
"""
import logging

from homeassistant.helpers.entity import Entity
from homeassistant.components.switch import (SwitchDevice)

_LOGGER = logging.getLogger(__name__)

def setup_platform(hass, config, add_devices, discovery_info=None):
    """Perform the setup for Xiaomi devices."""

    XIAOMI_GATEWAYS = hass.data['XIAOMI_GATEWAYS']

    for ip, gateway in XIAOMI_GATEWAYS.items():
        for device in gateway.XIAOMI_DEVICES['switch']:
            model = device['model']
            if (model == 'plug'):
                add_devices([XiaomiGenericSwitch(device, "Plug", 'status', gateway)])
            elif (model == 'ctrl_neutral1'):
                add_devices([XiaomiGenericSwitch(device, 'Wall Switch', 'channel_0', gateway)])
            elif (model == 'ctrl_neutral2'):
                add_devices([
                    XiaomiGenericSwitch(device, 'Wall Switch Left','channel_0', gateway), 
                    XiaomiGenericSwitch(device, 'Wall Switch Right', 'channel_1', gateway)])

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
            self.schedule_update_ha_state()

    def turn_off(self):
        """Turn the switch off."""
        if self.xiaomi_hub.write_to_hub(self._sid, self._data_key, 'off'):
            self._state = False
            self.schedule_update_ha_state()

    def toggle(self):
        if self._state == False:
            self.turn_on()
        else:
            self.turn_off()

    def parse_data(self, data):
        if not self._data_key in data:
            return False

        state = True if data[self._data_key] == 'on' else False
        if self._state == state:
            return False
        else:
            self._state = state
            return True

    def push_data(self, data):
        """Push from Hub"""
        if self.parse_data(data) == True:
            self.schedule_update_ha_state()

    def update(self):
        data = self.xiaomi_hub.get_from_hub(self._sid)
        self.push_data(data)
