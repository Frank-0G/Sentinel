import time
import struct
from plugin_interface import IPlugin
from openttd_types import ServerPacketType

class AntiFlood(IPlugin):
    def __init__(self, client):
        super().__init__(client)
        self.name = "AntiFlood"
        self.version = "1.0"
        
        # Config
        self.flood_limit = 4       # Max messages
        self.flood_interval = 3.0  # ...per 3 seconds
        self.mute_duration = 60    # Seconds
        
        # State: { client_id: [timestamp1, timestamp2, ...] }
        self.history = {}
        self.muted_until = {}

    def get_session(self):
        return self.client.get_service("OpenttdSession")

    def on_event(self, pt, pl):
        if pt == ServerPacketType.SERVER_CHAT:
            try:
                # Packet: ACTION(1), DEST_TYPE(1), ID(4), MSG(...)
                cid = struct.unpack('<I', pl[2:6])[0]
                if cid == 1: return # Ignore server
                
                now = time.time()
                
                # 1. Check Mute Status
                if cid in self.muted_until:
                    if now < self.muted_until[cid]:
                        # Kick/Warn if they try to talk while muted?
                        # OpenTTD doesn't allow "blocking" chat easily without RCON, 
                        # but we can warn them via PM.
                        return
                    else:
                        del self.muted_until[cid] # Unmute

                # 2. Record Message
                if cid not in self.history: self.history[cid] = []
                self.history[cid].append(now)
                
                # 3. Clean old history
                self.history[cid] = [t for t in self.history[cid] if now - t < self.flood_interval]
                
                # 4. Check Threshold
                if len(self.history[cid]) > self.flood_limit:
                    self.trigger_flood_protection(cid)
            
            except: pass
            
    def trigger_flood_protection(self, cid):
        s = self.get_session()
        if not s: return
        
        self.muted_until[cid] = time.time() + self.mute_duration
        self.history[cid] = [] # Reset history so we don't loop-trigger
        
        s.send_server_message(f"Anti-Flood: Client #{cid} muted for {self.mute_duration}s.")
        s.send_private_message(cid, "Stop spamming! You are temporarily ignored.")
        
        # Optional: Kick if it's severe
        # s.kick_player(cid, "Flood Protection")
