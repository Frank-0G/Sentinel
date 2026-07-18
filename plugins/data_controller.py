import time
from plugin_interface import IPlugin
from openttd_types import AdminUpdateType, AdminUpdateFrequency

class DataController(IPlugin):
    def __init__(self, client):
        super().__init__(client)
        self.name = "DataController"
        self.version = "4.0-COMPLETE-POLLING"
        self.last_poll = 0
        self._server_info = {
            "name": "Unknown",
            "year": 0,
            "map": "Unknown",
            "width": 0,
            "height": 0,
            "seed": 0,
            "landscape": 0,
            "start_date": 0
        }

    @property
    def clients(self):
        return {
            cid: {
                "name": p.name,
                "ip": p.ip,
                "company": p.company_id,
                "joined": p.joined_at,
            }
            for cid, p in self.client.state.players.items()
        }

    @property
    def companies(self):
        res = {}
        for cid, c in self.client.state.companies.items():
            res[cid] = {
                "name": c.name,
                "manager": c.manager,
                "color": c.color,
                "protected": c.protected,
                "passworded": c.passworded,
                "is_ai": c.is_ai,
                "founded": c.founded,
                "start_year": c.founded,
                "money": c.economy.get("money", 0) if isinstance(c.economy, dict) else getattr(c.economy, 'money', 0),
                "loan": c.economy.get("loan", 0) if isinstance(c.economy, dict) else getattr(c.economy, 'loan', 0),
                "income": c.economy.get("income", 0) if isinstance(c.economy, dict) else getattr(c.economy, 'income', 0),
                "delivered": c.economy.get("delivered", 0) if isinstance(c.economy, dict) else getattr(c.economy, 'delivered', 0),
                "performance": c.economy.get("performance", 0) if isinstance(c.economy, dict) else getattr(c.economy, 'performance', 0),
                "value": c.economy.get("value", 0) if isinstance(c.economy, dict) else getattr(c.economy, 'value', 0),
                "vehicles": (c.stats.get("trains", 0) + c.stats.get("roadvehicles", 0) + c.stats.get("ships", 0) + c.stats.get("aircraft", 0)) if isinstance(c.stats, dict) else 0,
                "stations": (c.stats.get("train_stations", 0) + c.stats.get("road_stations", 0) + c.stats.get("airports", 0) + c.stats.get("harbors", 0)) if isinstance(c.stats, dict) else 0,
                "trains": c.stats.get("trains", 0) if isinstance(c.stats, dict) else 0,
                "roadvehicles": c.stats.get("roadvehicles", 0) if isinstance(c.stats, dict) else 0,
                "aircraft": c.stats.get("aircraft", 0) if isinstance(c.stats, dict) else 0,
                "ships": c.stats.get("ships", 0) if isinstance(c.stats, dict) else 0,
                "trainstations": c.stats.get("train_stations", 0) if isinstance(c.stats, dict) else 0,
                "roadstations": c.stats.get("road_stations", 0) if isinstance(c.stats, dict) else 0,
                "airports": c.stats.get("airports", 0) if isinstance(c.stats, dict) else 0,
                "harbors": c.stats.get("harbors", 0) if isinstance(c.stats, dict) else 0,
            }
        return res

    @property
    def server_info(self):
        days = self.client.state.session.openttd_date_days
        if days is not None:
            if days > 36500:
                self._server_info["year"] = days // 365
            else:
                self._server_info["year"] = 1920 + (days // 365)
        return self._server_info

    def on_tick(self):
        pass

    def on_load(self):
        pass

    def on_connected(self):
        self.last_poll = time.time()

    def on_map_info(self, server_name, width, height, map_name, seed, landscape, start_date, flags):
        self._server_info.update({
            "name": server_name,
            "map": map_name,
            "width": width,
            "height": height,
            "seed": seed,
            "landscape": landscape,
            "start_date": start_date
        })

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
