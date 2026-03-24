require("Sentinel.nut");

class SentinelCore extends GSController
{
    // FIX: Defined missing 'api' variable to prevent crash
    api = null; 
    active_plugin = null;
    stats_plugin = null;
    ticks = 0;
    month = -1;
    quarter = -1;
    gs_log_level = -1;

    constructor() {
        GSLog.Info("SentinelGS: Kernel Initializing...");
    }

    function Start()
    {
        Sentinel.Log("Kernel Started. Version: " + Sentinel.VERSION);
        Sentinel.SendAdmin({ event = "gamescript_start", version = Sentinel.VERSION });

        // Force initial stats push
        this.month = GSDate.GetMonth(GSDate.GetCurrentDate());
        this.PushMonthlyStats();

        // Sync Log Level to Controller
        this.gs_log_level = GSController.GetSetting("log_level");
        Sentinel.SendAdmin({ event = "gs_log_level", value = this.gs_log_level });

        // --- MODE SELECTION ---
        local mode = GSController.GetSetting("game_mode");
        // ... (rest of the mode selection logic) ...
        // I'll use a larger block to ensure context is correct
        Sentinel.Log("Read 'game_mode' setting: " + mode);

        // Fallback for broken/missing config
        if (mode <= -1) { 
            Sentinel.Log("Warning: Config missing or corrupt (-1). Defaulting to Mode 2 (Aphid).");
            mode = 0; 
        }
        
        Sentinel.Log("Initializing Game Mode ID: " + mode);

        try {
            if (mode == 0) {
                require("plugins/CompanyValue/wrapper.nut");
                this.active_plugin = Sentinel_CompanyValue(null);
            }
            else if (mode == 1) {
                require("plugins/ClassicCB/wrapper.nut");
                this.active_plugin = Sentinel_ClassicCB(null);
            } 
            else {
                Sentinel.Log("Mode " + mode + " is Company Value (Default)");
                require("plugins/CompanyValue/wrapper.nut");
                this.active_plugin = Sentinel_CompanyValue(null);
            }

            if (this.active_plugin != null) {
                Sentinel.Log("Starting Active Plugin...");
                this.active_plugin.Start();
            }

            // --- BACKGROUND STATISTICS ---
            require("plugins/Statistics/wrapper.nut");
            this.stats_plugin = Sentinel_Statistics(null);
            this.stats_plugin.Start();
            
        } catch(e) {
            Sentinel.Error("CRITICAL INIT FAILURE: " + e);
        }

        this.RunLoop();
    }

    function RunLoop() {
        while(true) {
            this.HandleEvents();
            
            local now = GSDate.GetCurrentDate();
            if (GSDate.GetMonth(now) != this.month) {
                this.month = GSDate.GetMonth(now);
                this.PushMonthlyStats();
            }

            if (this.active_plugin != null) {
                try { 
                    this.active_plugin.Run(this.ticks);
                } catch(e) {
                    Sentinel.Error("Runtime Error: " + e);
                }
            }

            if (this.stats_plugin != null) {
                try {
                    this.stats_plugin.Run(this.ticks);
                } catch(e) { }
            }
            
            this.Sleep(1);
            this.ticks++;

            // Periodically sync log level if it changes in-game
            if (this.ticks % 100 == 0) {
                local lvl = GSController.GetSetting("log_level");
                if (lvl != this.gs_log_level) {
                    this.gs_log_level = lvl;
                    Sentinel.SendAdmin({ event = "gs_log_level", value = this.gs_log_level });
                }
            }
        }
    }

    function PushMonthlyStats() {
        Sentinel.Log("Processing Monthly Statistics Reporting...");
        
        // 1. Landscape Info (Legacy Event)
        Sentinel.SendAdmin({ event = "landscapeinfo", landscape = GSGame.GetLandscape() });
        
        // Note: Goal Type Info, Town Statistics, and Company Population Updates 
        // are now handled exclusively by the active GameScript plugins (CityBuilder, CompanyValue, etc)
        // to prevent overwriting of actual plugin data with default generic data.
    }

