import json
import urllib.request
from plugin_interface import IPlugin

class GeoIPService(IPlugin):
    def __init__(self, client):
        super().__init__(client)
        self.name = "GeoIPService"
        self.version = "1.3-ALIASES-COMPAT"

        # Cache stores dictionaries now: {'country': 'Netherlands', 'iso': 'NL'}
        self.ip_cache = {}
        self.local_api_url = "http://127.0.0.1:5555/resolve/{ip}"

    def _lookup(self, ip):
        """Internal helper to get full geo data (Name + ISO)"""
        if ip in ["127.0.0.1", "0.0.0.0", "::1", "", None]:
            return {"country": "Localhost", "iso": "XX"}

        if ip in self.ip_cache:
            return self.ip_cache[ip]

        # 1. Try Local Microservice
        try:
            url = self.local_api_url.replace("{ip}", ip)
            with urllib.request.urlopen(url, timeout=0.5) as response:
                data = json.loads(response.read().decode())
                # Normalize response keys
                res = {
                    "country": data.get("country", "Unknown"),
                    "iso": data.get("iso", "??")
                }
                self.ip_cache[ip] = res
                return res
        except:
            pass

        # 2. Fallback: External Web API
        try:
            # Request both country name AND countryCode
            url = f"http://ip-api.com/json/{ip}?fields=country,countryCode"
            with urllib.request.urlopen(url, timeout=1.5) as response:
                data = json.loads(response.read().decode())
                res = {
                    "country": data.get("country", "Unknown"),
                    "iso": data.get("countryCode", "??")
                }
                self.ip_cache[ip] = res
                return res
        except:
            return {"country": "Unknown", "iso": "??"}

    # --- Current API ---
    def resolve(self, ip):
        """Returns Full Country Name (e.g. Netherlands) - Used by Welcome Msg"""
        return self._lookup(ip).get("country", "Unknown")

    def resolve_iso(self, ip):
        """Returns ISO Code (e.g. NL) - Used by IRC"""
        return self._lookup(ip).get("iso", "??")

    # --- Backwards-compatible aliases (fixes your !players error) ---
    def resolve_country(self, ip):
        """Legacy alias for older plugins/commands."""
        return self.resolve(ip)

    def resolve_country_iso(self, ip):
        """Legacy alias for older plugins/commands."""
        return self.resolve_iso(ip)
