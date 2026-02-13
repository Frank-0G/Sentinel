from plugin_interface import IPlugin

class CompanyProtection(IPlugin):
    """
    Prevents unauthorized access to high-value companies.
    """
    def __init__(self, client):
        super().__init__(client)
        self.name = "CompanyProtection"
        self.version = "1.1-EVENT-FIXED"
        self.min_value_threshold = 500000 
        self.protected_companies = set()

    def get_data(self): return self.client.get_service("DataController")
    def get_session(self): return self.client.get_service("OpenttdSession")

    def on_tick(self):
        data = self.get_data()
        if not data: return
        for cid, comp in data.companies.items():
            value = comp.get('value', 0)
            is_passworded = comp.get('passworded', False)
            if value > self.min_value_threshold and not is_passworded:
                self.protected_companies.add(cid)
            else:
                if cid in self.protected_companies: self.protected_companies.remove(cid)

    # NO RAW PARSING HERE!
    def on_player_join(self, client_id, name, ip, company_id):
        self._check_protection(client_id, company_id)

    def on_player_update(self, client_id, name, company_id):
        self._check_protection(client_id, company_id)

    def _check_protection(self, client_id, company_id):
        if company_id == 255: return # Spectators OK
        
        if company_id in self.protected_companies:
            session = self.get_session()
            if session:
                session.move_player(client_id, 255)
                msg = "Security: High-value company with no password. Moved to spectators."
                session.send_private_message(client_id, msg)
                self.client.log(f"[{self.name}] Blocked join to Co #{company_id+1} by #{client_id}")
