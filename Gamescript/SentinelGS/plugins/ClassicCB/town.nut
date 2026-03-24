
/*
*
*	Known Issues
*   New Cities wont be included... at all
*   
*
*/

class Town
{
	id = 0;
	rate = 0;
	check_timer = 0;
	
	time_sinceLastPeriodicExpansion = 0;		// Needs to be SAVED!
	
	// Reference to the "global" Cache Object
	cache = null;
	
	// Work Vars
	is_congested = null;
	congestion_goal_id = null;
	lastpopulation = -1;
	lastfactor = -1;

	
	
	constructor(town_id, cache)
	{
		this.id = town_id;
		this.rate = 1;
		this.is_congested = false;
		this.congestion_goal_id = -1;

		this.cache = cache;
		
		local all_towns = GSTownList();

		foreach(t, _ in all_towns)
		{
			/* Skip town if it is the same as this.id */
			if(t == this.id)
				continue;

		}

	}

	// Main Function 
	function ManageTownOnDemand();
	
	// Inner Function
	function ManageTown(); 
	function ResetTimer();
	

	// private functions for town management
	function SetGrowthRate();
	function SetGoal();
	function CheckCongestion();
	function GetDifficultyFactor();
	function GetServiceQualityFactor();
	function CheckPeriodicExpansion();
}

/// 
///	ManageTownOnDemand
///
///	Will check if the Town needs to be managed and does so accordingly.
///	It is used by CityBuilder_v1 but has been deprecated in CityBuilder_v2.
/// @PARAMETER delta: Days ago since the last time this function was called.
///
function Town::ManageTownOnDemand(delta)
{
	// Add Delta to Timer
	this.check_timer += delta;
	
	// Town needs to be managed?
	if (this.check_timer < 35)
		return;
	else
	{
		// Manage Town 
		// (pass on check_timer as delta since last Manage)
		this.ManageTown(this.check_timer);
		
		// Reset Timer		
		this.ResetTimer();		
	}
			
}

/// 
///	ResetTimer
///
///	Resets the Timer of the Town to a Random amount.
/// The Random amount plus the Threshold will result in a check roughly once every 30 days.
///
function Town::ResetTimer()
{
	// Set Timer within a random intervall to spread processing of cities.
	this.check_timer = GSBase.RandRange(10);
}


/// 
///	ManageTown
///
///	Main Function for Managing a town. Will be called periodically by ManageTownOnDemand
/// @PARAMETER delta: Days ago since the last time the town was managed.
///
function Town::ManageTown(delta)
{
	// Expand the Tow Periodically
	this.CheckPeriodicExpansion(delta);
	
	// Check if the Town is congested
	this.CheckCongestion();
	
	// Adjust the Growth Rate
	this.SetGrowthRate();
	
	// Update the CargoGoals 
	this.SetGoal();
}


/// 
///	CheckPeriodicExpansion
///
///	Depending on the script settings will grow all Towns every once in a while
/// even if their respective CargoGoals have not been reached. It's a very small
/// amount of growth and not relative to the current population, but it gives 
/// unconnected cities a possibility to become more interesting over the years.
///
/// @PARAMETER delta: Days ago since the last time the town was managed.
///
function Town::CheckPeriodicExpansion(delta)
{
	// If the Town is currently Congested... 
	if (this.is_congested) 
		// bad luck... as we'll probably not implement factorizing here
		return;

	// Load Cache Value for GrowEveryXDay Variable
	local GEXD = this.cache.Get(CACHE_PERIODICGROWTH_RATE);
	
	// Periodic Grow is 
	// ... disabled?
	if (GEXD == -1) return;
	// ... enabled?
	else 
	{
			
		// Add delta Time to Check Value
		this.time_sinceLastPeriodicExpansion += delta;
			
		// The Town is ready to grow?
		if (this.time_sinceLastPeriodicExpansion > GEXD)
		{
			// Determine Amount to Expand the Town (or City)
			local amount = 1;
			if (GSTown.IsCity(this.id)) 
			{			
				local citybonus_setting = GSController.GetSetting("rtd.town.periodical_expansion.citybonus");
				amount += citybonus_setting;
				//Log.Info("City " + GSTown.GetName(this.id) + " expands by " + amount.tostring(), Log.LVL_INFO);
			}
			else 
			{
				amount = 1;
				//Log.Info("Town " + GSTown.GetName(this.id) + " expands by " + amount.tostring(), Log.LVL_INFO);

			}
		
			 		
			// Expand Town
			GSTown.ExpandTown(this.id, amount);
			
			// Reset Counter
			this.time_sinceLastPeriodicExpansion -= GEXD;
		}	
		else
		{
			//Log.Info("Town " + GSTown.GetName(this.id) + " has not expanded for " + this.time_sinceLastPeriodicExpansion.tostring() + " days.", Log.LVL_INFO);
		}
		
	}
}

