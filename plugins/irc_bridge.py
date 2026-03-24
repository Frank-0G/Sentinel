import socket
import threading
import time
import ssl
import xml.etree.ElementTree as ET
import os
import json 
import re
from plugin_interface import IPlugin
from openttd_types import ServerPacketType, NetworkAction

print("[IRCBridge] Module v1.11-JSON-FIX loaded.")

class IRCBridge(IPlugin):
    def __init__(self, client):
        super().__init__(client)
        self.name = "IRCBridge"
        self.version = "1.11-JSON-FIX"
        
        self.config = {}
        self.irc_auth_map = {} 
        self.admin_users = {}  
        
        self.load_config()

        self.enabled = self._get_conf("irc_enabled", False)
        self.server = self._get_conf("irc_server", "irc.oftc.net")
        self.port = self._get_conf("irc_port", 6667)
        self.nickserv_enabled = self._get_conf("irc_nickserv_enabled", False)
        self.nickname = self._get_conf("irc_nickname", "TTD_Bot")
        
        if self.nickserv_enabled:
            self.username = self._get_conf("irc_nickserv_username", self.nickname)
            self.nickserv_password = self._get_conf("irc_nickserv_password", "")
        else:
            self.username = self.nickname
            self.nickserv_password = ""
        self.server_id = str(self._get_conf("server_id", "99"))
        self.prefix_char = self._get_conf("trigger_prefix", "!")
        
        self.use_ssl = self._get_conf("irc_ssl", self.port == 6697)

        # FIXED: Added Error 12
        self.NETWORK_ERROR_MAP = {
            0: "General Error", 1: "Desync", 2: "Savegame Failed", 3: "Connection Lost",
            4: "Illegal Packet", 5: "NewGRF Mismatch", 6: "Not Expected", 7: "Wrong Revision",
            8: "Name in Use", 9: "Wrong Password", 10: "Player Mismatch", 
            11: "Kicked", 12: "Kicked", 
            13: "Server Full", 14: "Too Many Commands", 15: "Timeout",
            16: "No Server", 17: "No Permission", 18: "Wrong IP", 19: "Incompatible Content"
        }
        
        if "irc_channels" in self.config:
            self.channels = self.config["irc_channels"]
        elif "irc_channel" in self.config:
            chan = self.config["irc_channel"]
            self.channels = {
                chan: {"announcements": True, "gameactions": True, "gamechat": True, "chatlink": False, "statustopic": True}
            }
        else:
            self.channels = {
                "#openttd_controller": {"announcements": True, "gameactions": True, "gamechat": True, "chatlink": False, "statustopic": True}
            }
        
        self.sock = None
        self.running = False
        self.thread = None
        
        self.auth_cache = {} 
        self.whois_queue = [] 
        self.last_whois_time = 0
        self.notified_admins = set()
        
        self.client_cache = {}
        self.company_cache = {} 
        
        # CRASH FIX: Initialized recent_companies
        self.recent_companies = {} 
        
        self.pending_started_companies = set()
        self.pending_start_events = {} # Track CID waiting for company info
        self.last_new_game = 0
        self.cmd_map = {} 
        self.placed_signs = {} 
        self.last_topic_update = 0
        self.topic_update_pending = False

        self.IRC_COLORS = {
            0: "02", 1: "10", 2: "13", 3: "08", 4: "04", 5: "12", 6: "03", 7: "03",
            8: "02", 9: "14", 10: "06", 11: "06", 12: "07", 13: "05", 14: "14", 15: "15"
        }

        self.formats = {
            "chat": "\x02$playername\x02 ($companycolor): $message",
            "joinedgame": "* \x0311--->\x03 \x02$playername\x02 (#$playerid/$playerip/$playercountryshort) has joined the game",
            "joinedspectators": "* \x0311>>\x03 \x02$playername\x02 (#$playerid/$playerip/$playercountryshort) has joined spectators",
            "joinedcompany": "* \x0311>>\x03 \x02$playername\x02 (#$playerid/$playerip/$playercountryshort) has joined company $companyid ($companycolor)",
            "startedcompany": "* \x0311\x02#\x02\x03 \x02$playername\x02 (#$playerid/$playerip/$playercountryshort) has started company $companyid ($companycolor)",
            "leftgame": "* \x0311<---\x03 \x02$playername\x02 (#$playerid/$playerip/$companyid ($companycolor)/$playercountryshort) has left the game ($message)",
            "namechange": "* \x0311<x>\x03 \x02$playername\x02 (#$playerid/$companyid ($companycolor)/$playercountryshort) has changed his/her name to $tplayername",
            "companyrename": "* \x0311<x>\x03 \x02$old_name\x02 (#$companyid) is now known as $companyname",
            "gamerestarted": "* ----- The game has been (re)started -----",
            "companyclosed": "* \x034\x02X\x02\x03 $companyname ($companyid/$companycolor) has been closed ($message)",
            "companyunprotected": "* \x0311--\x03 Password of $companyname ($companyid/$companycolor) has been removed ($message)",
            "placedsign": "* \x0311\x02!!\x03 $playername\x02 (#$playerid/$companyid ($companycolor)/$playercountryshort) has placed a sign: $message",
            "removedsign": "* \x0311\x02!!\x03 $playername\x02 (#$playerid/$companyid ($companycolor)/$playercountryshort) has removed a sign: $message",
            "vehiclecrashed": "* \x037\x02!!\x03\x02 $companyname ($companyid/$companycolor) had a crash ($message).",
            "companymerge": "* \x0311\x02!!\x03\x02 $tcompanyname ($tcompanyid/$tcompanycolor) was bought by $companyname ($companyid/$companycolor).",
            "companytrouble": "* \x037\x02!!\x03\x02 $companyname ($companyid/$companycolor) is in trouble!",
            "mapsaved": "* \x0311\x02!\x02\x03 Game has been saved to $message.",
            "maploaded": "* \x0311\x02!\x02\x03 Saved game has been loaded from $message.",
            "sentinelstarted": "/me 🚀 \x02Sentinel Started and Active!\x02\n/me ----- The game has been (re)started -----",
            "info": "* \x0311\x02!!\x03\x02 $message",
            "warning": "* \x037\x02!!\x03\x02 $message",
            "error": "* \x034\x02!!\x03\x02 $message",
            "votestartedrestartnew": "* \x0311\x02??\x03 $playername\x02 (#$playerid/$companyid ($companycolor)/$playercountryshort) has started a vote to restart the game with a new map.",
            "votestartedrestartsame": "* \x0311\x02??\x03 $playername\x02 (#$playerid/$companyid ($companycolor)/$playercountryshort) has started a vote to restart the game with the same map.",
            "votestartedkick": "* \x0311\x02??\x03 $playername\x02 (#$playerid/$companyid ($companycolor)/$playercountryshort) has started a vote to kick \x02$tplayername\x02 (#$tplayerid/$tcompanyid ($tcompanycolor)/$tplayercountryshort).",
            "votestartedban": "* \x0311\x02??\x03 $playername\x02 (#$playerid/$companyid ($companycolor)/$playercountryshort) has started a vote to ban \x02$tplayername\x02 (#$tplayerid/$tcompanyid ($tcompanycolor)/$tplayercountryshort).",
            "votefinishedsuccess": "* \x039\x02??\x02\x03 Vote by \x02$playername\x02 (#$playerid/$companyid ($companycolor)/$playercountryshort) was accepted.",
            "votefinishedfail": "* \x034\x02??\x02\x03 Vote by \x02$playername\x02 (#$playerid/$companyid ($companycolor)/$playercountryshort) failed.",
            "votefinishedcancel": "* \x0312\x02??\x02\x03 Vote by \x02$playername\x02 (#$playerid/$companyid ($companycolor)/$playercountryshort) was cancelled.",
            "statusmessage": "* \x0311***\x03 Server status: $message",
            "goalreached": "* \x0311***\x03\x02 GOAL REACHED!\x02 $companyname ($companyid/$companycolor) ($message) has won this game!!!",
            "cb_destruction": "* \x037\x02!!\x03 $playername\x02 (#$playerid/$companyid ($companycolor)) caused destruction in $message, claimed by company $tcompanyid ($tcompanyname/$tcompanycolor)"
        }

    def _get_conf(self, key, default):
        val = self.config.get(key, default)
        if isinstance(val, list):
            return val[-1]
        return val

    def load_config(self):
        try:
            base_path = os.getcwd()
            config_path = os.path.join(base_path, "controller_config.xml")
            if os.path.exists(config_path):
                tree = ET.parse(config_path)
                self.config = self._xml_to_dict(tree.getroot())
            
            admins_path = os.path.join(base_path, "admins.json")
            if os.path.exists(admins_path):
                with open(admins_path, "r") as f: 
                    admin_data = json.load(f)
                    self.admin_users = admin_data.get("users", {})
                    irc_data = admin_data.get("irc_auth", {})
                    for admin, irc_acc in irc_data.items():
                        self.irc_auth_map[irc_acc.lower()] = admin
        except Exception as e:
            print(f"[{self.name}] Config Load Error: {e}")

    def _xml_to_dict(self, node):
        if len(node) > 0:
            tags = [child.tag for child in node]
            if len(tags) > 1 and all(t == tags[0] for t in tags):
                return [self._xml_to_dict(child) for child in node]
            d = {}
            for child in node:
                val = self._xml_to_dict(child)
                if child.tag in d:
                    if not isinstance(d[child.tag], list):
                        d[child.tag] = [d[child.tag]]
                    d[child.tag].append(val)
                else:
                    d[child.tag] = val
            return d
        else:
            text = node.text if node.text else ""
            if text.lower() == "true": return True
            if text.lower() == "false": return False
            if text.isdigit(): return int(text)
            return text

    def on_load(self):
        if self.enabled:
            self.client.log(f"[{self.name}] Starting... Connecting to {self.server}:{self.port} (SSL: {self.use_ssl})")
            self.running = True
            self.thread = threading.Thread(target=self.irc_loop, daemon=True)
            self.thread.start()

    def on_unload(self):
        self.running = False
        if self.sock:
            try: self.send_raw(f"QUIT :Reloading..."); self.sock.close()
            except: pass

    # --- HELPERS ---
    def get_data(self): return self.client.get_service("DataController")
    def get_manager(self): return self.client.get_service("CommandManager")
    def get_admin_manager(self): return self.client.get_service("AdminManager")
    def get_geoip(self): return self.client.get_service("GeoIPService")

    def get_cid_by_name(self, name):
        for cid, data in self.client_cache.items():
            if data['name'] == name: return cid
        return None

    def get_iso(self, ip):
        svc = self.get_geoip()
        if not svc or ip == "0.0.0.0": return "??"
        return svc.resolve_iso(ip)

    def get_admin_username(self, irc_account):
        if not irc_account: return None
        return self.irc_auth_map.get(irc_account.lower())

    def send_raw(self, data):
        if self.sock:
            try: self.sock.send(f"{data}\r\n".encode("utf-8"))
            except Exception as e:
                print(f"[IRCBridge] Send Error: {e}")
                try: self.sock.close()
                except: pass
                self.sock = None

    def send_to_channel(self, msg, type_flag):
        if not self.sock: return
        # Handle multiline messages
        lines = msg.split("\n")
        for line in lines:
            if not line.strip(): continue
            for chan, flags in self.channels.items():
                if flags.get(type_flag, False):
                    if line.startswith("/me "):
                        self.send_raw(f"PRIVMSG {chan} :\x01ACTION {line[4:]}\x01")
                    else:
                        self.send_raw(f"PRIVMSG {chan} :{line}")
                    time.sleep(0.5) # Prevent flooding

    def send_msg(self, msg, target=None):
        if not target:
            target = list(self.channels.keys())[0] if self.channels else "#openttd"
        # Handle multiline messages
        lines = msg.split("\n")
        for line in lines:
            if line.strip():
                if line.startswith("/me "):
                    self.send_raw(f"PRIVMSG {target} :\x01ACTION {line[4:]}\x01")
                else:
                    self.send_raw(f"PRIVMSG {target} :{line}")
                time.sleep(0.5)
    
    def send_notice(self, target, msg):
        if self.sock:
            lines = msg.split("\n")
            for line in lines:
                if line.strip():
                    self.send_raw(f"NOTICE {target} :{line}")
                    time.sleep(0.5)

    def format_msg(self, key, **kwargs):
        if key not in self.formats: return ""
        template = self.formats[key]
        for k, v in kwargs.items():
            val = str(v) if v is not None else "?"
            template = template.replace(f"${k}", val)
        return template

    def get_company_color_name(self, cid):
        if cid == 255: return "Spectator"
        col_id = 0
        if cid in self.company_cache:
            col_id = self.company_cache[cid].get('color', 0)
        else:
            data = self.get_data()
            if data:
                co = data.get_company(cid)
                if co: col_id = co.get('color', 0)
        
        data = self.get_data()
        cname = "Color"
        if data: cname, _ = data.get_color_info(col_id)
        
        irc_code = self.IRC_COLORS.get(col_id, "14")
        return f"\x03{irc_code}{cname}\x03"

    def get_company_name(self, cid):
        if cid in self.company_cache: return self.company_cache[cid]['name']
        data = self.get_data()
        if data:
            co = data.get_company(cid)
            if co: return co.get('name', f"Company {cid+1}")
        return f"Company {cid+1}"

    def get_player_vars(self, cid):
        name = "Unknown"; ip = "0.0.0.0"; iso = "??"; co_id = 255
        if cid in self.client_cache:
            c = self.client_cache[cid]
            name = c['name']; ip = c['ip']; iso = c['iso']; co_id = c['company']
        return {
            "playername": name,
            "playerid": cid,
            "playerip": ip,
            "playercountryshort": iso,
            "companyid": co_id + 1 if co_id != 255 else "Spec",
            "companycolor": self.get_company_color_name(co_id)
        }

    # --- EVENTS ---
    def on_tick(self):
        now = time.time()
        self.process_topic_update()
        if now - self.last_whois_time > 2.0 and self.whois_queue:
            nick = self.whois_queue.pop(0)
            self.send_raw(f"WHOIS {nick}")
            self.last_whois_time = now

    def process_topic_update(self):
        if not self.topic_update_pending: return
        if time.time() - self.last_topic_update < 10: return
        
        self.last_topic_update = time.time()
        self.topic_update_pending = False
        
        try:
            s_name = self.client.game_cfg.get('server_name', f"Server {self.server_id}")
            year = self.client.current_year
            data = self.get_data()
            cl_count = len([c for cid, c in data.clients.items() if cid != 1]) if data else 0
            max_cl = self.client.game_cfg.get('max_clients', 25)
            co_count = len(data.companies) if data else 0
            max_co = self.client.game_cfg.get('max_companies', 15)
            topic_str = f"{s_name} | Year: {year} | Clients: {cl_count}/{max_cl} | Companies: {co_count}/{max_co}"
            
            for chan, flags in self.channels.items():
                if flags.get("statustopic", True):
                    self.send_raw(f"TOPIC {chan} :{topic_str}")
        except: pass

    def on_wrapper_log(self, text):
        if "Map generation percentage complete: 90" in text: pass # on_new_game triggered via protocol
        
        # Started Company Logic
        # Format: *** Frank has started a new company (#1)
        if "has started a new company" in text:
            try:
                # Regex to extract name and company ID
                match = re.search(r"\*\*\* (.*) has started a new company \(#(\d+)\)", text.strip())
                if match:
                    name = match.group(1).strip()
                    human_id = int(match.group(2))
                    company_id = human_id - 1
                    
                    cid = self.get_cid_by_name(name)
                    if cid is not None:
                        # Queue this event until we get company info (color)
                        if company_id not in self.company_cache:
                            self.pending_start_events[company_id] = cid
                            self.pending_started_companies.add(company_id)
                        else:
                            self.send_company_started(cid, company_id)
                            self.pending_started_companies.add(company_id)
            except: pass

        if "CmdSaveGame: Saved game to" in text:
            try:
                filename = text.split("Saved game to ", 1)[1].strip()
                msg = self.format_msg("mapsaved", message=filename)
                self.send_to_channel("/me " + msg, "announcements")
            except: pass
        if "Loading map" in text and "success" in text:
             msg = self.format_msg("maploaded", message="Server")
             self.send_to_channel("/me " + msg, "announcements")

    # --- EVENT TRIGGERS ---
    def on_player_join(self, cid, name, ip, company_id):
        if cid == 1: return
        
        # If client is already in cache, this is just a polled update, not a new join
        if cid in self.client_cache:
            old = self.client_cache[cid]
            # If name or company changed during poll, delegate to on_player_update for notifications
            if old['name'] != name or old['company'] != company_id:
                self.on_player_update(cid, name, company_id)
            else:
                # Just update IP if it was unknown
                if old.get('ip') == '?':
                    self.client_cache[cid]['ip'] = ip
            return

        self.topic_update_pending = True
        iso = self.get_iso(ip)
        self.client_cache[cid] = {'name': name, 'ip': ip, 'company': company_id, 'iso': iso}
        msg = self.format_msg("joinedgame", playername=name, playerid=cid, playerip=ip, playercountryshort=iso)
        self.send_to_channel("/me " + msg, "gameactions")
        if company_id == 255:
            msg = self.format_msg("joinedspectators", playername=name, playerid=cid, playerip=ip, playercountryshort=iso)
            self.send_to_channel("/me " + msg, "gameactions")
        else:
            ccolor = self.get_company_color_name(company_id)
            msg = self.format_msg("joinedcompany", playername=name, playerid=cid, playerip=ip, playercountryshort=iso, companyid=company_id+1, companycolor=ccolor)
            self.send_to_channel("/me " + msg, "gameactions")
            if company_id in self.pending_started_companies:
                self.send_company_started(cid, company_id)
                self.pending_started_companies.remove(company_id)

    def on_player_quit(self, cid):
        if cid == 1: return
        self.topic_update_pending = True
        if cid in self.client_cache:
            old = self.client_cache[cid]
            ccolor = self.get_company_color_name(old['company'])
            msg = self.format_msg("leftgame", playername=old['name'], playerid=cid, playerip=old['ip'], companyid=old['company']+1 if old['company']!=255 else "Spec", companycolor=ccolor, playercountryshort=old['iso'], message="leaving")
            self.send_to_channel("/me " + msg, "gameactions")
            del self.client_cache[cid]

    def on_player_error(self, cid, err):
        if cid == 1: return
        self.topic_update_pending = True
        err_str = self.NETWORK_ERROR_MAP.get(err, f"Error {err}")
        if cid in self.client_cache:
            old = self.client_cache[cid]
            ccolor = self.get_company_color_name(old['company'])
            msg = self.format_msg("leftgame", playername=old['name'], playerid=cid, playerip=old['ip'], companyid=old['company']+1 if old['company']!=255 else "Spec", companycolor=ccolor, playercountryshort=old['iso'], message=err_str)
            self.send_to_channel("/me " + msg, "gameactions")
            del self.client_cache[cid]

    def on_company_created(self, company_id):
        self.pending_started_companies.add(company_id)
        self.topic_update_pending = True

    def on_company_remove(self, cid, reason):
        msg = self.format_msg("companyclosed", companyname=self.get_company_name(cid), companyid=cid+1, companycolor=self.get_company_color_name(cid), message="Bankrupt" if reason==1 else "Manual")
        self.send_to_channel("/me " + msg, "announcements")
        if cid in self.company_cache: del self.company_cache[cid]
        if cid in self.pending_started_companies: self.pending_started_companies.remove(cid)
        self.topic_update_pending = True

    def on_new_game(self):
        self.recent_companies = {} # Reset
        if time.time() - self.last_new_game < 20: return
        self.last_new_game = time.time()
        self.client_cache.clear()
        self.company_cache.clear()
        self.placed_signs.clear()
        self.pending_started_companies.clear()
        self.send_to_channel("/me " + self.format_msg("gamerestarted"), "gameactions")
        self.topic_update_pending = True

    def on_company_info(self, cid, name, man, col, prot, pw, founded, is_ai):
        old_name = None
        if cid in self.company_cache:
             old_name = self.company_cache[cid].get('name')

        was_pw = self.company_cache[cid].get('passworded', False) if cid in self.company_cache else False
        self.company_cache[cid] = {'name': name, 'color': col, 'passworded': pw}
        
        if old_name and old_name != name:
             msg = self.format_msg("companyrename", old_name=old_name, companyname=name, companyid=cid+1, companycolor=self.get_company_color_name(cid))
             self.send_to_channel("/me " + msg, "gameactions")

        if was_pw and not pw:
            msg = self.format_msg("companyunprotected", companyname=name, companyid=cid+1, companycolor=self.get_company_color_name(cid), message="manual removal")
            self.send_to_channel("/me " + msg, "announcements")
        
        # Check if we were waiting to send a "Started Company" message for this ID
        if cid in self.pending_start_events:
            player_cid = self.pending_start_events.pop(cid)
            self.send_company_started(player_cid, cid)

    def on_player_update(self, cid, name, company_id):
        if cid == 1: return
        self.topic_update_pending = True
        if cid not in self.client_cache:
            self.client_cache[cid] = {'name': name, 'ip': '?', 'company': company_id, 'iso': '?'}
            return
        old = self.client_cache[cid]
        iso = old['iso']
        if old['name'] != name:
            ccolor = self.get_company_color_name(old['company'])
            msg = self.format_msg("namechange", playername=old['name'], playerid=cid, companyid=old['company']+1 if old['company']!=255 else "Spec", companycolor=ccolor, playercountryshort=iso, tplayername=name)
            self.send_to_channel("/me " + msg, "gameactions")
            self.client_cache[cid]['name'] = name
        if old['company'] != company_id:
            ccolor = self.get_company_color_name(company_id)
            if company_id == 255:
                 msg = self.format_msg("joinedspectators", playername=name, playerid=cid, playerip=old['ip'], playercountryshort=iso)
                 self.send_to_channel("/me " + msg, "gameactions")
            else:
                 msg = self.format_msg("joinedcompany", playername=name, playerid=cid, playerip=old['ip'], playercountryshort=iso, companyid=company_id+1, companycolor=ccolor)
                 self.send_to_channel("/me " + msg, "gameactions")
                 # NOTE: send_company_started is now handled via on_wrapper_log + on_company_info/on_player_update 
                 # logic to ensure color is ready. 
                 # We still clear pending here if it fired.
                 if company_id in self.pending_started_companies:
                     self.pending_started_companies.remove(company_id)
            self.client_cache[cid]['company'] = company_id
        
        self.queue_topic_update()

    def send_company_started(self, cid, company_id):
        c = self.client_cache[cid]
        ccolor = self.get_company_color_name(company_id)
        msg = self.format_msg("startedcompany", playername=c['name'], playerid=cid, playerip=c['ip'], playercountryshort=c['iso'], companyid=company_id+1, companycolor=ccolor)
        self.send_to_channel("/me " + msg, "gameactions")

    def on_chat(self, cid, msg, action, dest_type):
        if cid == 1: return
        if action == NetworkAction.NETWORK_ACTION_CHAT:
            sender = self.client_cache[cid]['name'] if cid in self.client_cache else f"Client #{cid}"
            ccolor = self.get_company_color_name(self.client_cache[cid]['company']) if cid in self.client_cache else "Spectator"
            out = self.format_msg("chat", playername=sender, companycolor=ccolor, message=msg)
            self.send_to_channel(out, "gamechat")

    def on_event(self, pt, pl):
        if pt == ServerPacketType.SERVER_CHAT:
             try:
                msg, _ = self.client.unpack_string(pl, 6)
                if "GOAL REACHED!" in msg: 
                    # Clean up the message to avoid "Double GOAL REACHED"
                    clean_msg = msg.replace("GOAL REACHED!", "").replace("---", "").strip()
                    self.send_to_channel(f"/me \x0311***\x03\x02 \x0304GOAL REACHED!\x03 {clean_msg}", "gameactions")
             except: pass
    
    def on_data_event(self, etype, data):
        if etype == "game_saved": 
            msg = self.format_msg("mapsaved", message="Storage")
            self.send_to_channel("/me " + msg, "announcements")

    def get_crash_reason_str(self, reason):
        reasons = {
            0: "train collision",
            1: "aircraft crash",
            2: "level crossing collision",
            3: "destroyed by UFO"
        }
        return reasons.get(reason, f"reason {reason}")

    def on_gamescript_event(self, event_type, data):
        if event_type == "vehiclecrash":
            cid = data.get("company", 255)
            vid = data.get("vehicleid", "?")
            site = data.get("crashsite", 0)
            reason = data.get("crashreason", -1)
            
            reason_str = self.get_crash_reason_str(reason)
            site_hex = hex(site) if isinstance(site, int) else site
            msg_text = f"vehicle ID {vid}: {reason_str} at {site_hex}"
            
            msg = self.format_msg("vehiclecrashed", 
                companyname=self.get_company_name(cid), 
                companyid=cid+1, 
                companycolor=self.get_company_color_name(cid), 
                message=msg_text)
            self.send_to_channel("/me " + msg, "announcements")
            self.topic_update_pending = True
            
        elif event_type == "companymerge":
            old_cid = data.get("oldcompany", 255)
            new_cid = data.get("newcompany", 255)
            msg = self.format_msg("companymerge", 
                companyname=self.get_company_name(old_cid), 
                companyid=old_cid+1, 
                companycolor=self.get_company_color_name(old_cid),
                tcompanyname=self.get_company_name(new_cid),
                tcompanyid=new_cid+1,
                tcompanycolor=self.get_company_color_name(new_cid))
            self.send_to_channel("/me " + msg, "announcements")
            self.topic_update_pending = True

    # --- SIGNS ---
    def on_command_name(self, cmd_id, cmd_name):
        self.cmd_map[cmd_id] = cmd_name

    def on_do_command(self, client_id, cmd_id, p1, p2, tile, text, frame):
        cmd_name = self.cmd_map.get(cmd_id, "")
        if cmd_name == "CmdPlaceSign":
            self.placed_signs[tile] = {'owner': client_id}
        elif cmd_name == "CmdRenameSign":
            if not text:
                if tile in self.placed_signs: 
                    old = self.placed_signs[tile]
                    vars = self.get_player_vars(client_id)
                    vars['message'] = f"\"{old.get('text', 'Sign')}\""
                    msg = self.format_msg("removedsign", **vars)
                    self.send_to_channel("/me " + msg, "gameactions")
                    del self.placed_signs[tile]
            else:
                self.placed_signs[tile] = {'owner': client_id, 'text': text}
                vars = self.get_player_vars(client_id)
                vars['message'] = f"\"{text}\""
                msg = self.format_msg("placedsign", **vars)
                self.send_to_channel("/me " + msg, "gameactions")

    def irc_loop(self):
        try:
            while self.running:
                nickserv_identified = False
                try:
                    raw_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    raw_sock.settimeout(300) 
                    if self.use_ssl:
                        context = ssl.create_default_context()
                        context.check_hostname = False
                        context.verify_mode = ssl.CERT_NONE
                        self.sock = context.wrap_socket(raw_sock, server_hostname=self.server)
                    else:
                        self.sock = raw_sock
                    self.sock.connect((self.server, self.port))
                    self.send_raw(f"USER {self.username} 0 * :{self.username}")
                    self.send_raw(f"NICK {self.nickname}")
                    buffer = ""; joined = False; current_nick = self.nickname
                    self.topic_update_pending = True 
                    
                    while self.running:
                        if not self.sock: raise Exception("Socket closed locally")
                        chunk = self.sock.recv(2048).decode("utf-8", errors="ignore")
                        if not chunk:
                            print(f"[{self.name}] Disconnected by server.")
                            raise Exception("Connection closed")
                        buffer += chunk
                        while "\r\n" in buffer:
                            line, buffer = buffer.split("\r\n", 1)
                            if line.startswith("PING"): 
                                self.send_raw(f"PONG {line.split()[1]}")
                            self.process_irc_line(line)
                            parts = line.split()
                            if len(parts) > 1:
                                if (" 001 " in line or " 376 " in line) and not joined:
                                    if self.nickserv_enabled and self.nickserv_password and not nickserv_identified:
                                        self.send_raw(f"PRIVMSG NickServ :IDENTIFY {self.username} {self.nickserv_password}")
                                        self.client.log(f"[{self.name}] IRC Identify message has been sent.")
                                        nickserv_identified = True
                                        time.sleep(1)
                                    for chan in self.channels:
                                        self.send_raw(f"JOIN {chan}")
                                    # Send startup message
                                    msg = self.formats.get("sentinelstarted", "/me 🚀 \x02Sentinel Started and Active!\x02\n/me ----- The game has been (re)started -----")
                                    self.send_to_channel(msg, "announcements")
                                    joined = True
                                    
                                    self.client.log(f"[{self.name}] IRC Joined channels.")
                                if parts[1] == "433": 
                                    self.send_raw(f"NICK {self.nickname}_")
                                if "PRIVMSG" in line: self.handle_privmsg(line)
                except: 
                    time.sleep(10)
        except: pass

    def process_irc_line(self, line):
        try:
            parts = line.split()
            if len(parts) < 3: return
            if parts[1] == "330":
                target = parts[3]; account = parts[4]
                admin_user = self.get_admin_username(account)
                if admin_user:
                    self.auth_cache[target] = admin_user
                    if target not in self.notified_admins:
                         self.send_notice(target, f"Logged in as '{admin_user}'")
                         self.notified_admins.add(target)
            elif parts[1] == "JOIN":
                nick = parts[0].split("!")[0][1:]
                if nick != self.nickname: self.whois_queue.append(nick)
        except: pass

    def handle_privmsg(self, line):
        try:
            parts = line.split(" :", 1)
            msg = parts[1].strip()
            
            meta = parts[0].split()
            if len(meta) < 3: return
            
            sender = meta[0].split("!")[0][1:]
            msg_target = meta[2]
            
            # If message was sent to a channel, reply to that channel.
            # Otherwise (PM), reply to the sender.
            reply_target = msg_target if msg_target.startswith("#") else sender
            
            mgr = self.get_manager()
            
            trigger_found = False; cmd_payload = ""
            if msg.startswith(self.prefix_char):
                trigger_found = True; cmd_payload = msg[len(self.prefix_char):]
            elif msg.startswith(self.server_id):
                trigger_found = True; cmd_payload = msg[len(self.server_id):]

            if trigger_found and mgr:
                irc_account = self.auth_cache.get(sender)
                admin_user = self.get_admin_username(irc_account)
                is_admin = (admin_user is not None)
                if not irc_account: self.whois_queue.append(sender)
                success, reply = mgr.handle_command(cmd_payload.strip(), source="irc", is_admin=is_admin, admin_name=admin_user if admin_user else sender, context={'irc_target': reply_target})
                if success and reply: self.send_msg(reply, target=reply_target)
            else:
                # Chat Link Logic
                # Check if msg_target is a configured channel with chatlink enabled
                if msg_target in self.channels and self.channels[msg_target].get("chatlink", False):
                        # Relay to game
                        session = self.client.get_service("OpenttdSession")
                        if session:
                            sanitized = msg.replace('"', "'")
                            session.send_chat_message(f"<{sender}> {sanitized}")
        except: pass
