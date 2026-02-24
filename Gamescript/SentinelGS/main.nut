require("Sentinel.nut");

class SentinelCore extends GSController
{
    // FIX: Defined missing 'api' variable to prevent crash
    api = null; 
    active_plugin = null;
    ticks = 0;
    month = -1;
    quarter = -1;

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

        // --- MODE SELECTION ---
        local mode = GSGameSettings.GetValue("game_mode");
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
                require("plugins/CityBuilder1/wrapper.nut");
                this.active_plugin = Sentinel_CB1(null);
            } 
            else if (mode == 2) {
                require("plugins/AphidCB/wrapper.nut");
                this.active_plugin = Sentinel_AphidCB(null);
            }
            else if (mode == 3) {
                require("plugins/CityBuilder3/wrapper.nut");
                this.active_plugin = Sentinel_CB3(null);
            }
            else if (mode == 4) {
                require("plugins/CityBuilderCargo/wrapper.nut");
                this.active_plugin = Sentinel_CBCargo(null);
            }
            else if (mode == 6) {
                require("plugins/BusyBee/wrapper.nut");
                this.active_plugin = Sentinel_BusyBee(null);
            }
            else if (mode == 7) {
                require("plugins/NovaCB/wrapper.nut");
                this.active_plugin = Sentinel_NovaCB(null);
            }
            else {
                Sentinel.Log("Mode " + mode + " is Company Value (Default)");
            }

            if (this.active_plugin != null) {
                Sentinel.Log("Starting Active Plugin...");
                this.active_plugin.Start();
            }
            
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
            
            this.Sleep(1);
            this.ticks++;
        }
    }

    function PushMonthlyStats() {
        Sentinel.Log("Processing Monthly Statistics Reporting...");
        
        // 1. Landscape Info (Legacy Event)
        Sentinel.SendAdmin({ event = "landscapeinfo", landscape = GSGame.GetLandscape() });
        
        // 2. Goal Type Info (0 for default/master)
        Sentinel.SendAdmin({ event = "goaltypeinfo", goalmastergame = 0 });

        // 3. Town Statistics
        Sentinel.PushTownStats();
        
        // 4. Company Population Updates
        Sentinel.PushCompanyStats();
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
                
                // --- ANTICHEAT: RCON Interception ---
                if (typeof data == "string" && data.find("check_crossing") == 0) {
                    local parts = split(data, " ");
                    if (parts.len() >= 4) {
                        local client_id = parts[1].tointeger();
                        local company_id = parts[2].tointeger();
                        local tile = parts[3].tointeger();

                        GSCompanyMode(company_id);

                        local has_violation = false;
                        
                        // Check Road Ownership
                        if (GSRoad.IsRoadTile(tile)) {
                            local r_owner = GSRoad.GetRoadOwner(tile);
                            if (r_owner != GSCompany.COMPANY_INVALID && r_owner != GSCompany.COMPANY_TOWN && r_owner != company_id) {
                                has_violation = true;
                                GSRoad.RemoveRoad(tile);
                            }
                        }

                        // Check Rail Ownership
                        if (GSRail.IsRailTile(tile)) {
                            local r_owner = GSRail.GetRailOwner(tile);
                            if (r_owner != GSCompany.COMPANY_INVALID && r_owner != GSCompany.COMPANY_TOWN && r_owner != company_id) {
                                has_violation = true;
                                GSRail.RemoveRail(tile);
                            }
                        }

                        if (has_violation) {
                            Sentinel.ChatPrivate(client_id, "NOT ALLOWED: You cannot build level crossings over infrastructure owned by another company! You must build a bridge instead.");
                        }
                    }
                }
                else if (this.active_plugin != null) {
                    this.active_plugin.OnAdminEvent(data);
                }
            }

            if (this.active_plugin != null) {
                this.active_plugin.OnEvent(type, ev);
            }
        }
    }
}