/// 
///	SetGrowthRate
///
///	Calculates the Growth Rate for the town depending on population, difficulty
/// rating and other factors.
///
function Town::SetGrowthRate()
{
	local congestion_policy = GSController.GetSetting("rtd.congestion.effect");	
	if(congestion_policy == CONGESTION_GROW_STOP && this.is_congested)
	{
		// Congestion stops town from growing
		GSTown.SetGrowthRate(this.id, 365 * 1000); // grow every 1000 years
		return;
	}

	local rating = GSTown.TOWN_RATING_NONE;
	for (local companyID = GSCompany.COMPANY_FIRST; companyID <= GSCompany.COMPANY_LAST; companyID++) {
		if (GSCompany.ResolveCompanyID(companyID) != GSCompany.COMPANY_INVALID) {
			local r = GSTown.GetRating(this.id, companyID);
			if (r > rating) rating = r;
		}
	}

	local rate = 420;
	switch (rating) {
		case GSTown.TOWN_RATING_NONE:        rate = 420; break;
		case GSTown.TOWN_RATING_APPALLING:   rate = 360; break;
		case GSTown.TOWN_RATING_VERY_POOR:   rate = 300; break;
		case GSTown.TOWN_RATING_POOR:        rate = 260; break;
		case GSTown.TOWN_RATING_MEDIOCRE:    rate = 220; break;
		case GSTown.TOWN_RATING_GOOD:        rate = 190; break;
		case GSTown.TOWN_RATING_VERY_GOOD:   rate = 160; break;
		case GSTown.TOWN_RATING_EXCELLENT:   rate = 130; break;
		case GSTown.TOWN_RATING_OUTSTANDING: rate = 100; break;
	}

	if(this.is_congested)
	{
		if (congestion_policy == CONGESTION_GROW_HALFED)
			rate *= 2; // increase time between growth with factor 2
		else if (congestion_policy == CONGESTION_GROW_QUARTERED)
			rate *= 4; // increase time between growth with factor 4
	}

	local town_growth_rate = GSGameSettings.GetValue("economy.town_growth_rate") - 1;
	if (town_growth_rate < 1) town_growth_rate = 1;

	rate = rate >> town_growth_rate;
	rate = rate / (GSTown.GetPopulation(this.id) / 250 + 1);

	if (rate < 1) rate = 1;
	GSTown.SetGrowthRate(this.id, rate);
}


function MaxAsInt(a, b)
{
	return a > b? a.tointeger() : b.tointeger();
}

/*
function Town::GetDifficultyFactor(value)
{
	// Value ranges from 1 to 7 which equal 50% to 200% difficulty
	return (value + 1) * 0.25;
}
*/

