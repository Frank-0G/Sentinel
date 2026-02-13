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

    # ---- Players ----
    def upsert_player(
        self,
        client_id: int,
        *,
        name: Optional[str] = None,
        ip: Optional[str] = None,
        language: Optional[str] = None,
        company_id: Optional[int] = None,
    ) -> PlayerState:
        ps = self.players.get(client_id)
        if ps is None:
            ps = PlayerState(client_id=client_id)
            self.players[client_id] = ps

        if name is not None:
            ps.name = name
        if ip is not None:
            ps.ip = ip
        if language is not None:
            ps.language = language
        if company_id is not None:
            ps.company_id = company_id

        ps.last_seen = time.time()
        self.session.peak_players = max(self.session.peak_players, len(self.players))
        return ps

    def remove_player(self, client_id: int) -> None:
        self.players.pop(client_id, None)

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
    ) -> CompanyState:
        cs = self.companies.get(company_id)
        if cs is None:
            cs = CompanyState(company_id=company_id)
            self.companies[company_id] = cs

        if name is not None:
            cs.name = name
        if manager is not None:
            cs.manager = manager
        if color is not None:
            cs.color = color
        if protected is not None:
            cs.protected = protected
        if passworded is not None:
            cs.passworded = passworded

        cs.last_update = time.time()
        return cs

    def remove_company(self, company_id: int) -> None:
        self.companies.pop(company_id, None)

    def update_company_economy(self, company_id: int, economy: dict) -> None:
        cs = self.upsert_company(company_id)
        cs.economy = economy
        cs.last_update = time.time()

    def update_company_stats(self, company_id: int, stats: dict) -> None:
        cs = self.upsert_company(company_id)
        cs.stats = stats
        cs.last_update = time.time()

    # ---- Session ----
    def mark_newgame(self) -> None:
        self.session.last_newgame_at = time.time()

    def set_date(self, openttd_date_days: int) -> None:
        self.session.openttd_date_days = openttd_date_days


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
