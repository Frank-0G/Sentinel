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
                    self.client.send_chat(1, 0, 0, f"[{author_name}] {safe_content}")
                
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
                await ctx.send("Sentinel Discord Bridge v1.1-FIX is Online.")

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

    # --- BRIDGE METHODS (Async Dispatch) ---

    def _dispatch_discord(self, coro):
        if self.running and self.loop and self.loop.is_running():
            asyncio.run_coroutine_threadsafe(coro, self.loop)
        else:
            coro.close()

    async def _send_msg(self, msg):
        try:
            channel = self.bot.get_channel(self.main_channel_id)
            if channel: await channel.send(msg)
        except: pass

    async def _send_embed(self, embed):
        try:
            channel = self.bot.get_channel(self.main_channel_id)
            if channel: await channel.send(embed=embed)
        except: pass

    # --- EVENTS (Called by Sentinel Main Thread) ---
    # We wrap these in try-except to prevent crashing the main Sentinel loop.

    def on_tick(self):
        # Sync status every 30 seconds?
        # TODO in future
        pass
    
    # We add on_connected to force a status update when server connects
    def on_connected(self):
        self._dispatch_discord(self.update_status())

    def on_chat(self, action, dest_type, cid, msg):
        try:
            if cid == 1: return
            
            # Use DataController for name resolution
            name = "Unknown"
            data = self._get_data()
            if data and cid in data.clients:
                name = data.clients[cid].get('name', 'Unknown')
            
            formatted = f"**{name}**: {msg}"
            self._dispatch_discord(self._send_msg(formatted))
        except: pass

    def on_player_join(self, cid, name, ip, company_id):
        try:
            embed = discord.Embed(description=f"✅ **{name}** has joined the game.", color=0x00ff00)
            self._dispatch_discord(self._send_embed(embed))
            self._dispatch_discord(self.update_status())
        except: pass

    def on_player_quit(self, cid):
        try:
            name = "Unknown"
            data = self._get_data()
            if data and cid in data.clients:
                 name = data.clients[cid].get('name', 'Unknown')
            
            embed = discord.Embed(description=f"❌ **{name}** has left the game.", color=0xff0000)
            self._dispatch_discord(self._send_embed(embed))
            self._dispatch_discord(self.update_status())
        except: pass

    def on_company_created(self, company_id):
        try:
            embed = discord.Embed(description=f"🏢 Company #{company_id+1} has been founded!", color=0x0000ff)
            self._dispatch_discord(self._send_embed(embed))
            self._dispatch_discord(self.update_status())
        except: pass
    
    def on_new_game(self):
        try:
            embed = discord.Embed(title="New Game", description="Map has been reloaded.", color=0xffff00)
            self._dispatch_discord(self._send_embed(embed))
            self._dispatch_discord(self.update_status())
        except: pass
