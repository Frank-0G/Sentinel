require("Sentinel.nut");
require("api.nut");
require("kernel_services.nut");

class SentinelCore extends GSController
{
    // Kernel State
    active_plugin = null;
    stats_plugin = null;
    anticheat_plugin = null;
    ticks = 0;
    month = -1;
    gs_log_level = 1;
    server_id = 99;
    
    // Goal Targets (Synced from Sentinel XML)
    goal_win_limit = 0;
    goal_population = 0;
    
    // Goal & Progress Metadata (Synced from active plugin)
    goal_mode = 0; // 0: None, 1: Value, 2: CityBuilder, 9: Script
    goal_target = 0;
    goal_unit = "EUR";
    goal_description = "company value";
    goal_announce_interval = 0;
    currency_multiplier = 1.0;

    // Victory state
    game_won = false;
    winner_cid = -1;
    
    company_progress = null; // { cid: { value: 0, progress: 0 } }
    company_colors = null;   // [ colorIdx, ... ]
    
    // Protection State (Ported from goal_system.py)
    claimed_towns = null; 
    
    last_record_date = 0;
    handshake_done = false;
    last_handshake_tick = -20; // Allow immediate first attempt
    plugins_initialized = false;

    constructor() {
        Sentinel.Log("Kernel Initializing...");
        // this.server_id is initially 99 (from class member)
        this.company_progress = {};
        this.company_colors = array(15, 15); // Default to Grey
        this.claimed_towns = {};
        for (local i = 0; i < 15; i++) {
            this.company_progress[i] <- { value = null, progress = 0, inhabitants = null, bb_goals = null };
        }
    }

    function Start()
    {
        GSLog.Info("[SENTINEL] Kernel Start() beginning...");
        Sentinel.Log("Kernel Started. Version: " + Sentinel.VERSION);
        Sentinel.SendAdmin({ event = "gamescript_start", version = Sentinel.VERSION });

        // Force initial stats and color sync
        this.SyncCompanyColors();
        this.month = GSDate.GetMonth(GSDate.GetCurrentDate());
        this.PushMonthlyStats();

        this.gs_log_level = GSController.GetSetting("log_level");
        Sentinel.SendAdmin({ event = "gs_log_level", value = this.gs_log_level });

        this.RunLoop();
    }

    function LazyInitPlugins() {
        if (this.plugins_initialized) return;
        this.plugins_initialized = true;

        Sentinel.Log("Config received. Initializing plugins now...");

        try {
            // --- BACKGROUND STATISTICS ---
            require("plugins/Statistics/wrapper.nut");
            this.stats_plugin = Sentinel_Statistics(this);
            this.stats_plugin.Start();

            // --- ANTI-CHEAT ---
            require("plugins/AntiCheat/wrapper.nut");
            this.anticheat_plugin = Sentinel_AntiCheat(this);
            this.anticheat_plugin.Start();

            // --- MODE SELECTION ---
            local mode = GSController.GetSetting("game_mode").tointeger();
            Sentinel.Log("Initializing Game Mode ID: " + mode.tostring());

            if (mode == 9) {
                require("plugins/CompanyValueGS4/wrapper.nut");
                this.active_plugin = Sentinel_CompanyValueGS4(this);
            } else if (mode == 1) {
                require("plugins/ClassicCB/wrapper.nut");
                this.active_plugin = Sentinel_ClassicCB(this);
            } else {
                require("plugins/CompanyValue/wrapper.nut");
                this.active_plugin = Sentinel_CompanyValue(this);
            }

            if (this.active_plugin != null) {
                // Ensure immediate sync BEFORE starting so the plugin skips its own defaults
                if (this.goal_win_limit > 0 || this.goal_population > 0) {
                    this.active_plugin.UpdateGoalConfig({ 
                        winlimit = this.goal_win_limit,
                        population = this.goal_population
                    });
                }

                Sentinel.Log("Starting Active Plugin...");
                this.active_plugin.Start();
            }

        } catch(e) {
            Sentinel.Error("CRITICAL INIT FAILURE: " + e.tostring());
        }
    }

