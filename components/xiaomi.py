"""
Support for Xiaomi Gateways.

Developed by Rave from Lazcad.com
"""
import socket
import json
import logging
import struct
import platform
import voluptuous as vol
import homeassistant.helpers.config_validation as cv
from threading import Thread
from collections import defaultdict
from homeassistant.helpers import discovery
from homeassistant.const import EVENT_HOMEASSISTANT_STOP

REQUIREMENTS = ['pyCrypto']

DOMAIN = 'xiaomi'
CONF_GATEWAYS = 'gateways'
CONF_INTERFACE = 'interface'

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Required(CONF_GATEWAYS): cv.ensure_list,
        vol.Optional(CONF_INTERFACE, default='any'): cv.string
    })
}, extra=vol.ALLOW_EXTRA)

XIAOMI_COMPONENTS = ['binary_sensor', 'sensor', 'switch', 'light']

# Shortcut for the logger
_LOGGER = logging.getLogger(__name__)

def setup(hass, config):
    """Set up the Xiaomi component."""

    gateways = config[DOMAIN][CONF_GATEWAYS]
    interface = config[DOMAIN][CONF_INTERFACE]

    for gateway in gateways:
        key = gateway['key']
        if len(key) != 16:
            _LOGGER.error('Invalid key {0}. Key must be 16 characters'.format(key))
            return False

    comp = XiaomiComponent(hass, gateways, interface);

    trycount = 5
    for _ in range(trycount):
        comp.discoverGateways()
        if len(comp.XIAOMI_GATEWAYS) > 0:
            break

    if len(comp.XIAOMI_GATEWAYS) == 0:
        _LOGGER.error("No gateway discovered")
        return False

    if comp.listen():
        _LOGGER.info("Listening for broadcast")

    hass.data['XIAOMI_GATEWAYS'] = comp.XIAOMI_GATEWAYS

    def stop_xiaomi(event):
        _LOGGER.info("Shutting down Xiaomi Hub.")
        comp.stop()
        del hass.data['XIAOMI_GATEWAYS']

    hass.bus.listen_once(EVENT_HOMEASSISTANT_STOP, stop_xiaomi)

    for component in XIAOMI_COMPONENTS:
        discovery.load_platform(hass, component, DOMAIN, {}, config)

    return True

