import threading
import time
import json
import struct
import random
import hashlib
from datetime import datetime, timedelta

from plugin_interface import IPlugin
from openttd_types import ServerPacketType, NetworkAction, AdminUpdateType

# --- CONSTANTS ---
VIP_GROUP_ID = 14  
VIP_FORUM_RANK = 15

class Community(IPlugin):
    def __init__(self, client):
        super().__init__(client)
        self.name = "Community"
        self.version = "4.0-ASYNC-DB"
        
        self.auth_users = {}  
        self.players = {} 
        self.cached_logins = []  
        self.vip_cache = {}      
        self.sponsor_name = ""
        self.warned_players = set() 
        self.name_checks = {} 
        
        self.last_stat_sync = time.time()
        self.last_vip_refresh = 0
        self.last_sponsor_announce = time.time()
        self.last_name_check = time.time()
        
        self.db_config = {}
        self.server_id = 99

    def get_data(self):
        for p in self.client.plugins:
            if p.name == "DataController": return p
        return None

    def get_mysql(self):
        return self.client.get_service("MySQL")

    def execute_db(self, query, params=(), callback=None, fetch=False):
        mysql = self.get_mysql()
        if mysql and self.db_config:
            mysql.execute_query(self.db_config, query, params, callback, fetch)

    def refresh_vip_cache(self):
        def cb(res):
            new_cache = {}
            if res:
                for row in res: new_cache[row['username'].lower()] = row
            self.vip_cache = new_cache
        self.execute_db("SELECT * FROM openttd_vip_memberships", (), cb, fetch=True)

    def get_game_sponsor(self):
        if not self.sponsor_name:
            def cb(res):
                if res:
                    self.sponsor_name = res[0]['username']
                    self.execute_db("UPDATE openttd_vip_memberships SET last_sponsored = UNIX_TIMESTAMP(NOW()) WHERE username = %s", (self.sponsor_name,))
            self.execute_db("SELECT username FROM `openttd_vip_memberships` ORDER BY last_sponsored ASC limit 1", (), cb, fetch=True)

    def get_db_username(self, player_name, callback):
        def cb(res):
            callback(res[0]['username'] if res else "")
        self.execute_db("SELECT username FROM openttd_users WHERE username = %s", (player_name,), cb, fetch=True)

    def unix_to_dt(self, ts):
        return datetime.fromtimestamp(float(ts)).strftime('%Y-%m-%d %H:%M:%S')

    def is_name_registered_async(self, name, callback):
        def cb(res):
            callback(True if res else False)
        self.execute_db("SELECT id FROM openttd_users WHERE username=%s", (name,), cb, fetch=True)

    def is_vip(self, name):
        return name.lower() in self.vip_cache

    def get_vip_details(self, name):
        return self.vip_cache.get(name.lower())

    def on_load(self):
        self.db_config = self.client.config.get("mysql_config", {}).copy()
        if not self.db_config: return
        
        if 'port' in self.db_config: self.db_config['port'] = int(self.db_config['port'])
        valid_keys = ['user', 'password', 'host', 'database', 'port', 'unix_socket', 'flags']
        self.db_config = {k: v for k, v in self.db_config.items() if k in valid_keys}

        self.server_id = self.client.config.get("server_id", 99)
        self.refresh_vip_cache()
        self.get_game_sponsor()

    def on_unload(self):
        if self.db_config:
            self.execute_db("DELETE FROM openttd_serverStats WHERE serverID = %s", (self.server_id,))
            self.execute_db("DELETE FROM openttd_serverViewer WHERE serverID = %s", (self.server_id,))

    def on_tick(self):
        if not self.db_config: return
        now = time.time()
        if now - self.last_name_check > 5:
            self.last_name_check = now
            self.check_names_tick()
        if now - self.last_stat_sync > 30:
            self.last_stat_sync = now
            self.sync_server_stats()
        if now - self.last_vip_refresh > 300:
            self.last_vip_refresh = now
            self.refresh_vip_cache()
        if now - self.last_sponsor_announce > 900: 
            self.last_sponsor_announce = now
            self.announce_sponsor()

    def on_event(self, pt, pl):
        if pt == ServerPacketType.SERVER_CLIENT_INFO: self.handle_client_join(pl)
        elif pt == ServerPacketType.SERVER_CLIENT_UPDATE: self.handle_client_update(pl)
        elif pt == ServerPacketType.SERVER_CLIENT_QUIT: self.handle_client_quit(pl)
        elif pt == ServerPacketType.SERVER_NEWGAME: self.on_restarted()

    def check_name_violation(self, cid, name):
        def cb(is_reg):
            if is_reg:
                self._handle_violation_confirm(cid, name)
            else:
                if cid in self.name_checks: self.name_checks[cid]['blocked'] = True
        self.is_name_registered_async(name, cb)

    def _handle_violation_confirm(self, cid, name):
        current_user = self.auth_users.get(cid)
        if current_user:
            db_clean = current_user.strip().lower()
            pkt_clean = name.strip().lower()
            if db_clean == pkt_clean: return 
            self.client.log(f"[Community] Dropping session for #{cid}. DB='{current_user}' vs Packet='{name}'")
            del self.auth_users[cid]
            self.client.send_rcon(f"say_client {cid} \"Name change to a registered name, logged you out. Make sure to relogin before switching back to your own username!\"")

        if cid in self.name_checks and self.name_checks[cid]['blocked']:
            self.client.send_rcon(f"kick {cid} \"Repeatedly taking a registered nick without valid login.\"")
            return

        if cid not in self.name_checks:
            self.client.send_rcon(f"say_client {cid} \"This name is registered. If you are the owner of this account please login now, otherwise change your name.\"")
            self.name_checks[cid] = {'taken': time.time(), 'warned': time.time(), 'blocked': False}

    def check_names_tick(self):
        now = time.time()
        to_remove = []
        data = self.get_data()
        if not data: return

        for cid, check in self.name_checks.items():
            if cid not in data.clients: 
                to_remove.append(cid); continue
            
            client_data = data.clients[cid]
            if check['blocked']: continue 
            
            if self.auth_users.get(cid, "").lower() == client_data['name'].lower():
                to_remove.append(cid); continue

            if now - check['taken'] > 30:
                new_name = f"Unregistered{random.randint(100000, 999999)}"
                self.client.send_rcon(f"client_name {cid} \"{new_name}\"")
                self.client.send_rcon(f"say_client {cid} \"Your name was changed, because you have taken a registered name. If this is your name, please login before you change your name again.\"")
                check['blocked'] = True
            elif now - check['warned'] > 10:
                self.client.send_rcon(f"say_client {cid} \"This name is registered. If you are the owner of this account please login now, otherwise change your name.\"")
                check['warned'] = now

        for cid in to_remove: del self.name_checks[cid]

    def announce_sponsor(self):
        if self.sponsor_name: self.client.send_rcon(f"say \"*** This current game is sponsored by our VIP member: * {self.sponsor_name} * :-)\"")

    def on_restarted(self):
        self.sponsor_name = ""
        self.get_game_sponsor()
        self.name_checks.clear()
        self.warned_players.clear() 
        self.auth_users.clear()

    def handle_client_join(self, pl):
        try:
            cid = struct.unpack('<I', pl[0:4])[0]
            ip, off = self.client.unpack_string(pl, 4)
            name, off = self.client.unpack_string(pl, off)
            threading.Thread(target=self.delayed_join_logic, args=(cid, ip, name), daemon=True).start()
        except: pass

    def delayed_join_logic(self, cid, ip, name):
        time.sleep(1.0)
        try:
            if cid not in self.auth_users:
                now = time.time()
                self.cached_logins = [c for c in self.cached_logins if now - c['time'] < 600]
                found = next((c for c in self.cached_logins if c['ip'] == ip and c['name'] == name), None)
                if found:
                    self.auth_users[cid] = found['username']
                    self.client.send_rcon(f"say_client {cid} \"Welcome back {found['username']}! Auto-logged in.\"")
                    self.cached_logins.remove(found)
                    if cid in self.warned_players: self.warned_players.remove(cid)
                    if cid in self.name_checks: del self.name_checks[cid]

            if cid not in self.auth_users and cid not in self.warned_players:
                self.check_name_violation(cid, name)
        except: pass

    def handle_client_update(self, pl):
        try:
            cid = struct.unpack('<I', pl[0:4])[0]
            name, off = self.client.unpack_string(pl, 4)
            self.check_name_violation(cid, name)
        except: pass

    def handle_client_quit(self, pl):
        try:
            cid = struct.unpack('<I', pl[0:4])[0]
            if cid in self.auth_users:
                username = self.auth_users[cid]
                data = self.get_data()
                if data and cid in data.clients:
                    c = data.clients[cid]
                    self.cached_logins.append({'ip': c['ip'], 'name': c['name'], 'username': username, 'time': time.time()})
                del self.auth_users[cid]
            if cid in self.name_checks: del self.name_checks[cid]
            if cid in self.warned_players: self.warned_players.remove(cid)
        except: pass

    def process_command(self, cmd, args, source="game", admin_name="Unknown", cid=None):
        if isinstance(args, str): args = args.split()
        
        def send_reply(msg):
            if not msg: return
            if source == "game":
                session = self.client.get_service("OpenttdSession")
                if session:
                    for line in msg.split("\n"): session.send_private_message(cid, line)
            elif source == "irc":
                irc = self.client.get_service("IRCBridge")
                if irc:
                    for line in msg.split("\n"): 
                        irc.send_to_channel(line, "announcements")
                        time.sleep(0.1) # Small delay to prevent flood kick/ordering issues
            elif source == "discord":
                discord = self.client.get_service("DiscordBridge")
                if discord:
                    discord._dispatch_discord(discord._send_msg(msg))
                else:
                    self.client.log("[Community] ERROR: DiscordBridge service not found!")

        if cmd == "login":
            if source == "irc": return "Login is only supported in-game."
            self.cmd_login(cid, args, send_reply)
            return None # ASYNC
            
        elif cmd == "logout": return self.cmd_logout(cid)
        elif cmd == "me": return self.cmd_me(cid)
        
        elif cmd == "vipstatus":
            self.cmd_vipstatus(args, cid, source, send_reply)
            return None # ASYNC
            
        elif cmd == "sponsor":
            return f"This game is sponsored by our VIP member: * {self.sponsor_name} * :-)\nWant to sponsor a game to? Please use trigger !vipmembership for more information."
        
        elif cmd == "vipmembership":
            return "Thank you for your interest in the BTPro VIP membership :-)\nThe BTPro VIP Membership contains many advantages. Please check our website (openttd.btpro.nl) for more info!"
            
        elif cmd == "addvip":
            self.cmd_addvip(args, source, admin_name, send_reply)
            return None # ASYNC
            
        elif cmd == "extendvip":
            self.cmd_extendvip(args, source, admin_name, send_reply)
            return None # ASYNC
            
        elif cmd == "whois":
            self.cmd_whois(args, cid, send_reply)
            return None # ASYNC
            
        elif cmd == "rank":
            self.cmd_rank(cid, source, send_reply)
            return None # ASYNC
            
        return None

    def cmd_login(self, cid, args, reply_func):
        if cid in self.auth_users:
            reply_func(f"You are already logged in as '{self.auth_users[cid]}'.")
            return

        if not args:
            reply_func("Usage: !login <token> OR !login <user> <pass>")
            return
            
        data = self.get_data()
        client_data = data.get_client(cid) if data else None
        if not client_data:
            reply_func("Syncing data... retry in 2s.")
            return

        def db_cb(res):
            if not res:
                reply_func("Login failed. Invalid token or credentials.")
                return

            row = res[0]
            username = row['username'].strip()
            
            # Reset token if used
            if len(args) == 1:
                self.execute_db("UPDATE openttd_users SET token=NULL, tokenvalid=NULL WHERE username=%s", (username,))

            self.auth_users[cid] = username
            self.client.log(f"[Community] Logged in #{cid} as '{username}'")
            
            if cid in self.warned_players: self.warned_players.remove(cid)
            if cid in self.name_checks: del self.name_checks[cid]

            if client_data['name'].lower() != username.lower(): 
                self.client.send_rcon(f"client_name {cid} \"{username}\"")

            self.client.send_rcon(f"say \"{username} just logged in! {username} is a registered member of openttd.btpro.nl :-)\"")

            is_donator = str(row.get('donator', '0')) == '1'
            is_hw = str(row.get('hardwareDonator', '0')) == '1'
            is_op = str(row.get('serverOperator', '0')) == '1'
            
            if is_donator: self.client.send_rcon(f"say \"*** DONATOR *** < {username} is a well respected BTPro Community Donator.\"")
            if is_hw: self.client.send_rcon(f"say \"*** HARDWARE DONATOR *** < {username} is a well respected BTPro Community Hardware Donator.\"")
            if is_op: self.client.send_rcon(f"say \"*** SERVER OPERATOR *** < {username} is a BTPro Server Operator, Better be nice to this person ;-) \"")

            if self.is_vip(username):
                vip = self.get_vip_details(username)
                if vip['lifetime'] == 1:
                    self.client.send_rcon(f"say \"*** LIFETIME VIP MEMBER *** < {username} is a LIFETIME BTPro VIP Member!\"")
                else:
                    self.client.send_rcon(f"say \"*** VIP MEMBER *** < {username} is a BTPro VIP Member!\"")
                    try:
                        expire = datetime.fromtimestamp(float(vip['timestamp_expire']))
                        diff = expire - datetime.now()
                        reply_func(f"Your VIP Membership will expire in: {diff.days} Days, {diff.seconds//3600} Hours and {(diff.seconds//60)%60} Minutes.")
                    except: pass
            else:
                 reply_func("BTPro VIP Membership Status: NOT Active\nFor more info about our VIP Membership, use trigger !vipmembership")

        if len(args) == 1:
            token = args[0].strip()
            self.execute_db("SELECT username, donator, donateAmount, hardwareDonator, serverOperator FROM openttd_users WHERE block=0 AND token=%s AND UTC_TIMESTAMP() < tokenvalid", (token,), db_cb, fetch=True)
        elif len(args) == 2:
            user = args[0].lower(); pwd = args[1]
            md5_pwd = hashlib.md5(pwd.encode('utf-8')).hexdigest()
            self.execute_db("SELECT username, donator, donateAmount, hardwareDonator, serverOperator FROM openttd_users WHERE block=0 AND lower(username)=%s AND password=%s", (user, md5_pwd), db_cb, fetch=True)

    def cmd_logout(self, cid):
        if cid in self.auth_users: del self.auth_users[cid]; return "OK, bye."
        return "Can't logout, not logged in."

    def cmd_me(self, cid):
        username = self.auth_users.get(cid)
        if username:
            reply = [f"You are logged in as '{username}'."]
            if self.is_vip(username):
                vip = self.get_vip_details(username)
                if vip['lifetime'] == 1:
                    reply.append("You are a ***LIFETIME*** BTPro VIP Member! \\o/")
                else:
                    reply.append("You are a BTPro VIP Member! \\o/")
                    expire = datetime.fromtimestamp(float(vip['timestamp_expire']))
                    diff = expire - datetime.now()
                    reply.append(f"Your VIP Membership will expire in: {diff.days} days.")
            return "\n".join(reply)
        return "You aren't logged in."

    def cmd_vipstatus(self, args, cid, source, reply_func):
        if source == "irc" and not args:
            count = len(self.vip_cache)
            msg = f"--- Current number of VIP Members: {count} ---" if count > 0 else "--- No BTPro VIP Members were found in the Database ---"
            reply_func(msg)
            return

        target = args[0] if args else self.auth_users.get(cid)
        if not target: reply_func("Usage: !vipstatus <username>"); return

        def name_check_cb(is_reg):
            if is_reg:
                if self.is_vip(target):
                    vip = self.get_vip_details(target)
                    started = self.unix_to_dt(vip['timestamp_activated'])
                    if vip['lifetime'] == 1:
                        reply_func(f"{vip['username']} is a ***LIFETIME*** BTPro VIP Member!\nSince: {started}")
                    else:
                        expire = datetime.fromtimestamp(float(vip['timestamp_expire']))
                        diff = expire - datetime.now()
                        reply_func(f"{vip['username']} is a BTPro VIP Member!\nSince: {started}\nExpires in: {diff.days} Days.")
                else:
                     def get_real_name_cb(real_name):
                        reply_func(f"{real_name} is Registered, but is NOT a BTPro VIP Member!")
                     self.get_db_username(target, get_real_name_cb)
            else:
                reply_func(f"The name: {target} is NOT registered.")
        
        self.is_name_registered_async(target, name_check_cb)

    def cmd_addvip(self, args, source, admin_name, reply_func):
        reply_func("AddVIP not fully ported to async yet.") # Simplified for brevity unless requested

    def cmd_extendvip(self, args, source, admin_name, reply_func):
         reply_func("ExtendVIP not fully ported to async yet.") # Simplified 

    def cmd_whois(self, args, cid, reply_func):
        if not args: reply_func("Usage: !whois <#ID/Name>"); return
        data = self.get_data()
        if not data: return
        target = args[0]
        found = None
        
        if target.startswith("#") and target[1:].isdigit():
            t_cid = int(target[1:])
            if t_cid in data.clients: found = (t_cid, data.clients[t_cid])
        else:
            target_lower = target.lower()
            for c, d in data.clients.items():
                if target_lower in d['name'].lower():
                    found = (c, d); break
        
        if found:
            t_cid, d = found
            username = self.auth_users.get(t_cid)
            if username:
                reply_func(f"This player is logged in as '{username}'.")
            else:
                reply_func("This player isn't logged in.")
        else:
            reply_func("Player not found.")

    def cmd_rank(self, cid, source, reply_func):
        now = datetime.now()
        from_time = f"{now.year}-01-01 00:00:00"
        
        # Nested callbacks for sequential queries
        query_global = """SELECT openttd_users.username, SUM(openttd_gameresults.score) as score FROM openttd_gameresults INNER JOIN openttd_users ON( openttd_gameresults.userid = openttd_users.id ) INNER JOIN openttd_games ON( openttd_gameresults.gameid = openttd_games.gameid AND openttd_gameresults.serverid = openttd_games.serverid) WHERE openttd_games.endtime BETWEEN %s AND SYSDATE() GROUP BY username ORDER BY score DESC LIMIT 5"""
        
        def cb_global(res_global):
            query_server = """SELECT openttd_users.username, SUM(openttd_gameresults.score) as score FROM openttd_gameresults INNER JOIN openttd_users ON( openttd_gameresults.userid = openttd_users.id ) INNER JOIN openttd_games ON( openttd_gameresults.gameid = openttd_games.gameid AND openttd_gameresults.serverid = openttd_games.serverid) WHERE openttd_games.endtime BETWEEN %s AND SYSDATE() AND openttd_gameresults.serverid = %s GROUP BY username ORDER BY score DESC LIMIT 5"""
            
            def cb_server(res_server):
                reply = []
                
                if source == "irc":
                     reply.append(" Community High Scores - Top 5 players ")
                     reply.append("---------------------------------------")
                     reply.append("| Rank |       Nickname       | Score |")
                     if res_global:
                         for idx, row in enumerate(res_global):
                             name = row['username'][:20] 
                             reply.append(f"| {idx+1:3}. | {name:<20} | {int(row['score']):5} |")
                     reply.append("---------------------------------------")
                     reply.append(" ")
                     reply.append(f" Server {self.server_id} High Scores - Top 5 players")
                     reply.append("---------------------------------------")
                     reply.append("| Rank |       Nickname       | Score |")
                     if res_server:
                         for idx, row in enumerate(res_server):
                             name = row['username'][:20]
                             reply.append(f"| {idx+1:3}. | {name:<20} | {int(row['score']):5} |")
                     reply.append("---------------------------------------")

                else:
                    reply.append("--== Community High Scores - Top 5 Players ==--")
                    if res_global:
                        for idx, row in enumerate(res_global):
                            reply.append(f"Rank #{idx+1} is {row['username']} -- {int(row['score'])} points")
                    
                    reply.append(f"--== Server {self.server_id} High Scores - Top 5 players ==--")
                    if res_server:
                        for idx, row in enumerate(res_server):
                             reply.append(f"Rank #{idx+1} is {row['username']} -- {int(row['score'])} points")
                
                reply_func("\n".join(reply))
            
            self.execute_db(query_server, (from_time, self.server_id), cb_server, fetch=True)
            
        self.execute_db(query_global, (from_time,), cb_global, fetch=True)

    def sync_server_stats(self):
        data = self.get_data()
        if not data: return
        # ... stats sync logic (writes only) ...
        # Can be done with threaded execute_db calls
        dash = data
        spectators = 0
        for cid, d in dash.clients.items():
            if d.get('company') == 255: spectators += 1
        
        self.execute_db("DELETE FROM openttd_serverStats WHERE serverID=%s", (self.server_id,))
        self.execute_db("""INSERT INTO openttd_serverStats (serverID, serverName, GameYear, ClientsCurrent, ClientsMax, CompaniesCurrent, CompaniesMax, SpectatorsCurrent, CurrentSponsor, Winlimit, Performance, Population, Cargo, Income, Cash, Rating, CValue, Beegoal) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""", (self.server_id, dash.server_info.get('name', 'Server'), dash.server_info.get('year', 0), len(dash.clients) - 1, self.client.game_cfg.get('max_clients', 25), len(dash.companies), self.client.game_cfg.get('max_companies', 15), spectators, self.sponsor_name, "0", "0", "0", "0", "0", "0", "0", "0", "0"))
        
        self.execute_db("DELETE FROM openttd_serverViewer WHERE serverID=%s", (self.server_id,))
        for cid, comp in dash.companies.items():
            is_logged_in = 0
            for client_id, client_data in dash.clients.items():
                if client_data.get('company') == cid and client_id in self.auth_users:
                    is_logged_in = 1
                    break
            nickname = comp.get('name', 'Unnamed')
            self.execute_db("""INSERT INTO openttd_serverViewer (serverID, companyId, companyName, value, performance, loggedin, nickname, foundingYear, loan) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""", (self.server_id, cid, comp.get('name', 'Unnamed'), comp.get('value', 0), 0, is_logged_in, nickname, comp.get('start_year', dash.server_info.get('year', 0)), comp.get('loan', 0)))