/// 
///	SetGoal
///
///	Calculates the Cargo Goals for this Town to benefit from "normal" Growth.
///
function Town::SetGoal()
{	
	local population = GSTown.GetPopulation(this.id);
	
	if (GSTown.IsCity(this.id))
	{
			if (population == lastpopulation)
				return;
			// Grab Population
			GSTown.SetCargoGoal(this.id, GSCargo.TE_PASSENGERS, population / 10);
			GSTown.SetCargoGoal(this.id, GSCargo.TE_MAIL, 0);
			GSTown.SetCargoGoal(this.id, GSCargo.TE_WATER, 0);
			GSTown.SetCargoGoal(this.id, GSCargo.TE_GOODS, 0);
			GSTown.SetCargoGoal(this.id, GSCargo.TE_FOOD, 0);
	}
	else
	{
	
		// Factors
		// - Difficulty:
		local d_factor = this.cache.Get(CACHE_CARGOGOAL_DIFFICULTY_FACTOR);
	
		// Combined Factor
		local factor = d_factor;
		if ((factor == lastfactor) && (population == lastpopulation))
			return;
		lastfactor = factor;

		// Compute Goals
		local reqPassenger = (population / 5) * factor;
		local reqMail = (population / 20) * factor;
		local reqWater = population > 1000 ? (population / 10) * factor : 0;			// Water
		local reqFood = population > 500 ? (population / 10) * factor : 0;		// Food
		local reqGoods = population > 1500 ? (population / 10) * factor : 0;	// Goods
		
		// FIRS Cargo	
		if (GSController.GetSetting("rtd.cargogoal.compatibility") == 1)
		{	
			// Set Town Goals 
			// ( With FIRS we dont need to adjust for different Landscapes )
			GSTown.SetCargoGoal(this.id, GSCargo.TE_PASSENGERS, MaxAsInt(reqPassenger, 1));
			GSTown.SetCargoGoal(this.id, GSCargo.TE_MAIL,       MaxAsInt(reqMail, 0));
			GSTown.SetCargoGoal(this.id, GSCargo.TE_WATER,      MaxAsInt(reqWater, 0));
			GSTown.SetCargoGoal(this.id, GSCargo.TE_FOOD,       MaxAsInt(reqFood, 0));
			GSTown.SetCargoGoal(this.id, GSCargo.TE_GOODS,      MaxAsInt(reqGoods, 0));
		}
		else
		{
			switch (GSGame.GetLandscape()) {
				case GSGame.LT_TEMPERATE:
					GSTown.SetCargoGoal(this.id, GSCargo.TE_PASSENGERS, MaxAsInt(reqPassenger, 1));
					GSTown.SetCargoGoal(this.id, GSCargo.TE_MAIL,       MaxAsInt(reqMail, 0));
					GSTown.SetCargoGoal(this.id, GSCargo.TE_GOODS,      MaxAsInt(reqGoods, 0));
					break;

				case GSGame.LT_ARCTIC:
					GSTown.SetCargoGoal(this.id, GSCargo.TE_PASSENGERS, MaxAsInt(reqPassenger, 1));
					GSTown.SetCargoGoal(this.id, GSCargo.TE_MAIL,       MaxAsInt(reqMail, 0));
					GSTown.SetCargoGoal(this.id, GSCargo.TE_GOODS,      MaxAsInt(reqGoods, 0));
					GSTown.SetCargoGoal(this.id, GSCargo.TE_FOOD,       MaxAsInt(reqFood, 0));
					break;

				case GSGame.LT_TROPIC:
					GSTown.SetCargoGoal(this.id, GSCargo.TE_PASSENGERS, MaxAsInt(reqPassenger, 1));
					GSTown.SetCargoGoal(this.id, GSCargo.TE_MAIL,       MaxAsInt(reqMail, 0));
					GSTown.SetCargoGoal(this.id, GSCargo.TE_WATER,      MaxAsInt(reqWater, 0));
					GSTown.SetCargoGoal(this.id, GSCargo.TE_GOODS,      MaxAsInt(reqGoods, 0));
					GSTown.SetCargoGoal(this.id, GSCargo.TE_FOOD,       MaxAsInt(reqFood, 0));
					break;
				case GSGame.LT_TOYLAND:	
					GSTown.SetCargoGoal(this.id, GSCargo.TE_PASSENGERS, MaxAsInt(reqPassenger, 1));
					GSTown.SetCargoGoal(this.id, GSCargo.TE_MAIL,       MaxAsInt((reqMail/2), 0));
					// Toyland is weird, Food and Goods are exchanged (testing) - have attention on this
					GSTown.SetCargoGoal(this.id, GSCargo.TE_FOOD,      MaxAsInt(reqGoods, 0));
					GSTown.SetCargoGoal(this.id, GSCargo.TE_GOODS,       MaxAsInt(reqFood, 0));
					break;
			}	
		}
	}
	lastpopulation = population;
}

