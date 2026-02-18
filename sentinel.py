import socket
import struct
import threading
import time
import os
import sys
import importlib.util
import inspect
import subprocess
import json
import configparser
import traceback
import xml.etree.ElementTree as ET

# --- IMPORT TYPES ---
try:
    from openttd_types import AdminPacketType, ServerPacketType, AdminUpdateType, AdminUpdateFrequency, NetworkAction
except ImportError:
    print("Error: 'openttd_types.py' not found.")
    sys.exit(1)

# --- PATH CONFIG ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(CURRENT_DIR)
PLUGINS_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "plugins"))
CONFIG_FILE = os.path.join(CURRENT_DIR, "controller_config.xml")

# --- XML HELPER ---
def parse_xml_config(path):
    tree = ET.parse(path)
    root = tree.getroot()
    return _xml_to_dict(root)

def _xml_to_dict(node):
    if len(node) > 0:
        tags = [child.tag for child in node]
        if len(tags) > 1 and all(t == tags[0] for t in tags):
            return [_xml_to_dict(child) for child in node]
        d = {}
        for child in node:
            val = _xml_to_dict(child)
            if child.tag in d:
                if not isinstance(d[child.tag], list):
                    d[child.tag] = [d[child.tag]]
                d[child.tag].append(val)
            else:
                d[child.tag] = val
        return d
    else:
        text = node.text.strip() if node.text else ""
        if text.lower() == "true": return True
        if text.lower() == "false": return False
        if text.isdigit(): return int(text)
        return text

# --- IMPORT INTERFACE ---
try:
    from plugin_interface import IPlugin
except ImportError:
    print("Error: plugin_interface.py must be in the same directory.")
    sys.exit(1)

# --- SERVER LAUNCHER ---
class ServerLauncher:
    def __init__(self, config):
        self.config = config
        self.process = None

    def start(self):
        exe = self.config.get("executable")
        cfg = self.config.get("config_file")
        extra = self.config.get("extra_args", "").split()

        if not os.path.exists(exe):
            print(f"[Launcher] Error: Executable not found at {exe}")
            return False

        cmd = [exe, "-c", cfg] + extra
        try:
            self.process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.STDOUT, 
                text=True, 
                bufsize=1
            )
            return True
        except Exception as e:
            print(f"[Launcher] Failed to start server: {e}")
            return False

    def stop(self):
        if self.process:
            print("[Launcher] Shutting down OpenTTD server...")
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            self.process = None
            print("[Launcher] Server stopped.")

    def is_running(self):
        return self.process is not None and self.process.poll() is None

