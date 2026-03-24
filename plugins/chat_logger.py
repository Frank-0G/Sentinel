from plugin_interface import IPlugin
from sentinel import ServerPacketType, NetworkAction, AdminUpdateType, AdminUpdateFrequency
import struct

class ChatLogger(IPlugin):
    def __init__(self, client):
        super().__init__(client)
        self.name = "ChatLogger"
        self.version = "1.2-FIXED-IMPORT"

    def on_load(self):
        print(f"[{self.name}] Plugin loaded. Waiting for connection...")

    def on_event(self, packet_type, payload):
        # 1. Register for updates when connection is established
        if packet_type == ServerPacketType.SERVER_PROTOCOL:
            print(f"[{self.name}] Connection established. Registering for Chat and Client updates...")
            self.client.send_update_frequency(AdminUpdateType.ADMIN_UPDATE_CHAT, AdminUpdateFrequency.ADMIN_FREQUENCY_AUTOMATIC)
            self.client.send_update_frequency(AdminUpdateType.ADMIN_UPDATE_CLIENT_INFO, AdminUpdateFrequency.ADMIN_FREQUENCY_AUTOMATIC)

        # 2. Handle Chat Packets
        elif packet_type == ServerPacketType.SERVER_CHAT:
            self.handle_chat(payload)
        
        # 3. Handle Client Join
        elif packet_type == ServerPacketType.SERVER_CLIENT_JOIN:
            # ID(u32)
            if len(payload) >= 4:
                client_id = struct.unpack('<I', payload[0:4])[0]
                # Note: To get the name, we technically need to parse CLIENT_INFO, 
                # but for now we just log the ID to prove it works.
                print(f"[Server] Client #{client_id} has joined the game.")

        # 4. Handle Client Quit
        elif packet_type == ServerPacketType.SERVER_CLIENT_QUIT:
            # ID(u32)
            if len(payload) >= 4:
                client_id = struct.unpack('<I', payload[0:4])[0]
                print(f"[Server] Client #{client_id} has left the game.")

    def handle_chat(self, payload):
        try:
            # Protocol: action(u8), desttype(u8), clientid(u32), message(str), money(u64)
            action = payload[0]
            
            # Filter: Only show actual chat or server messages
            if action not in [NetworkAction.NETWORK_ACTION_CHAT, 
                              NetworkAction.NETWORK_ACTION_CHAT_COMPANY, 
                              NetworkAction.NETWORK_ACTION_CHAT_CLIENT, 
                              NetworkAction.NETWORK_ACTION_SERVER_MESSAGE]:
                return

            client_id = struct.unpack('<I', payload[2:6])[0]
            msg, _ = self.client.unpack_string(payload, 6)
            
            sender = f"Client #{client_id}"
            if client_id == 1: 
                sender = "Server"
                
            print(f"[Chat] {sender}: {msg}")
        except Exception as e:
            print(f"[ChatLogger] Error parsing chat: {e}")