class XiaomiComponent:

    MULTICAST_ADDRESS = '224.0.0.50'
    MULTICAST_PORT = 9898
    GATEWAY_DISCOVERY_PORT = 4321
    SOCKET_BUFSIZE = 1024

    XIAOMI_GATEWAYS = defaultdict(list)

    def __init__(self, hass, gateways_config, interface):

        self.hass = hass
        self._listening = False
        self._mcastsocket = None
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        if interface != 'any':
            self._socket.bind((interface, 0))

        self._threads = []
        self._gateways_config = gateways_config
        self._interface = interface

    def discoverGateways(self):
        _socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        if self._interface != 'any':
            _socket.bind((self._interface, 0))

        try:
            _LOGGER.info('Discovering Xiaomi Gateways')
            _socket.sendto('{"cmd":"whois"}'.encode(), (self.MULTICAST_ADDRESS, self.GATEWAY_DISCOVERY_PORT))
            _socket.settimeout(5.0)

            while True:
                data, addr = _socket.recvfrom(1024)
                if len(data) is None:
                    continue

                resp = json.loads(data.decode())
                if resp["cmd"] != 'iam':
                    _LOGGER.error("Response does not match return cmd")
                    continue

                if resp["model"] != 'gateway':
                    _LOGGER.error("Response must be gateway model")
                    continue

                gatewayKey = '';
                for gateway in self._gateways_config:
                    sid = gateway['sid']
                    key = gateway['key']
                    if sid is None or sid == resp["sid"]:
                        gatewayKey = key

                _LOGGER.info('Xiaomi Gateway {0} found at IP {1}'.format(resp["sid"], resp["ip"]))
                gateway = XiaomiGateway(resp["ip"], resp["port"], resp["sid"], gatewayKey, self._socket)
                self.XIAOMI_GATEWAYS[resp["ip"]] = gateway

        except socket.timeout:
            _LOGGER.info("Gateway finding finished in 5 seconds")
            _socket.close()

    def _create_mcast_socket(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        if self._interface != 'any':
            if platform.system() != "Windows":
                sock.bind((self.MULTICAST_ADDRESS, self.MULTICAST_PORT))
            else:
                sock.bind((self._interface, self.MULTICAST_PORT))

            mreq = socket.inet_aton(self.MULTICAST_ADDRESS) + socket.inet_aton(self._interface)
        else:
            sock.bind((self.MULTICAST_ADDRESS, self.MULTICAST_PORT))
            mreq = struct.pack("4sl", socket.inet_aton(self.MULTICAST_ADDRESS), socket.INADDR_ANY)

        sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        return sock

    def listen(self):

        _LOGGER.info('Creating Multicast Socket')
        self._mcastsocket = self._create_mcast_socket()

        """Start listening."""
        self._listening = True

        t = Thread(target=self._listen_to_msg, args=())
        self._threads.append(t)
        t.daemon = True
        t.start()

        return True

    def stop(self):
        """Stop listening."""
        self._listening = False

        if self._socket is not None:
            _LOGGER.info('Closing socket')
            self._socket.close()
            self._socket = None

        if self._mcastsocket is not None:
            _LOGGER.info('Closing multisocket')
            self._mcastsocket.close()
            self._mcastsocket = None

        for t in self._threads:
            t.join()

    def _listen_to_msg(self):
        while self._listening:
            if self._mcastsocket is None:
                continue
            data, (ip, port) = self._mcastsocket.recvfrom(self.SOCKET_BUFSIZE)
            try:
                data = json.loads(data.decode("ascii"))
                gateway = self.XIAOMI_GATEWAYS.get(ip)
                if gateway is None:
                    _LOGGER.error('Unknown gateway ip {0}'.format(ip))
                    continue

                cmd = data['cmd']
                if cmd == 'heartbeat' and data['model'] == 'gateway':
                    gateway.GATEWAY_TOKEN = data['token']
                elif cmd == 'report' or cmd == 'heartbeat':
                    self.hass.add_job(self._push_data, gateway, data)
                else:
                    _LOGGER.error('Unknown multicast data : {0}'.format(data))
            except Exception:
                _LOGGER.error('Cannot process multicast message : {0}'.format(data))
                raise

    def _push_data(self, gateway, data):
        jdata = json.loads(data['data'])
        if jdata is None:
            return
        sid = data['sid']
        for device in gateway.XIAOMI_HA_DEVICES[sid]:
            device.push_data(jdata)

class XiaomiGateway:

    def __init__(self, ip, port, sid, key, socket):

        self.GATEWAY_IP = ip
        self.GATEWAY_PORT = int(port)
        self.GATEWAY_SID = sid
        self.GATEWAY_KEY = key
        self.GATEWAY_TOKEN = None
        self.XIAOMI_DEVICES = defaultdict(list)
        self.XIAOMI_HA_DEVICES = defaultdict(list)

        self._socket = socket

        trycount = 5
        for _ in range(trycount):
            _LOGGER.info('Discovering Xiaomi Devices')
            if self._discover_devices():
                break

    def _discover_devices(self):

        cmd = '{"cmd" : "get_id_list"}'
        resp = self._send_cmd(cmd, "get_id_list_ack")
        if resp is None:
            return False
        self.GATEWAY_TOKEN = resp["token"]
        sids = json.loads(resp["data"])
        sids.append(self.GATEWAY_SID)

        _LOGGER.info('Found {0} devices'.format(len(sids)))

        sensors = ['sensor_ht']
        binary_sensors = ['magnet', 'motion', 'switch', '86sw1', '86sw2', 'cube']
        switches = ['plug', 'ctrl_neutral1', 'ctrl_neutral2']
        lights = ['gateway']

        for sid in sids:
            cmd = '{"cmd":"read","sid":"' + sid + '"}'
            resp = self._send_cmd(cmd, "read_ack")
            if resp is None:
                continue
            data = json.loads(resp["data"])
            if "error" in data:
                _LOGGER.error("Not a device")
                continue

            model = resp["model"]

            xiaomi_device = {
                "model":model,
                "sid":resp["sid"],
                "short_id":resp["short_id"],
                "data":data}

            device_type = None
            if model in sensors:
                device_type = 'sensor'
            elif model in binary_sensors:
                device_type = 'binary_sensor'
            elif model in switches:
                device_type = 'switch'
            elif model in lights:
                device_type = 'light'

            if device_type is None:
                _LOGGER.error('Unsupported devices : {0}'.format(model))
            else:
                self.XIAOMI_DEVICES[device_type].append(xiaomi_device)
        return True

    def _send_cmd(self, cmd, rtnCmd):
        try:
            self._socket.settimeout(10.0)
            self._socket.sendto(cmd.encode(), (self.GATEWAY_IP, self.GATEWAY_PORT))
            self._socket.settimeout(10.0)
            data, addr = self._socket.recvfrom(1024)
            if data is None:
                _LOGGER.error("No response from Gateway")
                return
            resp = json.loads(data.decode())
            if resp['cmd'] == rtnCmd:
                return resp
            else:
                _LOGGER.error("Response does not match return cmd. Expected {0}".format(resp['cmd']))
        except socket.timeout:
            _LOGGER.error("Cannot connect to Gateway")
            return

    def write_to_hub(self, sid, data_key, datavalue):
        key = self._get_key()
        data = {}
        data[data_key] = datavalue
        data['key'] = key
        cmd = {}
        cmd['cmd'] = 'write'
        cmd['sid'] = sid
        cmd['data'] = data
        cmd = json.dumps(cmd)
        resp = self._send_cmd(cmd, "write_ack")
        if resp is None or 'data' not in resp:
            return False
        data = resp['data']
        if 'error' in data:
            _LOGGER.error('Invalid Key')
            return False

        return True

    def get_from_hub(self, sid):
        cmd = '{ "cmd":"read","sid":"' + sid + '"}'
        resp = self._send_cmd(cmd, "read_ack")
        if resp is None or "data" not in resp:
            _LOGGER.error('No data in response from hub {0}'.format(resp))
            return
        data = resp["data"]
        try:
            return json.loads(resp["data"])
        except Exception:
            _LOGGER.error('Cannot process message got from hub : {0}'.format(data))

    def _get_key(self):
        from Crypto.Cipher import AES
        IV = bytes(bytearray.fromhex('17996d093d28ddb3ba695a2e6f58562e'))
        encryptor = AES.new(self.GATEWAY_KEY, AES.MODE_CBC, IV=IV)
        ciphertext = encryptor.encrypt(self.GATEWAY_TOKEN)
        return ''.join('{:02x}'.format(x) for x in ciphertext)
