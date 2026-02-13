import threading
import time
from plugin_interface import IPlugin
from openttd_types import ServerPacketType, NetworkAction

# --- CONSTANTS ---
ACTION_CHAT_PUBLIC  = 3
DESTTYPE_BROADCAST  = 0
# -----------------

class WelcomeMessage(IPlugin):
    def __init__(self, client):
        super().__init__(client)
        self.name = "WelcomeMessage"
        self.version = "3.1-PARSING-FIX"
        self.prepped_data = {}

    def get_geoip_service(self):
        for p in self.client.plugins:
            if p.name == "GeoIPService": return p
        return None

    def on_event(self, pt, pl):
        import struct

        # --- STEP 1: PRE-CALCULATE (Packet 102 - CLIENT_INFO) ---
        if pt == ServerPacketType.SERVER_CLIENT_INFO:
            try:
                # Correct OpenTTD Packet Structure:
                # [0:4]   uint32  Client ID
                # [4:...] string  Network Address (IP)  <-- FIRST
                # [x:...] string  Client Name           <-- SECOND
                # [y:...] string  Language              <-- THIRD
                
                client_id = struct.unpack('<I', pl[0:4])[0]
                offset = 4
                
                def read_str(data, start):
                    end = data.find(b'\0', start)
                    # If corrupt/missing null terminator, safely fail
                    if end == -1: return "", start
                    return data[start:end].decode('utf-8', 'ignore'), end + 1

                # 1. Read IP
                ip, offset = read_str(pl, offset)
                
                # 2. Read Name
                name, offset = read_str(pl, offset)
                
                # 3. Read Language (Ignore but need to advance offset if we needed more)
                # lang, offset = read_str(pl, offset)

                # Resolve Country NOW (while map downloads)
                country = "Unknown"
                geoip = self.get_geoip_service()
                if geoip:
                    # Clean IP (remove port if present)
                    clean_ip = ip.split(']')[0].strip('[') if '[' in ip else ip.split(':')[0]
                    country = geoip.resolve(clean_ip)

                # Store it
                self.prepped_data[client_id] = {'name': name, 'country': country}
                
            except Exception as e:
                # Fail silently but safely
                pass

        # --- STEP 2: EXECUTE (Packet 103 - CLIENT_JOIN) ---
        elif pt == ServerPacketType.SERVER_CLIENT_JOIN:
            try:
                client_id = struct.unpack('<I', pl[0:4])[0]
                
                if client_id in self.prepped_data:
                    data = self.prepped_data.pop(client_id)
                    name = data['name']
                    country = data['country']
                    
                    # Fire IMMEDIATELY
                    threading.Thread(target=self.fire_messages, args=(client_id, name, country), daemon=True).start()
            except: pass
            
        elif pt in [ServerPacketType.SERVER_CLIENT_ERROR, ServerPacketType.SERVER_CLIENT_QUIT]:
            try:
                client_id = struct.unpack('<I', pl[0:4])[0]
                if client_id in self.prepped_data:
                    del self.prepped_data[client_id]
            except: pass

    def fire_messages(self, client_id, name, country):
        config = self.client.config.get("welcome_message")
        if not config: return

        # 1. Public Message
        public_tmpl = config.get("public", "")
        if public_tmpl:
            msg = public_tmpl.replace("{name}", name).replace("{country}", country)
            try:
                self.client.send_chat(ACTION_CHAT_PUBLIC, DESTTYPE_BROADCAST, 0, msg)
            except: pass

        # 2. Private Message (RCON)
        private_lines = config.get("private", [])
        if private_lines:
            if isinstance(private_lines, str): private_lines = [private_lines]
            
            for line in private_lines:
                msg = line.replace("{name}", name).replace("{country}", country)
                safe_msg = msg.replace('"', '\\"')
                try:
                    self.client.send_rcon(f'say_client {client_id} "{safe_msg}"')
                    time.sleep(0.05) 
                except: pass