    function RunLoop() {
        while(true) {
            this.HandleEvents();
			
			// for running without Sentinel controller
			if (this.GSController.GetSetting("development")) this.LazyInitPlugins();

            local now = GSDate.GetCurrentDate();
            if (GSDate.GetMonth(now) != this.month) {
                this.month = GSDate.GetMonth(now);
                this.PushMonthlyStats();
            }
            
            // Periodic Progress Recording (Every 15 game days)
            if (now >= (this.last_record_date + 15)) {
                this.last_record_date = now;
                this.RecordAllProgress();
            }

            if (this.active_plugin != null) {
                try {
                    this.active_plugin.Run(this.ticks);
                } catch(e) {
                    Sentinel.Error("Plugin Runtime Error: " + e);
                }
            }

            if (this.stats_plugin != null) {
                try {
                    this.stats_plugin.Run(this.ticks);
                } catch(e) { }
            }

            this.Sleep(1);
            this.ticks++;

            // Heartbeat & Config Sync
            if (this.ticks % 100 == 0) {
                local lvl = GSController.GetSetting("log_level");
                if (lvl != this.gs_log_level) {
                    this.gs_log_level = lvl;
                    Sentinel.SendAdmin({ event = "gs_log_level", value = this.gs_log_level });
                }
            }

            // Handshake Heartbeat (shout until Python answers)
            if (!this.handshake_done && this.ticks >= (this.last_handshake_tick + 20)) {
                this.last_handshake_tick = this.ticks;
                Sentinel.SendAdmin({ command = "gs_init" });
            }
        }
    }

    function HandleEvents() {
        while (GSEventController.IsEventWaiting()) {
            local ev = GSEventController.GetNextEvent();
            local type = ev.GetEventType();

            // Intercept Internal Meta-Events
            if (type == GSEvent.ET_ADMIN_PORT) {
                local ev_admin = GSEventAdminPort.Convert(ev);
                local data = ev_admin.GetObject();
                
                GSLog.Info("[SENTINEL] DEBUG: Received Admin Port Event.");
                if (data == null) {
                    GSLog.Error("[SENTINEL] ERROR: Admin Packet Object is NULL!");
                    continue;
                }

                local cmd = ("command" in data ? data.command : ("event" in data ? data.event : "unknown"));
                Sentinel.Log("Kernel Trace: Handling Admin Command: " + cmd.tostring());
                
                if (cmd == "goal" || cmd == "cv") {
                    this.HandleGoalCmd(data);
                    continue;
                } else if (cmd == "progress") {
                    this.HandleProgressCmd(data);
                    continue;
                } else if (cmd == "check_crossing") {
                    if (this.anticheat_plugin != null) {
                        this.anticheat_plugin.check_crossing(data.c_id, data.comp_id, data.tiles);
                    }
                    continue;
                } else if (cmd == "cmd_log") {
                    this.HandleCommandLog(data);
                    continue;
                } else if (cmd == "town_claimed") {
                    this.HandleTownClaimed(data);
                    continue;
                } else if (cmd == "town_unclaimed") {
                    this.HandleTownUnclaimed(data);
                    continue;
                } else if (cmd == "winner") {
                    this.HandleWinner(data);
                    continue;
                } else if (cmd == "goalreached") {
                    this.HandleGoalReachedCmd(data);
                    continue;
                } else if (cmd == "townstats") {
                    this.HandleTownStatsCmd(data);
                    continue;
                } else if (cmd == "claimed") {
                    this.HandleClaimedCmd(data);
                    continue;
                } else if (cmd == "ping") {
                    local t = ("tick" in data ? data.tick : 0);
                    local m = (this.active_plugin != null ? this.active_plugin.GetName() : "None");
                    Sentinel.SendAdmin({ command = "pong", tick = t, mode = m });
                    continue;
                } else if (cmd == "requestinfo") {
                    if (this.active_plugin != null) this.active_plugin.SendGoalInfo();
                    continue;
                } else if (cmd == "display_victory_popup") {
                    this.HandleDisplayVictoryPopup(data);
                    continue;
                } else if (cmd == "set_server_id" || cmd == "set_server_config") {
                    this.handshake_done = true;
                    if (cmd == "set_server_config") {
                    if ("winlimit" in data) this.goal_target = data.winlimit.tointeger();
                    if ("unit" in data) this.goal_unit = data.unit.tostring();
                    if ("desc" in data) this.goal_description = data.desc.tostring();
                    if ("interval" in data) this.goal_announce_interval = data.interval.tointeger();
                    
                    if ("currency" in data) {
                        local code = data.currency.tostring();
                        this.currency_multiplier = KernelServices.GetCurrencyMultiplier(code);
                        Sentinel.Log("Kernel Trace: Currency mapped to " + code + " (Multiplier: " + this.currency_multiplier + ")");
                    }

                    // Lazy Init Plugins BEFORE syncing config to them
                    this.LazyInitPlugins();

                    // Adjust Sentinel Target to base units for internal logic
                    if (this.currency_multiplier != 1.0) {
                        local raw_limit = data.winlimit.tointeger();
                        this.goal_target = (raw_limit / this.currency_multiplier).tointeger();
                        
                        // Update the data packet so plugins also get the normalized base-unit value
                        data.winlimit = this.goal_target;
                        Sentinel.Log("Kernel Trace: Winlimit normalized from " + raw_limit + " to " + this.goal_target + " for plugin sync.");
                    }

                    Sentinel.Log("Kernel Trace: Server config updated from Sentinel.");
                    if (this.active_plugin != null) {
                       this.active_plugin.UpdateGoalConfig(data);
                    }
                    }
                    
                    continue;
                }

                // Pass to active plugin if not handled
                if (this.active_plugin != null) {
                    this.active_plugin.OnAdminEvent(data);
                }
            }

            // Forward to active plugin
            if (this.active_plugin != null) {
                this.active_plugin.OnEvent(type, ev);
            }
            if (this.stats_plugin != null) {
                this.stats_plugin.OnEvent(type, ev);
            }
        }
    }

