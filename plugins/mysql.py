import threading
import json
import hashlib
from plugin_interface import IPlugin

try:
    import mysql.connector
    from mysql.connector import pooling
except ImportError:
    print("[MySQL] Error: 'mysql-connector-python' not installed.")

class MySQL(IPlugin):
    def __init__(self, client):
        super().__init__(client)
        self.name = "MySQL"
        self.version = "1.0-THREADED"
        self.pools = {}
        self.lock = threading.Lock()

    def get_pool(self, db_config):
        # Create a unique key for this config to reuse pools
        # Sort keys to ensure stable hash for same config
        config_str = json.dumps(db_config, sort_keys=True)
        config_hash = hashlib.md5(config_str.encode('utf-8')).hexdigest()

        with self.lock:
            if config_hash not in self.pools:
                # Create a new pool
                # Use a specific pool name to avoid conflicts if multiple pools connect to same DB
                pool_name = f"pool_{config_hash[:8]}"
                self.client.log(f"[{self.name}] Creating new DB pool: {pool_name}")
                self.pools[config_hash] = mysql.connector.pooling.MySQLConnectionPool(
                    pool_name=pool_name,
                    pool_size=12,
                    **db_config
                )
            return self.pools[config_hash]

    def execute_query(self, db_config, query, params=None, callback=None, fetch=False):
        """
        Executes a query in a separate thread.
        db_config: Dictionary containing host, user, password, database, etc.
        query: SQL query string.
        params: Tuple of parameters for the query.
        callback: Function to call with result (if fetch=True) or None (if fetch=False).
                  Callback receives the result set (list of dicts) or None.
        fetch: Boolean, if True fetches results (SELECT), if False commits (INSERT/UPDATE).
        """
        if not db_config:
            self.client.log(f"[{self.name}] Error: Empty db_config provided.")
            return

        threading.Thread(
            target=self._worker, 
            args=(db_config, query, params, callback, fetch),
            daemon=True
        ).start()

    def _worker(self, db_config, query, params, callback, fetch):
        conn = None
        cursor = None
        result = None
        
        try:
            pool = self.get_pool(db_config)
            conn = pool.get_connection()
            
            # Use dictionary cursor if fetching, regular if not (though dict cursor is fine for both)
            cursor = conn.cursor(dictionary=True, buffered=True)
            cursor.execute(query, params or ())
            
            if fetch:
                result = cursor.fetchall()
            else:
                conn.commit()
            
        except Exception as e:
            self.client.log(f"[{self.name}] SQLError: {e} | Query: {query[:50]}...")
        finally:
            if cursor:
                try: cursor.close()
                except: pass
            if conn:
                try: conn.close()
                except: pass
        
        # Invoke callback if provided
        if callback:
            try:
                callback(result)
            except Exception as e:
                self.client.log(f"[{self.name}] CallbackError: {e}")

    def on_unload(self):
        # access to protected member _cnx_queue of CMySQLConnection which is not ideal but standard cleanup is hard with pools
        # In practice, we just let them die with the process or when GC'd
        self.pools.clear()
