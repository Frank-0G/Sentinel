from __future__ import annotations

class IPlugin:
    def __init__(self, client):
        self.client = client
        self.name = self.__class__.__name__
        self.version = "0.0"

    def on_load(self): pass
    def on_unload(self): pass
    def on_tick(self): pass
    def on_event(self, packet_type: int, payload: bytes): pass
    def on_connected(self): pass
    def on_disconnected(self): pass
    def register_commands(self, router): pass

    def on_player_join(self, client_id: int, name: str, ip: str, company_id: int): pass
    def on_player_update(self, client_id: int, name: str, company_id: int): pass
    def on_player_quit(self, client_id: int): pass
    def on_player_error(self, client_id: int, error_code: int): pass

    def on_company_created(self, company_id: int): pass
    def on_company_info(self, company_id: int, name: str, manager: str, color: int, protected: bool, passworded: bool, founded: int | None, is_ai: bool | None): pass
    def on_company_economy(self, company_id: int, money: int, loan: int, income: int, delivered: int, performance: int, value: int): pass
    def on_company_stats(self, company_id: int, vehicles: tuple, stations: int, airports: int, harbors: int): pass
    def on_company_remove(self, company_id: int, reason: int): pass

    def on_command_name(self, cmd_id: int, cmd_name: str): pass
    def on_do_command(self, client_id: int, cmd_id: int, p1: int, p2: int, tile: int, text: str, frame: int): pass
    
    def on_gamescript_event(self, event_type: str, data: dict): pass

    def on_wrapper_log(self, text: str): pass
    def on_map_save(self, filename: str): pass
    def on_map_load(self, filename: str): pass
    
    # NEW: Map Info
    def on_map_info(self, server_name: str, width: int, height: int, name: str, seed: int, landscape: int, start_date: int, map_counter: int): pass

    def on_chat(self, action: int, dest: int, client_id: int, msg: str): pass
    def on_newgame(self): pass
    def on_date_change(self, openttd_date_days: int): pass
    
    # RCON Result hook
    def on_rcon_result(self, command: str, result: str): pass