    // --- COMMAND HANDLERS (PORTED FROM PYTHON) ---

    function HandleGoalCmd(data) {
        Sentinel.Log("Kernel Trace: Entering HandleGoalCmd");
        local source = ("source" in data ? data.source : "game");
        local reply = [];

        // 1. Header
        if (this.goal_target == 0 && this.active_plugin != null) {
            this.active_plugin.SyncMetadata();
        }
        
        local display_target = (this.goal_target * this.currency_multiplier).tointeger();
        local formatted_val = KernelServices.FormatNumber(display_target);
        reply.push("--- First company with " + formatted_val + " " + this.goal_unit + " " + this.goal_description + " wins the game. ---");

        // 2. Rankings
        local ranks = [];
        for (local i = 0; i < 15; i++) {
            if (GSCompany.ResolveCompanyID(i) != GSCompany.COMPANY_INVALID) {
                local val = this.company_progress[i].value;
                local display_val = (val == null ? 0 : (val * this.currency_multiplier).tointeger());
                ranks.push({
                    cid = i,
                    progress = this.company_progress[i].progress,
                    value = display_val
                });
            }
        }

        // Sort by progress desc
        ranks.sort(function(a, b) {
            if (a.progress > b.progress) return -1;
            if (a.progress < b.progress) return 1;
            return 0;
        });

        for (local i = 0; i < ranks.len(); i++) {
            local r = ranks[i];
            local name = GSCompany.GetName(r.cid);
            local colorIdx = this.company_colors[r.cid];
            local color = KernelServices.GetColorName(colorIdx);
            local val_str = KernelServices.FormatNumber(r.value);
            reply.push("- (" + r.progress.tostring() + "%) Rank #" + (i + 1).tostring() + " is " + name + " (" + color + ") with " + val_str + " " + this.goal_unit + " " + this.goal_description);
        }

        if (ranks.len() == 0) reply.push("No active companies found.");

        Sentinel.Log("Kernel Trace: Sending Reply with " + reply.len().tostring() + " lines");
        this.SendReply(data, reply);
    }

    function HandleProgressCmd(data) {
        local max_progress = 0;
        for (local i = 0; i < 15; i++) {
            if (this.company_progress[i].progress > max_progress) {
                max_progress = this.company_progress[i].progress;
            }
        }

        local bar = KernelServices.GetProgressBar(max_progress);
        local msg = "Goal progress: " + bar + " - " + max_progress.tointeger() + "%";
        
        this.SendReply(data, [msg]);
    }

    function UpdateCompanyProgress(cid, value, progress) {
        this.company_progress[cid].value = value;
        this.company_progress[cid].progress = progress;

        local display_val = (value * this.currency_multiplier).tointeger();
        local formatted = KernelServices.FormatNumber(display_val);
        Sentinel.Log("Kernel Trace: Progress Update Co " + (cid+1) + " -> " + formatted + " (" + progress + "%)");
        
        // Optional: Trigger a broadcast if important threshold reached? 
    }

    function HandleClaimedCmd(data) {
        local reply = [];
        reply.push("--- Currently Claimed Towns ---");
        local found = false;
        foreach (cid, info in this.claimed_towns) {
            local co_name = GSCompany.GetName(cid);
            reply.push("Town '" + info.name + "' is claimed by " + co_name + " (" + (cid + 1) + ")");
            found = true;
        }
        if (!found) reply.push("No towns are currently claimed.");
        this.SendReply(data, reply);
    }

