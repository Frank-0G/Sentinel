import json
import threading
import struct
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

    def on_connected(self):
        # Subscriptions handled by central AdminClient
        pass

    def on_event(self, packet_type, payload):
        # 1. Packet 124 (Native GS Packet - Keep just in case)
        if packet_type == 124 or packet_type == ServerPacketType.SERVER_GAMESCRIPT:
            self.handle_gs_packet(payload)
            
        # 2. Packet 0 (Console/Log) - This is our new main channel
        elif packet_type == 0 or packet_type == 100: # SERVER_CONSOLE often mapped to 0 or 100
            self.handle_console_log(payload)

    def handle_gs_packet(self, payload):
        try:
            json_str, _ = self.client.unpack_string(payload)
            self.process_json_cmd(json_str)
        except: pass

    def handle_console_log(self, payload):
        try:
            # Console messages: [origin] [message] or just string
            # We need to decode the raw string
            log_line = payload.decode('utf-8', errors='ignore').strip()
            
            # Check for our tag: [SENTINEL]
            if "[SENTINEL]" in log_line:
                # Extract JSON part (everything after [SENTINEL])
                parts = log_line.split("[SENTINEL]", 1)
                if len(parts) > 1:
                    json_str = parts[1].strip()
                    self.process_json_cmd(json_str)
        except: pass

    def process_json_cmd(self, json_str):
        try:
            if not json_str.startswith("{"): return
            req = json.loads(json_str)
            cmd = req.get("cmd") or req.get("event")
            
            if cmd == "pong":
                self.client.log(f"[{self.name}] GameScript PONG received: Tick {req.get('tick')}")
                cm = self.client.get_service("CommandManager")
                if cm and hasattr(cm, "on_gs_pong"):
                    cm.on_gs_pong(req)
                return

            if cmd == "sql_write":
                self.run_sql_async(req.get("query"), req.get("params", []))
            elif cmd == "sql_read":
                self.run_sql_read_and_reply(req.get("query"), req.get("params", []), req.get("callback_id"))
            elif cmd == "irc_msg":
                irc = self.client.get_service("IRC_Bridge")
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

        except Exception as e:
            self.client.log(f"[{self.name}] Error processing JSON: {e}")

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
