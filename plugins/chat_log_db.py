import time
import threading
import json
import struct
from datetime import datetime

from plugin_interface import IPlugin
from openttd_types import ServerPacketType, NetworkAction

class ChatLogDB(IPlugin):
    def __init__(self, client):
        super().__init__(client)
        self.name = "ChatLogDB"
        self.version = "2.3-CENTRAL-DB"
        
        self.server_id = 99
        self.retention_days = 365
        self.last_cleanup = 0
        self.cleanup_interval = 3600
        self.db_config = {}

    def on_load(self):
        # Load Config
        self.server_id = self.client.config.get("server_id", 99)
        self.retention_days = self.client.config.get("chat_log_retention_days", 365)
        
        db_cfg = self.client.config.get("chat_db_config")
        if not db_cfg: db_cfg = self.client.config.get("mysql_config")
            
        if not db_cfg:
            self.client.log(f"[{self.name}] Error: No MySQL configuration found.")
            return

        # Prepare config for MySQL plugin
        self.db_config = db_cfg.copy()
        if 'port' in self.db_config: self.db_config['port'] = int(self.db_config['port'])
        valid_keys = ['user', 'password', 'host', 'database', 'port', 'unix_socket', 'flags']
        self.db_config = {k: v for k, v in self.db_config.items() if k in valid_keys}

        self.init_database()
        self.run_cleanup()
        self.register_updates()

    def get_mysql(self):
        return self.client.get_service("MySQL")

    def execute_db(self, query, params=(), callback=None, fetch=False):
        mysql = self.get_mysql()
        if mysql and self.db_config:
            mysql.execute_query(self.db_config, query, params, callback, fetch)

    def register_updates(self):
        try:
            freq = 65 
            for i in range(1, 11):
                self.client.send_packet(3, struct.pack('<HH', i, freq))
            self.client.log(f"[{self.name}] Registered for Server Updates.")
        except: pass

    def check_and_add_column(self, table, column, definition, next_step=None):
        check_sql = f"SELECT count(*) as cnt FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = '{table}' AND COLUMN_NAME = '{column}'"
        
        def cb(res):
            if res and res[0]['cnt'] == 0:
                self.client.log(f"[{self.name}] Migrating DB: Adding '{column}'...")
                self.execute_db(f"ALTER TABLE `{table}` ADD COLUMN `{column}` {definition}")
            
            if next_step: next_step()

        self.execute_db(check_sql, (), cb, fetch=True)

    def init_database(self):
        create_query = """
        CREATE TABLE IF NOT EXISTS `openttd_chat_log` (
            `id` INT AUTO_INCREMENT PRIMARY KEY,
            `server_id` INT NOT NULL,
            `timestamp` BIGINT NOT NULL,
            `datetime` DATETIME NOT NULL,
            `client_id` INT NOT NULL,
            `client_name` VARCHAR(100),
            `client_ip` VARCHAR(50),
            `company_name` VARCHAR(100),
            `is_logged_in` TINYINT(1) DEFAULT 0,
            `chat_type` VARCHAR(20),
            `target_id` INT DEFAULT 0,
            `target_name` VARCHAR(100),
            `message` TEXT,
            INDEX `idx_server_time` (`server_id`, `timestamp`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """
        
        # Chain via callbacks or just fire in sequence (since ALTER/CREATE might race if not chained)
        # However, threaded execution with same pool *might* be sequential if pool size 1, but we have size 3.
        # So chaining is safer.
        
        def step3():
            self.check_and_add_column("openttd_chat_log", "target_name", "VARCHAR(100) AFTER target_id", step4)
        def step2():
             self.check_and_add_column("openttd_chat_log", "is_logged_in", "TINYINT(1) DEFAULT 0 AFTER company_name", step3)
        def step1():
             self.check_and_add_column("openttd_chat_log", "company_name", "VARCHAR(100) AFTER client_ip", step2)
        def step4():
             self.check_and_add_column("openttd_chat_log", "source", "VARCHAR(20) DEFAULT 'GAME' AFTER chat_type")

        self.execute_db(create_query, (), callback=lambda r: step1())

    def run_cleanup(self):
        if self.retention_days <= 0: return
        cutoff_ts = int(time.time()) - (self.retention_days * 86400)
        query = "DELETE FROM openttd_chat_log WHERE timestamp < %s"
        self.execute_db(query, (cutoff_ts,))
        self.last_cleanup = time.time()

    def on_tick(self):
        if time.time() - self.last_cleanup > self.cleanup_interval:
            self.run_cleanup()

    def get_data(self):
        for p in self.client.plugins:
            if p.name == "DataController": return p
        return None

    def get_community(self):
        for p in self.client.plugins:
            if p.name == "Community": return p
        return None

    def is_command(self, msg):
        return msg.startswith("!")

    def on_event(self, pt, pl):
        if pt in [100, 101, 102]: self.register_updates()

        if pt == ServerPacketType.SERVER_CHAT or pt == 119:
            try:
                action = pl[0] 
                client_id = struct.unpack('<I', pl[2:6])[0]
                msg, _ = self.client.unpack_string(pl, 6)

                if not msg: return
                
                # --- SOURCE DETECTION ---
                is_irc_say = False
                irc_nick = "Server"
                msg_source = "GAME" # Default

                if client_id == 1:
                    # Detect IRC Style: "<Frank> Hello"
                    if msg.startswith("<") and "> " in msg:
                        end = msg.find("> ")
                        irc_nick = msg[1:end]
                        msg = msg[end+2:] # Strip prefix
                        is_irc_say = True
                        msg_source = "IRC"
                    
                    # Detect Admin Style: "[Admin: Frank] Hello"
                    elif msg.startswith("[Admin: ") and "] " in msg:
                        end = msg.find("] ")
                        irc_nick = msg[8:end]
                        msg = msg[end+2:]
                        is_irc_say = True
                        msg_source = "ADMIN"
                    
                    # Detect Discord Style: "[Discord: Frank] Hello"
                    elif msg.startswith("[Discord: ") and "] " in msg:
                        end = msg.find("] ")
                        irc_nick = msg[10:end]  # 10 = len("[Discord: ")
                        msg = msg[end+2:]
                        is_irc_say = True
                        msg_source = "DISCORD"
                    
                    # Ignore other server messages
                    if not is_irc_say:
                        return
                
                # Filter regular commands
                if self.is_command(msg): return

                # -- RESOLVE METADATA --
                data = self.get_data()
                comm = self.get_community()
                
                client_name = "Unknown"; client_ip = "0.0.0.0"
                company_id = 255; company_name = "Spectators"; is_logged_in = 0
                
                if is_irc_say:
                    client_id = 0 
                    client_name = irc_nick
                    client_ip = "IRC/Console"
                    is_logged_in = 1
                elif data and client_id in data.clients:
                    c = data.clients[client_id]
                    client_name = c.get('name', 'Unknown')
                    client_ip = c.get('ip', '0.0.0.0')
                    company_id = c.get('company', 255)
                    # Community auth check (sync access to Community.auth_users is allowed)
                    if comm and client_id in comm.auth_users: is_logged_in = 1
                
                if company_id != 255 and data and company_id in data.companies:
                    company_name = data.companies[company_id].get('name', f"Company #{company_id+1}")
                elif company_id == 255: company_name = "Spectators"
                
                # -- RESOLVE TYPE --
                chat_type = "PUBLIC"; target_id = 0; target_name = "All"
                
                if action == 4 or action == 1: 
                    chat_type = "TEAM"
                    target_id = company_id
                    target_name = company_name 
                elif action == 5 or action == 2: 
                    chat_type = "PRIVATE"
                    target_id = 0 
                    target_name = "Private Message" 
                else:
                    chat_type = "PUBLIC"

                # -- INSERT --
                ts = int(time.time())
                dt = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                # Added 'source' column
                query = """
                INSERT INTO openttd_chat_log 
                (server_id, timestamp, datetime, client_id, client_name, client_ip, company_name, is_logged_in, chat_type, source, target_id, target_name, message) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                params = (self.server_id, ts, dt, client_id, client_name, client_ip, company_name, is_logged_in, chat_type, msg_source, target_id, target_name, msg)
                
                self.execute_db(query, params)

            except Exception as e:
                self.client.log(f"[{self.name}] Error: {e}")
