import json
import os
from plugin_interface import IPlugin

class AdminManager(IPlugin):
    def __init__(self, client):
        super().__init__(client)
        self.name = "AdminManager"
        self.version = "1.1-AUTH-SUPPORT"
        self.groups = {}
        self.inheritance = {}
        self.users = {}      # Maps Username (Lower) -> Group
        self.irc_map = {}    # Maps IRC Nick (Lower) -> Username
        self.passwords = {}  # Maps Username (Lower) -> Password

    def on_load(self):
        self.reload_config()

    def reload_config(self):
        try:
            if os.path.exists("admins.json"):
                with open("admins.json", "r") as f:
                    data = json.load(f)
                    self.groups = data.get("groups", {})
                    self.inheritance = data.get("inheritance", {})
                    self.users = {k.lower(): v for k, v in data.get("users", {}).items()}
                    self.irc_map = {k.lower(): v for k, v in data.get("irc_auth", {}).items()}
                    self.passwords = {k.lower(): v for k, v in data.get("passwords", {}).items()}
                    
                self.client.log(f"[{self.name}] Loaded {len(self.users)} admins, {len(self.groups)} groups, {len(self.passwords)} passwords.")
            else:
                self.client.log(f"[{self.name}] admins.json not found!")
        except Exception as e:
            self.client.log(f"[{self.name}] Config Load Error: {e}")

    # --- API ---

    def verify_credentials(self, username, password):
        """Checks if the username exists and password matches."""
        if not username or not password: return False
        
        stored_pass = self.passwords.get(username.lower())
        if not stored_pass: return False
        
        return stored_pass == password

    def get_admin_user_from_irc(self, nickname):
        """Returns the internal username for a given IRC nickname, if mapped."""
        return self.irc_map.get(nickname.lower())

    def get_user_group(self, username):
        return self.users.get(username.lower())

    def has_privilege(self, username, privilege):
        if not username: return False
        group = self.users.get(username.lower())
        if not group: return False
        return self._check_group_privilege(group, privilege)

    def _check_group_privilege(self, group, privilege):
        # 1. Check direct privileges
        if privilege in self.groups.get(group, []):
            return True
        
        # 2. Check inheritance
        parents = self.inheritance.get(group, [])
        for parent in parents:
            if self._check_group_privilege(parent, privilege):
                return True
                
        return False
