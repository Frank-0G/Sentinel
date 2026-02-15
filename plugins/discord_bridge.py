import threading
import asyncio
import time
import os
import json
import xml.etree.ElementTree as ET
import inspect
from plugin_interface import IPlugin
from openttd_types import ServerPacketType, NetworkAction

# Try to import discord, but don't fail if not present (just disable plugin)
try:
    import discord # type: ignore
    from discord.ext import commands, tasks # type: ignore
    DISCORD_AVAILABLE = True
except ImportError:
    DISCORD_AVAILABLE = False
    print("[DiscordBridge] 'discord' module not found. Install with 'pip install discord.py'")

class DiscordBridge(IPlugin):
    def __init__(self, client):
        super().__init__(client)
        self.name = "DiscordBridge"
        self.version = "1.1-FIX"
        
        self.config = {}
        self.admin_users = {}
        self.loop = None
        self.bot = None
        self.running = False
        self.thread = None

        # Load Config
        self.load_config()

        self.enabled = self.config.get("discord_enabled", False)
        self.token = self.config.get("discord_token", "")
        self.prefix_char = self.config.get("trigger_prefix", "!")
        self.main_channel_id = int(self.config.get("discord_channel_id", 0))
        
        # Local cache
        self.client_cache = {}
        self.company_cache = {} 
        self.placed_signs = {}
        self.pending_started_companies = set()
        self.cmd_map = {}
        
        self.formats = {
            "chat": "**$playername** ($companycolor): $message",
            "joinedgame": "🌍 **$playername** (#$playerid/$playercountryshort) has joined the game",
            "joinedspectators": "👓 **$playername** (#$playerid/$playercountryshort) has joined spectators",
            "joinedcompany": "🚂 **$playername** (#$playerid/$playercountryshort) has joined company #$companyid ($companycolor)",
            "startedcompany": "🆕 **$playername** (#$playerid/$playercountryshort) has started company #$companyid ($companycolor)",
            "leftgame": "⬅️ **$playername** (#$playerid/$playercountryshort/$companycolor) left the game ($message)",
            "namechange": "📝 **$playername** is now known as **$tplayername**",
            "gamerestarted": "🔄 **The game has been (re)started**",
            "companyclosed": "🏚️ **$companyname** (#$companyid/$companycolor) has been closed ($message)",
            "companyunprotected": "🔓 Password of **$companyname** (#$companyid/$companycolor) has been removed ($message)",
            "placedsign": "🪧 **$playername** placed a sign: $message",
            "removedsign": "🪧 **$playername** removed a sign: $message",
            "vehiclecrashed": "💥 **$companyname** (#$companyid/$companycolor) had a crash ($message)",
            "companymerge": "🤝 **$companyname** (#$companyid/$companycolor) merged into **$tcompanyname** (#$tcompanyid/$tcompanycolor)",
            "companytrouble": "⚠️ **$companyname** (#$companyid/$companycolor) is in trouble!",
            "mapsaved": "💾 Game saved to $message",
            "maploaded": "📂 Map loaded: $message"
        }
        
        # Local cache is prone to de-sync if we miss events. 
        # We will use DataController as Source of Truth where possible.

    def _get_data(self):
        # Helper to get DataController plugin
        if hasattr(self.client, 'get_service'):
            return self.client.get_service("DataController")
        # Fallback search
        for p in self.client.plugins:
            if p.name == "DataController": return p
        return None

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
        if not DISCORD_AVAILABLE:
            self.client.log(f"[{self.name}] Plugin DISABLED: 'discord' module not found.")
            return

        if self.enabled and self.token:
            self.client.log(f"[{self.name}] Starting Discord Bot thread...")
            # Validate token minimal length to avoid immediate crash
            if len(self.token) < 10:
                self.client.log(f"[{self.name}] Error: Token seems invalid (too short).")
                return

            self.running = True
            self.thread = threading.Thread(target=self.discord_thread_entry, daemon=True)
            self.thread.start()
        else:
             self.client.log(f"[{self.name}] Disabled or no token provided.")

    def on_unload(self):
        self.running = False
        if self.loop and self.bot:
            asyncio.run_coroutine_threadsafe(self.bot.close(), self.loop)

    def discord_thread_entry(self):
        try:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            
            intents = discord.Intents.default()
            intents.message_content = True
            
            self.bot = commands.Bot(command_prefix=self.prefix_char, intents=intents)

            @self.bot.event
            async def on_ready():
                print(f"[{self.name}] Discord Connected as {self.bot.user} (ID: {self.bot.user.id})")
                await self.update_status()

            @self.bot.event
            async def on_command_error(ctx, error):
                # Ignore CommandNotFound as we pass these to Sentinel CommandManager
                if isinstance(error, commands.CommandNotFound):
                    return
                # Also ignore CheckFailures (e.g. missing permissions) to keep logs clean
                if isinstance(error, commands.CheckFailure):
                    return
                print(f"[{self.name}] Discord Command Error: {error}")

            @self.bot.event
            async def on_message(message):
                if message.author.bot: return
                if message.channel.id != self.main_channel_id: return
                
                # 1. Relay Chat to Game
                if not message.content.startswith(self.prefix_char):
                    author_name = message.author.display_name
                    # Sanitize
                    safe_content = message.content.replace('"', "'")
                    # Use Action=2 (NETWORK_ACTION_SERVER_MESSAGE) instead of 1 (INVALID)
                    # Or use 0 (NETWORK_ACTION_CHAT) if 2 is restricted. 
                    # Trying 2 as per openttd_types.py for "Server Message".
                    self.client.send_chat(2, 0, 0, f"[{author_name}] {safe_content}")
                
                # 2. Process Commands (this might raise CommandNotFound, which we now squash)
                await self.bot.process_commands(message)
                
                # 3. Handle Custom Commands (!command)
                if message.content.startswith(self.prefix_char):
                    # We can't access CommandManager directly from this thread safely? 
                    # Yes we can, Sentinel is not strictly thread-safe but reading is usually fine.
                    # Ideally we should queue this request to main thread, but CommandManager seems robust enough.
                    cmd_payload = message.content[len(self.prefix_char):].strip()
                    mgr = None
                    if hasattr(self.client, 'get_service'):
                        mgr = self.client.get_service("CommandManager")
                    
                    if mgr and cmd_payload:
                        success, reply = mgr.handle_command(cmd_payload, source="discord", is_admin=False, admin_name=message.author.name)
                        if reply:
                            await message.channel.send(reply)
            
            # --- DEBUG COMMAND ---
            @self.bot.command(name="discord")
            async def cmd_debug(ctx):
                channel = self.bot.get_channel(self.main_channel_id)
                status = "VISIBLE" if channel else "NOT FOUND in Cache"
                if not channel:
                    try:
                        channel = await self.bot.fetch_channel(self.main_channel_id)
                        status = "FETCHED via API (Cache miss)"
                    except Exception as e:
                        status = f"ERROR: {e}"
                
                await ctx.send(f"Sentinel Discord Bridge v1.2-DEBUG is Online.\nConfigured Channel ID: {self.main_channel_id}\nChannel Status: {status}")

            self.bot.run(self.token)
        except Exception as e:
            print(f"[{self.name}] Discord Thread Crash: {e}")
            self.running = False

    async def update_status(self):
        try:
            # Access DataController safely across threads
            count_str = "?"
            # This access is technically racy but reading a dict len is atomic enough in GIL
            data = self._get_data()
            if data and hasattr(data, 'clients'):
                # subtract 1 for server
                c_count = len(data.clients) - 1
                co_count = len(data.companies) if hasattr(data, 'companies') else 0
                count_str = f"{c_count} Pl | {co_count} Co"
            
            activity = discord.Activity(type=discord.ActivityType.watching, name=f"OpenTTD: {count_str}")
            await self.bot.change_presence(activity=activity)
        except: pass

    # --- HELPERS ---
    def get_data(self): return self.client.get_service("DataController")
    def get_manager(self): return self.client.get_service("CommandManager")
    def get_admin_manager(self): return self.client.get_service("AdminManager")
    def get_geoip(self): return self.client.get_service("GeoIPService")

    def get_iso(self, ip):
        svc = self.get_geoip()
        if not svc or ip == "0.0.0.0": return "??"
        return svc.resolve_iso(ip)

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
        
        # Emoji mapping for colors
        emoji = "⚫"
        if "Dark Blue" in cname: emoji = "🔵"
        elif "Pale Green" in cname: emoji = "🟢"
        elif "Pink" in cname: emoji = "🌸"
        elif "Yellow" in cname: emoji = "🟡"
        elif "Red" in cname: emoji = "🔴"
        elif "Light Blue" in cname: emoji = "🔹"
        elif "Green" in cname: emoji = "🌲"
        elif "Dark Green" in cname: emoji = "🌳"
        elif "Blue" in cname: emoji = "🔷"
        elif "Cream" in cname: emoji = "🍦"
        elif "Mauve" in cname: emoji = "💜"
        elif "Purple" in cname: emoji = "🟣"
        elif "Orange" in cname: emoji = "🟠"
        elif "Brown" in cname: emoji = "🟤"
        elif "Grey" in cname: emoji = "⚪"
        elif "White" in cname: emoji = "🏳️"

        return f"{emoji} {cname}"

    def get_company_name(self, cid):
        if cid in self.company_cache: return self.company_cache[cid]['name']
        data = self.get_data()
        if data:
            co = data.get_company(cid)
            if co: return co.get('name', f"Company {cid+1}")
        return f"Company {cid+1}"

    def get_player_vars(self, cid):
        name = "Unknown"; iso = "??"; co_id = 255
        if cid in self.client_cache:
            c = self.client_cache[cid]
            name = c['name']; iso = c['iso']; co_id = c['company']
        return {
            "playername": name,
            "playerid": cid,
            "playercountryshort": iso,
            "companyid": co_id + 1 if co_id != 255 else "Spec",
            "companycolor": self.get_company_color_name(co_id)
        }

    # --- BRIDGE METHODS (Async Dispatch) ---
    def _dispatch_discord(self, coro):
        target_loop = self.bot.loop if self.bot else self.loop
        if self.running and target_loop:
            try:
                if target_loop.is_running():
                    fut = asyncio.run_coroutine_threadsafe(coro, target_loop)
                    fut.add_done_callback(lambda f: f.exception() and print(f"[{self.name}] Async Error: {f.exception()}"))
                    return
                else: 
                     print(f"[{self.name}] Loop Check Fail: Loop not running.")
            except Exception as e:
                print(f"[{self.name}] Loop Check Error: {e}")
        
        # If we got here, we failed
        print(f"[{self.name}] Dispatch Failed! Running={self.running}, Loop={target_loop}")
        coro.close()

    async def _send_msg(self, msg):
        try:
            channel = self.bot.get_channel(self.main_channel_id)
            if not channel:
                channel = await self.bot.fetch_channel(self.main_channel_id)
            if channel: await channel.send(msg)
        except Exception as e:
            print(f"[{self.name}] Send Msg Error: {e}")

    async def _send_embed(self, embed):
        try:
            channel = self.bot.get_channel(self.main_channel_id)
            if not channel:
                channel = await self.bot.fetch_channel(self.main_channel_id)
            if channel: await channel.send(embed=embed)
        except Exception as e:
            print(f"[{self.name}] Send Embed Error: {e}")

    # --- EVENTS (Called by Sentinel Main Thread) ---
    def on_tick(self): pass

    def on_connected(self):
        self._dispatch_discord(self.update_status())

    def on_wrapper_log(self, text):
        if "Map generation percentage complete: 90" in text: self.on_new_game()
        if "CmdSaveGame: Saved game to" in text:
            try:
                filename = text.split("Saved game to ", 1)[1].strip()
                msg = self.format_msg("mapsaved", message=filename)
                self._dispatch_discord(self._send_msg(msg))
            except: pass
        if "Loading map" in text and "success" in text:
             msg = self.format_msg("maploaded", message="Server")
             self._dispatch_discord(self._send_msg(msg))

    def on_player_join(self, cid, name, ip, company_id):
        iso = self.get_iso(ip)
        self.client_cache[cid] = {'name': name, 'ip': ip, 'company': company_id, 'iso': iso}
        
        # Join Message
        msg = self.format_msg("joinedgame", playername=name, playerid=cid, playercountryshort=iso)
        self._dispatch_discord(self._send_msg(msg))

        if company_id == 255:
            msg = self.format_msg("joinedspectators", playername=name, playerid=cid, playercountryshort=iso)
            self._dispatch_discord(self._send_msg(msg))
        else:
            ccolor = self.get_company_color_name(company_id)
            msg = self.format_msg("joinedcompany", playername=name, playerid=cid, playercountryshort=iso, companyid=company_id+1, companycolor=ccolor)
            self._dispatch_discord(self._send_msg(msg))
            
            if company_id in self.pending_started_companies:
                self.send_company_started(cid, company_id)
                self.pending_started_companies.remove(company_id)

    def on_player_quit(self, cid):
        if cid in self.client_cache:
            old = self.client_cache[cid]
            ccolor = self.get_company_color_name(old['company'])
            msg = self.format_msg("leftgame", playername=old['name'], playerid=cid, companyid=old['company']+1 if old['company']!=255 else "Spec", companycolor=ccolor, playercountryshort=old['iso'], message="leaving")
            self._dispatch_discord(self._send_msg(msg))
            del self.client_cache[cid]
        self._dispatch_discord(self.update_status())

    def on_player_error(self, cid, err):
        err_str = f"Error {err}" 
        if cid in self.client_cache:
            old = self.client_cache[cid]
            ccolor = self.get_company_color_name(old['company'])
            msg = self.format_msg("leftgame", playername=old['name'], playerid=cid, companyid=old['company']+1 if old['company']!=255 else "Spec", companycolor=ccolor, playercountryshort=old['iso'], message=err_str)
            self._dispatch_discord(self._send_msg(msg))
            del self.client_cache[cid]
        self._dispatch_discord(self.update_status())

    def on_company_created(self, company_id):
        self.pending_started_companies.add(company_id)
        self._dispatch_discord(self.update_status())

    def on_company_remove(self, cid, reason):
        msg = self.format_msg("companyclosed", companyname=self.get_company_name(cid), companyid=cid+1, companycolor=self.get_company_color_name(cid), message="Bankrupt" if reason==1 else "Manual")
        self._dispatch_discord(self._send_msg(msg))
        if cid in self.company_cache: del self.company_cache[cid]
        if cid in self.pending_started_companies: self.pending_started_companies.remove(cid)
        self._dispatch_discord(self.update_status())

    def on_new_game(self):
        self.client_cache.clear()
        self.company_cache.clear()
        self.placed_signs.clear()
        self.pending_started_companies.clear()
        self._dispatch_discord(self._send_msg(self.format_msg("gamerestarted")))
        self._dispatch_discord(self.update_status())

    def on_company_info(self, cid, name, man, col, prot, pw, founded, is_ai):
        was_pw = self.company_cache[cid].get('passworded', False) if cid in self.company_cache else False
        self.company_cache[cid] = {'name': name, 'color': col, 'passworded': pw}
        if was_pw and not pw:
            msg = self.format_msg("companyunprotected", companyname=name, companyid=cid+1, companycolor=self.get_company_color_name(cid), message="manual removal")
            self._dispatch_discord(self._send_msg(msg))

    def on_player_update(self, cid, name, company_id):
        if cid not in self.client_cache:
            self.client_cache[cid] = {'name': name, 'ip': '?', 'company': company_id, 'iso': '?'}
            return
        old = self.client_cache[cid]
        iso = old['iso']
        
        if old['name'] != name:
            ccolor = self.get_company_color_name(old['company'])
            msg = self.format_msg("namechange", playername=old['name'], playerid=cid, companyid=old['company']+1 if old['company']!=255 else "Spec", companycolor=ccolor, playercountryshort=iso, tplayername=name)
            self._dispatch_discord(self._send_msg(msg))
            self.client_cache[cid]['name'] = name
            
        if old['company'] != company_id:
            ccolor = self.get_company_color_name(company_id)
            if company_id == 255:
                 msg = self.format_msg("joinedspectators", playername=name, playerid=cid, playercountryshort=iso)
                 self._dispatch_discord(self._send_msg(msg))
            else:
                 msg = self.format_msg("joinedcompany", playername=name, playerid=cid, playercountryshort=iso, companyid=company_id+1, companycolor=ccolor)
                 self._dispatch_discord(self._send_msg(msg))
                 if company_id in self.pending_started_companies:
                     self.send_company_started(cid, company_id)
                     self.pending_started_companies.remove(company_id)
            self.client_cache[cid]['company'] = company_id
        
        self._dispatch_discord(self.update_status())

    def send_company_started(self, cid, company_id):
        c = self.client_cache[cid]
        ccolor = self.get_company_color_name(company_id)
        msg = self.format_msg("startedcompany", playername=c['name'], playerid=cid, playercountryshort=c['iso'], companyid=company_id+1, companycolor=ccolor)
        self._dispatch_discord(self._send_msg(msg))

    def on_chat(self, cid, msg, action, dest_type):
        try:
            # Action 2 (Server Message)
            if action == 2: return 
            if cid == 1: return
            
            name = "Unknown"; iso = "??"
            if cid in self.client_cache:
                name = self.client_cache[cid]['name']
                # iso = self.client_cache[cid]['iso'] # Not used in chat format per user req
            
            # Format: **$playername** ($companycolor): $message
            # Using simple format per user request
            formatted = f"**{name}**: {msg}" 
            self._dispatch_discord(self._send_msg(formatted))
        except: pass

    def on_event(self, pt, pl):
        if pt == ServerPacketType.SERVER_CHAT: # Goal reached messages
             try:
                msg, _ = self.client.unpack_string(pl, 6)
                if "GOAL REACHED!" in msg: 
                    self._dispatch_discord(self._send_msg(f"🏆 **GOAL REACHED!** {msg}"))
             except: pass
    
    def on_data_event(self, etype, data):
        if etype == "game_saved": 
            msg = self.format_msg("mapsaved", message="Storage")
            self._dispatch_discord(self._send_msg(msg))

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
                    self._dispatch_discord(self._send_msg(msg))
                    del self.placed_signs[tile]
            else:
                self.placed_signs[tile] = {'owner': client_id, 'text': text}
                vars = self.get_player_vars(client_id)
                vars['message'] = f"\"{text}\""
                msg = self.format_msg("placedsign", **vars)
                self._dispatch_discord(self._send_msg(msg))
