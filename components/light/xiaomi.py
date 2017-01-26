"""
Support for Xiaomi Gateway Light.

Developed by Rave from Lazcad.com
"""
import logging
import struct
import binascii
from homeassistant.components.xiaomi import XiaomiDevice
from homeassistant.components.light import (
    ATTR_BRIGHTNESS, ATTR_COLOR_TEMP, ATTR_EFFECT,
    ATTR_RGB_COLOR, ATTR_WHITE_VALUE, ATTR_XY_COLOR, SUPPORT_BRIGHTNESS,
    SUPPORT_COLOR_TEMP, SUPPORT_EFFECT, SUPPORT_RGB_COLOR, SUPPORT_WHITE_VALUE,
    Light)

_LOGGER = logging.getLogger(__name__)

def setup_platform(hass, config, add_devices, discovery_info=None):
    """Perform the setup for Xiaomi devices."""
    devices = []
    for (ip, gateway) in hass.data['XIAOMI_GATEWAYS']:
        for device in gateway.XIAOMI_DEVICES['light']:
            model = device['model']
            if (model == 'gateway'):
                devices.append(XiaomiGatewayLight(device, 'Gateway Light', gateway))
    add_devices(devices)


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
        if self._data_key not in data:
            return False

        if data[self._data_key] == 0:
            if not self._state:
                return False
            else:
                self._state = False
                return True

        rgbhexstr = "%x" % data[self._data_key]
        if len(rgbhexstr) == 7:
            # fromhex can't deal with odd strings
            rgbhexstr = '0' + rgbhexstr

        rgbhex = bytes.fromhex(rgbhexstr)
        rgba = struct.unpack('BBBB',rgbhex)
        brightness = rgba[0]
        rgb = rgba[1:]

        self._brightness = int(255 * brightness / 100)
        self._rgb = rgb
        self._state = True

        return True

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
            self._brightness = int(100 * kwargs[ATTR_BRIGHTNESS] / 255)

        rgba = (self._brightness,) + self._rgb
        rgbhex = binascii.hexlify(struct.pack('BBBB',*rgba)).decode("ASCII")
        rgbhex = int(rgbhex, 16)

        if self.xiaomi_hub.write_to_hub(self._sid, self._data_key, rgbhex):
            self._state = True

    def turn_off(self, **kwargs):
        """Turn the light off."""
        if self.xiaomi_hub.write_to_hub(self._sid, self._data_key, 0):
            self._state = False
