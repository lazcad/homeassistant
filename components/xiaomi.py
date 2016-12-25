"""
Support for Xiaomi hubs.

"""
import socket
import json
import logging
import struct
import voluptuous as vol
import homeassistant.helpers.config_validation as cv
from Crypto.Cipher import AES
from threading import Thread
from queue import Queue
from collections import defaultdict
from homeassistant.helpers import discovery
from homeassistant.helpers.entity import Entity
from homeassistant.const import (EVENT_HOMEASSISTANT_START, EVENT_HOMEASSISTANT_STOP)

REQUIREMENTS = ['pyCrypto==2.6.1']

DOMAIN = 'xiaomi'
CONF_KEY = 'key'

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Required(CONF_KEY): cv.string
    })
}, extra=vol.ALLOW_EXTRA)

XIAOMI_COMPONENTS = ['binary_sensor', 'sensor', 'switch']
XIAOMI_HUB = None

# Shortcut for the logger
_LOGGER = logging.getLogger(__name__)

def setup(hass, config):
    """Set up the Xiaomi component."""

    key = config[DOMAIN][CONF_KEY]

    global XIAOMI_HUB
    XIAOMI_HUB = XiaomiHub(key)

    if XIAOMI_HUB is None:
        _LOGGER.error("Could not connect to Xiaomi Hub")
        return False

    def stop_xiaomi(event):
        _LOGGER.info("Shutting down Xiaomi Hub.")
        XIAOMI_HUB.stop()

    hass.bus.listen_once(EVENT_HOMEASSISTANT_STOP, stop_xiaomi)

    # Load components for the devices in Xiaomi Hub
    for component in XIAOMI_COMPONENTS:
        discovery.load_platform(hass, component, DOMAIN, {}, config)

    return True

