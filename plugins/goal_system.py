
import time
import json
import math
import sys
import os

# Ensure we can import from parent directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from plugin_interface import IPlugin

class GoalSystem(IPlugin):
    def __init__(self, client):
        super().__init__(client)
        self.name = "GoalSystem"
        self.version = "4.0-PORT-FIX"
        
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
        self.company_data = {i: {'pop': 0, 'val': 0} for i in range(15)}
        self.claimed_towns = {} # {cid: {'town': str, 'townid': int, 'center': (x,y), 'bbox': (minx,miny,maxx,maxy)}}
        self.town_demands = {} # {tid: [demand_dicts]}
        self.protection_exceptions = [] 
        
        self.game_won = False
        self.restart_countdown = -1
        self.last_announce = time.time()
        
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

    def on_tick(self):
        if not self.enabled: return
        now = time.time()
        
        if not self.game_won and (now - self.last_announce > self.announce_interval):
            self.last_announce = now
            self.announce_scoreboard()

        if not self.game_won:
            self.check_winners()

        if self.game_won and self.restart_countdown > 0:
            if now % 1 <= 0.1: 
                self.restart_countdown -= 1
                if self.restart_countdown <= 0:
                    sess = self.client.get_service("OpenttdSession")
                    if sess: sess.restart_game()
                    self.game_won = False

        if "OpenttdSession" in self.client.services: # Stub cleanup check
             pass

        if now % 60 == 0:
            self.bad_action_count = {k: v-1 for k, v in self.bad_action_count.items() if v > 1}

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
                    if cid >= 0:
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

                elif action == "towndemands":
                    tid = int(data.get("townid", -1))
                    if tid >= 0:
                        if "demands" in data: 
                            # If 'demands' is delivered as a list, store it directly
                            self.town_demands[tid] = data["demands"]
                        elif "cargo" in data:
                            # Accumulate incremental updates
                            if tid not in self.town_demands: self.town_demands[tid] = []
                            # Ensure it is a list before appending
                            if isinstance(self.town_demands[tid], list):
                                self.town_demands[tid].append(data)

            elif e == "populationupdated": 
                cid = int(data.get("company", -1))
                if cid >= 0: 
                    self.company_data[cid]['pop'] = int(data.get("population", 0))
                    # Update claim if missing (this part might be redundant if 'claimed' event is reliable)
                    # if 'townid' in data and cid not in self.claimed_towns:
                    #     self.claimed_towns[cid] = {'town': 'Town', 'townid': data['townid']}

        except Exception as err:
            self.client.log(f"[{self.name}] Event Error: {err}")
            import traceback
            traceback.print_exc()

    def on_company_economy(self, company_id, money, loan, income, delivered, performance, value):
         # Keep track of value/money
         if company_id in self.company_data:
             self.company_data[company_id]['val'] = value # or logic to calculate score

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
        if not self.is_city_builder: return
        if client_id == 1: return # Ignore server/system

        # Locate command name
        cmd_name = self.client.command_names.get(cmd_id, "")
        if not cmd_name: return

        # Check if it's a construction command
        is_construction = (cmd_name.startswith("CmdBuild") or 
                           cmd_name.startswith("CmdRemove") or 
                           cmd_name == "CmdClearArea" or 
                           cmd_name == "CmdTerraformLand" or
                           cmd_name == "CmdLevelLand" or 
                           cmd_name == "CmdConvertRail" or
                           cmd_name == "CmdConvertRoad" or
                           cmd_name == "CmdLandscapeClear" or
                           cmd_name == "CmdPlaceObject") # Objects too?

        if is_construction and params:
            tiles_to_check = []
            
            # 1. Primary Tile
            if "Tile" in params: tiles_to_check.append(params["Tile"])
            
            # 2. Start/End Ranges
            if "StartTile" in params:
                if "Tile" in params: # CmdClearArea, CmdLevelLand, CmdConvert*
                    tiles_to_check.append(params["StartTile"])
                    tiles_to_check.append(params["Tile"])
                elif "EndTile" in params: # CmdBuildLongRoad, CmdBuildRailroadTrack
                    tiles_to_check.append(params["StartTile"])
                    tiles_to_check.append(params["EndTile"])

            # Check for violation
            violation_tile = -1
            claimed_by = -1
            for t in tiles_to_check:
                is_safe, owner_cid = self.check_protection(client_id, t)
                if not is_safe:
                    violation_tile = t
                    claimed_by = owner_cid
                    break
            
            if violation_tile != -1:
                self.handle_violation(client_id, violation_tile, cmd_name, claimed_by)

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

    def handle_violation(self, client_id, tile, cmd_name, claimed_by):
        town_name = "Unknown"
        if claimed_by in self.claimed_towns:
             town_name = self.claimed_towns[claimed_by].get('town', 'Unknown')
             
        self.client.log(f"[{self.name}] VIOLATION: Client {client_id} built on {tile} ({cmd_name}) in {town_name} (Owned by #{claimed_by+1})")
        
        # 1. Revert Action
        # Try sending RCON to GS to clear tile. 
        # Usage: script <script_name> <command> <args...>
        pass
        
        # 2. Track & Penalize
        count = self.bad_action_count.get(client_id, 0) + 1
        self.bad_action_count[client_id] = count
        
        msg = f"Do not build in {town_name}! It belongs to Company #{claimed_by+1}!"
        self.client.send_chat(1, 2, client_id, msg) # Private message
        
        if count >= 3:
            # Move to spec
            self.client.send_rcon(f"move {client_id} 255")
            self.client.send_chat(3, 0, 0, f"Client {client_id} moved to spectators for griefing in {town_name}.")
        if count >= 10:
             self.client.send_rcon(f"kick {client_id} 'Griefing protected area'")

    # --- LOGIC ---
    def get_progress(self, cid):
        if self.is_city_builder and self.targets['pop'] > 0:
            return (self.company_data[cid]['pop'] / self.targets['pop']) * 100
        # Value based
        val = self.company_data[cid]['val']
        if self.targets['value'] > 0:
            return (val / self.targets['value']) * 100
        return 0

    def check_winners(self):
        for cid in range(15):
            if self.get_progress(cid) >= 100:
                self.trigger_win(cid)
                break

    def trigger_win(self, cid):
        self.game_won = True
        sess = self.client.get_service("OpenttdSession")
        if sess:
            sess.send_server_message(f"--- GOAL REACHED! Company #{cid+1} WINS! ---")
            sess.send_server_message("Restarting in 30 seconds...")
        self.restart_countdown = 30

    # --- COMMANDS ---
    def cmd_goal(self, cmd, args, reply, source, context):
        self.announce_scoreboard(reply)

    def cmd_townstats(self, cmd, args, reply, source, context):
        cid = -1
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

    def announce_scoreboard(self, force_reply=None):
        header = "--- Company Ranking ---"
        target_str = f"Target: {self.targets['pop']} Pop" if self.is_city_builder else f"Target: ${self.targets['value']}"
        header = f"--- {target_str} ---"
        
        ranks = []
        data_ctrl = self.client.get_service("DataController")
        for i in range(15):
             # Only list active companies
             if data_ctrl and i in data_ctrl.companies:
                p = self.get_progress(i)
                ranks.append({'id': i, 'pct': p, 'name': data_ctrl.companies[i].get('name', f"Company {i+1}")})
        ranks.sort(key=lambda x: x['pct'], reverse=True)

        if force_reply is not None: force_reply.append(header)
        else: self.client.send_chat(3, 0, 0, header) # Broadcast

        count = 0
        for r in ranks:
            if count >= 3: break
            msg = f"#{r['id']+1} {r['name']}: {int(r['pct'])}%"
            if force_reply is not None: force_reply.append(msg)
            else: self.client.send_chat(3, 0, 0, msg)
            count += 1