# --- ADMIN CLIENT ---
class AdminClient:
    def __init__(self, config=None):
        self.name = "SENTINEL"
        self.version = "3.25-STATS-FIX-V2"
        self.config = config or {}
        self.game_cfg = {}
        
        # Game State Tracking
        self.current_year = 0
        self.current_seed = "Unknown"
        
        self.load_openttd_config()
        
        self.socket = None
        self.connected = False
        self.launcher = None # Attached by main()
        self._stop_event = threading.Event()
        
        self.plugins = [] 
        self.dashboard_active = False
        
        self.command_names = {} 
        self._initial_sync_done = False

    def print_banner(self):
        print("\033[2J\033[H")
        print(r"""
   _____ ______ _   _ _______ _____ _   _ ______ _      
  / ____|  ____| \ | |__   __|_   _| \ | |  ____| |     
 | (___ | |__  |  \| |  | |    | | |  \| | |__  | |     
  \___ \|  __| | . ` |  | |    | | | . ` |  __| | |     
  ____) | |____| |\  |  | |   _| |_| |\  | |____| |____ 
 |_____/|______|_| \_|  |_|  |_____|_| \_|______|______|
        OpenTTD Administration System | v""" + self.version + """
        """)

    def load_openttd_config(self):
        cfg_path = self.config.get("config_file", "")
        # Load DoCommands.xml
        self.do_command_schema = {}
        try:
            do_cmd_path = os.path.join(CURRENT_DIR, "DoCommands.xml")
            if os.path.exists(do_cmd_path):
                tree = ET.parse(do_cmd_path)
                root = tree.getroot()
                # <DoCommands><DoCommand Name="..."><Params><Param Name="..." Type="..." />...
                for cmd_node in root.findall(".//DoCommand"):
                    cname = cmd_node.get("Name")
                    params = []
                    for p_node in cmd_node.findall(".//Param"):
                        params.append((p_node.get("Name"), p_node.get("Type")))
                    self.do_command_schema[cname] = params
                print(f"[System] Loaded {len(self.do_command_schema)} command schemas from DoCommands.xml")
            else:
                 print(f"[System] Warning: DoCommands.xml not found at {do_cmd_path}")
        except Exception as e:
            print(f"[System] Error loading DoCommands.xml: {e}")

        if not cfg_path or not os.path.exists(cfg_path):
            print(f"[Config] Warning: OpenTTD config file not found at: {cfg_path}")
            return
        
        try:
            parser = configparser.ConfigParser(strict=False)
            parser.read(cfg_path)
            
            # NETWORK
            net = parser["network"] if "network" in parser else {}
            # We try to read it, but Packet 101 will overwrite this with the real live value
            self.game_cfg["server_name"] = net.get("server_name", "Unnamed Server")
            self.game_cfg["max_clients"] = int(net.get("max_clients", 25))
            self.game_cfg["max_companies"] = int(net.get("max_companies", 15))
            self.game_cfg["server_port"] = int(net.get("server_port", 3979))
            
            # GAME CREATION
            gen = parser["game_creation"] if "game_creation" in parser else {}
            self.game_cfg["starting_year"] = gen.get("starting_year", "Unknown")
            self.game_cfg["map_x"] = gen.get("map_x", "8")
            self.game_cfg["map_y"] = gen.get("map_y", "8")
            self.game_cfg["generation_seed"] = gen.get("generation_seed", "Unknown")
            
            # VEHICLE
            veh = parser["vehicle"] if "vehicle" in parser else {}
            self.game_cfg["max_trains"] = veh.get("max_trains", "500")
            self.game_cfg["max_roadveh"] = veh.get("max_roadveh", "500")
            self.game_cfg["max_ships"] = veh.get("max_ships", "500")
            self.game_cfg["max_aircraft"] = veh.get("max_aircraft", "500")
            self.game_cfg["max_train_length"] = veh.get("max_train_length", "7")
            
            # STATION
            stn = parser["station"] if "station" in parser else {}
            self.game_cfg["station_spread"] = stn.get("station_spread", "12")

        except Exception as e:
            print(f"[Config] Error parsing OpenTTD config: {e}")

    def get_service(self, name):
        for p in self.plugins:
            if p.name == name: return p
        return None

    def log(self, message):
        if self.dashboard_active:
            for p in self.plugins:
                if hasattr(p, 'log_entry'): p.log_entry(message)
        else:
            print(message)
            sys.stdout.flush()

    def broadcast_wrapper_log(self, text):
        if "Generation Seed:" in text:
            try:
                parts = text.split("Generation Seed:")
                if len(parts) > 1:
                    self.current_seed = parts[1].strip()
            except: pass

        if not self.dashboard_active and self.config.get("wrapper_logs", True):
             print(f"[WRAPPER] {text.strip()}")
        for p in self.plugins:
            if hasattr(p, 'on_wrapper_log'): 
                try: p.on_wrapper_log(text)
                except: pass

    def load_plugins(self, plugins_dir):
        if not os.path.isdir(plugins_dir): os.makedirs(plugins_dir, exist_ok=True)
        self.log(f"[System] Scanning: {plugins_dir}")
        for filename in os.listdir(plugins_dir):
            if filename.endswith(".py") and not filename.startswith("__"):
                try:
                    spec = importlib.util.spec_from_file_location(filename[:-3], os.path.join(plugins_dir, filename))
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    print(f"[System] Loaded module: {filename}")
                    for name, obj in inspect.getmembers(module):
                        if inspect.isclass(obj) and issubclass(obj, IPlugin) and obj is not IPlugin:
                            inst = obj(self)
                            self.plugins.append(inst)
                            inst.on_load()
                            if name == "Dashboard": self.dashboard_active = True
                except Exception as e:
                    self.log(f"[System] Load Error {filename}: {e}")

    # --- CENTRAL PACKET DISPATCHER ---
    def _dispatch_packet(self, ptype, payload):
        if not self._initial_sync_done:
            # Trigger on Protocol, Welcome, or first Client/Company info
            if ptype in [103, 104, 109, 114]:
                self._do_initial_sync()

        for p in self.plugins:
            try: p.on_event(ptype, payload)
            except: pass

        try:
            if ptype == ServerPacketType.SERVER_CLIENT_INFO or ptype == ServerPacketType.SERVER_CLIENT_UPDATE:
                if len(payload) >= 4:
                    cid = struct.unpack('<I', payload[0:4])[0]
                    try:
                        ip = ""; name = ""; company_id = 255
                        if ptype == ServerPacketType.SERVER_CLIENT_INFO:
                            ip, off = self.unpack_string(payload, 4)
                            name, off = self.unpack_string(payload, off)
                            lang, off = self.unpack_string(payload, off)
                            if off + 4 <= len(payload): off += 4 # Skip join date
                            if off < len(payload): company_id = payload[off]
                        else:
                            name, off = self.unpack_string(payload, 4)
                            if off < len(payload): company_id = payload[off]

                        if ptype == ServerPacketType.SERVER_CLIENT_INFO:
                            for p in self.plugins: 
                                if hasattr(p, 'on_player_join'): p.on_player_join(cid, name, ip, company_id)
                        else:
                            for p in self.plugins:
                                if hasattr(p, 'on_player_update'): p.on_player_update(cid, name, company_id)
                    except Exception as e:
                        # self.log(f"Error parsing Player Info: {e}")
                        pass

            elif ptype == ServerPacketType.SERVER_CLIENT_QUIT:
                if len(payload) >= 4:
                    cid = struct.unpack('<I', payload[0:4])[0]
                    for p in self.plugins: 
                        if hasattr(p, 'on_player_quit'): p.on_player_quit(cid)

            elif ptype == ServerPacketType.SERVER_CLIENT_ERROR:
                if len(payload) >= 5:
                    cid = struct.unpack('<I', payload[0:4])[0]
                    err = payload[4]
                    # print(f"[DEBUG] SERVER_CLIENT_ERROR: ClientID={cid}, ErrorCode={err}")
                    for p in self.plugins: 
                        if hasattr(p, 'on_player_error'): p.on_player_error(cid, err)

            elif ptype == ServerPacketType.SERVER_CHAT:
                if len(payload) >= 6:
                    action = payload[0]; dtype = payload[1]
                    cid = struct.unpack('<I', payload[2:6])[0]
                    msg, _ = self.unpack_string(payload, 6)
                    for p in self.plugins: 
                        if hasattr(p, 'on_chat'): p.on_chat(cid, msg, action, dtype)

            elif ptype == 113: # SERVER_COMPANY_NEW
                if len(payload) >= 1:
                    cid = payload[0]
                    for p in self.plugins:
                        if hasattr(p, 'on_company_created'): p.on_company_created(cid)

            elif ptype == ServerPacketType.SERVER_COMPANY_INFO or ptype == ServerPacketType.SERVER_COMPANY_UPDATE:
                if len(payload) >= 2:
                    cid = payload[0]
                    cname, off = self.unpack_string(payload, 1)
                    man_name, off = self.unpack_string(payload, off)
                    tail = payload[off:]
                    if len(tail) >= 2:
                        color = tail[0]; passworded = bool(tail[1])
                        founded = None; is_ai = None
                        if len(tail) >= 7:
                            try:
                                founded = struct.unpack_from('<I', tail, 2)[0]
                                is_ai = bool(tail[6])
                            except: pass
                        
                        # DEBUG: Trace company info
                        # self.log(f"[DEBUG] Company Info: CID={cid}, Name='{cname}', Manager='{man_name}', Color={color}, PW={passworded}, Founded={founded}, AI={is_ai}")

                        for p in self.plugins:
                            if hasattr(p, 'on_company_info'):
                                try: p.on_company_info(cid, cname, man_name, color, False, passworded, founded, is_ai)
                                except Exception as e: self.log(f"Error in {p.name}.on_company_info: {e}")

            elif ptype == ServerPacketType.SERVER_COMPANY_ECONOMY:
                if len(payload) >= 37: 
                    cid = payload[0]
                    money, loan, income = struct.unpack_from('<qQq', payload, 1)
                    delivered = struct.unpack_from('<H', payload, 25)[0]
                    value = struct.unpack_from('<Q', payload, 27)[0] 
                    perf = struct.unpack_from('<H', payload, 35)[0]
                    for p in self.plugins:
                        if hasattr(p, 'on_company_economy'):
                            p.on_company_economy(cid, money, loan, income, delivered, perf, value)

            elif ptype == ServerPacketType.SERVER_COMPANY_STATS:
                if len(payload) >= 21:
                    cid = payload[0]
                    v = struct.unpack_from('<5H', payload, 1)
                    legacy_vehs = (v[0], v[1] + v[2], v[3], v[4])
                    i = struct.unpack_from('<5H', payload, 11)
                    legacy_infra = (i[0] + i[1] + i[2], i[3], i[4])
                    for p in self.plugins:
                        if hasattr(p, 'on_company_stats'):
                            p.on_company_stats(cid, legacy_vehs, legacy_infra[0], legacy_infra[1], legacy_infra[2])

            elif ptype == 122: # SERVER_CMD_NAMES
                offset = 0
                try:
                    while offset < len(payload):
                        if offset + 1 > len(payload): break
                        cont = payload[offset]; offset += 1
                        if not cont: break
                        if offset + 2 > len(payload): break
                        cmd_id = struct.unpack_from('<H', payload, offset)[0]; offset += 2
                        cmd_name, off = self.unpack_string(payload, offset); offset = off
                        self.command_names[cmd_id] = cmd_name
                        for p in self.plugins:
                            if hasattr(p, 'on_command_name'): p.on_command_name(cmd_id, cmd_name)
                except: pass

            elif ptype == 127: # SERVER_CMD_LOGGING
                if len(payload) >= 13:
                    try:
                        cid, co_id, cmd_id = struct.unpack_from('<IBH', payload, 0)
                        data_len = struct.unpack_from('<H', payload, 7)[0]
                        data_buf = payload[9 : 9+data_len]
                        cmd_name = self.command_names.get(cmd_id, "Unknown")
                        
                        # Default params
                        params = {'p1': 0, 'p2': 0, 'tile': 0, 'text': ""}
                        p1 = 0; p2 = 0; tile = 0; text = ""

                        # Dynamic Parsing via DoCommands.xml schema
                        if cmd_name in self.do_command_schema:
                            schema = self.do_command_schema[cmd_name]
                            off = 0
                            for param_name, param_type in schema:
                                if off >= len(data_buf): break
                                val = None
                                
                                if param_type == "bool":
                                    val = bool(data_buf[off]); off += 1
                                elif param_type in ["int8", "byte", "sbyte", "uint8"]:
                                    val = data_buf[off]; off += 1
                                elif param_type in ["int16", "short", "uint16", "ushort"]:
                                    val = struct.unpack_from('<H', data_buf, off)[0]; off += 2
                                elif param_type in ["int32", "int", "uint32", "uint"]:
                                    val = struct.unpack_from('<I', data_buf, off)[0]; off += 4
                                elif param_type in ["int64", "long", "uint64", "ulong"]:
                                    val = struct.unpack_from('<Q', data_buf, off)[0]; off += 8
                                elif param_type == "string":
                                    val, off_new = self.unpack_string(data_buf, off); off = off_new
                                
                                if val is not None:
                                    params[param_name] = val
                                    # Backwards compatibility mapping
                                    if param_name == "Tile": tile = val
                                    if param_type == "string": text = val

                        # Legacy manual overrides (keep for safety/fallback)
                        if cmd_name == "CmdPlaceSign":
                            if "Tile" in params: tile = params["Tile"]
                            if "Text" in params: text = params["Text"]
                        elif cmd_name == "CmdRenameSign":
                             if "Text" in params: text = params["Text"]

                        # Dispatch with params
                        for p in self.plugins:
                            if hasattr(p, 'on_do_command'):
                                try:
                                    # Try new signature first
                                    p.on_do_command(cid, cmd_id, p1, p2, tile, text, 0, params)
                                except TypeError:
                                    # Fallback to old signature
                                    p.on_do_command(cid, cmd_id, p1, p2, tile, text, 0)
                    except Exception as e:
                        # self.log(f"Packet 127 Error: {e}")
                        pass

            elif ptype == 124: # GAMESCRIPT
                try:
                    json_str, _ = self.unpack_string(payload, 0)
                    data = json.loads(json_str)
                    if "event" in data:
                        for p in self.plugins:
                            if hasattr(p, "on_gamescript_event"):
                                p.on_gamescript_event(data["event"], data)
                except Exception as e: 
                    self.log(f"[Gamescript] Error parsing Packet 124: {e}")

            elif ptype == 103 or ptype == ServerPacketType.SERVER_PROTOCOL: # SERVER_PROTOCOL
                # If we get protocol info, we can also try syncing here as a fallback
                if not self._initial_sync_done:
                     self._do_initial_sync()

            elif ptype == ServerPacketType.SERVER_WELCOME:  # Packet 104
                try:
                    if not self._initial_sync_done:
                        self._do_initial_sync()
                    
                    server_name, off = self.unpack_string(payload, 0)
                    version, off = self.unpack_string(payload, off)
                    
                    # Store real server name from packet (overrides config file)
                    self.game_cfg['server_name'] = server_name
                    
                    if off + 1 <= len(payload):
                        dedicated = bool(payload[off])
                        off += 1
                        map_name, off = self.unpack_string(payload, off)
                        if off + 13 <= len(payload):
                            seed, landscape, start_date, width, height = struct.unpack_from('<IBIHH', payload, off)
                            for p in self.plugins:
                                if hasattr(p, 'on_map_info'):
                                    p.on_map_info(server_name, width, height, map_name, seed, landscape, start_date, 0)
                except Exception as e: 
                    self.log(f"Error parsing Welcome (Map Info): {e}")

            elif ptype == 116: # COMPANY_REMOVE
                if len(payload) >= 2:
                    cid = payload[0]; reason = payload[1]
                    for p in self.plugins:
                         if hasattr(p, 'on_company_remove'): p.on_company_remove(cid, reason)

            elif ptype == ServerPacketType.SERVER_DATE:
                if len(payload) >= 4:
                    date_val = struct.unpack('<I', payload[0:4])[0]
                    # Robust Year Calculation handling old (1920-based) and new (0-based) dates
                    if date_val > 500000: # New system (roughly year 1369+)
                        self.current_year = int(date_val / 365.2425)
                    else: # Old system (Days since 1920)
                        self.current_year = 1920 + int(date_val / 365.2425)
                    
                    for p in self.plugins: 
                        if hasattr(p, 'on_date_change'): p.on_date_change(date_val)

            elif ptype == ServerPacketType.SERVER_NEWGAME:
                self.send_rcon("getseed")
                for p in self.plugins: 
                    if hasattr(p, 'on_new_game'): p.on_new_game()

            elif ptype == ServerPacketType.SERVER_SHUTDOWN:
                for p in self.plugins: 
                    if hasattr(p, 'on_shutdown'): p.on_shutdown()
                
            elif ptype == ServerPacketType.SERVER_RCON:
                output, _ = self.unpack_string(payload, 2)
                
                # Capture Seed from RCON output
                if "Generation Seed:" in output:
                    try:
                        self.current_seed = output.split("Generation Seed:")[1].strip()
                    except: pass
                
                for p in self.plugins: 
                    if hasattr(p, 'on_rcon_result'): p.on_rcon_result("Unknown", output)

        except Exception as e:
            self.log(f"[EventDispatcher] Error parsing packet {ptype}: {e}")

    def _plugin_tick_loop(self):
        while not self._stop_event.is_set():
            for p in self.plugins:
                try: p.on_tick()
                except Exception as e: self.log(f"Tick Error ({p.name}): {e}")
            time.sleep(1.0)

    def _do_initial_sync(self):
        """Unified initialization sequence called once readiness is confirmed."""
        if self._initial_sync_done: return
        self._initial_sync_done = True
        
        self.log("[Network] Syncing game details...")
        
        # 1. Subscriptions (Bitmask 0x40 = Automatic updates)
        freq = AdminUpdateFrequency.ADMIN_FREQUENCY_AUTOMATIC
        self.send_update_frequency(AdminUpdateType.ADMIN_UPDATE_CLIENT_INFO, freq)
        self.send_update_frequency(AdminUpdateType.ADMIN_UPDATE_COMPANY_INFO, freq)
        self.send_update_frequency(AdminUpdateType.ADMIN_UPDATE_CHAT, freq)
        self.send_update_frequency(AdminUpdateType.ADMIN_UPDATE_CONSOLE, freq)
        self.send_update_frequency(AdminUpdateType.ADMIN_UPDATE_CMD_LOGGING, freq)
        self.send_update_frequency(AdminUpdateType.ADMIN_UPDATE_GAMESCRIPT, freq)
        
        # Periodic updates (Weekly/Poll)
        self.send_update_frequency(AdminUpdateType.ADMIN_UPDATE_COMPANY_ECONOMY, AdminUpdateFrequency.ADMIN_FREQUENCY_WEEKLY)
        self.send_update_frequency(AdminUpdateType.ADMIN_UPDATE_COMPANY_STATS, AdminUpdateFrequency.ADMIN_FREQUENCY_WEEKLY)
        self.send_update_frequency(AdminUpdateType.ADMIN_UPDATE_DATE, AdminUpdateFrequency.ADMIN_FREQUENCY_WEEKLY)

        # 2. Initial Polling (Fetch current state immediately)
        self.send_poll(AdminUpdateType.ADMIN_UPDATE_CLIENT_INFO, 0xFFFFFFFF)
        self.send_poll(AdminUpdateType.ADMIN_UPDATE_COMPANY_INFO, 0xFFFFFFFF)
        self.send_poll(AdminUpdateType.ADMIN_UPDATE_CMD_NAMES, 0)
        self.send_poll(AdminUpdateType.ADMIN_UPDATE_DATE, 0)
        
        # Fetch Seed via RCON
        self.send_rcon("getseed")

    def connect(self, host, port, password):
        max_retries = 20
        attempt = 0
        base_delay = 1.0
        max_delay = 30.0

        while attempt < max_retries:
            try:
                attempt += 1
                # use create_connection for dual-stack (IPv4/IPv6) support
                self.socket = socket.create_connection((host, port), timeout=15.0)
                peer = self.socket.getpeername()
                self.log(f"[Network] Connection Established to {peer[0]}! Sending Handshake...")
                
                self.socket.settimeout(None)
                self.connected = True
                self._stop_event.clear()
                
                threading.Thread(target=self._receive_loop, daemon=True).start()
                threading.Thread(target=self._plugin_tick_loop, daemon=True).start()
                
                # Send ADMIN_JOIN packet
                self.send_packet(AdminPacketType.ADMIN_JOIN, self._pack_string(password) + self._pack_string(self.name) + self._pack_string(self.version))
                self.log(f"[Network] Handshake (ADMIN_JOIN) sent. Waiting for server response...")
                
                for p in self.plugins:
                    if hasattr(p, 'on_connected'): p.on_connected()
                return
            except Exception as e:
                self.log(f"[Network] Connection Failed: {e}")
                if self.socket:
                    self.socket.close()
                    self.socket = None
                
                if attempt < max_retries:
                    # Exponential Backoff with Jitter
                    delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
                    actual_delay = delay * (0.5 + 0.5 * (hash(str(time.time())) % 100 / 100.0))
                    self.log(f"[Network] Retrying in {actual_delay:.2f} seconds...")
                    time.sleep(actual_delay)
                else:
                    raise Exception(f"Could not connect after {max_retries} attempts.")

    def disconnect(self):
        if self.connected:
            try: self.send_packet(AdminPacketType.ADMIN_QUIT)
            except: pass
            self.connected = False
            self._stop_event.set()
            if self.socket: self.socket.close()
            for p in self.plugins: 
                try: p.on_unload()
                except: pass
                if hasattr(p, 'on_disconnected'): p.on_disconnected()
            self.log("Disconnected.")

    def send_update_frequency(self, t, f): self.send_packet(AdminPacketType.ADMIN_UPDATE_FREQUENCY, struct.pack('<HH', t, f))
    def send_poll(self, t, d=0): self.send_packet(AdminPacketType.ADMIN_POLL, struct.pack('<BI', t, d))
    def send_chat(self, a, dt, di, m): self.send_packet(AdminPacketType.ADMIN_CHAT, struct.pack('<BBI', a, dt, di) + self._pack_string(m))
    def send_rcon(self, c): self.send_packet(AdminPacketType.ADMIN_RCON, self._pack_string(c))
    
    def send_packet(self, pt, pl=b''):
        if not self.socket or not self.connected: return
        try: 
            # self.log(f"[DEBUG] Raw Send: Type={pt} Len={len(pl)}")
            self.socket.sendall(struct.pack('<HB', 3 + len(pl), pt) + pl)
        except Exception as e: self.log(f"Send Error: {e}"); self.disconnect()

    def _receive_loop(self):
        buf = b''
        while not self._stop_event.is_set():
            try:
                while len(buf) < 3:
                    chunk = self.socket.recv(4096)
                    if not chunk: return self.disconnect()
                    buf += chunk
                
                plen, ptype = struct.unpack('<HB', buf[:3])
                
                while len(buf) < plen:
                    chunk = self.socket.recv(4096)
                    if not chunk: return self.disconnect()
                    buf += chunk
                
                self._dispatch_packet(ptype, buf[3:plen])
                buf = buf[plen:]
            except Exception as e: 
                if not self._stop_event.is_set(): self.disconnect()
                break

    def _pack_string(self, s): return s.encode('utf-8') + b'\x00'
    def unpack_string(self, pl, off=0):
        end = pl.find(b'\x00', off)
        return (pl[off:].decode('utf-8', 'replace'), len(pl)) if end == -1 else (pl[off:end].decode('utf-8', 'replace'), end + 1)

