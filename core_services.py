from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional, Callable, Any, List, Tuple
import time


# -----------------------
# State (single source of truth)
# -----------------------

@dataclass
class PlayerState:
    client_id: int
    name: str = ""
    ip: str = ""
    language: str = ""
    iso: str = ""
    company_id: int = 255
    joined_at: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)


@dataclass
class CompanyState:
    company_id: int
    name: str = ""
    manager: str = ""
    color: int = 0
    protected: bool = False
    passworded: bool = False
    founded: Optional[int] = None
    is_ai: bool = False
    last_update: float = field(default_factory=time.time)
    economy: dict = field(default_factory=dict)
    stats: dict = field(default_factory=dict)


@dataclass
class ServerSessionState:
    started_at: float = field(default_factory=time.time)
    openttd_date_days: Optional[int] = None
    last_newgame_at: float = field(default_factory=time.time)
    peak_players: int = 0


class StateManager:
    """
    Single source of truth for players/companies/session.
    Plugins should prefer reading from client.state instead of maintaining parallel caches.
    """
    def __init__(self):
        self.players: Dict[int, PlayerState] = {}
        self.companies: Dict[int, CompanyState] = {}
        self.session = ServerSessionState()
        self._listeners: Dict[str, List[Callable[..., Any]]] = {}

    def subscribe(self, event_name: str, callback: Callable[..., Any]) -> None:
        event_name = event_name.lower().strip()
        if event_name not in self._listeners:
            self._listeners[event_name] = []
        if callback not in self._listeners[event_name]:
            self._listeners[event_name].append(callback)

    def unsubscribe(self, event_name: str, callback: Callable[..., Any]) -> None:
        event_name = event_name.lower().strip()
        if event_name in self._listeners:
            try:
                self._listeners[event_name].remove(callback)
            except ValueError:
                pass

    def publish(self, event_name: str, *args, **kwargs) -> None:
        event_name = event_name.lower().strip()
        listeners = self._listeners.get(event_name, [])
        for callback in list(listeners):
            try:
                callback(*args, **kwargs)
            except Exception as e:
                print(f"[StateManager] Error in event listener for {event_name}: {e}")

    # ---- Players ----
    def upsert_player(
        self,
        client_id: int,
        *,
        name: Optional[str] = None,
        ip: Optional[str] = None,
        language: Optional[str] = None,
        company_id: Optional[int] = None,
        iso: Optional[str] = None,
    ) -> PlayerState:
        is_new = client_id not in self.players
        ps = self.players.get(client_id)
        if ps is None:
            ps = PlayerState(client_id=client_id)
            self.players[client_id] = ps

        changed = {}
        if name is not None and ps.name != name:
            changed['name'] = (ps.name, name)
            ps.name = name
        if ip is not None and ps.ip != ip:
            changed['ip'] = (ps.ip, ip)
            ps.ip = ip
        if language is not None and ps.language != language:
            changed['language'] = (ps.language, language)
            ps.language = language
        if company_id is not None and ps.company_id != company_id:
            changed['company_id'] = (ps.company_id, company_id)
            ps.company_id = company_id
        if iso is not None and ps.iso != iso:
            changed['iso'] = (ps.iso, iso)
            ps.iso = iso

        ps.last_seen = time.time()
        self.session.peak_players = max(self.session.peak_players, len(self.players))
        
        if is_new:
            self.publish("data_changed", type="player_join", client_id=client_id, name=ps.name, ip=ps.ip, company_id=ps.company_id, iso=ps.iso)
        elif changed:
            self.publish("data_changed", type="player_update", client_id=client_id, changed=changed)
        return ps

    def remove_player(self, client_id: int) -> None:
        if client_id in self.players:
            p = self.players.pop(client_id)
            self.publish("data_changed", type="player_quit", client_id=client_id, player=p)

    def get_player(self, client_id: int) -> Optional[PlayerState]:
        return self.players.get(client_id)

    def find_player_by_name(self, name: str) -> Optional[PlayerState]:
        needle = (name or "").strip().lower()
        for p in self.players.values():
            if p.name.strip().lower() == needle:
                return p
        return None

    # ---- Companies ----
    def upsert_company(
        self,
        company_id: int,
        *,
        name: Optional[str] = None,
        manager: Optional[str] = None,
        color: Optional[int] = None,
        protected: Optional[bool] = None,
        passworded: Optional[bool] = None,
        founded: Optional[int] = None,
        is_ai: Optional[bool] = None,
    ) -> CompanyState:
        is_new = company_id not in self.companies
        cs = self.companies.get(company_id)
        if cs is None:
            cs = CompanyState(company_id=company_id)
            self.companies[company_id] = cs

        changed = {}
        if name is not None and cs.name != name:
            changed['name'] = (cs.name, name)
            cs.name = name
        if manager is not None and cs.manager != manager:
            changed['manager'] = (cs.manager, manager)
            cs.manager = manager
        if color is not None and cs.color != color:
            changed['color'] = (cs.color, color)
            cs.color = color
        if protected is not None and cs.protected != protected:
            changed['protected'] = (cs.protected, protected)
            cs.protected = protected
        if passworded is not None and cs.passworded != passworded:
            changed['passworded'] = (cs.passworded, passworded)
            cs.passworded = passworded
        if founded is not None and cs.founded != founded:
            changed['founded'] = (cs.founded, founded)
            cs.founded = founded
        if is_ai is not None and cs.is_ai != is_ai:
            changed['is_ai'] = (cs.is_ai, is_ai)
            cs.is_ai = is_ai

        cs.last_update = time.time()
        
        if is_new:
            self.publish("data_changed", type="company_created", company_id=company_id)
        elif changed:
            self.publish("data_changed", type="company_info", company_id=company_id, changed=changed)
        return cs

    def remove_company(self, company_id: int) -> None:
        if company_id in self.companies:
            co = self.companies.pop(company_id, None)
            self.publish("data_changed", type="company_remove", company_id=company_id, company=co)

    def update_company_economy(self, company_id: int, economy: dict) -> None:
        cs = self.companies.get(company_id)
        changed = cs is None or cs.economy != economy
        cs = self.upsert_company(company_id)
        cs.economy = economy
        cs.last_update = time.time()
        if changed:
            self.publish("data_changed", type="company_economy", company_id=company_id)

    def update_company_stats(self, company_id: int, stats: dict) -> None:
        cs = self.companies.get(company_id)
        changed = cs is None or cs.stats != stats
        cs = self.upsert_company(company_id)
        cs.stats = stats
        cs.last_update = time.time()
        if changed:
            self.publish("data_changed", type="company_stats", company_id=company_id)

    # ---- Session ----
    def mark_newgame(self) -> None:
        self.session.last_newgame_at = time.time()
        self.publish("data_changed", type="newgame")

    def set_date(self, openttd_date_days: int) -> None:
        changed = self.session.openttd_date_days != openttd_date_days
        self.session.openttd_date_days = openttd_date_days
        if changed:
            self.publish("data_changed", type="date_change", openttd_date_days=openttd_date_days)


