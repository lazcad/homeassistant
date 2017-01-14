"""
Support for Xiaomi Gateway Light.

Developed by Rave from Lazcad.com
"""
import logging
import struct
import binascii
from homeassistant.helpers.entity import Entity
from homeassistant.components.light import (
    ATTR_BRIGHTNESS, ATTR_COLOR_TEMP, ATTR_EFFECT,
    ATTR_RGB_COLOR, ATTR_WHITE_VALUE, ATTR_XY_COLOR, SUPPORT_BRIGHTNESS,
    SUPPORT_COLOR_TEMP, SUPPORT_EFFECT, SUPPORT_RGB_COLOR, SUPPORT_WHITE_VALUE,
    Light)

_LOGGER = logging.getLogger(__name__)

def setup_platform(hass, config, add_devices, discovery_info=None):
    """Perform the setup for Xiaomi devices."""

    XIAOMI_GATEWAYS = hass.data['XIAOMI_GATEWAYS']
    for (ip, gateway) in XIAOMI_GATEWAYS.items():
        for device in gateway.XIAOMI_DEVICES['light']:
            model = device['model']
            if (model == 'gateway'):
                add_devices([XiaomiGatewayLight(device, 'Gateway Light', gateway)])

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

class XiaomiGatewayLight(XiaomiDevice, Light):
    """Representation of a XiaomiGatewayLight."""

    def __init__(self, device, name, xiaomi_hub):
        """Initialize the XiaomiGatewayLight."""
        self._data_key = 'rgb'

        self._state = False
        self._rgb = (255,255,255)
        self._ct = None
        self._brightness = 180
        self._xy_color = (.5, .5)
        self._white = 200
        self._effect_list = None
        self._effect = None

        XiaomiDevice.__init__(self, device, name, xiaomi_hub)

    def parse_data(self, data):
        _LOGGER.error('Parsing light data {0}'.format(data))
        if not self._data_key in data:
            return False

        if data['rgb'] == 0:
            if self._state == False:
                return False
            else:
                self._state = False
                return True

        rgbhex = bytes.fromhex("%x" % data['rgb'])
        rgba = struct.unpack('BBBB',rgbhex)
        brightness = rgba[0]
        rgb = rgba[1:]

        self._brightness = brightness
        self._rgb = rgb
        self._state = True

        return True

    def push_data(self, data):
        """Push from Hub"""
        if self.parse_data(data) == True:
            self.schedule_update_ha_state()

    def update(self):
        data = self.xiaomi_hub.get_from_hub(self._sid)
        self.push_data(data)

    @property
    def brightness(self):
        """Return the brightness of this light between 0..255."""
        return self._brightness

    @property
    def xy_color(self):
        """Return the XY color value [float, float]."""
        return self._xy_color

    @property
    def rgb_color(self):
        """Return the RBG color value."""
        return self._rgb

    @property
    def color_temp(self):
        """Return the CT color temperature."""
        return self._ct

    @property
    def white_value(self):
        """Return the white value of this light between 0..255."""
        return self._white

    @property
    def effect_list(self):
        """Return the list of supported effects."""
        return self._effect_list

    @property
    def effect(self):
        """Return the current effect."""
        return self._effect

    @property
    def is_on(self):
        """Return true if light is on."""
        return self._state

    @property
    def supported_features(self):
        return (SUPPORT_BRIGHTNESS | SUPPORT_RGB_COLOR)

    def turn_on(self, **kwargs):
        if ATTR_RGB_COLOR in kwargs:
            self._rgb = kwargs[ATTR_RGB_COLOR]

        if ATTR_BRIGHTNESS in kwargs:
            self._brightness = kwargs[ATTR_BRIGHTNESS]

        rgba = (self._brightness,) + self._rgb
        rgbhex = binascii.hexlify(struct.pack('BBBB',*rgba)).decode("ASCII")
        rgbhex = int(rgbhex, 16)

        if self.xiaomi_hub.write_to_hub(self._sid, self._data_key, rgbhex):
            self._state = True
            self.schedule_update_ha_state()

    def turn_off(self, **kwargs):
        """Turn the light off."""
        if self.xiaomi_hub.write_to_hub(self._sid, self._data_key, 0):
            self._state = False
            self.schedule_update_ha_state()
