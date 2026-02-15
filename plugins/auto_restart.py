import time
import math
import os
import sys
import threading
from plugin_interface import IPlugin

class AutoRestart(IPlugin):
    def __init__(self, client):
        super().__init__(client)
        self.name = "AutoRestart"
        self.version = "1.7-MANUAL-RESTART"
        
        self.empty_since = 0
        self.restart_triggered = False
        
        # Config (Default 60 minutes)
        self.limit_minutes = self.client.config.get("auto_restart_minutes", 60)
        self.limit_seconds = self.limit_minutes * 60

    def get_data(self):
        for p in self.client.plugins:
            if p.name == "DataController": return p
        return None

    def get_irc(self):
        for p in self.client.plugins:
            if p.name == "IRCBridge": return p
        return None

    def on_load(self):
        self.client.log(f"[{self.name}] Loaded. Restart interval: {self.limit_minutes} minutes.")

    def on_tick(self):
        if self.restart_triggered: return

        data = self.get_data()
        if not data: return

        # 1. Count Real Players (Exclude Client ID 1)
        real_player_count = 0
        for cid in data.clients:
            if cid != 1:
                real_player_count += 1

        # 2. Check Conditions
        if len(data.companies) == 0 and real_player_count == 0:
            if self.empty_since == 0:
                self.empty_since = time.time()
            else:
                elapsed = time.time() - self.empty_since
                if elapsed >= self.limit_seconds:
                    self.trigger_auto_restart(elapsed)
        else:
            self.empty_since = 0

    def trigger_auto_restart(self, elapsed_seconds):
        # Format time string
        hours = math.floor(elapsed_seconds / 3600)
        mins = math.floor((elapsed_seconds % 3600) / 60)
        time_str = f"{hours} hour{'s' if hours!=1 else ''} {mins} minute{'s' if mins!=1 else ''}"
        
        msg = f"Executing automatic server restart (no companies or players for {time_str})"
        self.perform_restart_sequence(msg)

    def perform_restart_sequence(self, broadcast_msg):
        if self.restart_triggered: return
        self.restart_triggered = True

        # 1. IRC Message
        irc = self.get_irc()
        if irc: irc.send_msg(broadcast_msg)
        
        self.client.log(f"[{self.name}] {broadcast_msg}")

        # 2. In-Game Warning
        self.client.send_rcon("say \"*** Server restarting in 5 seconds...\"")

        # 3. Quit & Restart Wrapper
        def kill_sequence():
            time.sleep(5.0)
            if irc: irc.send_msg("OpenTTD server process terminated.")
            self.client.send_rcon("quit")
            
            time.sleep(2.0)
            self.client.log(f"[{self.name}] RESTARTING SENTINEL PROCESS...")
            
            try:
                if self.client.socket: self.client.socket.close()
            except: pass

            try:
                # Self-Restart
                os.execv(sys.executable, [sys.executable] + sys.argv)
            except Exception as e:
                self.client.log(f"[{self.name}] Restart Failed: {e}")
                os._exit(1)

        threading.Thread(target=kill_sequence, daemon=True).start()

    def process_command(self, cmd, args, source, admin_name, cid):
        if cmd == "restart":
            msg = f"Manual server restart triggered by {admin_name}."
            self.perform_restart_sequence(msg)
            return "Restart sequence initiated."
        return None