if __name__ == "__main__":
    if not os.path.exists(CONFIG_FILE):
        print(f"Error: {CONFIG_FILE} not found.")
        sys.exit(1)

    try:
        config = parse_xml_config(CONFIG_FILE)
        client = AdminClient(config)
        client.print_banner()
        launcher = ServerLauncher(config)
        client.launcher = launcher
        
        server_ready_event = threading.Event()
        def monitor_wrapper_output():
            try:
                if launcher.process:
                    for line in iter(launcher.process.stdout.readline, ''):
                        if line: 
                            client.broadcast_wrapper_log(line)
                            if ("Map generated, starting game" in line or "Map generation percentage complete: 100" in line) and not server_ready_event.is_set(): 
                                server_ready_event.set()
            except: pass
        
        if not launcher.start(): sys.exit(1)
        threading.Thread(target=monitor_wrapper_output, daemon=True).start()
        print("[Launcher] OpenTTD Server is Starting, Please wait...")
        if not config.get("wrapper_logs", True):
             print("[Launcher] TIP: If you want to see what is happening, please enable the 'Wrapper Logs' in the settings.")
        server_ready_event.wait(timeout=config.get("launch_wait", 60))
        
        client.load_plugins(PLUGINS_DIR)
        client.connect(config.get("admin_host", "127.0.0.1"), config.get("admin_port", 3979), config.get("admin_password", ""))
        
        while client.connected and launcher.is_running():
            cmd = input()
            if cmd == "quit": break
            client.send_rcon(cmd)
    
    except SystemExit as e: sys.exit(e.code)
    except Exception as e:
        with open("CRASH_REPORT.log", "w") as f: f.write(f"{e}\n{traceback.format_exc()}")
        sys.exit(1)
    finally:
        try: client.disconnect(); launcher.stop()
        except: pass