    function HandleEvents() {
        while (GSEventController.IsEventWaiting()) {
            local ev = GSEventController.GetNextEvent();
            local type = ev.GetEventType();

            // --- LEGACY EVENT FORWARDING ---
            switch (type) {
                case GSEvent.ET_VEHICLE_CRASHED:
                    local crash = GSEventVehicleCrashed.Convert(ev);
                    local v_id = crash.GetVehicleID();
                    Sentinel.SendAdmin({ 
                        event = "vehiclecrash", 
                        vehicleid = v_id, 
                        company = GSVehicle.GetOwner(v_id), 
                        crashsite = crash.GetCrashSite(), 
                        crashreason = crash.GetCrashReason() 
                    });
                    break;
                    
                case GSEvent.ET_COMPANY_MERGER:
                    local merger = GSEventCompanyMerger.Convert(ev);
                    Sentinel.SendAdmin({ 
                        event = "companymerge", 
                        oldcompany = merger.GetOldCompanyID(), 
                        newcompany = merger.GetNewCompanyID() 
                    });
                    break;
                    
                case GSEvent.ET_COMPANY_BANKRUPT:
                    local bankrupt = GSEventCompanyBankrupt.Convert(ev);
                    Sentinel.SendAdmin({ event = "companybankrupt", company = bankrupt.GetCompanyID() });
                    break;

                case GSEvent.ET_COMPANY_IN_TROUBLE:
                    local trouble = GSEventCompanyInTrouble.Convert(ev);
                    Sentinel.SendAdmin({ event = "companyintrouble", company = trouble.GetCompanyID() });
                    break;

                case GSEvent.ET_GOAL_QUESTION_ANSWER:
                    local qa = GSEventGoalQuestionAnswer.Convert(ev);
                    Sentinel.SendAdmin({ 
                        event = "goalquestionanswer", 
                        id = qa.GetUniqueID(), 
                        company = qa.GetCompany(), 
                        button = qa.GetButton() 
                    });
                    break;
            }

            if (type == GSEvent.ET_ADMIN_PORT) {
                local data = GSEventAdminPort.Convert(ev).GetObject();
                if (data != null && "event" in data && data.event == "check_crossing") {
                    this.check_crossing(data.c_id, data.comp_id, data.tiles);
                } else if (data != null && "event" in data && data.event == "ping") {
                    Sentinel.SendAdmin({ event = "pong", tick = this.ticks, time = GSDate.GetCurrentDate() });
                } else if (data != null && "event" in data && data.event == "requestinfo") {
                    if (this.active_plugin != null) this.active_plugin.SendGoalInfo();
                } else if (this.active_plugin != null) {
                    this.active_plugin.OnAdminEvent(data);
                }
            }

            if (this.active_plugin != null) {
                this.active_plugin.OnEvent(type, ev);
            }

            if (this.stats_plugin != null) {
                this.stats_plugin.OnEvent(type, ev);
            }
        }
    }

