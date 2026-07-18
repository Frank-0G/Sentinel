import os
import time
import threading
from plugin_interface import IPlugin
from openttd_types import AdminPacketType, AdminUpdateType

class OpenttdSession(IPlugin):
    def __init__(self, client):
        super().__init__(client)
        self.name = "OpenttdSession"
        self.version = "1.5-SCREENSHOT-ECHO"
        self.map_width = 0
        self.map_height = 0
        # Pending screenshot callbacks: tile_str -> (callback_fn, context)
        self._pending_screenshots = {}
        self._pending_lock = threading.Lock()

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

    def rename_player(self, client_id, name):
        """Changes a player's name."""
        self.client.send_rcon(f"client_name {client_id} \"{name}\"")

    # --- SCREENSHOT LOGIC ---
    def take_screenshot(self, tile_or_x, y=None, on_done=None):
        """
        Initiates a screenshot at the given tile or X/Y coordinate pair.
        
        Uses the old xShunter approach:
          1. scrollto <tile>
          2. echo "doscreenshot <tile_key>"   <- RCON echoes this back
          3. on_rcon_result() detects "doscreenshot" and fires the actual
             "screenshot no_con <path>" command, then calls on_done(url).
        
        Args:
            tile_or_x: tile index (int or hex string), or X coordinate if y is provided.
            y:         optional Y coordinate.
            on_done:   optional callback fn(url_or_message) called when screenshot is taken.
        
        Returns:
            (str) An immediate status message. The URL is delivered via on_done().
        """
        try:
            # 1. Resolve Tile ID
            if y is not None:
                map_w = self.map_width or self.client.map_width
                if map_w == 0:
                    return "Error: Map size unknown (wait for sync)."
                x = int(tile_or_x)
                y_int = int(y)
                tile = (y_int << _log2(map_w)) + x
            else:
                s_tile = str(tile_or_x).lower()
                if s_tile.startswith("0x"):
                    tile = int(s_tile, 16)
                else:
                    tile = int(s_tile)

            # 2. Get Configuration
            save_path = self.client.config.get("screenshot_path", "")
            base_url = self.client.config.get("screenshot_url", "")

            # 3. Generate unique tile key (tile + timestamp for uniqueness)
            timestamp = int(time.time())
            tile_key = f"{tile}_{timestamp}"

            # 4. Determine File Path for OpenTTD (RCON) - no extension, OT appends it
            if save_path:
                full_fs_path = os.path.join(save_path, tile_key).replace("\\", "/")
            else:
                full_fs_path = tile_key

            # 5. Register pending callback
            with self._pending_lock:
                self._pending_screenshots[tile_key] = {
                    "tile": tile,
                    "fs_path": full_fs_path,
                    "base_url": base_url,
                    "on_done": on_done,
                }

            # 6. Scroll to location, then echo "doscreenshot <tile_key>" to trigger
            #    the actual screenshot from on_rcon_result (exactly like xShunter did)
            self.client.send_rcon(f"scrollto {tile}")
            self.client.send_rcon(f"echo \"doscreenshot {tile_key}\"")

            # 7. Return an immediate status — the real result arrives via on_done()
            return "Screenshot in progress..."

        except Exception as e:
            return f"Screenshot Error: {e}"

    def on_rcon_result(self, command, result):
        """
        Mirrors xShunter's onConsoleUpdated handler:
        Watches for "doscreenshot <tile_key>" in RCON output, then fires
        the actual 'screenshot no_con <path>' command and notifies callers.
        """
        result = result.strip()
        if not result.startswith("doscreenshot "):
            return

        tile_key = result[len("doscreenshot "):].strip()

        with self._pending_lock:
            pending = self._pending_screenshots.pop(tile_key, None)

        if pending is None:
            return

        fs_path = pending["fs_path"]
        base_url = pending["base_url"]
        on_done = pending.get("on_done")

        # Fire the actual screenshot command (no_con = no GUI confirmation popup)
        self.client.send_rcon(f"screenshot no_con \"{fs_path}\"")

        # Build the public URL
        filename_with_ext = tile_key + ".png"
        if base_url:
            clean_url = base_url.rstrip("/")
            url_msg = f"Screenshot taken: {clean_url}/{filename_with_ext}"
        else:
            url_msg = f"Screenshot taken (file: {filename_with_ext}). Set 'screenshot_url' in config to get a link."

        self.client.log(f"[{self.name}] {url_msg}")

        # Publish event so IRC/Discord bridges can announce it
        self.client.state.publish("screenshot_taken", url=url_msg, tile_key=tile_key)

        # Call the per-request callback (e.g. to send private message to requester)
        if on_done:
            try:
                on_done(url_msg)
            except Exception as e:
                self.client.log(f"[{self.name}] on_done callback error: {e}")


def _log2(n):
    """Integer log2 for power-of-2 values."""
    import math
    return int(math.log2(n)) if n > 0 else 9
