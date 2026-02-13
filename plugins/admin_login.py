import struct
from plugin_interface import IPlugin
from openttd_types import ServerPacketType

class AdminLogin(IPlugin):
    """
    Manages in-game admin authentication.
    Handles Auth login logic for game clients.
    """
    def __init__(self, client):
        super().__init__(client)
        self.name = "AdminLogin"
        self.version = "2.0-INTEGRATED"
        
        # Maps ClientID (int) -> AdminUsername (str)
        self.authenticated_sessions = {}

    def get_admin_manager(self):
        return self.client.get_service("AdminManager")

    def get_authenticated_user(self, client_id):
        """API: Returns the username if the client is logged in as admin."""
        return self.authenticated_sessions.get(client_id)

    def on_event(self, pt, pl):
        # Clean up sessions when a client disconnects
        if pt == ServerPacketType.SERVER_CLIENT_QUIT:
            try:
                client_id = struct.unpack('<I', pl[0:4])[0]
                if client_id in self.authenticated_sessions:
                    user = self.authenticated_sessions[client_id]
                    self.client.log(f"[{self.name}] Admin session ended for {user} (Client #{client_id})")
                    del self.authenticated_sessions[client_id]
            except: pass

    def process_command(self, cmd, args, source, admin_name, cid):
        """Called by CommandManager to handle !alogin / !alogout"""
        if source != "game":
            return "Admin Login is only available in-game."

        if cmd == "alogin":
            if len(args) < 2:
                return "Usage: !alogin <username> <password>"
            
            username = args[0]
            password = args[1]
            
            am = self.get_admin_manager()
            if not am:
                return "Error: AdminManager not loaded."

            if am.verify_credentials(username, password):
                self.authenticated_sessions[cid] = username.lower()
                self.client.log(f"[{self.name}] Client #{cid} logged in as admin '{username}'.")
                return f"Authenticated as '{username}'. Welcome back, Administrator."
            else:
                self.client.log(f"[{self.name}] Failed login attempt from #{cid} for user '{username}'.")
                return "Invalid username or password."

        elif cmd == "alogout":
            if cid in self.authenticated_sessions:
                del self.authenticated_sessions[cid]
                return "Logged out successfully."
            else:
                return "You are not logged in."
        
        return None