/// 
///	VehicleInRectValuator
///
///	Returns the Number of Vehicles in a List within the specified rectangle.
///
function Town::VehicleInRectValuator(vehicle, min_x, min_y, max_x, max_y)
{
	local loc = GSVehicle.GetLocation(vehicle);
	local x = GSMap.GetTileX(loc);
	local y = GSMap.GetTileY(loc);

	return x >= min_x && y >= min_y && x <= max_x && y <= max_y;
}


/// 
///	CheckCongestion
///
///	Checks if a city is suffering from vehicle Congestion and adjusts its growth accordingly
///
function Town::CheckCongestion()
{
	local congestion_policy = GSController.GetSetting("rtd.congestion.effect");

	// don't waste time on finding out congestion if towns don't care
	if(congestion_policy == CONGESTION_DONT_CARE)
	{
		return; 
	}

	// Which area to consider for congestion?
	local center = GSTown.GetLocation(this.id);
	local radius = min(GSTown.GetPopulation(this.id) / 160 + 2, 8);

	local new_x1 = GSMap.GetTileX(center) + radius;
	local new_y1 = GSMap.GetTileY(center) + radius;
	local new_x2 = GSMap.GetTileX(center) - radius;
	local new_y2 = GSMap.GetTileY(center) - radius;
	local north_corner = GSMap.GetTileIndex(new_x2, new_y2);
	local south_corner = GSMap.GetTileIndex(new_x1, new_y1);

	local min_x = GSMap.GetTileX(north_corner);
	local min_y = GSMap.GetTileY(north_corner);
	local max_x = GSMap.GetTileX(south_corner);
	local max_y = GSMap.GetTileY(south_corner);

	local square_side = radius * 2 + 1;
	local tile_count = square_side * square_side;

	// Figure out how many road vehicles there are in the town
	local total_vehicles_count = 0;
	local companies = [];
	for(local c = GSCompany.COMPANY_FIRST; c <= GSCompany.COMPANY_LAST; c++)
	{
		if(GSCompany.ResolveCompanyID(c) == GSCompany.COMPANY_INVALID)
			continue;

		local cm = GSCompanyMode(c);

		local vehicles = GSVehicleList();
		vehicles.Valuate(GSVehicle.GetVehicleType);
		vehicles.KeepValue(GSVehicle.VT_ROAD);
		vehicles.Valuate(Town.VehicleInRectValuator, min_x, min_y, max_x, max_y);
		vehicles.KeepValue(1);

		local company_count = vehicles.Count();
		if(company_count > 0)
			companies.append(c);

		total_vehicles_count += company_count;
	}
	

	// Calculate Congestion Limit Factor
	// - Load Cached Factor
	local congestion_limit_factor = this.cache.Get(CACHE_CONGESTION_DIFFICULTY_FACTOR);
	
	
	// Determine what the actual Congestion Limit is
	// ( Population / 45 ) + 5
	local congestion_limit = ((GSTown.GetPopulation(this.id) / 125) * congestion_limit_factor).tointeger() + 5;
	local is_congested = total_vehicles_count > congestion_limit;

	/*
	if (GSTown.GetName(this.id) == "Hamburg")
	{
		Log.Info("Vehicles in " + GSTown.GetName(this.id) + ": " + total_vehicles_count + "   congestion limit: " + congestion_limit + "  radius: " + radius, Log.LVL_INFO);
	}
	*/
		
	// Has the congested state changed since last check?
	if(is_congested != this.is_congested)
	{
		// Remove old goal regardless if we expect there to be any
		
		// !!! GOAL is Commented out for now because it crashed the gamescript! Need to make this compatible with CityBuilder <<< FRANK !!!
		
		// GSGoal.Remove(this.congestion_goal_id);
		// this.congestion_goal_id = -1;

		if(is_congested) {
			Sentinel.Log (GSTown.GetName(this.id) + " is congested");
			foreach(c in companies)
			{
				if(congestion_policy == CONGESTION_GROW_HALFED || congestion_policy == CONGESTION_GROW_QUARTERED)
					GSNews.Create(GSNews.NT_GENERAL, GSText(GSText.STR_NEWS_TOWN_CONGESTED_GROW_REDUCED, this.id), c, GSNews.NR_NONE, 0);
				else
					GSNews.Create(GSNews.NT_GENERAL, GSText(GSText.STR_NEWS_TOWN_CONGESTED_GROW_STOPPED, this.id), c, GSNews.NR_NONE, 0);
			}

			// Add a sign to the congested City
			local signlist = GSSignList();
			foreach (sign, dummy in signlist) {
				local a = GSSign.GetName(sign);
				if (a.find("'") && GSSign.GetLocation(sign) == GSTown.GetLocation(this.id)) {
					// Returns the position of "'", eg. 56
					local b = a.find("'");
					// Returns from position 0 to b, eg 0-56 
					local c = a.slice(0,b);
					// Get the company ID for that company
					local mystring = Town.GetCompanyID(c);
					// Put sign! :P
					GSSign.RemoveSign(sign);
					GSSign.BuildSign(GSTown.GetLocation(this.id), GSText(GSText.STR_HQCITY_CONGESTED, mystring));
					break;
				}
			}
			if (!Town.Owned(GSTown.GetLocation(this.id)) && !GSTown.IsCity(this.id)) { GSSign.BuildSign(GSTown.GetLocation(this.id), GSText(GSText.STR_SIGN_TOWN_CONGESTED)); }
			else if (GSTown.IsCity(this.id)) { 
			GSSign.RemoveSign(Town.Location2Sign(GSTown.GetLocation(this.id)));
			GSSign.BuildSign(GSTown.GetLocation(this.id), GSText(GSText.STR_SIGN_CITY_CONGESTED));
			}
			// this.congestion_goal_id = GSGoal.New(GSCompany.COMPANY_INVALID, GSText(GSText.STR_REDUCE_TOWN_CONGESTION_GOAL, this.id), GSGoal.GT_TOWN, this.id);
		}
		else {
			Sentinel.Log (GSTown.GetName(this.id) + " is no longer congested");
			if (GSTown.IsCity(this.id)) {
				// If the town is a City, place back the City sign!
				GSSign.RemoveSign(Town.Location2Sign(GSTown.GetLocation(this.id)));
				GSSign.BuildSign(GSTown.GetLocation(this.id), GSText(GSText.STR_CITY));
			}
			else if (!Town.Owned(GSTown.GetLocation(this.id))) {
				GSSign.RemoveSign(Town.Location2Sign(GSTown.GetLocation(this.id)));
			}
			local signlist = GSSignList();
			foreach (sign, dummy in signlist) {
				local a = GSSign.GetName(sign);
				if (a.find("'") && GSSign.GetLocation(sign) == GSTown.GetLocation(this.id)) {
					// Returns the position of "'", eg. 56
					local b = a.find("'");
					// Returns from position 0 to b, eg 0-56 
					local c = a.slice(0,b);
					// Get the company ID for that company
					local mystring = Town.GetCompanyID(c);
					// Put sign! :P
					GSSign.RemoveSign(sign);
					GSSign.BuildSign(GSTown.GetLocation(this.id), GSText(GSText.STR_HQCITY, mystring));
					break;
				}
			}
		}

		this.is_congested = is_congested;
	}

}

function Town::Owned(getloc) {
    local getloca = getloc;
	local signlist = GSSignList();
	foreach (sign, dummy in signlist) {
		// GSLog.Info(GSSign.GetName(sign));  
		local a = GSSign.GetName(sign);
		if (a.find("Town") && GSSign.GetLocation(sign) == getloca) {
			return true;
		}
	}
	return false;
}


function Town::GetCompanyID(company) {
	for(local c = GSCompany.COMPANY_FIRST; c <= GSCompany.COMPANY_LAST; c++) {
		if(GSCompany.ResolveCompanyID(c) != GSCompany.COMPANY_INVALID) {
			if (GSCompany.GetName(GSCompany.ResolveCompanyID(c)) == company) {
				return GSCompany.ResolveCompanyID(c);
			}
		}
	}
	return false;
}
function Town::Location2Sign(location) {
	local signlist = GSSignList();
	foreach (sign, dummy in signlist) {
		if (GSSign.GetLocation(sign) == location) {
			return sign;
		}
	}
	return 0;
}