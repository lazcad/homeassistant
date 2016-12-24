"""
Support for Xiaomi binary sensors.

"""
import logging

from homeassistant.components.switch import (SwitchDevice)
from homeassistant.components.xiaomi import (XiaomiDevice, XIAOMI_HUB)

_LOGGER = logging.getLogger(__name__)

def setup_platform(hass, config, add_devices, discovery_info=None):
    """Perform the setup for Xiaomi devices."""
    
    for resp in XIAOMI_HUB.XIAOMI_DEVICES['switch']:
        model = resp['model']
        if (model == 'plug'):
            add_devices([XiaomiGenericSwitch(resp, "Plug", 'status', XIAOMI_HUB)])
        elif (model == 'ctrl_neutral1'):
            add_devices([XiaomiGenericSwitch(resp, 'Wall Switch', 'channel_0', XIAOMI_HUB)])
        elif (model == 'ctrl_neutral2'):
            add_devices([
                XiaomiGenericSwitch(resp, 'Wall Switch Left','channel_0', XIAOMI_HUB), 
                XiaomiGenericSwitch(resp, 'Wall Switch Right', 'channel_1', XIAOMI_HUB)])

class XiaomiGenericSwitch(XiaomiDevice, SwitchDevice):
    """Representation of a XiaomiPlug."""

    def __init__(self, resp, name, dataKey, xiaomiHub):
        """Initialize the XiaomiPlug."""
        self._state = False
        self._dataKey = dataKey
        XiaomiDevice.__init__(self, resp, name, xiaomiHub)

    @property
    def icon(self):
        if self._dataKey == 'status':
           return 'mdi:power-plug'
        else:
            return 'mdi:power-socket'

    @property
    def is_on(self):
        """Return true if plug is on."""
        return self._state

    def turn_on(self, **kwargs):    
        """Turn the switch on."""
        self._state = True
        self.xiaomiHub.sendDataToHub(self._sid, self._dataKey, 'on')
        self.schedule_update_ha_state()

    def turn_off(self):
        """Turn the switch off."""
        self._state = False
        self.xiaomiHub.sendDataToHub(self._sid, self._dataKey, 'off')
        self.schedule_update_ha_state()

    def toggle(self):
        if self._state == False:
            self.turn_on()
        else:
            self.turn_off()

    def parseStatus(self, data):
        state = True if data[self._dataKey] == 'on' else False
        
        if self._state == state:
            return False
        else:
            self._state = state
            return True

    def pushData(self, data):
        if self._dataKey in data and self.parseStatus(data) == True:
            self.schedule_update_ha_state()
