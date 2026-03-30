/**
 * Statistics Plugin for SentinelGS
 * Collects detailed company, vehicle, and station metrics using an amortized approach.
 */
class Statistics
{
    api = null;
    state = 0; // 0: Idle, 1: Collecting Vehicles, 2: Collecting Stations, 3: Finalizing
    
    // Cycle Management
    c_idx = 0; // Current index in company iteration
    co_id = -1; // Current active company being processed
    last_run_tick = -4000; // Force run on first hit if tick 0
    
    // Work Lists for amortization
    v_list = null;
    s_list = null;
    
    // Results
    curr_results = null; 
    all_results = null;  
    c_observed = null;   

    constructor(_api) {
        this.api = _api;
        this.all_results = {};
    }

    function GetName() { return "Statistics"; }
    function Start() { this.api.Log("Plugin Statistics: Initialized (API 15 Native)"); }

    function Run(ticks) {
        try {
            // Trigger cycle every 4000 ticks (~2 months)
            if (this.state == 0 && (ticks - this.last_run_tick >= 4000 || ticks < this.last_run_tick)) {
                this.last_run_tick = ticks;
                this.StartCycle();
            }

            if (this.state > 0) {
                this.ProcessStep();
            }
        } catch(e) {
            this.api.Log("CRITICAL ERROR in Statistics Plugin: " + e);
            this.state = 0; // Reset to avoid infinite crash loop
        }
    }

    function StartCycle() {
        this.state = 1;
        this.c_idx = GSCompany.COMPANY_FIRST;
        this.all_results = {};
        this.PrepareNextCompany();
    }

    function PrepareNextCompany() {
        while (this.c_idx <= GSCompany.COMPANY_LAST) {
            local cid = GSCompany.ResolveCompanyID(this.c_idx);
            if (cid != GSCompany.COMPANY_INVALID) {
                this.co_id = cid;
                this.c_observed = {};
                this.curr_results = {
                    stopped_vehs = 0, stopped_val = 0,
                    crashed_vehs = 0, crashed_val = 0,
                    loss_vehs = 0, loss_val = 0,
                    old_vehs = 0, old_val = 0,
                    avg_veh_age = 0, v_count = 0,
                    station_count = 0, serviced_stations = 0,
                    avg_station_rating = 0, rated_stations = 0,
                    avg_town_rating = 0,
                    income = 0, delivered = 0,
                    cargo_types_transported = 0,
                    bank_balance = 0, loan = 0, performance_rating = 0,
                    infra_rail = 0, infra_road = 0, infra_tram = 0, 
                    infra_signals = 0, infra_canals = 0, infra_station = 0, 
                    infra_airport = 0, infra_dock = 0,
                    tot_age = 0, tot_rating = 0, company_name = ""
                };
                
                local scope = GSCompanyMode(this.co_id);

                this.curr_results.company_name = GSCompany.GetName(this.co_id);
                this.curr_results.bank_balance = GSCompany.GetBankBalance(this.co_id);
                this.curr_results.loan = GSCompany.GetLoanAmount(); 
                this.curr_results.income = GSCompany.GetQuarterlyIncome(this.co_id, 0);
                this.curr_results.delivered = GSCompany.GetQuarterlyCargoDelivered(this.co_id, 0);
                this.curr_results.performance_rating = GSCompany.GetQuarterlyPerformanceRating(this.co_id, 0);
                
                // Infrastructure Piece Counts (API 15)
                this.curr_results.infra_rail = GSInfrastructure.GetInfrastructurePieceCount(this.co_id, GSInfrastructure.INFRASTRUCTURE_RAIL);
                this.curr_results.infra_road = GSInfrastructure.GetInfrastructurePieceCount(this.co_id, GSInfrastructure.INFRASTRUCTURE_ROAD);
                this.curr_results.infra_signals = GSInfrastructure.GetInfrastructurePieceCount(this.co_id, GSInfrastructure.INFRASTRUCTURE_SIGNALS);
                this.curr_results.infra_canals = GSInfrastructure.GetInfrastructurePieceCount(this.co_id, GSInfrastructure.INFRASTRUCTURE_CANAL);
                this.curr_results.infra_station = GSInfrastructure.GetInfrastructurePieceCount(this.co_id, GSInfrastructure.INFRASTRUCTURE_STATION);
                this.curr_results.infra_airport = GSInfrastructure.GetInfrastructurePieceCount(this.co_id, GSInfrastructure.INFRASTRUCTURE_AIRPORT);
                
                // Fallbacks for types not appearing in basic INFRA list
                if ("INFRASTRUCTURE_TRAM" in GSInfrastructure) this.curr_results.infra_tram = GSInfrastructure.GetInfrastructurePieceCount(this.co_id, GSInfrastructure.INFRASTRUCTURE_TRAM);
                if ("INFRASTRUCTURE_DOCK" in GSInfrastructure) this.curr_results.infra_dock = GSInfrastructure.GetInfrastructurePieceCount(this.co_id, GSInfrastructure.INFRASTRUCTURE_DOCK);
                    
                // Town Ratings 
                local t_list = GSTownList();
                local t_rating_sum = 0;
                local t_count = 0;
                foreach (tid, _ in t_list) {
                    local r = GSTown.GetRating(tid, this.co_id);
                    if (r > 0) {
                        t_rating_sum += r;
                        t_count++;
                    }
                }
                this.curr_results.avg_town_rating = (t_count > 0) ? (t_rating_sum / t_count) : 0;
                
                this.v_list = GSVehicleList();
                this.s_list = GSStationList(GSStation.STATION_ANY);
                
                this.state = 1; 
                this.c_idx++; 
                return;
            }
            this.c_idx++;
        }
        this.state = 3; 
    }

