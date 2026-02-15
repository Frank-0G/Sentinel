import json
import os
import struct
import traceback
import threading
import time
from plugin_interface import IPlugin
from openttd_types import ServerPacketType, AdminPacketType, AdminUpdateType, AdminUpdateFrequency

# Colors
C_RESET = "\x0f"; C_BOLD = "\x02"; C_CYAN = "\x0311"; C_GREY = "\x0314"

class CommandManager(IPlugin):
    def __init__(self, client):
        super().__init__(client)
        self.name = "CommandManager"
        self.version = "6.29-GS-SUB-FIX" # Version bumped
        
        self.triggers = {}
        self.alias_map = {}
        self.prefix = "!"
        self.shutdown_pending = False
        self.last_pending_announce = 0
        self.locked_companies = set()
        self.pending_resets = set()
        
        self.IRC_COLORS = {
            0: "02", 1: "10", 2: "13", 3: "08", 4: "04", 5: "12", 6: "03", 7: "03",
            8: "02", 9: "14", 10: "06", 11: "06", 12: "07", 13: "05", 14: "14", 15: "15"
        }
        
        self.admin_native_commands = [
            "shutdown", "kick", "ban", "move", "rcon", "say", "reloadplugins", 
            "cancelvote", "pause", "unpause", "reset", "empty", "lockcompany", 
            "unlockcompany", "news", "goalreached", "awarning"
        ]
        
        self.native_commands = [
            "login", "logout", "me", "vipstatus", "sponsor", "addvip", "extendvip", 
            "vipmembership", "whois", "rank", "help", "status", "server", "version", 
            "players", "companies", "cv", "shutdown", "name", "kick", "saveme", 
            "savedcompanies", "restart", "rules", "admin", "rcon", "say", "ban", 
            "pause", "unpause", "reset", "move", "empty", "lockcompany", "unlockcompany",
            "plugins", "reloadplugins", "vote", "yes", "no", "votekick", "voteban", 
            "voterestart", "votereset", "cancelvote", "votestatus", "alogin", "alogout",
            "resetme", "limits", "seed", "news", "screenshot",
            # Goal System
            "goal", "progress", "townstats", "claimed", "goalreached", "awarning"
        ]

        self.help_text = {
            "help": ["Usage: !help [<Command>]", "Shows available commands or help for a specific command."],
            "players": ["Usage: !players", "Shows a list of all players currently on the server."],
            "companies": ["Usage: !companies", "Shows a list of all companies currently on the server."],
            "server": ["Usage: !server", "Shows information about the server, e.g. its name."],
            "status": ["Usage: !status", "Shows basic game status information (current/max companies, players, year)."],
            "version": ["Usage: !version", "Shows the version of the OpenTTD server and Sentinel."],
            "rcon": ["Usage: !rcon <Command>", "Executes a command on the server console."],
            "say": ["Usage: !say <Text>", "Sends a message to the server chat."],
            "kick": ["Usage: !kick <#ID/Name> [reason]", "Kicks a player."],
            "ban": ["Usage: !ban <#ID/Name> [reason]", "Bans a player."],
            "move": ["Usage: !move <#ID/Name> <Company ID>", "Moves a player to a specific company (255 for Spectator)."],
            "reset": ["Usage: !reset <Company ID>", "Resets (closes) a company."],
            "resetme": ["Usage: !resetme", "Flags your company to be reset as soon as you leave it."],
            "empty": ["Usage: !empty <Company ID>", "Empties a company by moving all players to spectators."],
            "lockcompany": ["Usage: !lockcompany <Company ID>", "Empties and locks a company."],
            "unlockcompany": ["Usage: !unlockcompany <Company ID>", "Unlocks a previously locked company."],
            "pause": ["Usage: !pause", "Pauses the game."],
            "unpause": ["Usage: !unpause", "Unpauses the game."],
            "shutdown": ["Usage: !shutdown [now]", "Shuts down the server."],
            "restart": ["Usage: !restart [now]", "Restarts the Server."],
            "cv": ["Usage: !cv", "Shows the goal of the current game script."],
            "rules": ["Usage: !rules", "Shows the server rules."],
            "admin": ["Usage: !admin", "Lists available admin commands."],
            "login": ["Usage: !login <user> <pass>", "Log in to your community account."],
            "vote": ["Usage: !vote", "Cast a YES vote for the active poll."],
            "votekick": ["Usage: !votekick <id>", "Start a vote to kick a player."],
            "voteban": ["Usage: !voteban <id>", "Start a vote to ban a player."],
            "voterestart": ["Usage: !voterestart", "Start a vote to restart the game."],
            "votereset": ["Usage: !votereset <co_id>", "Start a vote to reset a company."],
            "cancelvote": ["Usage: !cancelvote", "Cancel the active vote (Admin only)."],
            "alogin": ["Usage: !alogin <user> <pass>", "Log in as an In-Game Admin."],
            "limits": ["Usage: !limits", "Shows server limits."],
            "seed": ["Usage: !seed", "Shows the random seed of the current map."],
            "news": ["Usage: !news <text>", "Broadcasts a news message."],
            "screenshot": ["Usage: !screenshot <tile_id>", "Takes a screenshot at the specified location."],
            
            # Goal System
            "goal": ["Usage: !goal", "Shows the current scoreboard and goal progress."],
            "progress": ["Usage: !progress", "Displays a visual progress bar of the leading company."],
            "townstats": ["Usage: !townstats <CompanyID>", "Displays CityBuilder town requirements for a specific company."],
            "claimed": ["Usage: !claimed", "Lists all currently claimed towns and their owners."],
            "goalreached": ["Usage: !goalreached", "Admin only: Forces the current game to end and declares the leader as winner."],
            "awarning": ["Usage: !awarning <CompanyID>", "Admin only: Issues a warning to a company."]
        }

        self.local_handlers = {
            "help": self.cmd_help,
            "players": self.cmd_players,
            "rules": self.cmd_rules,
            "admin": self.cmd_admin_help,
            "rcon": self.cmd_rcon,
            "say": self.cmd_say,
            "kick": self.cmd_kick,
            "ban": self.cmd_ban,
            "move": self.cmd_move,
            "pause": self.cmd_pause,
            "unpause": self.cmd_unpause,
            "reset": self.cmd_reset,
            "empty": self.cmd_empty,
            "lockcompany": self.cmd_lockcompany,
            "unlockcompany": self.cmd_unlockcompany,
            "shutdown": self.cmd_shutdown,
            "reloadplugins": self.cmd_reloadplugins,
            "status": self.cmd_status,
            "server": self.cmd_server,
            "version": self.cmd_version,
            "companies": self.cmd_companies,
            "cv": self.cmd_cv,
            "plugins": self.cmd_plugins,
            "alogin": self.cmd_auth,
            "alogout": self.cmd_auth,
            "vote": self.cmd_vote_cast,
            "yes": self.cmd_vote_cast, 
            "votekick": self.cmd_vote_start,
            "voteban": self.cmd_vote_start,
            "voterestart": self.cmd_vote_start,
            "votereset": self.cmd_vote_start,
            "cancelvote": self.cmd_vote_cancel,
            "votestatus": self.cmd_vote_status,
            "resetme": self.cmd_resetme,
            "limits": self.cmd_limits,
            "seed": self.cmd_seed,
            "news": self.cmd_news,
            "screenshot": self.cmd_screenshot,
            
            # Goal System Proxy Handlers
            "goal": self.proxy_goal_cmd,
            "progress": self.proxy_goal_cmd,
            "townstats": self.proxy_goal_cmd,
            "claimed": self.proxy_goal_cmd,
            "goalreached": self.proxy_goal_cmd,
            "awarning": self.proxy_goal_cmd
        }
        
        self.load_triggers()

    def on_connected(self):
        # FIX: Added subscription for GAMESCRIPT (9) so we receive JSON packets!
        self.client.log(f"[{self.name}] Connected. Subscribing to CHAT, CLIENT_INFO, and GAMESCRIPT...")
        self.client.send_packet(AdminPacketType.ADMIN_UPDATE_FREQUENCY, struct.pack('<HH', 5, 0x40)) # Chat
        self.client.send_packet(AdminPacketType.ADMIN_UPDATE_FREQUENCY, struct.pack('<HH', 1, 0x40)) # Client Info
        self.client.send_packet(AdminPacketType.ADMIN_UPDATE_FREQUENCY, struct.pack('<HH', 9, 0x40)) # GameScript

    def _get_service_safe(self, name):
        if hasattr(self.client, 'get_service'): return self.client.get_service(name)
        for p in self.client.plugins:
            if p.name == name: return p
        return None

    def get_session(self): return self._get_service_safe("OpenttdSession")
    def get_data(self): return self._get_service_safe("DataController")
    def get_admin_manager(self): return self._get_service_safe("AdminManager")
    def get_community(self): return self._get_service_safe("Community")
    def get_geoip(self): return self._get_service_safe("GeoIPService")

    def load_triggers(self):
        try:
            self.prefix = self.client.config.get("trigger_prefix", "!")
            trigger_file = self.client.config.get("trigger_file", "triggers.json")
            
            if os.path.exists(trigger_file):
                with open(trigger_file, "r") as f:
                    for item in json.load(f):
                        if "name" not in item: continue
                        self.triggers[item["name"].lower()] = item
                        for a in item.get("aliases", []): 
                            self.alias_map[a.lower()] = item["name"].lower()
            else:
                self.client.log(f"[{self.name}] Warning: {trigger_file} not found.")
        except Exception as e:
            self.client.log(f"[{self.name}] Error loading triggers: {e}")

    def requires_admin(self, cmd_str, source="game"):
        try:
            cmd = cmd_str.split()[0].lower()
            if cmd not in self.triggers and cmd in self.alias_map: cmd = self.alias_map[cmd]
            
            public_cmds = [
                "vote", "yes", "no", "alogin", "alogout", "resetme", "limits", 
                "seed", "screenshot", "status", "server", "players", "companies", 
                "goal", "progress", "townstats", "claimed"
            ]
            if cmd in public_cmds: return False
            
            # say is public from IRC and Discord, but admin from in-game
            if cmd == "say": return True if source == "game" else False
            
            conf = self.triggers.get(cmd)
            if conf: return conf.get("admin", False)
            
            if cmd in self.admin_native_commands: return True
            return False
        except: return True 

    def resolve_target(self, arg):
        data = self.get_data()
        if not data: return None
        clean_arg = arg.lstrip('#')
        if clean_arg.isdigit(): return int(clean_arg)
        search = arg.lower()
        candidates = []
        for cid, info in data.clients.items():
            name = info.get('name', '').lower()
            if name == search: return cid
            if search in name: candidates.append(cid)
        if len(candidates) == 1: return candidates[0]
        return None

    def on_tick(self):
        if self.shutdown_pending:
            data = self.get_data()
            if data and len(data.companies) == 0:
                self.perform_shutdown("Graceful shutdown: All companies closed.")
            elif time.time() - self.last_pending_announce > 60:
                self.last_pending_announce = time.time()
                session = self.get_session()
                if session:
                    session.send_server_message("WARNING: Shutdown pending! Waiting for companies to close...")

    def perform_shutdown(self, reason):
        self.shutdown_pending = False
        self.client.shutdown_intentional = True
        self.client.log(f"[{self.name}] {reason}")
        session = self.get_session()
        if session:
            session.send_server_message("Server Shutting Down...")
            session.execute_raw("quit")
        def delayed_exit():
            time.sleep(3.0); os._exit(0)
        threading.Thread(target=delayed_exit, daemon=True).start()

    def on_player_quit(self, cid): self.trigger_reset_check()
    def on_player_update(self, cid, name, company_id): self.trigger_reset_check()
    def trigger_reset_check(self): threading.Timer(1.0, self._check_resets_impl).start()

    def _check_resets_impl(self):
        if not self.pending_resets: return
        data = self.get_data()
        if not data: return
        session = self.get_session()
        to_remove = set()
        for co_id in list(self.pending_resets):
            count = 0
            for client in data.clients.values():
                if client.get('company') == co_id:
                    count += 1
            if count == 0:
                if session:
                    session.reset_company(co_id)
                    session.send_server_message(f"Company #{co_id+1} has been reset (empty).")
                to_remove.add(co_id)
        self.pending_resets -= to_remove

    def on_event(self, pt, pl):
        if pt == 19 or pt == 119 or pt == ServerPacketType.SERVER_CHAT:
            try:
                if len(pl) < 6: return
                cid = struct.unpack('<I', pl[2:6])[0]
                msg, _ = self.client.unpack_string(pl, 6)
                if cid == 1: return 
                if msg.startswith(self.prefix):
                    cmd_part = msg[len(self.prefix):].strip()
                    self.client.log(f"[{self.name}] CMD: {cmd_part} from Client {cid}")
                    success, reply = self.handle_command(cmd_part, source="game", context={'cid': cid})
                    if success and reply:
                        session = self.get_session()
                        if session:
                            for line in reply.split("\n"): session.send_private_message(cid, line)
            except Exception as e: self.client.log(f"[{self.name}] Chat Error: {e}")
        elif pt == 108 or pt == 8:
            try:
                cid = struct.unpack('<I', pl[0:4])[0]
                company_id = pl[4]
                if company_id in self.locked_companies:
                    session = self.get_session()
                    if session:
                        session.move_player(cid, 255)
                        session.send_private_message(cid, f"WARNING: Company #{company_id+1} is LOCKED by Administrators.")
            except: pass

    def handle_command(self, cmd_str, source="irc", is_admin=False, admin_name="Unknown", context=None):
        try:
            parts = cmd_str.split(" ", 1)
            cmd = parts[0].lower()
            args = parts[1].split() if len(parts) > 1 else []
            if cmd not in self.triggers and cmd in self.alias_map: cmd = self.alias_map[cmd]
            
            admin_user = None; community_user = None
            if source == "game":
                cid = context.get('cid')
                alogin = self._get_service_safe("AdminLogin")
                if alogin: admin_user = alogin.get_authenticated_user(cid)
                comm = self.get_community()
                if comm and cid in comm.auth_users: community_user = comm.auth_users[cid]
            elif source == "irc":
                am = self.get_admin_manager()
                if am: admin_user = am.get_admin_user_from_irc(admin_name); community_user = admin_user
            elif source == "discord":
                alogin = self._get_service_safe("AdminLogin")
                if alogin and context and 'discord_id' in context:
                    auth_key = f"discord:{context['discord_id']}"
                    admin_user = alogin.get_authenticated_user(auth_key)

            effective_name = admin_user if admin_user else (community_user if community_user else admin_name)
            
            if self.requires_admin(cmd, source):
                am = self.get_admin_manager()
                if not admin_user:
                    if cmd != "alogin": return True, "Permission Denied. You must log in via !alogin first."
                if admin_user and am:
                    if not am.has_privilege(admin_user, cmd): return True, "Permission Denied."

            if context is None: context = {}
            context['is_admin_auth'] = (admin_user is not None)
            context['effective_user'] = community_user if community_user else admin_user
            context['nick'] = admin_name 

            context['nick'] = admin_name 

            conf = self.triggers.get(cmd)
            if conf and isinstance(conf, dict):
                if source == "irc" and not conf.get("irc", True): return False, None
                if source == "game" and not conf.get("in_game", True): return False, None
                if source == "discord" and not conf.get("discord", True): return False, None

            if cmd in self.local_handlers:
                reply = []
                self.local_handlers[cmd](cmd, args, reply, source, effective_name, context)
                return True, "\n".join(reply) if reply else None

            if cmd in ["login", "logout", "me", "vipstatus", "sponsor", "addvip", "extendvip", "vipmembership", "whois", "rank"]:
                comm = self.get_community()
                cid = context.get('cid') if context else None
                if comm: return True, comm.process_command(cmd, args, source, effective_name, cid)
                return True, "Community plugin missing or not loaded."

            if cmd == "restart" and not args: 
                restarter = self._get_service_safe("AutoRestart")
                if restarter:
                    cid = context.get('cid') if context else None
                    return True, restarter.process_command(cmd, args, source, effective_name, cid)
            
            if conf:
                resp = conf.get("response")
                if isinstance(resp, list): return True, "\n".join(resp)
                return True, str(resp)

            return False, None
        except Exception as e:
            self.client.log(f"[{self.name}] CMD Error: {e}")
            traceback.print_exc()
            return True, "Error executing command."

    def _announce(self, text, is_action=False):
        game_text = f"*** {text}" if is_action else text
        session = self.get_session()
        if session: session.send_server_message(game_text)
        
        irc = self._get_service_safe("IRCBridge")
        if irc: 
            irc_text = f"/me {text}" if is_action else text
            irc.send_to_channel(irc_text, "announcements")
            
        discord = self._get_service_safe("DiscordBridge")
        if discord:
            discord_text = f"**{text}**" if is_action else text
            discord._dispatch_discord(discord._send_msg(discord_text))

    def _get_company_name(self, co_id):
        data = self.get_data()
        try:
            display_id = co_id + 1
            if data and co_id in data.companies:
                name = data.companies[co_id].get('name', 'Unnamed')
                return f"{name} (#{display_id})"
            return f"Company #{display_id}"
        except: return f"Company #{co_id+1}"

    def cmd_cv(self, cmd, args, reply, source, admin_name, context):
        gs = self.client.get_service("GoalSystem")
        if gs: gs.cmd_goal(cmd, args, reply, source, context)
        else: reply.append("Goal: Money")

    def cmd_resetme(self, cmd, args, reply, source, admin_name, context):
        if source != "game": 
            reply.append("This command can only be used in-game.")
            return
        cid = context.get('cid')
        data = self.get_data()
        if not data or cid not in data.clients: return
        client = data.clients[cid]
        co_id = client.get('company', 255)
        if co_id == 255:
            reply.append("You must be in a company to reset it.")
            return
        self.pending_resets.add(co_id)
        reply.append("Company flagged for reset. It will be reset automatically as soon as you leave (or move to Spectators).")

    def cmd_reset(self, cmd, args, reply, source, admin_name, context):
        if not args: reply.append("Usage: !reset <company_id>"); return
        s = self.get_session(); data = self.get_data()
        try: 
            user_input = int(args[0])
            cid = user_input - 1
        except: cid = -1
        
        if cid < 0: reply.append("Invalid company ID."); return

        moved_count = 0
        if data and s:
            for client_id, client_info in data.clients.items():
                if client_info.get('company') == cid:
                    s.move_player(client_id, 255)
                    moved_count += 1
            
        if s: 
            s.reset_company(cid)
            reply.append(f"OK, emptying ({moved_count} moved) and resetting company #{user_input}.")
            co_name = self._get_company_name(cid)
            self._announce(f"Admin {context.get('nick', '?')} (Account '{admin_name}') has reset {co_name} (method: movespec)", is_action=True)

    def cmd_lockcompany(self, cmd, args, reply, source, admin_name, context):
        if not args: reply.append("Usage: !lockcompany <CompanyID>"); return
        try: 
            user_input = int(args[0])
            cid = user_input - 1
        except: cid = -1
        if cid < 0: reply.append("Invalid ID"); return

        self.locked_companies.add(cid)
        s = self.get_session(); data = self.get_data()
        
        moved_count = 0
        if data and s:
            for client_id, client_info in data.clients.items():
                if client_info.get('company') == cid:
                    s.move_player(client_id, 255)
                    moved_count += 1

        if s: 
            s.execute_raw(f"company_pw {cid+1} \"LOCKED_BY_ADMIN\"")
            reply.append(f"OK, emptying ({moved_count} moved) and locking company #{user_input}.")
            co_name = self._get_company_name(cid)
            self._announce(f"Admin {context.get('nick', '?')} (Account '{admin_name}') has locked {co_name}", is_action=True)

    def cmd_unlockcompany(self, cmd, args, reply, source, admin_name, context): 
        if not args: reply.append("Usage: !unlockcompany <CompanyID>"); return
        try: 
            cid = int(args[0])-1
            self.get_session().execute_raw(f"company_pw {cid+1} \"\"")
            self.locked_companies.discard(cid)
            reply.append(f"Unlocked #{cid+1}")
            co_name = self._get_company_name(cid)
            self._announce(f"Admin {context.get('nick', '?')} (Account '{admin_name}') has unlocked {co_name}", is_action=True)
        except: pass

    def cmd_empty(self, cmd, args, reply, source, admin_name, context):
        if not args: reply.append("Usage: !empty <id>"); return
        try: 
            user_input = int(args[0])
            co = user_input - 1
        except: return
        data = self.get_data(); sess = self.get_session(); count=0
        if data and sess:
            for cid,v in data.clients.items():
                if v.get('company')==co: sess.move_player(cid,255); count+=1
        reply.append(f"Emptied company. ({count} moved)")
        co_name = self._get_company_name(co)
        self._announce(f"Admin {context.get('nick', '?')} (Account '{admin_name}') has cleared {co_name}", is_action=True)

    def cmd_kick(self, cmd, args, reply, source, admin_name, context):
        if not args: reply.append("Usage: !kick <id> [reason]"); return
        target = self.resolve_target(args[0])
        if target:
            sess = self.get_session(); data = self.get_data()
            reason = " ".join(args[1:]) if len(args)>1 else "Admin Kick"
            target_name = data.clients[target]['name'] if data and target in data.clients else f"#{target}"
            sess.kick_player(target, reason)
            reply.append(f"OK, kicking player #{target}")
            self._announce(f"Admin {context.get('nick', '?')} (Account '{admin_name}') has kicked player {target_name}", is_action=True)
        else: reply.append("Target not found.")

    def cmd_ban(self, cmd, args, reply, source, admin_name, context):
        if not args: reply.append("Usage: !ban <id> [reason]"); return
        target = self.resolve_target(args[0])
        if target:
            sess = self.get_session(); data = self.get_data()
            reason = " ".join(args[1:]) if len(args)>1 else "Admin Ban"
            target_name = data.clients[target]['name'] if data and target in data.clients else f"#{target}"
            sess.ban_player(target, reason)
            reply.append(f"OK, banning player #{target}")
            self._announce(f"Admin {context.get('nick', '?')} (Account '{admin_name}') has banned player {target_name}", is_action=True)
        else: reply.append("Target not found.")

    def cmd_move(self, cmd, args, reply, source, admin_name, context): 
        if len(args) < 2: reply.append("Usage: !move <id> <company>"); return
        t = self.resolve_target(args[0])
        if t: 
            self.get_session().move_player(t, args[1])
            data = self.get_data()
            target_name = data.clients[t]['name'] if data and t in data.clients else f"#{t}"
            try:
                co_id = int(args[1])
                co_name = f"Company {co_id+1}" if co_id != 255 else "Spectators"
                if data and co_id != 255 and co_id in data.companies:
                    co_name = f"{data.companies[co_id].get('name', 'Unnamed')} (#{co_id+1})"
            except: co_name = args[1]
            reply.append(f"OK, moving player #{t}")
            self._announce(f"Admin {context.get('nick', '?')} (Account '{admin_name}') has moved player {target_name} to {co_name}", is_action=True)
        else: reply.append("Target not found.")

    def cmd_pause(self, cmd, args, reply, source, admin_name, context):
        self.get_session().pause_game()
        reply.append("Paused.")
        self._announce(f"Admin {context.get('nick', '?')} (Account '{admin_name}') has requested to pause the game.", is_action=True)

    def cmd_unpause(self, cmd, args, reply, source, admin_name, context):
        self.get_session().unpause_game()
        reply.append("Unpaused.")
        self._announce(f"Admin {context.get('nick', '?')} (Account '{admin_name}') has requested to unpause the game.", is_action=True)

    def cmd_shutdown(self, cmd, args, reply, source, admin_name, context):
        self.perform_shutdown("Admin")
        reply.append("Shutting down.")
        self._announce(f"Admin {context.get('nick', '?')} (Account '{admin_name}') has requested to shutdown the server.", is_action=True)

    def cmd_restart(self, cmd, args, reply, source, admin_name, context):
        self._announce(f"Admin {context.get('nick', '?')} (Account '{admin_name}') has requested to restart the server.", is_action=True)
        self.perform_shutdown("Restart")
        reply.append("Restarting...")

    def cmd_screenshot(self, cmd, args, reply, source, admin_name, context):
        if not args:
            reply.append("Usage: !screenshot <tile_id> OR !screenshot <x> <y>")
            return
        
        session = self.get_session()
        if not session:
            reply.append("Session not available.")
            return

        result = ""
        if len(args) >= 2:
            result = session.take_screenshot(args[0], args[1])
        else:
            result = session.take_screenshot(args[0])
        
        reply.append(result)

    def cmd_server(self, cmd, args, reply, source, admin_name, context): 
        name = self.client.game_cfg.get("server_name", "Sentinel")
        reply.append(f"This server's name is: {name}")

    def cmd_status(self, cmd, args, reply, source, admin_name, context): 
        d = self.get_data()
        cl_count = 0
        sp_count = 0
        if d:
            for cid, v in d.clients.items():
                if cid != 1: 
                    cl_count += 1
                    if v.get('company') == 255:
                        sp_count += 1
        
        co_count = len(d.companies) if d else 0
        max_cl = self.client.game_cfg.get('max_clients', 25)
        max_co = self.client.game_cfg.get('max_companies', 15)
        year = self.client.current_year
        
        if source == "irc":
            reply.append(f"Server status: Players: {cl_count}/{max_cl} - Companies: {co_count}/{max_co} - Year: {year}")
        else:
            reply.append(f"Server status: Players: {cl_count}/{max_cl} ({sp_count}) - Companies: {co_count}/{max_co} - Year: {year}")

    def cmd_players(self, cmd, args, reply, source, admin_name, context):
        data = self.get_data(); geoip = self.get_geoip(); found = False
        if not data: return
        for cid, d in sorted(getattr(data, "clients", {}).items()):
            if cid == 1: continue 
            found = True
            name = d.get("name", "?"); ip = d.get("ip", "?"); company_id = d.get("company", 255)
            if company_id == 255: company_label = "Spectator"
            else:
                company_label = str(company_id + 1)
                try:
                    co = data.get_company(company_id)
                    if co and hasattr(data, "get_color_info"):
                        color_name, _ = data.get_color_info(co.get("color", 0))
                        if source == "irc":
                            color_code = self.IRC_COLORS.get(co.get("color", 0), "01")
                            company_label = f"\x03{color_code}{color_name}\x0f"
                        else: company_label = color_name
                except: pass
            location = "Unknown"
            try:
                if geoip and ip not in (None, "", "?", "0.0.0.0"):
                    if hasattr(geoip, "resolve"): location = geoip.resolve(ip)
                    elif hasattr(geoip, "resolve_country"): location = geoip.resolve_country(ip)
            except: location = "Unknown"
            reply.append(f"#{cid} '{name}' ({company_label}) - Location: {location} - Connection: {ip}")
        if not found: reply.append("No clients currently connected.")

    def cmd_companies(self, cmd, args, reply, source, admin_name, context):
        try: self.client.send_poll(AdminUpdateType.ADMIN_UPDATE_COMPANY_ECONOMY, 0)
        except: pass
        data = self.get_data()
        if not data: return
        companies = getattr(data, "companies", {}) or {}
        if len(companies) == 0: reply.append("No companies formed."); return
        for company_id, d in sorted(companies.items(), key=lambda kv: kv[0]):
            name = d.get("name", "").strip()
            manager = d.get("manager", "").strip()
            if not name: name = f"{manager} & Co" if manager else "Unnamed"
            try: color_id = int(d.get("color", 0))
            except: color_id = 0
            if hasattr(data, "get_color_info"): color_name, _ = data.get_color_info(color_id)
            else: color_name = "Unknown"
            display_color = color_name
            if source == "irc":
                color_code = self.IRC_COLORS.get(color_id, "01")
                display_color = f"\x03{color_code}{color_name}\x0f"
            founded = d.get("founded_year", d.get("foundingYear", d.get("founded", 0)))
            try: founded_i = int(founded) if founded is not None else 0
            except: founded_i = 0
            founded_str = str(founded_i) if founded_i > 0 else "Unknown"
            veh = d.get("vehicles", (0, 0, 0, 0))
            if not isinstance(veh, (list, tuple)): veh = (0, 0, 0, 0)
            veh = list(veh) + [0, 0, 0, 0]
            t, r, p, s = int(veh[0]), int(veh[1]), int(veh[2]), int(veh[3])
            passworded = bool(d.get("passworded", False))
            reply.append(f"{company_id + 1} ({display_color}) '{name}' - Founded: {founded_str} - T/R/P/S: {t}/{r}/{p}/{s} - Password: {'yes' if passworded else 'no'}")

    def cmd_say(self, cmd, args, reply, source, admin_name, context): 
        if args: self.get_session().send_chat_message(f"[{admin_name}] {' '.join(args)}")

    def cmd_rcon(self, cmd, args, reply, source, admin_name, context):
        self.get_session().execute_raw(" ".join(args))
        reply.append("Exec.")

    def cmd_news(self, cmd, args, reply, source, admin_name, context):
        self.get_session().send_server_message(f"[NEWS] {' '.join(args)}")

    def cmd_seed(self, cmd, args, reply, source, admin_name, context):
        seed = self.client.current_seed
        if seed == "Unknown":
            seed = self.client.game_cfg.get('generation_seed', 'Unknown')
        reply.append(f"The current seed is: {seed}")

    def cmd_limits(self, cmd, args, reply, source, admin_name, context):
        cfg = self.client.game_cfg
        t = cfg.get("max_trains", 500)
        r = cfg.get("max_roadveh", 500)
        s = cfg.get("max_ships", 500)
        a = cfg.get("max_aircraft", 500)
        ss = cfg.get("station_spread", 12)
        tl = cfg.get("max_train_length", 7)
        reply.append(f"Current vehicle limits: Trains: {t}, Road vehicles: {r}, Ships: {s}, Aircraft: {a} | Station spread: {ss} tile(s), Train length: {tl} tile(s)")

    def cmd_rules(self, cmd, args, reply, source, admin_name, context):
        reply.append("Rules: Be nice.")

    def cmd_version(self, cmd, args, reply, source, admin_name, context):
        reply.append(f"OpenTTD: v14.1 with Sentinel: v{self.version}")

    def cmd_admin_help(self, cmd, args, reply, source, admin_name, context):
        reply.append("Admin Commands: !rcon, !say, !kick, !ban, !pause, !unpause, !reset, !shutdown, !move, !empty, !lockcompany, !unlockcompany, !plugins, !reloadplugins, !cancelvote, !news")

    def cmd_plugins(self, cmd, args, reply, source, admin_name, context):
        reply.append(f"Loaded Plugins: {len(self.client.plugins)}")

    def cmd_reloadplugins(self, cmd, args, reply, source, admin_name, context):
        reply.append("Reload not available in this version.")

    def cmd_vote_start(self, cmd, args, reply, source, admin_name, context): 
        v = self._get_service_safe("VoteSystem")
        if v: v.start_vote(cmd.replace("vote",""), args[0] if args else "", args[0] if args else "", admin_name, context.get('cid',0))

    def cmd_vote_cast(self, cmd, args, reply, source, admin_name, context):
        v = self._get_service_safe("VoteSystem")
        if v: reply.append(v.cast_vote(context.get('cid',0), admin_name))

    def cmd_vote_cancel(self, cmd, args, reply, source, admin_name, context):
        v = self._get_service_safe("VoteSystem")
        if v: v.cancel_vote()

    def cmd_vote_status(self, cmd, args, reply, source, admin_name, context):
        v = self._get_service_safe("VoteSystem")
        if v: reply.append(v.get_status())

    def cmd_auth(self, cmd, args, reply, source, admin_name, context):
        al = self._get_service_safe("AdminLogin")
        if al: 
            auth_id = context.get('cid')
            if source == "discord": auth_id = f"discord:{context.get('discord_id')}"
            reply.append(al.process_command(cmd, args, source, admin_name, auth_id) or "")

    def proxy_goal_cmd(self, cmd, args, reply, source, admin_name, context):
        gs = self.client.get_service("GoalSystem")
        if gs:
            if cmd == "goal" or cmd == "cv": gs.cmd_goal(cmd, args, reply, source, context)
            elif cmd == "progress": gs.cmd_progress(cmd, args, reply, source, context)
            elif cmd == "townstats": gs.cmd_townstats(cmd, args, reply, source, context)
            elif cmd == "claimed": gs.cmd_claimed(cmd, args, reply, source, context)
            elif cmd == "goalreached": gs.cmd_goalreached(cmd, args, reply, source, context)
            elif cmd == "awarning": gs.cmd_awarning(cmd, args, reply, source, context)
        else:
            reply.append("GoalSystem plugin not loaded.")

    def cmd_help(self, cmd, args, reply, source, admin_name, context):
        # Use the prefix that was actually used to invoke the command
        # If no prefix_used in context, default to server_id for Discord, otherwise use trigger_prefix
        if context and 'prefix_used' in context:
            prefix = context['prefix_used']
        elif source == "discord":
            # For Discord, prefer server ID as default
            server_id = str(self.client.config.get("server_id", "99"))
            prefix = server_id if server_id else self.client.config.get("trigger_prefix", "!")
        else:
            prefix = self.client.config.get("trigger_prefix", "!")
            
        if args:
            topic = args[0].lower()
            if topic in self.help_text: reply.extend(self.help_text[topic]); return
        regular_cmds = []; admin_cmds = []
        all_cmds = sorted(list(set(list(self.triggers.keys()) + self.native_commands)))
        am = self.get_admin_manager(); username = admin_name 
        is_admin_auth = context.get('is_admin_auth', False) if context else False
        for c in all_cmds:
            if c in ["alogin", "alogout"]: continue
            is_allowed = True; is_admin_cmd = False
            if c == "say" and source == "game": is_admin_cmd = True
            elif c in self.admin_native_commands: is_admin_cmd = True
            else:
                conf = self.triggers.get(c)
                if conf and isinstance(conf, dict) and conf.get("admin"): is_admin_cmd = True
            conf = self.triggers.get(c)
            # If this is an alias, look up the parent command's config
            if not conf and c in self.alias_map:
                parent_cmd = self.alias_map[c]
                conf = self.triggers.get(parent_cmd)
            if conf and isinstance(conf, dict):
                if source == "irc" and not conf.get("irc", True): is_allowed = False
                if source == "game" and not conf.get("in_game", True): is_allowed = False
                if source == "discord" and not conf.get("discord", True): is_allowed = False
            if is_allowed:
                if is_admin_cmd:
                    if not is_admin_auth: is_allowed = False
                    elif am and not am.has_privilege(username, c): is_allowed = False
                if is_allowed:
                    cmd_str = f"{prefix}{c}"
                    (admin_cmds if is_admin_cmd else regular_cmds).append(cmd_str)
        reply.append(f"Commands: {', '.join(regular_cmds)}")
        if admin_cmds: reply.append(f"Admin Commands: {', '.join(admin_cmds)}")
        reply.append(f"Type {prefix}help <command> for details.")
