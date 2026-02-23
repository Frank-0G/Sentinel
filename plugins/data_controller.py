import time
from plugin_interface import IPlugin
from openttd_types import AdminUpdateType, AdminUpdateFrequency

class DataController(IPlugin):
    def __init__(self, client):
        super().__init__(client)
        self.name = "DataController"
        self.version = "4.0-COMPLETE-POLLING"

        self.clients = {}
        self.companies = {}
        self.server_info = {
            "name": "Unknown",
            "year": 0,
            "map": "Unknown",
            "width": 0,
            "height": 0,
            "seed": 0,
            "landscape": 0,
            "start_date": 0
        }
        self.last_poll = 0

    def _subscribe(self):
        # Subscriptions handled by central AdminClient
        pass

    def _initial_poll(self):
        # Initial polling handled by central AdminClient
        pass

    def on_tick(self):
        """Periodically poll for fresh data to ensure single source of truth."""
        now = time.time()
        if now - self.last_poll >= 10:  # Poll every 10 seconds (Increased freq for debug)
            self.last_poll = now
            # print(f"[DEBUG][DataController] Periodic Poll") # Commented out to reduce spam
            try:
                self.client.send_poll(AdminUpdateType.ADMIN_UPDATE_COMPANY_INFO, 0xFFFFFFFF)
                self.client.send_poll(AdminUpdateType.ADMIN_UPDATE_COMPANY_ECONOMY, 0xFFFFFFFF)
                self.client.send_poll(AdminUpdateType.ADMIN_UPDATE_COMPANY_STATS, 0xFFFFFFFF)
                self.client.send_poll(AdminUpdateType.ADMIN_UPDATE_CLIENT_INFO, 0xFFFFFFFF)
            except:
                pass

    def on_load(self):
        # print(f"[DEBUG][DataController] Plugin Loaded")
        try: self._subscribe()
        except: pass

    def on_connected(self):
        # Polling/Subscriptions handled by central AdminClient
        self.last_poll = time.time()  # Initialize polling timer

    def on_map_info(self, server_name, width, height, map_name, seed, landscape, start_date, flags):
        """Called when SERVER_WELCOME packet is received with map details."""
        self.server_info.update({
            "name": server_name,
            "map": map_name,
            "width": width,
            "height": height,
            "seed": seed,
            "landscape": landscape,
            "start_date": start_date
        })
    
    def on_player_join(self, client_id, name, ip, company_id):
        if client_id not in self.clients:
            self.clients[client_id] = {
                "name": name,
                "ip": ip,
                "company": company_id,
                "joined": time.time(),
            }
        else:
            self.clients[client_id]["name"] = name
            self.clients[client_id]["ip"] = ip
            self.clients[client_id]["company"] = company_id

    def on_player_update(self, client_id, name, company_id):
        if client_id in self.clients:
            self.clients[client_id]["name"] = name
            self.clients[client_id]["company"] = company_id
        else:
            # Player updated before join event - create entry with current time
            self.clients[client_id] = {"name": name, "ip": "Unknown", "company": company_id, "joined": time.time()}

    def on_player_quit(self, client_id):
        if client_id in self.clients:
            del self.clients[client_id]

    def on_player_error(self, client_id, error_code):
        if client_id in self.clients:
            del self.clients[client_id]

    def on_company_info(self, company_id, name, manager, color, protected, passworded, founded, is_ai):
        if company_id not in self.companies:
            self.companies[company_id] = {
                "money": 0, "loan": 0, "income": 0, "delivered": 0, 
                "performance": 0, "value": 0,
                "vehicles": 0, "stations": 0, "airports": 0, "harbors": 0
            }
        
        self.companies[company_id].update({
            "name": name,
            "manager": manager,
            "color": color,
            "protected": bool(protected),
            "passworded": bool(passworded),
            "is_ai": bool(is_ai) if is_ai is not None else False
        })
        # print(f"[DEBUG][DataController] Updated Company {company_id}: Name='{name}', Color={color}, AI={is_ai}")
        
        # Store founded year and calculate start_year for display
        if founded is not None:
            self.companies[company_id]["founded"] = founded
            # Calculate actual year from days (founded is in days since epoch)
            if founded > 36500:  # After year 2020 in new date system
                self.companies[company_id]["start_year"] = founded // 365
            else:  # Old date system (days since 1920)
                self.companies[company_id]["start_year"] = 1920 + (founded // 365)

    def on_company_economy(self, company_id, money, loan, income, delivered, performance, value):
        if company_id not in self.companies:
            self.companies[company_id] = {
                "name": "Unknown", "manager": "Unknown", "color": 0, 
                "protected": False, "passworded": False, "is_ai": False,
                "vehicles": 0, "stations": 0, "airports": 0, "harbors": 0
            }
        self.companies[company_id].update({
            "money": money,
            "loan": loan,
            "income": income,
            "delivered": delivered,
            "performance": performance,
            "value": value
        })

    def on_company_stats(self, company_id, trains, rv, ships, aircraft, train_stations, road_stations, airports, harbors):
        if company_id not in self.companies:
            self.companies[company_id] = {}
        
        self.companies[company_id].update({
            "vehicles": trains + rv + ships + aircraft,
            "trains": trains,
            "roadvehicles": rv,
            "aircraft": aircraft,
            "ships": ships,
            "trainstations": train_stations,
            "roadstations": road_stations,
            "airports": airports,
            "harbors": harbors,
            "stations": train_stations + road_stations + airports + harbors
        })

    def on_company_remove(self, company_id, reason):
        if company_id in self.companies:
            del self.companies[company_id]

    def on_date_change(self, game_date):
        if game_date > 36500:
            self.server_info["year"] = game_date // 365
        else:
            self.server_info["year"] = 1920 + (game_date // 365)

    def on_new_game(self):
        self.clients.clear()
        self.companies.clear()
        self.last_poll = time.time()  # Reset polling timer
        self._initial_poll()

    def get_client(self, cid):
        return self.clients.get(cid)

    def get_company(self, co_id):
        return self.companies.get(co_id)

    def get_color_info(self, color_id):
        colors = [
            "Dark Blue", "Pale Green", "Pink", "Yellow", "Red", "Light Blue",
            "Green", "Dark Green", "Blue", "Cream", "Mauve", "Purple",
            "Orange", "Brown", "Grey", "White"
        ]
        try: color_id = int(color_id)
        except: color_id = -1
        if 0 <= color_id < len(colors):
            return colors[color_id], "\x0302"
        return "Unknown", "\x0301"
