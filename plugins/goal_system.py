import time
import json
from plugin_interface import IPlugin

class GoalSystem(IPlugin):
    def __init__(self, client):
        super().__init__(client)
        self.name = "GoalSystem"
        self.version = "3.6-FORCE-UPDATE"  # <--- Look for this in logs!
        
        self.enabled = True
        self.goal_master_game = 0 
        self.is_city_builder = False
        
        # Targets
        self.targets = {'value': 0, 'pop': 0}
        
        # Data Stores
        self.company_data = {i: {'pop': 0, 'val': 0} for i in range(15)}
        self.claimed_towns = {} 
        self.town_demands = {}
        
        self.game_won = False
        self.restart_countdown = -1
        self.last_announce = time.time()
        self.announce_interval = 600 

    def on_load(self):
        self.reload_config()
        self.client.log(f"[{self.name}] Loaded v{self.version}. Waiting for GS events...")

    def reload_config(self):
        cfg = self.client.config.get("goal", {})
        if cfg:
            self.targets['value'] = int(cfg.get("winlimit", 0))
            self.targets['pop'] = int(cfg.get("population", 0))
            self.announce_interval = int(cfg.get("interval", 600))

    def on_tick(self):
        if not self.enabled: return
        now = time.time()
        
        if not self.game_won and (now - self.last_announce > self.announce_interval):
            self.last_announce = now
            self.announce_scoreboard()

        if not self.game_won:
            self.check_winners()

        if self.game_won and self.restart_countdown > 0:
            if now % 1 == 0: 
                self.restart_countdown -= 1
                if self.restart_countdown <= 0:
                    sess = self.client.get_service("OpenttdSession")
                    if sess: sess.restart_game()
                    self.game_won = False

    # --- CRITICAL EVENT LISTENER ---
    def on_gamescript_event(self, event_type, data):
        # 1. Normalize Event Name
        e = event_type.lower()
        if not e and 'id' in data: e = data['id'].lower()
        
        # 2. Debug Log (Visible in console)
        # self.client.log(f"[{self.name}] RAW EVENT: {e} | {data}")

        try:
            if e == "goaltypeinfo": 
                self.goal_master_game = int(data.get("goalmastergame", 0))
                if "target_pop" in data: self.targets['pop'] = int(data["target_pop"])
                self.is_city_builder = (self.goal_master_game == 1)

            elif e == "citybuilder": 
                action = data.get("action", "").lower()
                
                # --- CLAIM HANDLING ---
                if action == "claimed":
                    cid = int(data.get("company", -1))
                    
                    # Fix: 1-based indexing from legacy scripts
                    if cid > 14: cid = 0 
                    
                    if cid >= 0:
                        self.claimed_towns[cid] = {
                            'town': data.get("town", "Unknown"), 
                            'townid': int(data.get("townid", -1))
                        }
                        self.client.log(f"[{self.name}] CLAIM REGISTERED: Co #{cid+1} -> {data.get('town')}")
                        
                        # Force a save of this state if needed (optional)
                        # self.client.save_data() 

                # --- DEMANDS HANDLING ---
                elif action == "towndemands":
                    tid = int(data.get("townid", -1))
                    if tid >= 0:
                        # Store demands list for !townstats
                        if "demands" in data:
                            self.town_demands[tid] = data["demands"]
                        # Fallback for simple packets
                        elif "cargo" in data:
                            if tid not in self.town_demands: self.town_demands[tid] = []
                            self.town_demands[tid].append(data)

            elif e == "populationupdated": 
                cid = int(data.get("company", -1))
                if cid >= 0: 
                    self.company_data[cid]['pop'] = int(data.get("population", 0))
                    # Sync claim if missing
                    if 'townid' in data and cid not in self.claimed_towns:
                        self.claimed_towns[cid] = {'town': 'Town', 'townid': data['townid']}

        except Exception as err:
            self.client.log(f"[{self.name}] Event Error: {err}")

    # --- LOGIC ---
    def get_progress(self, cid):
        if self.is_city_builder and self.targets['pop'] > 0:
            return (self.company_data[cid]['pop'] / self.targets['pop']) * 100
        data = self.client.get_service("DataController")
        if data and cid in data.companies:
            val = data.companies[cid].get('value', 0)
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
        # 1. Check Arguments
        if args:
            try: cid = int(args[0]) - 1
            except: reply.append("Invalid ID"); return
        else:
            # 2. Check Sender
            sender_cid = context.get('cid', -1)
            data = self.client.get_service("DataController")
            if data and sender_cid in data.clients:
                cid = data.clients[sender_cid].get('company', 255)

        # 3. Validation
        if cid == 255 or cid < 0:
            reply.append("Usage: !townstats <ID> or join a company.")
            return

        # 4. Lookup
        if cid in self.claimed_towns:
            info = self.claimed_towns[cid]
            town_name = info['town']
            pop = self.company_data[cid]['pop']
            
            reply.append(f"Company #{cid+1}: {town_name} (Pop: {pop})")
            
            # 5. Show Demands
            tid = info.get('townid', -1)
            if tid in self.town_demands:
                # Format demands nicely if available
                demands = self.town_demands[tid]
                if isinstance(demands, list) and len(demands) > 0:
                    req_strs = []
                    for d in demands:
                        # Try various keys common in legacy scripts
                        c_name = d.get('cargo', d.get('name', 'Cargo'))
                        req = d.get('required', d.get('goal', 0))
                        cur = d.get('delivered', d.get('current', 0))
                        req_strs.append(f"{c_name}: {cur}/{req}")
                    reply.append("Needs: " + ", ".join(req_strs))
        else: 
            reply.append(f"Company #{cid+1} has no town claimed.")

    def cmd_claimed(self, cmd, args, reply, source, context):
        if not self.claimed_towns: return reply.append("No claims.")
        reply.append("--- Claimed Towns ---")
        for cid, info in self.claimed_towns.items():
            pop = self.company_data[cid]['pop']
            reply.append(f"#{cid+1}: {info['town']} (Pop: {pop})")

    # Stubs
    def cmd_progress(self, c, a, r, s, x): pass
    def cmd_goalreached(self, c, a, r, s, x): pass
    def cmd_awarning(self, c, a, r, s, x): pass

    def announce_scoreboard(self, force_reply=None):
        header = "--- Company Ranking ---"
        if self.is_city_builder: header = f"--- First to {self.targets['pop']} Pop Wins! ---"
        
        ranks = []
        data_ctrl = self.client.get_service("DataController")
        for i in range(15):
            if data_ctrl and i in data_ctrl.companies:
                p = self.get_progress(i)
                ranks.append({'id': i, 'pct': p})
        ranks.sort(key=lambda x: x['pct'], reverse=True)

        if force_reply is not None: force_reply.append(header)
        else: 
            sess = self.client.get_service("OpenttdSession")
            if sess: sess.send_server_message(header)

        count = 0
        for r in ranks:
            if count >= 5: break
            msg = f"#{r['id']+1}: {int(r['pct'])}%"
            if force_reply is not None: force_reply.append(msg)
            else:
                sess = self.client.get_service("OpenttdSession")
                if sess: sess.send_server_message(msg)
            count += 1
