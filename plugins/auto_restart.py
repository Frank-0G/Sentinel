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
        self.version = "1.8-DUAL-TIMEOUT"
        
        self.empty_since = 0
        self.restart_triggered = False
        
        # Configs (0 to disable)
        self.limit_empty_min = self.client.config.get("auto_restart_minutes", 60)
        self.limit_abandoned_min = self.client.config.get("auto_restart_abandoned_minutes", 480)

    def get_data(self):
        for p in self.client.plugins:
            if p.name == "DataController": return p
        return None

    def get_irc(self):
        for p in self.client.plugins:
            if p.name == "IRCBridge": return p
        return None

    def get_discord(self):
        for p in self.client.plugins:
            if p.name == "DiscordBridge": return p
        return None

    def on_load(self):
        self.client.log(f"[{self.name}] Loaded. Empty: {self.limit_empty_min}m | Abandoned: {self.limit_abandoned_min}m")

    def on_tick(self):
        if self.restart_triggered: return

        data = self.get_data()
        if not data: return

        # 1. Count ALL Real Clients (Exclude Client ID 1)
        # Spectators ARE counted in data.clients, so this covers the user's "1 spectator = no restart" rule.
        real_client_count = len([cid for cid in data.clients if cid != 1])

        # 2. Determine State and Limit
        has_companies = (len(data.companies) > 0)
        
        limit_min = 0
        state_msg = ""
        
        if real_client_count > 0:
            # Any player/spectator blocks the timer
            self.empty_since = 0
            return

        if has_companies:
            limit_min = self.limit_abandoned_min
            state_msg = "abandoned companies"
        else:
            limit_min = self.limit_empty_min
            state_msg = "no companies or players"

        # 3. Check if condition is enabled
        if limit_min <= 0:
            self.empty_since = 0
            return

        # 4. Timer Logic
        if self.empty_since == 0:
            self.empty_since = time.time()
        else:
            elapsed = time.time() - self.empty_since
            if elapsed >= (limit_min * 60):
                self.trigger_auto_restart(elapsed, state_msg)

    def trigger_auto_restart(self, elapsed_seconds, state_msg):
        # Format time string
        hours = math.floor(elapsed_seconds / 3600)
        mins = math.floor((elapsed_seconds % 3600) / 60)
        time_str = f"{hours} hour{'s' if hours!=1 else ''} {mins} minute{'s' if mins!=1 else ''}"
        
        msg = f"Executing automatic server restart ({state_msg} for {time_str})"
        self.perform_restart_sequence(msg)

    def perform_restart_sequence(self, broadcast_msg):
        if self.restart_triggered: return
        self.restart_triggered = True

        # 1. IRC Message
        irc = self.get_irc()
        if irc: irc.send_to_channel(broadcast_msg, "announcements")
        
        # 2. Discord Message
        discord = self.get_discord()
        if discord: discord.send_msg(broadcast_msg)
        
        self.client.log(f"[{self.name}] {broadcast_msg}")

        # 2. In-Game Warning
        self.client.send_rcon("say \"*** Server restarting in 5 seconds...\"")

        # 3. Quit & Restart Game
        def kill_sequence():
            time.sleep(5.0)
            if irc: irc.send_to_channel("OpenTTD server process terminated.", "announcements")
            if discord: discord.send_msg("OpenTTD server process terminated.")
            
            # Graceful Shutdown of OpenTTD
            if hasattr(self.client, 'launcher') and self.client.launcher:
                self.client.launcher.stop()
            else:
                self.client.send_rcon("quit")
                time.sleep(2.0)
            
            self.client.log(f"[{self.name}] Requesting Game Restart (Sentinel stays active)...")
            
            # Signal Sentinel to restart ONLY the game process
            self.client.restart_requested = True

        threading.Thread(target=kill_sequence, daemon=True).start()

    def process_command(self, cmd, args, source, admin_name, cid, context=None):
        if cmd == "restart":
            msg = f"Manual server restart triggered by {admin_name}."
            self.perform_restart_sequence(msg)
            return "Restart sequence initiated."
            
        if cmd == "restarttimer":
            if self.restart_triggered:
                return "Restart is already in progress (shutting down in 5 seconds)."
            
            if self.empty_since == 0:
                return "The restart timer is not currently active (server is active or feature is disabled)."
                
            data = self.get_data()
            if not data: return "Unable to retrieve game data."
            
            has_companies = (len(data.companies) > 0)
            limit_min = self.limit_abandoned_min if has_companies else self.limit_empty_min
            
            if limit_min <= 0:
                return "The auto-restart timer is disabled for this server state."
                
            elapsed = time.time() - self.empty_since
            remaining = (limit_min * 60) - elapsed
            
            if remaining <= 0:
                return "The timer has expired; restart should trigger any moment."
                
            # Format remaining time
            rem_mins = math.ceil(remaining / 60)
            state_text = "abandoned companies" if has_companies else "empty server"
            return f"Auto-restart ({state_text}) in approximately {rem_mins} minute{'s' if rem_mins != 1 else ''}."
            
        return None
