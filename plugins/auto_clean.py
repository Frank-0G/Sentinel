import json
import os
import time
from plugin_interface import IPlugin

class AutoClean(IPlugin):
    def __init__(self, client):
        super().__init__(client)
        self.name = "AutoClean"
        self.version = "1.4-SAVED-LIST"
        self.saved_companies = [] 
        self.last_year = 0
        self.max_companies = 15
        self.data_file = "autoclean.json"

    def on_load(self):
        # Requirement: Empty the json when the plugin starts
        self.saved_companies = []
        self.save_data()
        
        self.max_companies = self.client.game_cfg.get("max_companies", 15)
        self.client.log(f"[{self.name}] Loaded & Cleared Save List. Max Companies: {self.max_companies}")

    def on_unload(self):
        self.save_data()

    def save_data(self):
        try:
            with open(self.data_file, "w") as f:
                json.dump({"saved_companies": self.saved_companies}, f)
        except: pass

    def get_data(self):
        for p in self.client.plugins:
            if p.name == "DataController": return p
        return None

    def get_community(self):
        for p in self.client.plugins:
            if p.name == "Community": return p
        return None

    # --- EVENT LISTENERS ---

    def on_tick(self):
        data = self.get_data()
        if data:
            current_year = data.server_info.get("year", 0)
            if current_year > self.last_year:
                if self.last_year != 0: 
                    if len(data.companies) >= self.max_companies:
                        self.check_companies()
                self.last_year = current_year

    def on_data_event(self, event_type, payload):
        if event_type == "new_game":
            self.saved_companies = []
            self.save_data()
            self.client.log(f"[{self.name}] New Game detected. Saved list cleared.")
            return

        elif event_type == "company_close":
            cid = payload.get("id")
            if cid is not None and cid in self.saved_companies:
                self.saved_companies.remove(cid)
                self.save_data()
            return

        data = self.get_data()
        if not data: return

        if event_type == "company_founded":
            if len(data.companies) >= (self.max_companies - 1):
                self.check_companies()
        
        elif event_type == "client_join":
            if len(data.companies) >= self.max_companies:
                self.check_companies()

    # --- CORE LOGIC ---

    def check_companies(self):
        data = self.get_data()
        if not data: return

        empty_companies = []
        for cid, co in data.companies.items():
            player_count = 0
            for client in data.clients.values():
                if client.get("company") == cid:
                    player_count += 1
            
            if player_count == 0:
                val = co.get("money", 0) + co.get("value", 0)
                empty_companies.append({'id': cid, 'val': val, 'data': co})

        empty_companies.sort(key=lambda x: x['val'])
        self.client.log(f"[{self.name}] Checking {len(empty_companies)} empty companies for cleanup...")

        # 1. No Vehicles
        for item in empty_companies:
            cid = item['id']
            vehs = item['data'].get("vehicles", (0,0,0,0,0))
            if sum(vehs) == 0:
                self.do_reset(cid, item['data'], "Auto-cleaned, empty and no vehicles")
                return 

        # 2. Not Saved AND Not Passworded
        for item in empty_companies:
            cid = item['id']
            is_saved = cid in self.saved_companies
            is_locked = item['data'].get("passworded", False)
            if not is_saved and not is_locked:
                self.do_reset(cid, item['data'], "Auto-cleaned, empty and no save flag")
                return

        # 3. Any Empty (Not Locked)
        for item in empty_companies:
            cid = item['id']
            is_locked = item['data'].get("passworded", False)
            if not is_locked:
                self.do_reset(cid, item['data'], "Auto-cleaned, empty")
                return

    def do_reset(self, cid, co_data, reason):
        c_name = co_data.get("name", f"Company #{cid+1}")
        self.client.log(f"[{self.name}] RESETTING {c_name} (ID {cid}). Reason: {reason}")
        self.client.send_rcon(f"reset_company {cid+1}")
        self.client.send_rcon(f"say \"*** {c_name} (#{cid+1}) has been closed ({reason})\"")
        
        if cid in self.saved_companies:
            self.saved_companies.remove(cid)
            self.save_data()

    # --- COMMAND HANDLER ---

    def process_command(self, cmd, args, source, admin_name, cid):
        data = self.get_data()
        if not data: return "Internal Error."

        if cmd == "savedcompanies":
            if not self.saved_companies:
                return "List is empty. No companies are currently saved."
            
            lines = []
            for co_id in self.saved_companies:
                co = data.get_company(co_id)
                name = co.get("name", "Unknown") if co else "Unknown"
                lines.append(f"#{co_id+1} '{name}'")
            
            return f"Saved Companies ({len(lines)}): " + ", ".join(lines)

        if cmd == "saveme":
            comm = self.get_community()
            
            # 1. Check Login
            if not comm or cid not in comm.auth_users:
                return "Sorry, you have to be logged in to use this feature."
            
            username = comm.auth_users[cid]

            # 2. Check VIP (Disabled until Community is ready, or use fallback)
            # if hasattr(comm, 'is_vip'):
            #    if not comm.is_vip(username):
            #        return "Sorry, this feature is only available for BTPro VIP members!"
            
            # 3. Check Company
            client = data.get_client(cid)
            if not client: return "Error finding you."
            
            co_id = client.get("company", 255)
            if co_id == 255:
                return "Sorry, you have to be in a company when using this command."

            # 4. Toggle Save
            if co_id in self.saved_companies:
                self.saved_companies.remove(co_id)
                self.save_data()
                self.notify_company(co_id, cid, f"Info: your company member '{client['name']}' has set this company to *not* be saved from autocleans anymore.")
                return "OK, your company is no longer being saved from autocleans."
            else:
                self.saved_companies.append(co_id)
                self.save_data()
                
                co = data.get_company(co_id)
                vehs = sum(co.get("vehicles", (0,0,0,0,0))) if co else 0
                warning = ""
                if vehs == 0:
                    warning = " Warning: companies without vehicles will be autocleaned first, even with saving enabled."

                self.notify_company(co_id, cid, f"Info: your company member '{client['name']}' has set this company to be saved from autocleans.")
                return f"OK, your company is now being saved from autocleans.{warning}"

        return None

    def notify_company(self, co_id, exclude_cid, msg):
        data = self.get_data()
        if not data: return
        for cid, c in data.clients.items():
            if c.get("company") == co_id and cid != exclude_cid:
                self.client.send_rcon(f"say_client {cid} \"{msg}\"")
