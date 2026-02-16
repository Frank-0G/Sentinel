import os
import time
from plugin_interface import IPlugin
from openttd_types import AdminPacketType, AdminUpdateType

class OpenttdSession(IPlugin):
    def __init__(self, client):
        super().__init__(client)
        self.name = "OpenttdSession"
        self.version = "1.4-RESTART-FIX"
        self.map_width = 0
        self.map_height = 0

    def on_connected(self):
        # Poll map info on connect just in case
        self.client.send_poll(AdminUpdateType.ADMIN_UPDATE_DATE, 0)

    def on_map_info(self, server_name, width, height, name, seed, landscape, start_date, map_counter):
        self.map_width = width
        self.map_height = height
        self.client.log(f"[{self.name}] Map Info: {width}x{height}, '{name}'")

    # --- ACTION METHODS ---
    def execute_raw(self, cmd):
        self.client.send_rcon(cmd)

    def send_server_message(self, msg):
        self.client.send_rcon(f"say \"{msg}\"")

    def send_private_message(self, client_id, msg):
        self.client.send_rcon(f"say_client {client_id} \"{msg}\"")

    def send_chat_message(self, msg):
        self.client.send_rcon(f"say \"{msg}\"")

    def move_player(self, client_id, company_id):
        self.client.send_rcon(f"move {client_id} {company_id}")

    def kick_player(self, client_id, reason="Admin Kick"):
        self.client.send_rcon(f"kick {client_id} \"{reason}\"")

    def ban_player(self, client_id, reason="Admin Ban"):
        self.client.send_rcon(f"ban {client_id} \"{reason}\"")

    def reset_company(self, company_id):
        self.client.send_rcon(f"reset_company {company_id+1}")

    def lock_company(self, company_id):
        self.client.send_rcon(f"company_pw {company_id+1} \"LOCKED\"")

    def unlock_company(self, company_id):
        self.client.send_rcon(f"company_pw {company_id+1} \"\"")

    def pause_game(self):
        self.client.send_rcon("pause")

    def unpause_game(self):
        self.client.send_rcon("unpause")

    # --- MISSING METHOD ADDED ---
    def restart_game(self):
        """Restarts the game (map reset)."""
        self.client.send_rcon("restart")

    # --- SCREENSHOT LOGIC ---
    def take_screenshot(self, tile_or_x, y=None):
        try:
            # 1. Resolve Tile ID
            if y is not None:
                if self.map_width == 0:
                    return "Error: Map size unknown (wait for sync)."
                x = int(tile_or_x)
                y = int(y)
                tile = (y * self.map_width) + x
            else:
                s_tile = str(tile_or_x).lower()
                if s_tile.startswith("0x"):
                    tile = int(s_tile, 16)
                else:
                    tile = int(s_tile)

            # 2. Get Configuration
            save_path = self.client.config.get("screenshot_path", "") 
            base_url = self.client.config.get("screenshot_url", "")

            # 3. Generate Filename Base (Tile + Timestamp) NO EXTENSION
            timestamp = int(time.time())
            filename_base = f"{tile}_{timestamp}"
            
            # 4. Determine File Path for OpenTTD (RCON)
            # OpenTTD automatically appends extension (e.g. .png)
            if save_path:
                full_fs_path = os.path.join(save_path, filename_base)
                full_fs_path = full_fs_path.replace("\\", "/") 
            else:
                full_fs_path = filename_base

            # 5. Send Commands
            self.client.send_rcon(f"scrollto {tile}")
            self.client.send_rcon(f"screenshot no_con \"{full_fs_path}\"")

            # 6. Return Formatted Message (Add extension here for the link)
            filename_with_ext = filename_base + ".png"
            
            if base_url:
                clean_url = base_url.rstrip("/")
                return f"Screenshot taken: {clean_url}/{filename_with_ext}"
            else:
                return f"Screenshot taken (File: {filename_with_ext}). Set 'screenshot_url' in config to see link."

        except Exception as e:
            return f"Screenshot Error: {e}"
