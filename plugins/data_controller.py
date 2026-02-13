from plugin_interface import IPlugin
from openttd_types import AdminUpdateType, AdminUpdateFrequency

class DataController(IPlugin):
    def __init__(self, client):
        super().__init__(client)
        self.name = "DataController"
        self.version = "3.14-CMD-MAP-FIX"

        self.clients = {}
        self.companies = {}
        self.server_info = {"name": "Unknown", "year": 0, "map": "Unknown"}

    def _subscribe(self):
        self.client.send_update_frequency(AdminUpdateType.ADMIN_UPDATE_CLIENT_INFO, AdminUpdateFrequency.ADMIN_FREQUENCY_AUTOMATIC)
        self.client.send_update_frequency(AdminUpdateType.ADMIN_UPDATE_COMPANY_INFO, AdminUpdateFrequency.ADMIN_FREQUENCY_AUTOMATIC)
        self.client.send_update_frequency(AdminUpdateType.ADMIN_UPDATE_COMPANY_ECONOMY, AdminUpdateFrequency.ADMIN_FREQUENCY_WEEKLY)
        self.client.send_update_frequency(AdminUpdateType.ADMIN_UPDATE_COMPANY_STATS, AdminUpdateFrequency.ADMIN_FREQUENCY_WEEKLY)
        self.client.send_update_frequency(AdminUpdateType.ADMIN_UPDATE_DATE, AdminUpdateFrequency.ADMIN_FREQUENCY_WEEKLY)
        
        # Subscribe to CMD_LOGGING (8)
        self.client.send_update_frequency(8, AdminUpdateFrequency.ADMIN_FREQUENCY_AUTOMATIC)

    def _initial_poll(self):
        try:
            self.client.send_poll(AdminUpdateType.ADMIN_UPDATE_CLIENT_INFO, 0)
            self.client.send_poll(AdminUpdateType.ADMIN_UPDATE_COMPANY_INFO, 0)
            self.client.send_poll(AdminUpdateType.ADMIN_UPDATE_COMPANY_ECONOMY, 0)
            self.client.send_poll(AdminUpdateType.ADMIN_UPDATE_COMPANY_STATS, 0)
            
            # Poll CMD_NAMES (7) once on connect
            self.client.send_poll(7, 0) 
        except Exception: pass

    def on_load(self):
        try: self._subscribe()
        except: pass

    def on_connected(self):
        try:
            self._subscribe()
            self._initial_poll()
        except: pass

    def on_player_join(self, client_id, name, ip, company_id):
        self.clients[client_id] = {
            "name": name,
            "ip": ip,
            "company": company_id,
            "joined": self.clients.get(client_id, {}).get("joined", 0),
        }

    def on_player_update(self, client_id, name, company_id):
        if client_id in self.clients:
            self.clients[client_id]["name"] = name
            self.clients[client_id]["company"] = company_id
        else:
            self.clients[client_id] = {"name": name, "ip": "Unknown", "company": company_id, "joined": 0}

    def on_player_quit(self, client_id):
        if client_id in self.clients:
            del self.clients[client_id]

    def on_player_error(self, client_id, error_code):
        if client_id in self.clients:
            del self.clients[client_id]

    def on_company_info(self, company_id, name, manager, color, protected, passworded, founded, is_ai):
        if company_id not in self.companies:
            self.companies[company_id] = {}
        self.companies[company_id].update({
            "name": name,
            "manager": manager,
            "color": color,
            "passworded": bool(passworded)
        })
        if founded is not None: self.companies[company_id]["founded"] = founded
        if is_ai is not None: self.companies[company_id]["is_ai"] = is_ai

    def on_company_economy(self, company_id, money, loan, income, delivered, performance, value):
        if company_id not in self.companies:
            self.companies[company_id] = {}
        self.companies[company_id].update({
            "money": money,
            "loan": loan,
            "income": income,
            "delivered": delivered,
            "performance": performance,
            "value": value
        })

    def on_company_stats(self, company_id, vehicles, stations, airports, harbors):
        if company_id not in self.companies:
            self.companies[company_id] = {}
        
        self.companies[company_id].update({
            "vehicles": vehicles,
            "stations": stations,
            "airports": airports,
            "harbors": harbors
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
