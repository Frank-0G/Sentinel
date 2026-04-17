import time
import json
import sys
import os
from datetime import datetime

# Ensure we can import from parent directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from plugin_interface import IPlugin
except ImportError:
    from plugin_interface import IPlugin

class StatisticsRecorder(IPlugin):
    """
    Records detailed company statistics from the Gamescript into the MySQL database.
    """
    def __init__(self, client):
        super().__init__(client)
        self.name = "StatisticsRecorder"
        self.version = "1.0-DB"
        self.db_config = {}
        self.server_id = 99
        self.table_name = "openttd_company_stats"
        self.latest_stats = {} # Cache: {company_id: stats_dict}
        self._stats_cleared = False

    def on_load(self):
        # Configuration
        self.server_id = self.client.config.get("server_id", 99)
        self.table_name = self.client.config.get("statistics_table", "openttd_company_stats")
        
        # Priority 1: dedicated statistics DB config
        db_cfg = self.client.config.get("statistics_db_config")
        # Priority 2: general MySQL config
        if not db_cfg: db_cfg = self.client.config.get("mysql_config")
            
        if not db_cfg:
            self.client.log(f"[{self.name}] Error: No MySQL configuration found. Statistics will not be recorded.")
            return

        self.db_config = db_cfg.copy()
        if 'port' in self.db_config: self.db_config['port'] = int(self.db_config['port'])
        
        self.client.log(f"[{self.name}] Plugin Loaded. Server ID: {self.server_id}")
        self._clear_stats()

    def on_tick(self):
        # Attempt to clear stats if it hasn't been done yet (e.g., MySQL service wasn't ready on_load)
        if not self._stats_cleared:
            self._clear_stats()

    def on_newgame(self):
        self._stats_cleared = False # Force re-clear for a new game
        self._clear_stats()

    def _clear_stats(self):
        mysql = self.client.get_service("MySQL")
        if mysql and self.db_config:
            sid = int(self.server_id)
            self.client.log(f"[{self.name}] Clearing old statistics for Server ID: {sid} in table {self.table_name}")
            query = f"DELETE FROM {self.table_name} WHERE server_id = %s"
            mysql.execute_query(self.db_config, query, (sid,))
            self.latest_stats = {} # Clear cache too
            self._stats_cleared = True # Mark as cleared
        else:
            # Only log if we haven't succeeded yet, otherwise it's just normal startup noise
            if not self._stats_cleared:
                self.client.log(f"[{self.name}] Startup: Waiting for MySQL service to clear stats...")

    def on_gamescript_event(self, event_type, data):
        # Handle the event from Statistics GS plugin
        if event_type.lower() == "statistics_full_update":
            stats_map = data.get("stats", {})
            self.process_stats(stats_map)

    def process_stats(self, stats_map):
        mysql = self.client.get_service("MySQL")
        if not mysql or not self.db_config:
            # Still update cache even if MySQL is down
            for co_id_str, s in stats_map.items():
                self.latest_stats[int(co_id_str)] = s
            return

        ts = int(time.time())
        dt = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Insert stats for each company reported
        for co_id_str, s in stats_map.items():
            try:
                co_id = int(co_id_str)
                self.latest_stats[co_id] = s # Update Cache
                
                query = f"""
                INSERT INTO {self.table_name}
                (server_id, company_id, 
                company_name, performance, company_value, bank_balance, 
                income, loan, cargo_delivered, cargo_transported, cargo_count,
                trains, roadveh, ships, aircrafts, vehicles_count,
                stopped_vehs, stopped_val, crashed_vehs, crashed_val, 
                loss_vehs, loss_val, old_vehs, old_val, avg_veh_age,
                trainstation, truckstop, busstop, airport, dock,
                serviced_towns, avg_town_rating, station_count, 
                rated_stations, serviced_stations, avg_station_rating,
                infra_rail, infra_road, infra_tram, infra_signals, 
                infra_canals, infra_station, infra_airport, infra_dock, 
                timestamp, datetime) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                
                params = (
                    self.server_id, co_id,
		            s.get('company_name','Unnamed'), s.get('performance', 0), s.get('company_value', 0), s.get('bank_balance', 0), 
                    s.get('income', 0), s.get('loan', 0), s.get('cargo_delivered', 0), s.get('cargo_transported', 0), s.get('cargo_count', 0),
                    s.get('trains', 0), s.get('roadveh', 0), s.get('ships', 0), s.get('aircrafts', 0), s.get('vehicles_count', 0), 
                    s.get('stopped_vehs', 0), s.get('stopped_val', 0), s.get('crashed_vehs', 0), s.get('crashed_val', 0),
                    s.get('loss_vehs', 0), s.get('loss_val', 0), s.get('old_vehs', 0), s.get('old_val', 0), s.get('avg_veh_age', 0),
                    s.get('trainstation', 0), s.get('truckstop', 0), s.get('busstop', 0), s.get('airport', 0), s.get('dock', 0),
                    s.get('serviced_towns', 0), s.get('avg_town_rating', 0), s.get('station_count', 0), 
                    s.get('rated_stations', 0), s.get('serviced_stations', 0), s.get('avg_station_rating', 0),
                    s.get('infra_rail', 0), s.get('infra_road', 0), s.get('infra_tram', 0), s.get('infra_signals', 0), 
                    s.get('infra_canals', 0), s.get('infra_station', 0), s.get('infra_airport', 0), s.get('infra_dock', 0),
                    ts, dt
                )
                
                mysql.execute_query(self.db_config, query, params)
                
            except Exception as e:
                self.client.log(f"[{self.name}] Error processing Co {co_id_str}: {e}")

    def get_company_stats(self, company_id):
        """
        API for other plugins to retrieve the latest stats for a company.
        """
        return self.latest_stats.get(company_id)
