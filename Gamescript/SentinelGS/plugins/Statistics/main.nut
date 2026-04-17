/**
 * Statistics Plugin for SentinelGS
 * Collects detailed company, vehicle, and station metrics using an amortized approach.
 */
class Statistics
{
    api = null;

    // Cycle Management
    last_run_tick = -4000; // Force run on first hit if tick 0

    // Results
    curr_results = null;
    all_results = null;

    constructor(_api) {
        this.api = _api;
        this.all_results = {};
    }

    function GetName() { return "Statistics"; }
    function Start() { this.api.Log("Plugin Statistics: Initialized (API 15 Native)"); }

    function Run(ticks) {
        try {
            // Trigger cycle every 4000 ticks (~2 months)
            if (ticks - this.last_run_tick >= 2000 || ticks < this.last_run_tick) {
                this.last_run_tick = ticks;
                this.StartCycle();
            }
        } catch(e) {
            this.api.Log("CRITICAL ERROR in Statistics Plugin: " + e);
            this.state = 0; // Reset to avoid infinite crash loop
        }
    }

    function StartCycle() {
        this.all_results = {};
        this.GetStatistics();
    }

    function GetStatistics() {

        // Create list of valid companies
        local companies = GSList();
    	for (local c_id = GSCompany.COMPANY_FIRST; c_id < GSCompany.COMPANY_LAST; c_id++) {
    		if (GSCompany.ResolveCompanyID(c_id) != GSCompany.COMPANY_INVALID) {
                companies.AddItem(c_id, 1);
    		} else {
    			continue;
    		}
        }

        // Start iterating companies
        local c_id = 0;
        foreach (c_id, _ in companies) {
            this.curr_results = {
                    company_name = "",
                    bank_balance = 0,
                    loan = 0,
                    company_value = 0,
                    income = 0,
                    cargo_delivered = 0,
                    performance = 0,
                    infra_rail = 0,
                    infra_road = 0,
                    infra_signals = 0,
                    infra_canals = 0,
                    infra_station = 0,
                    infra_airport = 0,
                    infra_tram = 0,
                    infra_dock = 0,
                    trains = 0,
                    roadveh = 0,
                    ships = 0,
                    aircrafts = 0,
                    vehicles_count = 0,
                    avg_town_rating = 0,
                    serviced_towns = 0,
                    stopped_vehs = 0,
                    stopped_val = 0,
                    crashed_vehs = 0,
                    crashed_val = 0,
                    loss_vehs = 0,
                    loss_val = 0,
                    old_vehs = 0,
                    old_val = 0,
                    avg_veh_age = 0,
                    station_count = 0,
                    serviced_stations = 0,
                    rated_stations = 0,
                    avg_station_rating = 0,
                    trainstation = 0,
                    truckstop = 0,
                    busstop = 0,
                    airport = 0,
                    dock = 0,
                    cargo_transported = 0,
                    cargo_count = 0
            };
            local scope = GSCompanyMode(c_id);

            // Basic company info
            this.curr_results.company_name = GSCompany.GetName(c_id);
            this.curr_results.bank_balance = GSCompany.GetBankBalance(c_id);
            this.curr_results.loan = GSCompany.GetLoanAmount();

            //Quarterly data for current quarter (API 15)
            this.curr_results.company_value = GSCompany.GetQuarterlyCompanyValue(c_id, 1);
            this.curr_results.income = GSCompany.GetQuarterlyIncome(c_id, 1);
            this.curr_results.cargo_delivered = GSCompany.GetQuarterlyCargoDelivered(c_id, 1);
            this.curr_results.performance = GSCompany.GetQuarterlyPerformanceRating(c_id, 1);

            // Infrastructure Piece Counts (API 15)
            this.curr_results.infra_rail = GSInfrastructure.GetInfrastructurePieceCount(c_id, GSInfrastructure.INFRASTRUCTURE_RAIL);
            this.curr_results.infra_road = GSInfrastructure.GetInfrastructurePieceCount(c_id, GSInfrastructure.INFRASTRUCTURE_ROAD);
            this.curr_results.infra_signals = GSInfrastructure.GetInfrastructurePieceCount(c_id, GSInfrastructure.INFRASTRUCTURE_SIGNALS);
            this.curr_results.infra_canals = GSInfrastructure.GetInfrastructurePieceCount(c_id, GSInfrastructure.INFRASTRUCTURE_CANAL);
            this.curr_results.infra_station = GSInfrastructure.GetInfrastructurePieceCount(c_id, GSInfrastructure.INFRASTRUCTURE_STATION);
            this.curr_results.infra_airport = GSInfrastructure.GetInfrastructurePieceCount(c_id, GSInfrastructure.INFRASTRUCTURE_AIRPORT);

            // Fallbacks for types not appearing in basic INFRA list
            if ("INFRASTRUCTURE_TRAM" in GSInfrastructure) this.curr_results.infra_tram = GSInfrastructure.GetInfrastructurePieceCount(this.co_id, GSInfrastructure.INFRASTRUCTURE_TRAM);
            if ("INFRASTRUCTURE_DOCK" in GSInfrastructure) this.curr_results.infra_dock = GSInfrastructure.GetInfrastructurePieceCount(this.co_id, GSInfrastructure.INFRASTRUCTURE_DOCK);

            //Create and sort townlist of current company
            local towns = GSList();
            local t_rating_sum = 0;
            foreach (t_id, _ in GSTownList()) {
                    local rating = GSTown.GetRating(t_id, c_id);
                    if (rating > 0) {
                        towns.AddItem(t_id, rating);
                        t_rating_sum += rating;
                        }
            }
            this.curr_results.avg_town_rating = (towns.Count() > 0) ? (t_rating_sum / towns.Count()) : 0; //average town rating for company
            this.curr_results.serviced_towns = towns.Count();


            // check vehicles of current company
            local tot_age = 0;
            foreach (v_id, _ in GSVehicleList()) {

                // count vehicles by type
                if (GSVehicle.GetVehicleType(v_id) == GSVehicle.VT_RAIL)
                    this.curr_results.trains++;
                else if (GSVehicle.GetVehicleType(v_id) == GSVehicle.VT_ROAD)
                    this.curr_results.roadveh++;
                else if (GSVehicle.GetVehicleType(v_id) == GSVehicle.VT_WATER)
                    this.curr_results.ships++;
                else if (GSVehicle.GetVehicleType(v_id) == GSVehicle.VT_AIR)
                	this.curr_results.aircrafts++;
                else if (GSVehicle.GetVehicleType(v_id) == GSVehicle.VT_INVALID)
                    continue; //unknown type, do nothing
                this.curr_results.vehicles_count++; // total vehicle count

                // common vehicle metrics
                local val = GSVehicle.GetCurrentValue(v_id);
                local st = GSVehicle.GetState(v_id);
                if (st == GSVehicle.VS_STOPPED || st == GSVehicle.VS_IN_DEPOT) {
                    this.curr_results.stopped_vehs++;
                    this.curr_results.stopped_val += val;
                } else if (st == GSVehicle.VS_CRASHED) {
                    this.curr_results.crashed_vehs++;
                    this.curr_results.crashed_val += val;
                }

                // loss making vehicles
                if (GSVehicle.GetProfitThisYear(v_id) < 0) {
                    this.curr_results.loss_vehs++;
                    this.curr_results.loss_val += val;
                }

                // average age calculation
                local max_age = GSVehicle.GetMaxAge(v_id);
                if (max_age > 0) {
                    local age_pct = (GSVehicle.GetAge(v_id) * 100) / max_age;
                    tot_age += age_pct;
                }

                // end of life vehicles
                if (GSVehicle.GetAgeLeft(v_id) <= 0) {
                    this.curr_results.old_vehs++;
                    this.curr_results.old_val += val;
                }
            }
            this.curr_results.avg_veh_age = (this.curr_results.vehicles_count > 0) ? (100 - (tot_age / this.curr_results.vehicles_count)) : 0;

            local CompanyCargoList = GSList();
            local tot_station_rating = 0;
            // check stations of current company

            foreach (s_id, _ in GSStationList(GSStation.STATION_ANY)) {

                this.curr_results.station_count++; // total station count

                if (GSCargoList_StationAccepting(s_id).Count() > 0)
                    this.curr_results.serviced_stations++; // serviced station count

                // station rating calculation
                local station_rating_sum = 0;
                local station_rating_count = 0;
                foreach (cargo_id, _ in GSCargoList_StationAccepting(s_id)) {
                    local r = GSStation.GetCargoRating(s_id, cargo_id);
                    if (r > 0) {
                        station_rating_sum += r;
                        station_rating_count++;
                    }
                }
                if (station_rating_count > 0) {
                    tot_station_rating += (station_rating_sum / station_rating_count);
                    this.curr_results.rated_stations++;
                }

                //check transported cargo
                foreach(cargo_id, _ in GSCargoList()){
                    if (GSStation.HasCargoRating(s_id, cargo_id)) {
                        if (CompanyCargoList.HasItem(cargo_id)) continue;
                        else CompanyCargoList.AddItem(cargo_id, 1)
                    }
                }

                //count type of stations
                if (GSStation.HasStationType(s_id, GSStation.STATION_TRAIN))
                    this.curr_results.trainstation++;
                else if (GSStation.HasStationType(s_id, GSStation.STATION_TRUCK_STOP))
                    this.curr_results.truckstop++;
                else if (GSStation.HasStationType(s_id, GSStation.STATION_BUS_STOP))
                    this.curr_results.busstop++;
                else if (GSStation.HasStationType(s_id, GSStation.STATION_AIRPORT))
                    this.curr_results.airport++;
                else if (GSStation.HasStationType(s_id, GSStation.STATION_DOCK))
                    this.curr_results.dock++;

            }
            if (this.curr_results.serviced_stations > 0) {
            	this.curr_results.avg_station_rating = (this.curr_results.rated_stations > 0) ? (tot_station_rating / this.curr_results.rated_stations) : 0;
            }
            local cargolist = GSCargoList();
            this.curr_results.cargo_transported = CompanyCargoList.Count();
            this.curr_results.cargo_count = GSCargoList().Count();

            //for debug
            //this.api.Log("Company ID: " + c_id + " Name: " + this.curr_results.company_name + " Money: " + this.curr_results.bank_balance +" Income: " + this.curr_results.income +" CV: " + this.curr_results.company_value + " Loan: " + this.curr_results.loan+ " Performance: " + this.curr_results.performance);
            //this.api.Log("Serviced Towns: " + towns.Count() + " Average Town Rating: " + this.curr_results.avg_town_rating+" Cargo transported: " + this.curr_results.cargo_transported + " Cargos: "+ this.curr_results.cargo_count);
            //this.api.Log("Total Vehicles: " + this.curr_results.vehicles_count + " Trains: " + this.curr_results.trains + " Road: " + this.curr_results.roadveh + " Ships: " + this.curr_results.ships +" Aircrafts: " + this.curr_results.aircrafts);
            //this.api.Log("Vehicles Stopped: " + this.curr_results.stopped_vehs + " Crashed: " + this.curr_results.crashed_vehs + " Old: " + this.curr_results.old_vehs + " Loss: " + this.curr_results.loss_vehs + " Average Age: " + this.curr_results.avg_veh_age);
            //this.api.Log("Serviced Stations: " + this.curr_results.serviced_stations + " Rated Stations: " + this.curr_results.rated_stations + " Average Station Rating: " + this.curr_results.avg_station_rating);
            //this.api.Log("Trainstations: " + this.curr_results.trainstation + " Truckstops: " + this.curr_results.truckstop + " Busstops: " + this.curr_results.busstop + " Airports: " + this.curr_results.airport + " Docks: " + this.curr_results.dock);

            //prepare current company results for controller
            this.all_results[c_id.tostring()] <- this.curr_results;
        }
        //Send final results to controller
        this.api.SendToController({ event = "statistics_full_update", stats = this.all_results });
        //this.api.Log("Send to controller complete.");
    }
}