    function HandleTownStatsCmd(data) {
        // This is mode-dependent (usually CityBuilder)
        if (this.active_plugin != null && "HandleTownStats" in this.active_plugin) {
            this.active_plugin.HandleTownStats(data);
        } else {
            this.SendReply(data, ["Command '!townstats' is not available in the current game mode."]);
        }
    }

    // --- PROTECTION LOGIC ---

    function HandleTownClaimed(data) {
        local cid = data.company.tointeger();
        local tid = data.townid.tointeger();
        local tx = data.x.tointeger();
        local ty = data.y.tointeger();
        local range = ("range" in data ? data.range : 20).tointeger();

        local min_x = tx - range; if (min_x < 0) min_x = 0;
        local min_y = ty - range; if (min_y < 0) min_y = 0;
        local max_x = tx + range;
        local max_y = ty + range;

        this.claimed_towns[cid] <- {
            townid = tid,
            bbox = [min_x, min_y, max_x, max_y],
            name = ("town" in data ? data.town : "Unknown")
        };
        
        Sentinel.Log("Kernel: Recorded Claim for Co " + (cid+1).tostring() + " -> " + this.claimed_towns[cid].name);
    }

    function HandleTownUnclaimed(data) {
        local cid = data.company.tointeger();
        if (cid in this.claimed_towns) {
            delete this.claimed_towns[cid];
        }
    }

    function HandleCommandLog(data) {
        local cmd_name = ("name" in data ? data.name : "");
        local actor_cid = ("company" in data ? data.company : 255).tointeger();
        if (actor_cid == 255) return;

        // Simplified construction check (Ported from goal_system.py)
        local is_con = (cmd_name.len() >= 8 && cmd_name.slice(0, 8) == "CmdBuild") || 
                       (cmd_name.len() >= 9 && cmd_name.slice(0, 9) == "CmdRemove") || 
                       cmd_name == "CmdClearArea";
        
        if (is_con) {
            local tile = ("tile" in data ? data.tile : -1).tointeger();
            if (tile == -1) return;

            local tx = GSMap.GetTileX(tile);
            local ty = GSMap.GetTileY(tile);

            foreach (owner_cid, info in this.claimed_towns) {
                if (owner_cid == actor_cid) continue;

                local bb = info.bbox;
                if (tx >= bb[0] && tx <= bb[2] && ty >= bb[1] && ty <= bb[3]) {
                    this.HandleViolation(actor_cid, tile, info.name, owner_cid);
                    return;
                }
            }
        }
    }

    function HandleViolation(actor_cid, tile, town_name, owner_cid) {
        Sentinel.Log("!!! VIOLATION !!! Co " + (actor_cid+1) + " built in " + town_name + " (Owned by Co " + (owner_cid+1) + ")");
        
        // 1. Revert Tile
        GSTile.DemolishTile(tile); // As Kernel (Company 255 equivalent in some contexts, but GS always has power)
        
        // 2. Notify Python for penalties
        Sentinel.SendAdmin({
            command = "violation",
            company = actor_cid,
            tile = tile,
            town = town_name,
            owner = owner_cid
        });
    }

    function HandleWinner(data) {
        local cid = data.company.tointeger();
        local amount = ("amount" in data ? data.amount : 0);
        this.TriggerVictory(cid, amount);
    }

    function HandleGoalReachedCmd(data) {
        Sentinel.Log("HandleGoalReachedCmd: Searching for leader...");
        local leader_cid = -1;
        local max_progress = -1;
        local is_tie = false;
        
        for (local i = 0; i < 15; i++) {
            if (GSCompany.ResolveCompanyID(i) != GSCompany.COMPANY_INVALID) {
                local prog = this.company_progress[i].progress;
                if (prog > max_progress) {
                    max_progress = prog;
                    leader_cid = i;
                    is_tie = false;
                } else if (prog == max_progress && prog > 0) {
                    is_tie = true;
                }
            }
        }
        
        if (is_tie) {
            Sentinel.Log("Goal Reached: TIE detected at " + max_progress + "%. No winner.");
            this.TriggerVictory(-1, 0);
        } else if (leader_cid != -1) {
            Sentinel.Log("Goal Reached: Leader is Co " + (leader_cid+1) + " with " + max_progress + "%");
            this.TriggerVictory(leader_cid, this.company_progress[leader_cid].value);
        } else {
            Sentinel.Log("Goal Reached: No active companies with progress found.");
            this.TriggerVictory(-1, 0);
        }
    }