class XiaomiHub:

    GATEWAY_KEY = None
    GATEWAY_IP = None
    GATEWAY_PORT = None
    GATEWAY_SID = None
    GATEWAY_TOKEN = None
    XIAOMI_DEVICES = defaultdict(list)
    XIAOMI_HA_DEVICES = defaultdict(list)

    MULTICAST_ADDRESS = '224.0.0.50'
    MULTICAST_PORT = 9898
    GATEWAY_DISCOVERY_PORT = 4321
    SOCKET_BUFSIZE = 1024

    def __init__(self, key):
        self.GATEWAY_KEY = key
        self._listening = False
        self._queue = None
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._mcastsocket = None
        self._deviceCallbacks = defaultdict(list)
        self._threads = []

        try:
            resp = self._send_socket('{"cmd":"whois"}', "iam", self.MULTICAST_ADDRESS, self.GATEWAY_DISCOVERY_PORT)
            if resp["model"] == "gateway":
                self.GATEWAY_IP = resp["ip"]
                self.GATEWAY_PORT = int(resp["port"])
                self.GATEWAY_SID = resp["sid"]
            else:
                _LOGGER.error("Error with gateway response")
        except Exception as e:
            raise
            _LOGGER.error("Cannot discover hub using whois: {0}".format(e))

        if self.GATEWAY_IP is None:
            return None

        self._mcastsocket = self._create_mcast_socket()
        if self._listen() is True:
            _LOGGER.info("Listening")

        self._discover_devices()


    def _discover_devices(self):

        cmd = '{"cmd" : "get_id_list"}'
        resp = self._send_cmd(cmd, "get_id_list_ack")
        self.GATEWAY_TOKEN = resp["token"]
        sids = json.loads(resp["data"])
        
        for sid in sids:
            cmd = '{"cmd":"read","sid":"' + sid + '"}'
            resp = self._send_cmd(cmd, "read_ack")
            model = resp["model"]
            xiaomiDevice = {
                "model":resp["model"], 
                "sid":resp["sid"], 
                "short_id":resp["short_id"], 
                "data":json.loads(resp["data"])}

            if model == 'sensor_ht':
                self.XIAOMI_DEVICES['sensor'].append(resp)
            elif model == 'magnet':
                self.XIAOMI_DEVICES['binary_sensor'].append(resp)
            elif model == 'motion':
                self.XIAOMI_DEVICES['binary_sensor'].append(resp)
            elif model == 'switch':
                self.XIAOMI_DEVICES['binary_sensor'].append(resp)
            elif model == '86sw1':
                self.XIAOMI_DEVICES['binary_sensor'].append(resp)
            elif model == '86sw2':
                self.XIAOMI_DEVICES['binary_sensor'].append(resp)
            elif model == 'plug':
                self.XIAOMI_DEVICES['switch'].append(resp)
            elif model == 'ctrl_neutral1':
                self.XIAOMI_DEVICES['switch'].append(resp)
            elif model == 'ctrl_neutral2':
                self.XIAOMI_DEVICES['switch'].append(resp)

    def _send_cmd(self, cmd, rtnCmd):
        return self._send_socket(cmd, rtnCmd, self.GATEWAY_IP, self.GATEWAY_PORT)

    def _send_socket(self, cmd, rtnCmd, ip, port):
        socket = self._socket
        try:
            socket.sendto(cmd.encode(), (ip, port))
            data, addr = socket.recvfrom(1024)
            if len(data) is not None:
                resp = json.loads(data.decode())
                if resp["cmd"] == rtnCmd:
                    return resp
                else:
                    _LOGGER.error("Response does not match return cmd")
            else:
                _LOGGER.error("No response from Gateway")
        except socket.timeout:
            _LOGGER.error("Cannot connect to Gateway")
            socket.close()

    def write_to_hub(self, sid, datakey, datavalue):
        key = self._get_key()
        cmd = '{ "cmd":"write","sid":"' + sid + '","data":"{"' + datakey + '":"' + datavalue + '","key":"' + key + '"}}'
        return self._send_cmd(cmd, "write_ack")     

    def get_from_hub(self, sid):
        cmd = '{ "cmd":"read","sid":"' + sid + '"}'
        return self._send_cmd(cmd, "read_ack")     

    def _get_key(self):
        key = self.GATEWAY_KEY
        IV = bytes(bytearray.fromhex("17996d093d28ddb3ba695a2e6f58562e"))
        mode = AES.MODE_CBC
        encryptor = AES.new(key, mode, IV=IV)
        text = self.GATEWAY_TOKEN
        ciphertext = encryptor.encrypt(text)
        return ''.join('{:02x}'.format(x) for x in ciphertext)

    def _create_mcast_socket(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((self.MULTICAST_ADDRESS, self.MULTICAST_PORT))
        mreq = struct.pack("4sl", socket.inet_aton(self.MULTICAST_ADDRESS), socket.INADDR_ANY)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        return sock

    def _listen(self):
        """Start listening."""
        self._queue = Queue()
        self._listening = True

        t1 = Thread(target=self._listen_to_msg, args=())
        t2 = Thread(target=self._process_report, args=())

        self._threads.append(t1)
        self._threads.append(t2)

        t1.daemon = True
        t2.da = True

        t1.start()
        t2.start()

        return True

    def stop(self):
        """Stop listening."""
        self._listening = False
        self._queue.put(None)

        for t in self._threads:
            t.join()

        if self._mcastsocket is not None:
            self._mcastsocket.close()
            self._mcastsocket = None

    def _listen_to_msg(self):
        while self._listening:
            if self._mcastsocket is not None:
                data, addr = self._mcastsocket.recvfrom(self.SOCKET_BUFSIZE)
                try:
                    data = json.loads(data.decode("ascii"))
                    cmd = data['cmd']
                    if cmd == 'heartbeat' and data['model'] == 'gateway':
                        self.GATEWAY_TOKEN = data['token']
                    elif cmd == 'report' or cmd == 'heartbeat':
                        self._queue.put(data)
                    else:
                        _LOGGER.error("Unknown data")
                except Exception as e:
                    raise
                    _LOGGER.error("Cannot process Listen")

    def _process_report(self):
        while self._listening:
            packet = self._queue.get(True)
            if isinstance(packet, dict):
                try:
                    sid = packet['sid']
                    model = packet['model']
                    data = json.loads(packet['data'])
                    if 'battery' in data:
                        _LOGGER.error('Battery data:{0}'.format(data))

                    for device in self.XIAOMI_HA_DEVICES[sid]:
                        device.push_data(data)

                except Exception as e:
                    _LOGGER.error("Cannot process Report: {0}".format(e))

            self._queue.task_done()

class XiaomiDevice(Entity):
    """Representation a base Xiaomi device."""

    def __init__(self, resp, name, xiaomiHub):
        """Initialize the xiaomi device."""
        self._sid = resp['sid']
        self._name = '{}_{}'.format(name, self._sid)

        if len(resp['data']) > 2:
            self.parse_data(json.loads(resp['data']))

        self.xiaomiHub = xiaomiHub
        xiaomiHub.XIAOMI_HA_DEVICES[self._sid].append(self)

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