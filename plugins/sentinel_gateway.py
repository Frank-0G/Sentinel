import json
import time
import threading
import struct
from plugin_interface import IPlugin
from openttd_types import AdminPacketType, AdminUpdateType, ServerPacketType

class SentinelGateway(IPlugin):
    def __init__(self, client):
        super().__init__(client)
        self.name = "SentinelGateway"
        self.version = "1.4-LEGACY-STUB"

    def on_connected(self):
        self.client.log(f"[{self.name}] Legacy Gateway Active. (Logic moved to GameScriptConnector)")

    def on_event(self, packet_type, payload):
        # Kept for future extension or legacy packet sniffing if needed
        pass