# -----------------------
# Subscriptions (deduplicated update frequency)
# -----------------------

class SubscriptionManager:
    """
    Deduplicates ADMIN_UPDATE_FREQUENCY requests coming from multiple plugins.

    Rule: for a given update type, we OR together requested frequencies.
    """
    def __init__(self, send_update_frequency: Callable[[int, int], None]):
        self._send = send_update_frequency
        self._desired: Dict[int, int] = {}

    def subscribe(self, update_type: int, frequency: int) -> None:
        current = self._desired.get(int(update_type), 0)
        merged = current | int(frequency)
        if merged != current:
            self._desired[int(update_type)] = merged
            self._send(int(update_type), int(merged))

    def snapshot(self) -> Dict[int, int]:
        return dict(self._desired)


# -----------------------
# Commands (optional core router)
# -----------------------

@dataclass
class CommandContext:
    source: str  # "ingame" or "irc" (or others)
    client_id: Optional[int] = None
    company_id: Optional[int] = None
    name: str = ""
    raw: str = ""
    is_admin: bool = False
    meta: Dict[str, Any] = field(default_factory=dict)


class CommandRouter:
    """
    Minimal core command router.
    Plugins can register commands via:
      - client.commands.register("help", handler, admin_only=False)
    Or implement IPlugin.register_commands(router).
    """
    def __init__(self, prefix: str = "!"):
        self.prefix = prefix or "!"
        self._commands: Dict[str, Tuple[Callable[[CommandContext, List[str]], Any], bool]] = {}

    def set_prefix(self, prefix: str) -> None:
        if prefix:
            self.prefix = prefix

    def register(
        self,
        name: str,
        handler: Callable[[CommandContext, List[str]], Any],
        *,
        admin_only: bool = False,
    ) -> None:
        key = (name or "").strip().lower()
        if not key:
            raise ValueError("Command name cannot be empty")
        self._commands[key] = (handler, admin_only)

    def unregister(self, name: str) -> None:
        self._commands.pop((name or "").strip().lower(), None)

    def handle_message(self, ctx: CommandContext) -> bool:
        msg = (ctx.raw or "").strip()
        if not msg.startswith(self.prefix):
            return False

        parts = msg[len(self.prefix):].strip().split()
        if not parts:
            return False

        cmd = parts[0].lower()
        args = parts[1:]
        item = self._commands.get(cmd)
        if not item:
            return False

        handler, admin_only = item
        if admin_only and not ctx.is_admin:
            return True  # recognized but denied

        handler(ctx, args)
        return True

    def list_commands(self) -> List[str]:
        return sorted(self._commands.keys())