    // --- ANTICHEAT: Native Crossing Check ---
    function check_crossing(c_id_str, comp_id_str, tiles_array) {
        GSController.Sleep(1); // Wait 1 tick for map update
        local c_id = c_id_str.tointeger();
        local comp_id = comp_id_str.tointeger();
        
        if (tiles_array.len() == 0) return;

        local min_x = 999999;
        local max_x = 0;
        local min_y = 999999;
        local max_y = 0;

        foreach (t_id_str in tiles_array) {
            local t_id = t_id_str.tointeger();
            local x = GSMap.GetTileX(t_id);
            local y = GSMap.GetTileY(t_id);
            if (x < min_x) min_x = x;
            if (x > max_x) max_x = x;
            if (y < min_y) min_y = y;
            if (y > max_y) max_y = y;
        }

        local crossing_demolished = false;

        for (local x = min_x; x <= max_x; x++) {
            for (local y = min_y; y <= max_y; y++) {
                local t_id = GSMap.GetTileIndex(x, y);

                local has_road = GSRoad.IsRoadTile(t_id);
                local has_rail = GSRail.IsRailTile(t_id);
                local has_tram = false;
                try { has_tram = GSRoad.IsTramTile(t_id); } catch(e) { }

                // LOG: Find where road and rail coexist
                if ((has_road || has_tram) && has_rail) {
                    local rail_owner = 255;
                    local road_owner = 255;
                    
                    // In GS API 1.6, GSTile.GetOwner returns the rail owner on level crossings.
                    // We must check neighbors to find the road owner.
                    rail_owner = GSTile.GetOwner(t_id);
                    
                    local neighbors = [
                        GSMap.GetTileIndex(x + 1, y), GSMap.GetTileIndex(x - 1, y),
                        GSMap.GetTileIndex(x, y + 1), GSMap.GetTileIndex(x, y - 1)
                    ];
                    
                    foreach (nt_id in neighbors) {
                        if (!GSMap.IsValidTile(nt_id)) continue;
                        if (GSRoad.IsRoadTile(nt_id) && !GSRail.IsRailTile(nt_id)) {
                            road_owner = GSTile.GetOwner(nt_id);
                            if (road_owner != 255) break; 
                        }
                    }
                    
                    // Fallback: If still 255, it might be a tram
                    if (road_owner == 255 && has_tram) {
                        foreach (nt_id in neighbors) {
                            if (!GSMap.IsValidTile(nt_id)) continue;
                            if (GSRoad.IsTramTile(nt_id) && !GSRail.IsRailTile(nt_id)) {
                                road_owner = GSTile.GetOwner(nt_id);
                                if (road_owner != 255) break;
                            }
                        }
                    }

                    local violation = false;
                    local to_remove = ""; // "rail", "road"
                    local original_owner = 255;

                    if (rail_owner == comp_id) {
                        // Builder is the rail owner. Check if it's over someone else's road.
                        if (road_owner != 255 && road_owner != comp_id) {
                            violation = true; to_remove = "rail"; original_owner = road_owner;
                        }
                    } else if (road_owner == comp_id) {
                        // Builder is the road owner. Check if it's over someone else's rail.
                        if (rail_owner != 255 && rail_owner != comp_id) {
                            violation = true; to_remove = "road"; original_owner = rail_owner;
                        }
                    }

                    if (violation) {
                         if (!crossing_demolished) {
                            Sentinel.Log("[AntiCheat] !!! VIOLATION DETECTED !!! Tile " + t_id + " - " + to_remove + " built by Company " + comp_id + " over infrastructure of Company " + original_owner);
                            
                            local __mode = GSCompanyMode(comp_id);
                            
                            // Targeted removal - dynamic parameter check
                            local res = false;
                            if (to_remove == "rail") {
                                // For rail-over-road, the road IS the overlay. 
                                // To remove the rail base, we MUST remove the road overlay first.
                                // If the builder doesn't own the road, we act as the road owner to clear it.
                                if (road_owner != 255 && road_owner != comp_id) {
                                    {
                                        local __tmp_mode = GSCompanyMode(road_owner);
                                        GSTile.DemolishTile(t_id); // Removes road
                                    }
                                    
                                    // Now remove the violating rail as the builder
                                    {
                                        local __tmp_mode = GSCompanyMode(comp_id);
                                        res = GSTile.DemolishTile(t_id); // Removes rail
                                    }
                                    
                                    // Now RESTORE the road as the original owner
                                    if (road_owner != 255) {
                                        local __tmp_mode = GSCompanyMode(road_owner);
                                        // Give them a small budget to cover restoration costs
                                        GSCompany.ChangeBankBalance(road_owner, 2000, GSCompany.EXPENSES_OTHER, t_id);
                                        
                                        // Attempt to rebuild road based on neighbors
                                        local road_neighbors = [];
                                        foreach (nt_id in neighbors) {
                                            if (GSMap.IsValidTile(nt_id) && GSRoad.IsRoadTile(nt_id)) road_neighbors.push(nt_id);
                                        }
                                        
                                        if (road_neighbors.len() >= 1) {
                                            // Sleep 1 tick to ensure tile state is updated
                                            GSController.Sleep(1);
                                            
                                            local r_type = has_tram ? GSRoad.ROADTYPE_TRAM : GSRoad.ROADTYPE_ROAD;
                                            GSRoad.SetCurrentRoadType(r_type);
                                            
                                            // Rebuild by connecting to each neighbor to ensure the tile is filled
                                            foreach (nt_id in road_neighbors) {
                                                GSRoad.BuildRoad(t_id, nt_id);
                                            }
                                        }
                                    }
                                } else {
                                    // Standard removal if builder owns road
                                    res = GSRail.RemoveRail(t_id, t_id, GSRail.GetRailType(t_id));
                                }
                            } else if (to_remove == "road") {
                                // For road-over-rail, road is the overlay. Removing overlay is easy.
                                local rtype = GSRoad.ROADTYPE_ROAD;
                                res = GSRoad.RemoveRoad(t_id, rtype);
                                if (!res) {
                                    rtype = GSRoad.ROADTYPE_TRAM;
                                    res = GSRoad.RemoveRoad(t_id, rtype);
                                }
                                if (!res) {
                                    res = GSTile.DemolishTile(t_id); // This usually works as the overlay owner
                                }
                            }
                            
                            Sentinel.ChatPrivate(c_id, "ILLEGAL CROSSING: You cannot build over another company's infrastructure! Build a bridge or tunnel instead.");
                            crossing_demolished = true;
                        }
                    }
                }
            }
        }
    }
}