"""
Support for Xiaomi binary sensors.

Developed by Rave from Lazcad.com
"""
import logging
import asyncio

from homeassistant.components.binary_sensor import BinarySensorDevice
try:
    from homeassistant.components.xiaomi import XiaomiDevice
except ImportError:
    from custom_components.xiaomi import XiaomiDevice

_LOGGER = logging.getLogger(__name__)


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Perform the setup for Xiaomi devices."""

    devices = []
    for (ip, gateway) in hass.data['XIAOMI_GATEWAYS'].items():
        for device in gateway.XIAOMI_DEVICES['binary_sensor']:
            model = device['model']
            if (model == 'motion'):
                devices.append(XiaomiMotionSensor(device, hass, gateway))
            elif (model == 'magnet'):
                devices.append(XiaomiDoorSensor(device, gateway))
            elif (model == 'switch'):
                devices.append(XiaomiButton(device, 'Switch', 'status', hass, gateway))
            elif (model == '86sw1'):
                devices.append(XiaomiButton(device, 'Wall Switch', 'channel_0', hass, gateway))
            elif (model == '86sw2'):
                devices.append(XiaomiButton(device, 'Wall Switch (Left)', 'channel_0', hass, gateway))
                devices.append(XiaomiButton(device, 'Wall Switch (Right)', 'channel_1', hass, gateway))
            elif (model == 'cube'):
                devices.append(XiaomiCube(device, hass, gateway))
    add_devices(devices)


class XiaomiMotionSensor(XiaomiDevice, BinarySensorDevice):
    """Representation of a XiaomiMotionSensor."""

    def __init__(self, device, hass, xiaomi_hub):
        """Initialize the XiaomiMotionSensor."""
        self._state = False
        self._hass = hass
        self._data_key = 'status'
        XiaomiDevice.__init__(self, device, 'Motion Sensor', xiaomi_hub)

    @property
    def sensor_class(self):
        return 'motion'

    @property
    def is_on(self):
        """Return true if sensor is on."""
        return self._state

    def parse_data(self, data):
        if 'no_motion' in data:
            if self._state:
                self._state = False
                return True
            else:
                return False

        if self._data_key not in data:
            return False
        value = data[self._data_key]
        if value == 'motion':
            self._hass.loop.create_task(self.async_poll_status())
            if self._state:
                return False
            else:
                self._state = True
                return True
        elif value == 'no_motion':
            if not self._state:
                return False
            else:
                self._state = False
                return True

    @asyncio.coroutine
    def async_poll_status(self):
        yield from asyncio.sleep(10)
        if not self.xiaomi_hub.get_from_hub(self._sid) and self._state:
            self._state = False
            self.schedule_update_ha_state()


class XiaomiDoorSensor(XiaomiDevice, BinarySensorDevice):
    """Representation of a XiaomiDoorSensor."""

    def __init__(self, device, xiaomi_hub):
        """Initialize the XiaomiDoorSensor."""
        self._state = False
        self._data_key = 'status'
        XiaomiDevice.__init__(self, device, 'Door Window Sensor', xiaomi_hub)

    @property
    def sensor_class(self):
        return 'opening'

    @property
    def is_on(self):
        """Return true if sensor is on."""
        return self._state

    def parse_data(self, data):
        if self._data_key not in data:
            return False

        value = data[self._data_key]
        if value == 'open' or value == 'no_close':
            if self._state:
                return False
            else:
                self._state = True
                return True
        elif value == 'close':
            if self._state:
                self._state = False
                return True
            else:
                return False


class XiaomiButton(XiaomiDevice, BinarySensorDevice):

    def __init__(self, device, name, data_key, hass, xiaomi_hub):
        """Initialize the XiaomiButton."""
        self._is_down = False
        self._hass = hass
        self._data_key = data_key
        XiaomiDevice.__init__(self, device, name, xiaomi_hub)

    @property
    def is_on(self):
        """Return true if sensor is on."""
        return self._is_down

    def parse_data(self, data):
        if self._data_key not in data:
            return False

        state = data[self._data_key]
        if state == 'long_click_press':
            self._is_down = True
            click_type = 'long_click_press'
        elif state == 'long_click_release':
            self._is_down = False
            click_type = 'hold'
        elif state == 'click':
            click_type = 'single'
        elif state == 'double_click':
            click_type = 'double'

        self._hass.bus.fire('click', {
            'entity_id': self.entity_id,
            'click_type': click_type
        })
        if state in ('long_click_press', 'long_click_release'):
            return True
        return False


class XiaomiCube(XiaomiDevice, BinarySensorDevice):

    STATUS = 'status'
    ROTATE = 'rotate'
    # flip90, flip180, move, tap_twice, shake_air, swing, alert

    def __init__(self, device, hass, xiaomi_hub):
        """Initialize the XiaomiButton."""
        self._hass = hass
        XiaomiDevice.__init__(self, device, 'Cube', xiaomi_hub)

    @property
    def is_on(self):
        """Return true if sensor is on."""
        return False

    def parse_data(self, data):
        """Push from Hub"""
        print(data)
        if self.STATUS in data:
            self._hass.bus.fire('cube_action', {
                'entity_id': self.entity_id,
                'action_type': data[self.STATUS]
            })

        if self.ROTATE in data:
            self._hass.bus.fire('cube_action', {
                'entity_id': self.entity_id,
                'action_type': self.ROTATE,
                'action_value': data[self.ROTATE]
            })

        return False