class ClientCacheDict(dict):
    def __init__(self, client):
        self._client = client

    def __getitem__(self, key):
        p = self._client.state.get_player(key)
        if not p:
            raise KeyError(key)
        return {
            'name': p.name,
            'ip': p.ip,
            'company': p.company_id,
            'iso': p.iso or "??"
        }

    def __contains__(self, key):
        return self._client.state.get_player(key) is not None

    def get(self, key, default=None):
        if key in self:
            return self[key]
        return default

    def items(self):
        return {
            cid: {
                'name': p.name,
                'ip': p.ip,
                'company': p.company_id,
                'iso': p.iso or "??"
            }
            for cid, p in self._client.state.players.items()
        }.items()

    def __len__(self):
        return len(self._client.state.players)

    def __setitem__(self, key, value):
        p = self._client.state.get_player(key)
        if p:
            if 'iso' in value: p.iso = value['iso']
            if 'ip' in value: p.ip = value['ip']
            if 'name' in value: p.name = value['name']
            if 'company' in value: p.company_id = value['company']
        else:
            self._client.state.upsert_player(
                key, 
                name=value.get('name', ''), 
                ip=value.get('ip', ''), 
                company_id=value.get('company', 255), 
                iso=value.get('iso', '??')
            )

    def __delitem__(self, key):
        self._client.state.remove_player(key)

    def clear(self):
        self._client.state.players.clear()


class CompanyCacheDict(dict):
    def __init__(self, client):
        self._client = client

    def __getitem__(self, key):
        c = self._client.state.companies.get(key)
        if not c:
            raise KeyError(key)
        return {
            'name': c.name,
            'color': c.color,
            'passworded': c.passworded
        }

    def __contains__(self, key):
        return key in self._client.state.companies

    def get(self, key, default=None):
        if key in self:
            return self[key]
        return default

    def items(self):
        return {
            cid: {
                'name': c.name,
                'color': c.color,
                'passworded': c.passworded
            }
            for cid, c in self._client.state.companies.items()
        }.items()

    def __len__(self):
        return len(self._client.state.companies)

    def __setitem__(self, key, value):
        c = self._client.state.companies.get(key)
        if c:
            if 'name' in value: c.name = value['name']
            if 'color' in value: c.color = value['color']
            if 'passworded' in value: c.passworded = value['passworded']
        else:
            self._client.state.upsert_company(
                key,
                name=value.get('name', ''),
                color=value.get('color', 0),
                passworded=value.get('passworded', False)
            )

    def __delitem__(self, key):
        self._client.state.remove_company(key)

    def clear(self):
        self._client.state.companies.clear()