    function ProcessStep() {
        if (this.state == 1) {
            local scope = GSCompanyMode(this.co_id);
            local quota = 50;
            while (quota > 0 && !this.v_list.IsEmpty()) {
                local vid = this.v_list.Begin();
                this.v_list.RemoveItem(vid);
                this.curr_results.v_count++;
                local val = GSVehicle.GetCurrentValue(vid);
                local st = GSVehicle.GetState(vid);
                if (st == GSVehicle.VS_STOPPED || st == GSVehicle.VS_IN_DEPOT) {
                    this.curr_results.stopped_vehs++;
                    this.curr_results.stopped_val += val;
                } else if (st == GSVehicle.VS_CRASHED) {
                    this.curr_results.crashed_vehs++;
                    this.curr_results.crashed_val += val;
                }
                if (GSVehicle.GetProfitThisYear(vid) < 0) {
                    this.curr_results.loss_vehs++;
                    this.curr_results.loss_val += val;
                }
                local max_age = GSVehicle.GetMaxAge(vid);
                if (max_age > 0) {
                    local age_pct = (GSVehicle.GetAge(vid) * 100) / max_age;
                    this.curr_results.tot_age += age_pct;
                }
                if (GSVehicle.GetAgeLeft(vid) <= 0) {
                    this.curr_results.old_vehs++;
                    this.curr_results.old_val += val;
                }
                quota--;
            }
            if (this.v_list.IsEmpty()) this.state = 2;
        } else if (this.state == 2) {
            local scope = GSCompanyMode(this.co_id);
            local quota = 25;
            while (quota > 0 && !this.s_list.IsEmpty()) {
                local sid = this.s_list.Begin();
                this.s_list.RemoveItem(sid);
                this.curr_results.station_count++;
                if (GSVehicleList_Station(sid).Count() > 0) this.curr_results.serviced_stations++;
                local c_list = GSCargoList_StationAccepting(sid);
                local station_rating_sum = 0;
                local station_rating_count = 0;
                foreach (cid, _ in c_list) {
                    local r = GSStation.GetCargoRating(sid, cid);
                    if (r > 0) {
                        station_rating_sum += r;
                        station_rating_count++;
                        if (!(cid in this.c_observed)) this.c_observed[cid] <- 0;
                        this.c_observed[cid]++;
                    }
                }
                if (station_rating_count > 0) {
                    this.curr_results.tot_rating += (station_rating_sum / station_rating_count);
                    this.curr_results.rated_stations++;
                }
                quota--;
            }
            if (this.s_list.IsEmpty()) {
                this.FinalizeCompany();
                this.PrepareNextCompany(); 
            }
        } else if (this.state == 3) {
            this.api.SendToController({ event = "statistics_full_update", stats = this.all_results });
            this.state = 0;
        }
    }

    function FinalizeCompany() {
        this.curr_results.avg_veh_age = (this.curr_results.v_count > 0) ? (100 - (this.curr_results.tot_age / this.curr_results.v_count)) : 0;
        this.curr_results.avg_station_rating = (this.curr_results.rated_stations > 0) ? (this.curr_results.tot_rating / this.curr_results.rated_stations) : 0;
        local variety = 0;
        local threshold = this.curr_results.station_count * 0.2;
        foreach (cid, count in this.c_observed) { if (count >= threshold) variety++; }
        this.curr_results.cargo_types_transported = variety;
        delete this.curr_results.tot_age;
        delete this.curr_results.tot_rating;
        this.all_results[this.co_id.tostring()] <- this.curr_results;
    }
}
