"""
Support for Xiaomi Gateway Light.

Developed by Rave from Lazcad.com
"""
import logging
import struct
import binascii
try:
    from homeassistant.components.xiaomi import XiaomiDevice
except ImportError:
    from custom_components.xiaomi import XiaomiDevice
from homeassistant.components.light import (
    ATTR_BRIGHTNESS, ATTR_COLOR_TEMP, ATTR_EFFECT,
    ATTR_RGB_COLOR, ATTR_WHITE_VALUE, ATTR_XY_COLOR, SUPPORT_BRIGHTNESS,
    SUPPORT_COLOR_TEMP, SUPPORT_EFFECT, SUPPORT_RGB_COLOR, SUPPORT_WHITE_VALUE,
    Light)

_LOGGER = logging.getLogger(__name__)

def setup_platform(hass, config, add_devices, discovery_info=None):
    """Perform the setup for Xiaomi devices."""
    devices = []
    XIAOMI_GATEWAYS = hass.data['XIAOMI_GATEWAYS']
    for (ip, gateway) in XIAOMI_GATEWAYS.items():
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
        self._brightness = 180

        XiaomiDevice.__init__(self, device, name, xiaomi_hub)

    def parse_data(self, data):
        value = data.get(self._data_key)
        if value is None:
            return False

        if value == 0:
            if self._state:
                return False
            else:
                self._state = False
                return True

        rgbhexstr = "%x" % value
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
    def rgb_color(self):
        """Return the RBG color value."""
        return self._rgb

    @property
    def brightness(self):
        """Return the brightness of this light between 0..255."""
        return self._brightness

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
