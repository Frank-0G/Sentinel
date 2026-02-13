import http.server
import socketserver
import json
import threading
import os
from urllib.parse import urlparse

# Settings
PORT = 5555
DB_PATH = "GeoLite2-Country.mmdb"

# Global Reader
reader = None

try:
    import geoip2.database
    if os.path.exists(DB_PATH):
        print(f"[GeoIP Server] Loading Database: {DB_PATH}...")
        reader = geoip2.database.Reader(DB_PATH)
        print("[GeoIP Server] Database Loaded. Ready to serve.")
    else:
        print(f"[GeoIP Server] ERROR: {DB_PATH} not found.")
except ImportError:
    print("[GeoIP Server] ERROR: 'geoip2' library not installed.")

class GeoIPHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        # Parse URL: /resolve/1.2.3.4
        path = urlparse(self.path).path
        parts = path.strip("/").split("/")

        if len(parts) == 2 and parts[0] == "resolve":
            ip = parts[1]
            response_data = {"ip": ip, "country": "Unknown", "iso": "XX"}
            
            if reader:
                try:
                    resp = reader.country(ip)
                    name = resp.country.name
                    iso = resp.country.iso_code
                    if name: response_data["country"] = name
                    if iso: response_data["iso"] = iso
                except Exception:
                    pass # IP not found
            
            # Send JSON Header
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            
            # Send Body
            self.wfile.write(json.dumps(response_data).encode())
        else:
            self.send_response(404)
            self.end_headers()

    # Silence default logging to keep console clean
    def log_message(self, format, *args):
        return

class ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    """Handle requests in a separate thread."""

if __name__ == "__main__":
    if not reader:
        print("CRITICAL: Server starting without Database. All lookups will fail.")
    
    server = ThreadedHTTPServer(('127.0.0.1', PORT), GeoIPHandler)
    print(f"[GeoIP Server] Listening on http://127.0.0.1:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[GeoIP Server] Stopping...")
        server.server_close()
