import json
import threading
import struct
import time
from plugin_interface import IPlugin
from openttd_types import AdminPacketType, AdminUpdateType, ServerPacketType

class GameScriptConnector(IPlugin):
    def __init__(self, client):
        super().__init__(client)
        self.name = "GameScriptConnector"
        self.version = "1.1-CENTRAL-DB"
        
        self.game_scores = {} 
        
        # Load MySQL Configuration
        self.db_config = self.client.config.get("mysql_config", {}).copy()
        
        if not self.db_config:
            self.client.log(f"[{self.name}] CRITICAL: 'mysql_config' missing in controller_config.json!")
        else:
            if 'port' in self.db_config:
                self.db_config['port'] = int(self.db_config['port'])
            valid_keys = ['user', 'password', 'host', 'database', 'port', 'unix_socket', 'flags']
            self.db_config = {k: v for k, v in self.db_config.items() if k in valid_keys}

        # Watchdog State
        self.last_ping_sent = time.time()
        self.ping_pending = False
        self.failure_announced = False
        
        # Server State
        self.server_id = self.client.config.get("server_id", 99)
        self.debug = self.client.config.get("logs", {}).get("gs_connector_debug", False)
        self.restart_in_progress = False
        self.currency_code = "GBP"
        self.currency_multiplier = 1.0

    def on_connected(self):
        # Subscriptions handled by central AdminClient
        pass

    def on_event(self, packet_type, payload):
        # 1. Packet 124 (Native GS Packet - Keep just in case)
        if packet_type == 124 or packet_type == ServerPacketType.SERVER_GAMESCRIPT:
            self.handle_gs_packet(payload)
            
        # 2. Packet 0 (Console/Log) - This is our new main channel
        elif packet_type == ServerPacketType.SERVER_CONSOLE:
            self.handle_console_log(payload)
            
        # 3. Packet 127 (CMD_LOGGING) - Used for protection system
        elif packet_type == ServerPacketType.SERVER_CMD_LOGGING:
            self.handle_cmd_log(payload)

    def handle_gs_packet(self, payload):
        try:
            json_str, _ = self.client.unpack_string(payload)
            if self.debug:
                self.client.log(f"[{self.name}] Received Packet 124: {json_str[:100]}...")
            self.process_json_cmd(json_str)
        except Exception as e:
            self.client.log(f"[{self.name}] Error in GS packet handler: {e}")

    def handle_console_log(self, payload):
        try:
            # SERVER_CONSOLE (Packet 121) has two strings: [origin] and [message]
            origin, offset = self.client.unpack_string(payload, 0)
            log_line, _ = self.client.unpack_string(payload, offset)
            log_line = log_line.strip()
            
            # Check for our tag: [SENTINEL]
            if "[SENTINEL]" in log_line:
                if self.debug:
                    self.client.log(f"[{self.name}] GS LOG: {log_line}")
                # Extract JSON part (everything after [SENTINEL])
                parts = log_line.split("[SENTINEL]", 1)
                if len(parts) > 1:
                    json_str = parts[1].strip()
                    self.process_json_cmd(json_str)
            else:
                # Log other GS messages just in case
                if origin == "script":
                     if self.debug:
                        self.client.log(f"[{self.name}] GS Console: {log_line}")
        except Exception as e:
            self.client.log(f"[{self.name}] Error in console log handler: {e}")

    def process_json_cmd(self, json_str):
        try:
            if not json_str.startswith("{"): return
            req = json.loads(json_str)
            cmd = req.get("cmd") or req.get("event") or req.get("command")
            
            if cmd == "pong":
                if self.debug:
                    self.client.log(f"[{self.name}] GameScript PONG received: Tick {req.get('tick')}")
                
                # Watchdog recovery logic
                if self.failure_announced:
                    self.broadcast_gs_recovery()
                    self.failure_announced = False
                self.ping_pending = False
                
                cm = self.client.get_service("CommandManager")
                if cm and hasattr(cm, "on_gs_pong"):
                    cm.on_gs_pong(req)
                return

            if cmd == "sql_write":
                self.run_sql_async(req.get("query"), req.get("params", []))
            elif cmd == "sql_read":
                self.run_sql_read_and_reply(req.get("query"), req.get("params", []), req.get("callback_id"))
            elif cmd == "irc_msg":
                irc = self.client.get_service("IRCBridge")
                if irc: irc.send_message(req.get("channel"), req.get("msg"))
            elif cmd == "game_chat":
                target_type = req.get("type", 0) 
                target_id = req.get("target_id", 0)
                msg = req.get("msg", "")
                if target_type == 0: self.client.send_rcon(f"say \"{msg}\"")
                elif target_type == 2: self.client.send_rcon(f"say_client {target_id} \"{msg}\"")
            elif cmd == "restart_game":
                self.client.log(f"[{self.name}] GameScript requested restart.")
                self.client.send_rcon("restart")
            elif cmd == "update_score":
                cid = req.get("company_id")
                self.game_scores[cid] = req.get("stats")
            elif cmd == "chat_reply":
                target = req.get("target")
                source = req.get("source", "game")
                lines = req.get("lines", [])
                text = req.get("text")
                
                cm = self.client.get_service("CommandManager")
                if cm:
                    # target=0 is a global broadcast. We pass None to IDs to trigger global say in CommandManager.
                    actual_target = target if target != 0 else None
                    context = {"cid": actual_target, "irc_target": actual_target, "discord_channel_id": actual_target}
                    
                    # Handle multi-line bundle
                    if isinstance(lines, list) and lines:
                        if source in ["discord", "irc"]:
                            # Join lines for external platforms to ensure message ordering
                            cm._send_directed("\n".join(lines), source, context)
                        else:
                            # In-game console or other sources might prefer separate packets
                            for line in lines:
                                cm._send_directed(line, source, context)
                    # Handle legacy single-line
                    elif text:
                        cm._send_directed(text, source, context)
            elif cmd == "violation":
                actor_cid = req.get("company")
                town = req.get("town")
                owner = req.get("owner")
                tile = req.get("tile")
                
                # Resolve client IDs for the actor company
                data = self.client.get_service("DataController")
                bad_clients = []
                if data:
                    for cid, cinfo in data.clients.items():
                        if cinfo.get("company") == actor_cid:
                            bad_clients.append(cid)
                
                for client_id in bad_clients:
                    # Track violations per client (in memory for now, mimicking GoalSystem)
                    if not hasattr(self, "bad_actions"): self.bad_actions = {}
                    count = self.bad_actions.get(client_id, 0) + 1
                    self.bad_actions[client_id] = count
                    
                    self.client.log(f"[{self.name}] VIOLATION {count}/3: Client {client_id} in {town}")
                    
                    if count == 1:
                        self.client.send_rcon(f"say_client {client_id} \"Warning: That town is claimed by another company! (1/3)\"")
                    elif count == 2:
                        self.client.send_rcon(f"move {client_id} 255")
                        self.client.send_rcon(f"say \"Client {client_id} moved to spectators for griefing in {town} (2/3).\"")
                    elif count >= 3:
                        self.client.send_rcon(f"kick {client_id} \"Griefing protected area (3/3)\"")
                        self.client.send_rcon(f"say \"Client {client_id} kicked for griefing in {town} (3/3).\"")
            elif cmd == "game_win":
                company = req.get("company")
                name = req.get("name")
                amount = req.get("amount")
                self.client.log(f"[{self.name}] WINNER: {name} with {amount}")
                # Trigger automatic restart
                self.client.send_rcon("restart")
            elif cmd == "gs_init":
                goal_cfg = self.client.config.get("goal", {})
                self.client.log(f"[{self.name}] GameScript Kernel Initialized. Injecting config (Goal: {goal_cfg.get('winlimit', 0)})...")
                
                cfg = {
                    "command": "set_server_config", 
                    "server_id": self.server_id
                }
                
                # Goal Settings
                goal = self.client.config.get("goal")
                if goal is not None:
                    winlimit = int(goal.get("winlimit", 0))
                    population = int(goal.get("population", 0))
                    interval = int(goal.get("interval", 600))
                    currency = goal.get("currency", "EUR")
                    
                    # Map currency to multiplier for Python-side reporting
                    rates = {
                        "GBP": 1.0, "USD": 1.6, "EUR": 2.0, "JPY": 202.0, "SEK": 9.17, "RUB": 43.6
                    }
                    self.currency_multiplier = rates.get(currency.upper(), 1.0)
                    self.currency_code = currency.upper()

                    cfg.update({
                        "winlimit": winlimit,
                        "population": population,
                        "interval": interval,
                        "currency": self.currency_code,
                        "unit": self.currency_code,
                        "desc": "company value"
                    })
                
                self.send_to_gs(cfg)
            elif cmd == "progress_snapshot":
                self.handle_progress_snapshot(req)
            elif cmd == "prepare_restart":
                self.on_gs_prepare_restart(req)
            elif cmd == "restart_now":
                self.client.send_rcon("restart")
            elif cmd == "log":
                text = req.get("text")
                self.client.log(f"[GameScript] {text}")

        except Exception as e:
            self.client.log(f"[{self.name}] Error processing JSON: {e}")

    def on_gs_prepare_restart(self, data):
        """
        Handles the victory cleanup phase: moves losers to spec and resets their companies.
        This is triggered by the GameScript Kernel when it starts its victory countdown.
        """
        winner_id = data.get("winner", -1)
        amount = data.get("amount", 0)
        
        data_ctrl = self.client.get_service("DataController")
        if not data_ctrl: return
        
        # 1. Announce Winner Globally
        winner_name = data.get("winner_name", "Unknown")
        winner_color = data.get("winner_color", "Unknown")
        player_str = "AI/Empty"
        
        if winner_id >= 0:
            # Fallback to cache if packet is missing details
            co_info = data_ctrl.companies.get(winner_id)
            if co_info:
                if winner_name == "Unknown": winner_name = co_info.get("name", f"Company #{winner_id+1}")
                if winner_color == "Unknown":
                    c_idx = co_info.get("color", 0)
                    winner_color, _ = data_ctrl.get_color_info(c_idx)
                
            players = []
            for cid, cinfo in data_ctrl.clients.items():
                if cinfo.get("company") == winner_id:
                    players.append(cinfo.get("name", "Unknown"))
            
            if players:
                player_str = ", ".join(players)
            
            display_amount = int(amount * self.currency_multiplier)
            formatted_amount = f"{display_amount:,}"
            win_msg = f"--- GOAL REACHED! {winner_name} ({winner_color}) ({player_str}) has won this game with {formatted_amount} {self.currency_code}!!! ---"
        else:
            win_msg = "--- GAME ENDED: DRAW! No winner declared. ---"

        self.client.log(f"[{self.name}] {win_msg}")
        self.client.send_rcon(f"say \"{win_msg}\"")
        
        # 2. Identify 'Keep-Alive' Player to prevent server pause
        # Priority: 1. Someone already in winner_id, 2. Anyone else
        keep_alive_id = None
        human_clients = [cid for cid in data_ctrl.clients.keys() if cid != 1]
        
        # Check for players already in the winning company
        for cid in human_clients:
            if data_ctrl.clients[cid].get("company") == winner_id:
                keep_alive_id = cid
                break
        
        # If none found, pick any human
        if keep_alive_id is None and human_clients:
            keep_alive_id = human_clients[0]
            self.client.log(f"[{self.name}] Keep-Alive: Selecting player {keep_alive_id} to keep game unpaused.")

        # 3. Move players: Everyone to Spectators EXCEPT the Keep-Alive player
        quit_msg = "The game has ended. You have been moved to spectators."
        for client_id in human_clients:
            if client_id == keep_alive_id:
                # Ensure the Keep-Alive player is in the winning company
                if data_ctrl.clients[client_id].get("company") != winner_id:
                    self.client.send_rcon(f"move {client_id} {winner_id}")
                continue
            
            # Everyone else moves to spectator
            self.client.send_rcon(f"say_client {client_id} \"{quit_msg}\"")
            self.client.send_rcon(f"move {client_id} 255")
        
        # 4. Reset all non-winning companies
        for co_id in list(data_ctrl.companies.keys()):
            if co_id != winner_id:
                self.client.send_rcon(f"reset_company {co_id}")
        
        # 4. START THREADED VICTORY SEQUENCE
        if self.restart_in_progress:
            self.client.log(f"[{self.name}] Victory sequence already in progress. Skipping duplicate.")
            return

        self.restart_in_progress = True
        
        # Launch dedicated thread for the 30-second countdown
        threading.Thread(target=self._victory_sequence_worker, args=(win_msg, winner_id, amount), daemon=True).start()

    def _victory_sequence_worker(self, win_msg, winner_id, amount):
        """
        Threaded worker that handles the 30-second restart countdown and announcements.
        """
        # Signal GameScript to show victory popup AFTER administrative actions (moves/resets) are sent
        self.send_to_gs({
            "command": "display_victory_popup", 
            "winner_id": winner_id, 
            "amount": amount
        })
        
        # Countdown intervals (in seconds remaining)
        intervals = [30, 20, 10, 5, 4, 3, 2, 1]
        
        try:
            for i in range(30, 0, -1):
                if i in intervals:
                    msg = f"--- SERVER RESTART IN {i} SECONDS ---"
                    self.client.send_rcon(f"say \"{msg}\"")
                    
                time.sleep(1)
            
            # Final action
            self.client.log(f"[{self.name}] Victory Sequence Complete: Restarting server.")
            self.client.send_rcon("restart")
        except Exception as e:
            self.client.log(f"[{self.name}] Error in victory sequence: {e}")
            # Ensure restart happens regardless
            self.client.send_rcon("restart")
        finally:
            self.restart_in_progress = False

    def on_tick(self):
        # Watchdog: Every 5 minutes (300s)
        now = time.time()
        if now - self.last_ping_sent > 300:
            if not self.ping_pending:
                self.send_ping()
                self.last_ping_sent = now
                self.ping_pending = True
        
        # Check for timeout (15s after ping)
        if self.ping_pending and (now - self.last_ping_sent > 15):
            if not self.failure_announced:
                self.broadcast_gs_failure()
                self.failure_announced = True
            # We don't reset ping_pending here so it doesn't immediately re-ping
            # It will reset on next 300s interval if failure persists

    def broadcast_gs_failure(self):
        msg = "⚠️ CRITICAL: GameScript liveness check FAILED! The script may have crashed or is hanging."
        self.client.log(f"[{self.name}] {msg}")
        
        # Notify Discord
        discord = self.client.get_service("DiscordBridge")
        if discord: discord.send_msg(f"@here {msg}")
        
        # Notify IRC
        irc = self.client.get_service("IRCBridge")
        if irc: irc.send_to_channel(msg, "announcements")

    def broadcast_gs_recovery(self):
        msg = "✅ RECOVERY: GameScript is responding again."
        self.client.log(f"[{self.name}] {msg}")
        
        # Notify Discord
        discord = self.client.get_service("DiscordBridge")
        if discord: discord.send_msg(msg)
        
        # Notify IRC
        irc = self.client.get_service("IRCBridge")
        if irc: irc.send_to_channel(msg, "announcements")
        
    def handle_progress_snapshot(self, data):
        companies = data.get("companies", [])
        mode = data.get("mode", 0)
        if self.debug:
            self.client.log(f"[{self.name}] Received Progress Snapshot with {len(companies)} active companies.")
        
        mysql = self.get_mysql()
        if not mysql or not self.db_config: return
        
        batch = []
        # 1. DELETE - Clear old records for this server
        batch.append(("DELETE FROM openttd_game_progress WHERE server_id = %s", (self.server_id,)))
        
        # 2. INSERTS - Add current active companies
        for co in companies:
            # New schema: datetime=NOW(), added inhabitants and bb_goals
            query = """
            INSERT INTO openttd_game_progress 
            (server_id, datetime, game_mode, company_id, company_name, value, progress, client_count, inhabitants, bb_goals) 
            VALUES (%s, NOW(), %s, %s, %s, %s, %s, %s, %s, %s)
            """
            params = (
                self.server_id,
                mode,
                co.get("id"),
                co.get("name"),
                co.get("value"),
                co.get("progress"),
                co.get("clients"),
                co.get("inhabitants"),
                co.get("bb_goals")
            )
            batch.append((query, params))
        
        mysql.execute_batch(self.db_config, batch)

    def get_mysql(self):
        return self.client.get_service("MySQL")

    def run_sql_async(self, query, params):
        mysql = self.get_mysql()
        if mysql and self.db_config:
            mysql.execute_query(self.db_config, query, params, fetch=False)

    def run_sql_read_and_reply(self, query, params, callback_id):
        mysql = self.get_mysql()
        if not mysql or not self.db_config: return

        def callback(result):
            response = {"cmd": "sql_result", "callback_id": callback_id, "data": result}
            self.send_to_gs(response)

        mysql.execute_query(self.db_config, query, params, callback=callback, fetch=True)

    def handle_cmd_log(self, payload):
        try:
            # Openttd Admin Protocol Packet 127 structure:
            # 1 bit boolean (cmd_failed), then string (cmd_name), etc.
            cmd_failed = payload[0]
            if cmd_failed: return
            
            # cmd_name starts at byte 1
            cmd_name, pointer = self.client.unpack_string(payload, 1)
            # company_id is at byte pointer
            company_id = payload[pointer]
            # tile is at byte pointer + 1 (uint32)
            tile = struct.unpack('<I', payload[pointer+1:pointer+5])[0]
            
            # Forward to GameScript for protection check
            self.send_to_gs({
                "command": "cmd_log",
                "name": cmd_name,
                "company": int(company_id),
                "tile": int(tile)
            })
        except: pass

    def send_to_gs(self, data):
        # We still try to send back via packet, but if GSAdmin is broken, GS might not receive it.
        # This is fine for now as we mostly need one-way (GS -> Sentinel) for claims.
        try:
            payload = json.dumps(data).encode('utf-8') + b'\x00'
            self.client.send_packet(AdminPacketType.ADMIN_GAMESCRIPT, payload)
        except Exception as e:
            self.client.log(f"[{self.name}] Failed to send to GS: {e}")

    def send_ping(self):
        self.send_to_gs({"event": "ping"})
