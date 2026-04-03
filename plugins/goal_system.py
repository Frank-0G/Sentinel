
import time
import json
import math
import sys
import os

# Ensure we can import from parent directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from plugin_interface import IPlugin
    from openttd_types import AdminUpdateType, AdminUpdateFrequency

except ImportError:
    # Fallback for when running directly or in IDE without proper path context
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from plugin_interface import IPlugin
    from openttd_types import AdminUpdateType, AdminUpdateFrequency

class GoalSystem(IPlugin):
    def __init__(self, client):
        super().__init__(client)
        self.name = "GoalSystem"
        self.version = "4.0-PORT-FIX"
        import uuid
        self.iid = str(uuid.uuid4())[:8]
        
        # Configuration
        self.enabled = True
        self.announce_interval = 600
        self.join_announce_delay = 10
        self.victory_count = 10000 
        self.victory_interval = 0
        self.min_population = 100
        self.protection_range = 20
        
        # Game State
        self.goal_master_game = 0 # 0=None, 1=CityBuilder
        self.is_city_builder = False
        self.targets = {'value': 0, 'pop': 0}
        self.map_width = 0
        self.map_height = 0
        
        # Data Stores
        self.company_data = {i: {'pop': 0, 'val': 0, 'name': f"Company #{i+1}", 'color': "Unknown"} for i in range(15)}
        self.claimed_towns = {} # {cid: {'town': str, 'townid': int, 'center': (x,y), 'bbox': (minx,miny,maxx,maxy)}}
        self.claim_stats = {} # {cid: {stats_dict}}
        self.town_demands = {} # {tid: [demand_dicts]}
        self.protection_exceptions = [] 
        
        self.game_won = False
        self.restart_countdown = -1
        self.last_announce = time.time()
        self.last_db_sync = 0
        
        # Anti-Flood / Protection
        self.bad_action_count = {} 
        self.last_action_time = {} 

    def on_load(self):
        self.reload_config()
        self.client.log(f"[{self.name}] Loaded v{self.version}")

    def reload_config(self):
        cfg = self.client.config.get("goal", {})
        if cfg:
            self.targets['value'] = int(cfg.get("winlimit", 0))
            self.targets['pop'] = int(cfg.get("population", 0))
            self.announce_interval = int(cfg.get("interval", 600))
            self.victory_count = int(cfg.get("victorycount", 10000))
            self.protection_range = int(cfg.get("protectionrange", 20))

    def on_connected(self):
        # Request current game mode info from GameScript
        self.client.log(f"[{self.name}] Connected. Requesting game mode info...")
        gs_conn = self.client.get_service("GameScriptConnector")
        if gs_conn:
            if hasattr(gs_conn, "send_to_gs"):
                gs_conn.send_to_gs({"event": "requestinfo"})
            else:
                self.client.send_admin_gamescript(json.dumps({"event": "requestinfo"}))

    def get_company_details(self, cid):
        """
        Retrieves company name, color name, list of player names, and duration played.
        Returns: (company_name, color_name, player_string, duration_text)
        """
        data = self.client.get_service("DataController")
        
        # Defaults
        c_name = self.company_data[cid].get('name', f"Company #{cid+1}")
        c_color = "Unknown"
        players = []
        duration_text = ""
        
        if data:
            # 1. Get Color
            co_info = data.companies.get(cid)
            if co_info:
                if 'color' in co_info:
                    raw_color = co_info['color']
                    c_color, _ = data.get_color_info(raw_color)
                
                # 2. Get Duration
                founded = co_info.get('joined') # Using 'joined' as best proxy for founding real-time
                if founded:
                    diff = int(time.time() - founded)
                    hours = diff // 3600
                    minutes = (diff % 3600) // 60
                    seconds = diff % 60
                    if hours > 0: duration_text = f" in {hours}h {minutes}m {seconds}s"
                    elif minutes > 0: duration_text = f" in {minutes}m {seconds}s"
                    else: duration_text = f" in {seconds}s"

            # 3. Get Players
            for client_id, info in data.clients.items():
                if info.get('company') == cid:
                    players.append(info.get('name', 'Unknown'))
        
        # Format players string: "Player1, Player2" or "Empty" (C# says "Empty" for player string if none)
        is_ai = False
        if data:
            co_info = data.companies.get(cid)
            if co_info and co_info.get('is_ai'):
                is_ai = True
                
        if is_ai: player_str = "AI"
        elif not players: player_str = "Empty"
        else: player_str = ", ".join(players)
        
        return c_name, c_color, player_str, duration_text

    def on_tick(self):
        if not self.enabled: return
        now = time.time()
        
        if not self.game_won and (now - self.last_announce > self.announce_interval):
            self.last_announce = now
            self.announce_scoreboard()

        if not self.game_won and self.is_city_builder and (now - self.last_db_sync > 30):
            self.last_db_sync = now
            self.sync_cb_data_to_db()

        if not self.game_won:
            self.check_winners()

        if self.game_won and self.restart_countdown > 0:
            self.restart_countdown -= 1
            
            should_announce = False
            if self.restart_countdown % 10 == 0: should_announce = True # 30, 20, 10
            if self.restart_countdown <= 5: should_announce = True      # 5, 4, 3, 2, 1
            
            if should_announce and self.restart_countdown > 0:
                 # Mirror C# Message: "New game starts in X seconds, hold on..."
                 msg = f"New game starts in {self.restart_countdown} seconds, hold on..."
                 self.client.send_chat(3, 0, 0, msg) # Server Chat
                 
                 # NOTE: Removed repeated "GOAL REACHED" message as per user request to reduce spam.


            if self.restart_countdown <= 0:
                self.client.log(f"[{self.name}] Triggering Game Restart now.")
                sess = self.client.get_service("OpenttdSession")
                if sess: 
                    sess.restart_game()
                else:
                    self.client.log(f"[{self.name}] Error: OpenttdSession service not found!")
                self.game_won = False
                self.winner_cid = -1

        pass # Stub cleanup check removed

        if now % 60 == 0:
            self.bad_action_count = {k: v-1 for k, v in self.bad_action_count.items() if v > 1}
            
    def on_newgame(self):
        self.client.log(f"[{self.name}] New Game Detected! Resetting Goal System state.")
        self.town_demands.clear()
        self.last_db_sync = time.time()
        self._win_lock = False
        
        # Reset Company Data but keep keys/structure
        for cid in self.company_data:
            self.company_data[cid]['pop'] = 0
            self.company_data[cid]['val'] = 0
            # Name/Color might stay or update later via packets, strictly speaking new game resets them too usually,
            # but we can leave them until updated by packet.
            # safe to reset name to default if needed, but 'Company #X' is fallback logic anyway.

    # --- EVENT HANDLING ---
    def on_gamescript_event(self, event_type, data):
        e = event_type.lower()
        if not e and 'id' in data: e = data['id'].lower()
        
        try:
            if e == "goaltypeinfo": 
                self.goal_master_game = int(data.get("goalmastergame", 0))
                if "target_pop" in data: self.targets['pop'] = int(data["target_pop"])
                self.is_city_builder = (self.goal_master_game == 1)
                
            elif e == "citybuilder": 
                action = data.get("action", "").lower()
                
                if action == "claimed":
                    cid = int(data.get("company", -1))
                    if cid in self.company_data:
                        town_name = data.get("town", "Unknown")
                        town_id = int(data.get("townid", -1))
                        
                        loc_x = int(data.get("x", 0))
                        loc_y = int(data.get("y", 0))
                        prot_range = self.protection_range 
                        max_x = self.map_width - 1
                        max_y = self.map_height - 1
                        
                        min_x = max(0, loc_x - prot_range)
                        min_y = max(0, loc_y - prot_range)
                        max_tx = min(max_x, loc_x + prot_range)
                        max_ty = min(max_y, loc_y + prot_range)
                        
                        self.claimed_towns[cid] = {
                            'town': town_name, 
                            'townid': town_id,
                            'center': (loc_x, loc_y),
                            'bbox': (min_x, min_y, max_tx, max_ty)
                        }
                        self.client.log(f"[{self.name}] Claim: Co #{cid+1} -> {town_name} @ {loc_x},{loc_y}")
                        
                elif action == "unclaimed":
                    cid = int(data.get("company", -1))
                    self.claimed_towns.pop(cid, None)
                    self.claim_stats.pop(cid, None)

                elif action == "towndemands":
                    tid = int(data.get("townid", -1))
                    if tid >= 0:
                        if "demands" in data: 
                            self.town_demands[tid] = data["demands"]
                        elif "cargo" in data:
                            if tid not in self.town_demands: self.town_demands[tid] = []
                            if isinstance(self.town_demands[tid], list):
                                self.town_demands[tid].append(data)

                elif action == "townstats":
                    cid = int(data.get("company", -1))
                    if cid in self.company_data:
                        # Store in a separate dict for sync
                        
                        raw_statue = data.get("statue", False)
                        is_statue = raw_statue if isinstance(raw_statue, bool) else str(raw_statue).lower() == "true"
                        
                        self.claim_stats[cid] = {
                            'cid': cid,
                            'tid': int(data.get("townid", -1)),
                            'name': data.get("townname", "Unknown"),
                            'pop': int(data.get("population", 0)),
                            'house_count': int(data.get("housecount", 0)),
                            'growth_rate': int(data.get("growthrate", 0)),
                            'statue': is_statue,
                            'location': data.get("location", "0x0")
                        }

                elif action == "cleardemands":
                    self.claim_stats.clear()
                    self.town_demands.clear()

            elif e == "populationupdated": 
                cid = int(data.get("company", -1))
                if cid in self.company_data: 
                    self.company_data[cid]['pop'] = int(data.get("population", 0))

            elif e == "multigoalsupdated":
                cid = int(data.get("company", -1))
                if cid in self.company_data:
                    val = 0
                    
                    # Fix: Prioritize 'cvalue' if present, regardless of GMG (handles missing start packet)
                    if "cvalue" in data:
                        val = int(data.get("cvalue", 0))
                        # Optional: Auto-correct GMG if we see cvalue
                        if self.goal_master_game == 0: self.goal_master_game = 4 
                        
                    # Map field based on game type (0=Cargo, 1=Income, 2=Cash, 3=Rating, 4=Value)
                    # Note: We treat all non-population goals as 'val' for the purpose of checking win limit.
                    elif self.goal_master_game == 4:
                        val = int(data.get("cvalue", 0))
                    elif self.goal_master_game == 0:
                        val = int(data.get("cargo", 0))
                    elif self.goal_master_game == 1:
                        val = int(data.get("income", 0))
                    elif self.goal_master_game == 2:
                        val = int(data.get("cash", 0))
                    elif self.goal_master_game == 3:
                        val = int(data.get("rating", 0))
                    
                    self.company_data[cid]['val'] = val
                    # self.client.log(f"[{self.name}] Fast Update Co #{cid+1}: {val} (Type {self.goal_master_game})")
                    self.check_winners()
        
        except Exception as err:
            self.client.log(f"[{self.name}] Event Error: {err}")
            import traceback
            traceback.print_exc()

    def sync_cb_data_to_db(self):
        comm = self.client.get_service("Community")
        if not comm: return
        
        # Match C# sequence: sync stats, then town names, then refill
        # send_server_stats happens in Community.on_tick every 30s as well.
        # But here we do the CB specific ones
        
        comm.delete_town_names()
        for cid, s in self.claim_stats.items():
            comm.send_company_stats(cid, s['tid'], s['name'], s['pop'], s['house_count'], s['growth_rate'], s['statue'], s['location'])
            
        comm.delete_company_demands()
        for tid, demands in self.town_demands.items():
            if isinstance(demands, list):
                for d in demands:
                    # d should have: cargo_suffix, cargo_supply, cargo_goal, cargo_stocked
                    comm.send_company_demands(tid, d.get('cargo_suffix', ''), d.get('cargo_supply', 0), d.get('cargo_goal', 0), d.get('cargo_stocked', 0))

    def on_company_economy(self, company_id, money, loan, income, delivered, performance, value):
         # Keep track of value/money
         if company_id in self.company_data:
             # Only update 'val' from Economy packet if NOT in Company Value mode (Mode 4).
             # In Mode 4, the GameScript sends authoritative high-frequency updates via 'multigoalsupdated'.
             if self.goal_master_game != 4:
                 self.company_data[company_id]['val'] = value 
             # self.client.log(f"DEBUG: Economy Update Co {company_id} Val: {value} (GMG: {self.goal_master_game})")

    def on_company_info(self, cid, name, manager, color, protected, passworded, founded, is_ai):
        if cid in self.company_data:
            self.company_data[cid]['name'] = name
            # Map color int to string name if possible, for now use generic
            self.company_data[cid]['color'] = f"Color {color}"

    def on_company_remove(self, company_id, reason):
        if company_id in self.company_data:
            # Recreate with default empty values so it stops reporting pop/val for the dead company
            self.company_data[company_id] = {'val': 0, 'pop': 0, 'beegoal': 0, 'rating': 0, 'cargo': 0, 'cash': 0, 'income': 0}

    # --- LOGGING & ERROR HANDLING ---
    def on_wrapper_log(self, text): pass

    # --- MAP GEOMETRY ---
    def on_map_info(self, server_name, width, height, name, seed, landscape, start_date, map_counter):
        self.map_width = width
        self.map_height = height
        self.client.log(f"[{self.name}] Map Geometry: {width}x{height}")

    def get_tile_x(self, tile): return tile % self.map_width if self.map_width > 0 else 0
    def get_tile_y(self, tile): return tile // self.map_width if self.map_width > 0 else 0
    def get_tile_index(self, x, y): return (y * self.map_width) + x if self.map_width > 0 else 0

    # --- PROTECTION LOGIC ---
    def on_do_command(self, client_id, cmd_id, p1, p2, tile, text, frame, params=None):
        if client_id == 1: return # Ignore server/system
        
        # Identify command name
        cmd_name = self.client.command_names.get(cmd_id, "")
        
        # HQ RELOCATION/BUILD DETECTION (Legacy Support for ClassicCB)
        if (cmd_name == "CmdBuildObject" and params and params.get("ObjectType") == 4) or cmd_name == "CmdBuildCompanyHq":
            actor_cid = frame # company_id passed from sentinel.py
            
            if actor_cid != 255:
                self.client.log(f"[{self.name}] HQ Build Detected for Co #{actor_cid+1}. Notifying GameScript...")
                gs_conn = self.client.get_service("GameScriptConnector")
                if gs_conn:
                    if hasattr(gs_conn, "send_to_gs"):
                        gs_conn.send_to_gs({"event": "hqbuilt", "company": actor_cid})
                    else:
                        # Fallback for older GameScriptConnector
                        self.client.send_admin_gamescript(json.dumps({"event": "hqbuilt", "company": actor_cid}))

        if not self.is_city_builder: return

        # Check if it's a construction command
        is_construction = (cmd_name.startswith("CmdBuild") or 
                           cmd_name.startswith("CmdRemove") or 
                           cmd_name == "CmdClearArea" or 
                           cmd_name == "CmdTerraformLand" or
                           cmd_name == "CmdLevelLand" or 
                           cmd_name == "CmdConvertRail" or
                           cmd_name == "CmdConvertRoad" or
                           cmd_name == "CmdLandscapeClear" or
                           cmd_name == "CmdPlaceObject")

        if is_construction and params:
            tiles_to_check = []
            
            # 1. Primary Tile
            if "Tile" in params: tiles_to_check.append(params["Tile"])
            
            # 2. Start/End Ranges (fill the gap for linear builds)
            if "StartTile" in params:
                start = params["StartTile"]
                end = params.get("Tile") or params.get("EndTile")
                if end is not None:
                     tiles_to_check.extend(self.get_tiles_in_range(start, end))
                else:
                     tiles_to_check.append(start)

            # Check for violation
            violation_tiles = []
            claimed_by = -1
            for t in tiles_to_check:
                is_safe, owner_cid = self.check_protection(client_id, t)
                if not is_safe:
                    violation_tiles.append(t)
                    claimed_by = owner_cid
            
            if violation_tiles:
                self.handle_violation(client_id, violation_tiles, cmd_name, claimed_by)

    def check_protection(self, client_id, tile):
        # Return (IsSafe: bool, OwnerCID: int)
        
        # 1. Identify Actor Company
        data = self.client.get_service("DataController")
        actor_cid = 255
        if data and client_id in data.clients:
            actor_cid = data.clients[client_id].get('company', 255)
        
        if actor_cid == 255: return True, -1 # Spectators logic? C# kicks specs too? Assume safe for now or block all.
        
        # 2. Check if tile is in ANY bbox
        tx = self.get_tile_x(tile)
        ty = self.get_tile_y(tile)
        
        # Iterate safely
        for owner_cid, info in list(self.claimed_towns.items()):
            # Skip own claims
            if owner_cid == actor_cid: continue
            if not isinstance(info, dict): continue
            
            # Check Bounding Box
            bbox = info.get('bbox') # (min_x, min_y, max_x, max_y)
            if not bbox or not isinstance(bbox, (list, tuple)) or len(bbox) < 4: continue
            
            if (tx >= bbox[0] and tx <= bbox[2] and 
                ty >= bbox[1] and ty <= bbox[3]):
                
                return False, owner_cid # Violation!
                
        return True, -1

    def get_tiles_in_range(self, t1, t2):
        x1, y1 = self.get_tile_x(t1), self.get_tile_y(t1)
        x2, y2 = self.get_tile_x(t2), self.get_tile_y(t2)
        
        tiles = []
        for x in range(min(x1, x2), max(x1, x2) + 1):
            for y in range(min(y1, y2), max(y1, y2) + 1):
                tiles.append(self.get_tile_index(x, y))
        return tiles

    def handle_violation(self, client_id, tiles, cmd_name, claimed_by):
        if not isinstance(tiles, list): tiles = [tiles]
        
        town_name = "Unknown"
        if claimed_by in self.claimed_towns:
             town_name = self.claimed_towns[claimed_by].get('town', 'Unknown')
             
        self.client.log(f"[{self.name}] VIOLATIONS ({len(tiles)}): Client {client_id} built {cmd_name} in {town_name} (Owned by #{claimed_by+1})")
        
        # 1. Revert Actions
        gs_conn = self.client.get_service("GameScriptConnector")
        if gs_conn:
            # Get the company ID of the violator
            data = self.client.get_service("DataController")
            actor_cid = -1
            if data and client_id in data.clients:
                actor_cid = data.clients[client_id].get('company', -1)
            
            if actor_cid != -1:
                # Send cleartile for EVERY tile in the list
                for tile in tiles:
                    gs_conn.send_to_gs({"event": "cleartile", "tile": tile, "company": actor_cid})
        
        # 2. Track & Penalize
        count = self.bad_action_count.get(client_id, 0) + 1
        self.bad_action_count[client_id] = count
        
        # Get actual company name
        owner_name = self.company_data.get(claimed_by, {}).get('name', f"Company #{claimed_by+1}")
        msg = f"Warning: That town is claimed by {owner_name}."
        self.client.send_chat(5, 2, client_id, msg) # Private message
        
        if count == 2:
            # Move to spec
            self.client.send_rcon(f"move {client_id} 255")
            self.client.send_chat(3, 0, 0, f"Client {client_id} moved to spectators for griefing in {town_name} (2/3).")
        elif count >= 3:
             # Kick
             self.client.send_rcon(f"kick {client_id} 'Griefing protected area (3/3)'")
             self.client.send_chat(3, 0, 0, f"Client {client_id} kicked for griefing in {town_name} (3/3).")

    # --- LOGIC ---
    def get_progress(self, cid):
        if self.is_city_builder and self.targets['pop'] > 0:
            return (self.company_data[cid]['pop'] / self.targets['pop']) * 100
        
        # Value based
        val = self.company_data[cid]['val']
        target = self.targets['value']
        
        if target > 0:
            return (val / target) * 100
        return 0

    def check_winners(self):
        if getattr(self, '_win_lock', False): return
        if self.game_won: return
        
        for cid in range(15):
            progress = self.get_progress(cid)
            if progress >= 100:
                self._win_lock = True
                self.client.log(f"[{self.name}-{self.iid}] Win detected for Company #{cid+1} (Progress: {progress}%) (game_won={self.game_won})")
                self.trigger_win(cid, abort=False)
                break

    def trigger_win(self, cid, abort=False):
        self.game_won = True
        self.winner_cid = cid # Store for periodic announcements
        self.client.log(f"[{self.name}] Triggering WIN sequence for Company #{cid+1}")
        
        c_name, c_color, p_str, win_duration = self.get_company_details(cid)
        
        # Exact C# Message: "--- GOAL REACHED! {CompanyName} ({ColorString}) ({Players}) has won this game{winDuration}!!! ---"
        msg = f"--- GOAL REACHED! {c_name} ({c_color}) ({p_str}) has won this game{win_duration}!!! ---"
        
        sess = self.client.get_service("OpenttdSession")
        if sess:
            sess.send_server_message(msg)
            # C# immediately sends the "starts in X seconds" message too
            sess.send_server_message(f"New game starts in 30 seconds, hold on...")
            
            # Reset losing companies and move their players to spectators
            data = self.client.get_service("DataController")
            if data:
                for client_id, cdata in list(data.clients.items()):
                    if client_id == 1: continue # Server
                    if cdata.get('company') not in (cid, 255):
                        sess.move_player(client_id, 255)
                        sess.send_private_message(client_id, "The game has ended. You have been moved to spectators.")
                for comp_id in list(data.companies.keys()):
                    if comp_id != cid:
                        sess.reset_company(comp_id)
            
        self.restart_countdown = 30

        # Notify Community Plugin to calculate points
        comm = self.client.get_service("Community")
        if comm:
            try:
                comm.on_goal_reached(cid, self.targets.copy(), abort)
            except Exception as e:
                self.client.log(f"[{self.name}] Error notifying Community plugin: {e}")

    def cmd_goal(self, cmd, args, reply, source, context):
        self.announce_scoreboard(reply, context=context, source=source)

    def cmd_progress(self, cmd, args, reply, source, context):
        if not self.enabled:
            reply.append("GoalSystem is currently disabled.")
            return

        # Find the maximum progress among all active companies
        max_progress = 0
        for cid in range(15):
            progress = self.get_progress(cid)
            if progress > max_progress:
                max_progress = progress
        
        display_pct = min(max_progress, 100)
        bar_length = int(display_pct / 2) # 50 character bar
        
        if source == "irc":
            # IRC color codes (03XX)
            C_IRC = "\x03"
            C_HEAD = f"{C_IRC}06"    # Purple
            C_BRACKET = f"{C_IRC}02" # Dark Blue
            C_BAR = f"{C_IRC}04"     # Red
            C_TEXT = f"{C_IRC}01"    # Black
            
            bar_filled = "/" * bar_length
            bar_empty = " " * (50 - bar_length)
            
            msg = f"/me {C_HEAD}Goal progress: {C_BRACKET}[{C_BAR}{bar_filled}{bar_empty}{C_BRACKET}]{C_TEXT} - {int(display_pct)}%"
            reply.append(msg)
        elif source == "discord":
            # Discord ANSI coloring in code blocks
            # Magenta: [35m, Blue: [34m, Red: [31m, Reset: [0m
            C_ESC = "\u001b"
            C_HEAD = f"{C_ESC}[35m"
            C_BRACKET = f"{C_ESC}[34m"
            C_BAR = f"{C_ESC}[31m"
            C_RESET = f"{C_ESC}[0m"
            
            bar_filled = "/" * bar_length
            bar_empty = " " * (50 - bar_length)
            
            # Wrap in ansi code block
            msg = f"```ansi\n{C_HEAD}Goal progress: {C_BRACKET}[{C_BAR}{bar_filled}{bar_empty}{C_BRACKET}]{C_RESET} - {int(display_pct)}%\n```"
            reply.append(msg)
        else:
            # Game / Other
            bar = "[" + ("/" * bar_length) + ("-" * (50 - bar_length)) + "]"
            reply.append(f"Goal progress: {bar} - {int(display_pct)}%")

    def cmd_townstats(self, cmd, args, reply, source, context):
        if args:
            try: cid = int(args[0]) - 1
            except: reply.append("Invalid ID"); return
        else:
            sender_cid = context.get('cid', -1)
            data = self.client.get_service("DataController")
            if data and sender_cid in data.clients:
                cid = data.clients[sender_cid].get('company', 255)

        if cid == 255 or cid < 0:
            reply.append("Usage: !townstats <ID> or join a company.")
            return

        if cid in self.claimed_towns:
            info = self.claimed_towns[cid]
            town_name = info['town']
            pop = self.company_data[cid]['pop']
            reply.append(f"Company #{cid+1}: {town_name} (Pop: {pop})")
            
            tid = info.get('townid', -1)
            if tid in self.town_demands:
                demands = self.town_demands[tid] # Assume list of dicts or dict
                # ... formatting logic ...
                reply.append("Demands listed (implied)")
        else: 
            reply.append(f"Company #{cid+1} has no town claimed.")

    def cmd_claimed(self, cmd, args, reply, source, context):
        if not self.claimed_towns: return reply.append("No claims.")
        reply.append("--- Claimed Towns ---")
        for cid, info in self.claimed_towns.items():
            pop = self.company_data[cid]['pop']
            reply.append(f"#{cid+1}: {info['town']} (Pop: {pop})")

    def announce_scoreboard(self, force_reply=None, context=None, source=None):
        # Color Map
        colors = [
            "Dark Blue", "Pale Green", "Pink", "Yellow", "Red", "Light Blue", "Green", "Dark Green",
            "Blue", "Cream", "Mauve", "Purple", "Orange", "Brown", "Grey", "White"
        ]
        
        # 1. Private Messages (only if force_reply is present and goal is active)
        if force_reply is not None:
             # Restrict scoring strings to in-game (source == "game")
             if source != "game":
                  goal_active = False # Don't show these on IRC/Discord
             else:
                  goal_active = self.is_city_builder or self.targets.get('score', 0) > 0 or self.targets.get('value', 0) > 0
             
             if goal_active:
                  force_reply.append("When the goal is reached all logged in players will score points, the winner gets an additional bonus!")
                  
                  comm = self.client.get_service("Community")
                  cid = context.get('cid', -1) if context else -1
                  
                  if comm and cid != -1:
                       data_ctrl = self.client.get_service("DataController")
                       player_cid = data_ctrl.clients[cid].get('company', 255) if data_ctrl and cid in data_ctrl.clients else 255
                       
                       is_logged_in = False
                       if comm and hasattr(comm, 'auth_users'):
                            if cid in comm.auth_users:
                                 is_logged_in = True

                       if is_logged_in:
                            if player_cid != 255:
                                 score = comm.get_player_current_score(player_cid)
                                 bonus_score = int(score * 1.5)
                                 force_reply.append(f"Your current score in this game is: {score} point{'s' if score != 1 else ''} (if your company would win the game now: {bonus_score})")
                       else:
                            force_reply.append(f"You are not logged in. You can still login now if you want to score any points, check: {comm.website_url}")

        # 2. Determine Header & Unit
        header = ""
        unit_singular = ""
        unit_plural = ""
        
        if self.is_city_builder:
             target_val = self.targets.get('pop', 0)
             unit_singular = self.client.config.get("goal_unit_name", "inhabitant")
             unit_plural = self.client.config.get("goal_unit_name_plural", "inhabitants")
             unit_str = unit_singular if target_val == 1 else unit_plural
             header = f"--- First company with {target_val:,} {unit_str} wins the game. ---"
        elif self.targets.get('score', 0) > 0:
             target_val = self.targets['score']
             header = f"--- First company with a score of {target_val:,} wins the game. ---"
        else:
             target_val = self.targets.get('value', 0)
             # Pure CV Goal logic: "GBP company value"
             header = f"--- First company with {target_val:,} GBP company value wins the game. ---"
             
        if force_reply is not None: force_reply.append(header)
        else: self.client.send_chat(3, 0, 0, header) # Broadcast

        # 2. Get and Sort Data
        ranks = []
        data_ctrl = self.client.get_service("DataController")
        
        for cid in range(15):
             is_active = False
             if data_ctrl:
                 if cid in data_ctrl.companies: is_active = True
             else:
                 # Fallback: Check if we have data (cast to int to be safe)
                 pop = int(self.company_data[cid].get('pop', 0))
                 val = int(self.company_data[cid].get('val', 0))
                 if pop > 0 or val > 0: is_active = True
             
             if is_active:
                 p = self.get_progress(cid)
                 
                 # Prepare Value Text
                 pop = int(self.company_data[cid].get('pop', 0))
                 val = int(self.company_data[cid].get('val', 0))
                 
                 value_text = ""
                 if self.is_city_builder:
                     # e.g. "1,200 inhabitants"
                     u = unit_singular if pop == 1 else unit_plural
                     value_text = f"{pop:,} {u}"
                 else:
                     # e.g. "100,000 GBP company value"
                     value_text = f"{val:,} GBP company value"
                 
                 name = self.company_data[cid].get('name', f"Company #{cid+1}")
                 
                 # Resolve Color
                 col_str = "Unknown"
                 try:
                     raw_col = str(self.company_data[cid].get('color', "Color 0"))
                     if raw_col.startswith("Color "):
                         col_parts = raw_col.split(" ")
                         if len(col_parts) > 1:
                             col_idx = int(col_parts[1])
                             if 0 <= col_idx < len(colors): col_str = colors[col_idx]
                             else: col_str = raw_col
                         else: col_str = raw_col
                     else: col_str = raw_col
                 except: col_str = "Unknown"

                 ranks.append({
                     'id': cid, 
                     'pct': int(p), 
                     'name': name,
                     'color': col_str,
                     'value_text': value_text,
                     'abs_val': pop if self.is_city_builder else val
                 })

        # Sort by percentage descending, then by absolute value desc
        ranks.sort(key=lambda x: (x['pct'], x['abs_val']), reverse=True)

        # 3. Output Top 3
        count = 0
        for i, r in enumerate(ranks):
            if count >= 3: break
            
            # Format: - ({PCT}%) Rank #{RANK} is {NAME} ({COLOR}) with {VALUE_TEXT}
            # C# Rank string: "- ({0}%) Rank #{1} is {2} ({3}) with {4} point{5}" if it's points
            if self.targets.get('score', 0) > 0:
                pts = int(r.get('pts', 0))
                msg = f"- ({r['pct']}%) Rank #{i+1} is {r['name']} ({r['color']}) with {pts:,} point{'s' if pts != 1 else ''}"
            else:
                msg = f"- ({r['pct']}%) Rank #{i+1} is {r['name']} ({r['color']}) with {r['value_text']}"
             
            if force_reply is not None: force_reply.append(msg)
            else: self.client.send_chat(3, 0, 0, msg)
            count += 1

    def cmd_goalreached(self, cmd, args, reply, source, context):
        if self.game_won:
            reply.append("The game has already been won.")
            return

        # Check for online players
        data_ctrl = self.client.get_service("DataController")
        player_count = len(data_ctrl.clients) if data_ctrl else 0
        
        # If no players online, restart immediately
        if player_count == 0:
             sess = self.client.get_service("OpenttdSession")
             if sess:
                 reply.append("No players online. Restarting game immediately...")
                 self.client.log(f"[{self.name}] Admin forced restart (No players online).")
                 sess.restart_game()
             else:
                 reply.append("Error: OpenttdSession not found.")
             return

        # Normal Win Logic (with players)
        # Optional: Allow specifying a winner, otherwise pick the leader
        target_cid = -1
        if args:
             try:
                 target_cid = int(args[0]) - 1 # 1-based to 0-based
             except: pass
        
        if target_cid < 0:
            # Find current leader
            best_cid = -1
            best_val = -1
            
            for cid in self.company_data:
                val = self.get_progress(cid)
                if val > best_val:
                    best_val = val
                    best_cid = cid
            
            target_cid = best_cid

        if target_cid >= 0:
            name = self.company_data[target_cid].get('name', f"Company #{target_cid+1}")
            reply.append(f"Forcing win for {name}...")
            self.client.log(f"[{self.name}] Admin forced win for Company {target_cid}")
            
            # Use standard trigger_win for consistency (forced win = abort=True)
            self.trigger_win(target_cid, abort=True)
            
        else:
            reply.append("Could not determine a winner to force.")
