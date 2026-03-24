

/*
*	
*	Realistic Town Dependencies
*	by Fanatik (http://www.tt-forums.net/memberlist.php?mode=viewprofile&u=61574)
*	adapted from Zuu's "Neighbours are important"-Script. Rebalanced and heavily extended.
*
*	RTDCache
*   Caches numerous variables for the Game which otherwise would have to be generated 
*	numerous times between Loops of otherwise independent objects.
*	
*   
*
*/





class RTDCache
{
	// Timing Related Variables
	TimeSinceLastSync = 0;
	MaxTimeSinceLastSync = 14;
	
	// Table for Storing Cached Data
	Store = {};
	
	// Constructor fills table with NULLs
	constructor() {
		this.Store[CACHE_CONGESTION_DIFFICULTY_FACTOR] <- null;
		this.Store[CACHE_PERIODICGROWTH_RATE] <- null;
		this.Store[CACHE_CARGOGOAL_DIFFICULTY_FACTOR] <- null;
	}

	// Sync Invoke Functions
	function SyncOnDemand();
	function Sync();

	// Get Function
	function Get();
	
	// Internal SyncRelated Functions
	function GetCongestionLimit();
	function GetPeriodicalGrowthThreshold();
	function GetCargoGoalDifficultyFactor();
	
	// Debug
	function Print();
	
}


///
///	SyncOnDemand()
/// Checks wether the Cache has not been synced for a given time and will issue Sync() is necessary
///
function RTDCache::SyncOnDemand(delta)
{
	this.TimeSinceLastSync += delta;
	
	if (this.TimeSinceLastSync > this.MaxTimeSinceLastSync)
	{				
		this.Sync();	
		this.TimeSinceLastSync = 0;			
	}	
}


function RTDCache::GetCongestionLimit()
{
	// Congestion Limit Factor	
	local congestion_difficulty = GSController.GetSetting("rtd.congestion.difficulty");
	local congestion_limit_factor;
	// - Very Easy, Easy and Normal
	if (congestion_difficulty <= 2)
		congestion_limit_factor = 2.0 - (congestion_difficulty * 0.5);
	// - Hard, Very Hard and Insane
	else if (congestion_difficulty <= 5)
		congestion_limit_factor = 1.50 - (congestion_difficulty * 0.25);
	// - Disastrous
	else
		congestion_limit_factor = 0.10;

	return congestion_limit_factor;
}

function RTDCache::GetPeriodicalGrowthThreshold()
{
	local periodicExpansion = GSController.GetSetting("rtd.town.periodical_expansion.rate");
		
	// Never
	if (periodicExpansion == 0)
		return -1;	
	// 12 months
	else if (periodicExpansion == 1) 
		return 365;
	// 6 months
	else if (periodicExpansion == 2)
		return 182;
	// 3 months
	else if (periodicExpansion == 3)
		return 91;
	// 1.5 months
	else 
		return 45;
		
}

function RTDCache::GetCargoGoalDifficultyFactor()
{
	local difficulty = GSController.GetSetting("rtd.cargogoal.difficulty");
	return ( 1 + difficulty ) * 0.25;
}


///
/// Print()
/// Prints all relevant stored values into the Log 
///
function RTDCache::Print()
{
	Sentinel.Log("RTDCache::Print()");
	Sentinel.Log("Congestion.DifficultyFactor: " + this.Store[CACHE_CONGESTION_DIFFICULTY_FACTOR].tostring());
	Sentinel.Log("PeriodicGrowth.DayThreshold: " + this.Store[CACHE_PERIODICGROWTH_RATE].tostring());
	Sentinel.Log("CargoGoal.DifficultyFactor: " + this.Store[CACHE_CARGOGOAL_DIFFICULTY_FACTOR].tostring());
}

///
/// Sync()
/// Recalculates and stores all necessary values. Will be called once at startup and after a set
/// amount of time has passed determined by SyncOnDemand()
///
function RTDCache::Sync()
{
	Sentinel.Log("RTDCache::Sync()");
	// CongestionLimit
	//this.Store[CACHE_CONGESTION_DIFFICULTY_FACTOR] <- this.GetCongestionLimit();	
	this.Set(CACHE_CONGESTION_DIFFICULTY_FACTOR, this.GetCongestionLimit());	
	this.Set(CACHE_PERIODICGROWTH_RATE, this.GetPeriodicalGrowthThreshold());
	this.Set(CACHE_CARGOGOAL_DIFFICULTY_FACTOR, this.GetCargoGoalDifficultyFactor());
}


function RTDCache::Set(key, value)
{
	if (this.Store[key] != value)
	{
		this.Store[key] <- value;
		Sentinel.Log("Key: " + key.tostring() + " -> " + value.tostring());
	}
}


function RTDCache::Get(key)
{
	return this.Store[key];
}