    function HandleWinner(data) {
        local cid = data.company.tointeger();
        local amount = ("amount" in data ? data.amount : 0);
        this.TriggerVictory(cid, amount);
    }

    function TriggerVictory(cid, amount) {
        if (this.game_won) return;
        this.game_won = true;
        this.winner_cid = cid;
        
        local name = (cid >= 0 ? GSCompany.GetName(cid) : "Draw");
        local color_name = "N/A";
        if (cid >= 0) {
            local scope = GSCompanyMode(cid);
            color_name = KernelServices.GetColorName(GSCompany.GetPrimaryLiveryColour(GSCompany.LS_DEFAULT));
        }
        Sentinel.Log("Kernel Victory Triggered: Winner=" + name + " (CID: " + cid + ")");
        
        // 1. Signal Python for Cleanup & Restart Countdown
        Sentinel.SendAdmin({
            command = "prepare_restart",
            winner = cid,
            winner_name = name,
            winner_color = color_name,
            amount = amount
        });
    }

    function HandleDisplayVictoryPopup(data) {
        local cid = ("winner_id" in data ? data.winner_id : -1);
        local amount = ("amount" in data ? data.amount : 0);
        
        // Use STR_GOAL_REACHED
        // Params: days, company, company_num, amount
        GSGoal.Question(25, GSCompany.COMPANY_INVALID, 
            GSText(GSText.STR_GOAL_REACHED, 0, cid, cid, amount), 
            GSGoal.QT_INFORMATION, GSGoal.BUTTON_OK);
    }

    function Tick() {
        if (this.game_won) {
        }
        
        // --- TICK FOR PLUGINS ---
        if (this.active_plugin != null) {
            this.active_plugin.Run(1);
        }
    }

    function SendReply(data, lines) {
        local reply_to = ("source_id" in data ? data.source_id : 0);
        local source = ("source" in data ? data.source : "game");
        
        Sentinel.SendAdmin({
            command = "chat_reply",
            target = reply_to,
            source = source,
            lines = lines
        });
    }

    // --- SHARED UTILITIES ---

    function UpdateGoalMetadata(type, target, unit, desc) {
        this.goal_mode = type;
        this.goal_target = target;
        this.goal_unit = unit;
        this.goal_description = desc;
    }

    function UpdateCompanyProgress(cid, value, progress) {
        this.UpdateCompanyStats(cid, { value = value, progress = progress });
    }

    function UpdateCompanyStats(cid, stats) {
        if (cid >= 0 && cid < 15) {
            foreach (key, val in stats) {
                if (key in this.company_progress[cid]) {
                    this.company_progress[cid][key] = val;
                }
            }
        }
    }

    function PushMonthlyStats() {
        this.SyncCompanyColors();
        Sentinel.SendAdmin({ event = "landscapeinfo", landscape = GSGame.GetLandscape() });
    }

    function RecordAllProgress() {
        Sentinel.Log("Kernel Trace: Recording multi-company progress snapshot...");
        local mode = GSController.GetSetting("game_mode").tointeger();
        local active_companies = [];
        
        for (local i = 0; i < 15; i++) {
            if (GSCompany.ResolveCompanyID(i) != GSCompany.COMPANY_INVALID) {
                local client_count = 0;
                local client_list = GSClientList();
                foreach (client_id, _ in client_list) {
                    if (GSClient.GetCompany(client_id) == i) {
                        client_count++;
                    }
                }
                
                active_companies.push({
                    id = i,
                    name = GSCompany.GetName(i),
                    value = this.company_progress[i].value,
                    progress = this.company_progress[i].progress,
                    inhabitants = this.company_progress[i].inhabitants,
                    bb_goals = this.company_progress[i].bb_goals,
                    clients = client_count
                });
            }
        }
        
        // Send snapshot to controller
        Sentinel.SendAdmin({
            command = "progress_snapshot",
            mode = mode,
            companies = active_companies
        });
    }

    function SyncCompanyColors() {
        for (local i = 0; i < 15; i++) {
            local cid = GSCompany.ResolveCompanyID(i);
            if (cid != GSCompany.COMPANY_INVALID) {
                local scope = GSCompanyMode(i);
                this.company_colors[i] = GSCompany.GetPrimaryLiveryColour(GSCompany.LS_DEFAULT);
            }
        }
    }

    // (Delegated to AntiCheat plugin)
}