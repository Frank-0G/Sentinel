require("n_CityBuilder7.nut");

class Sentinel_NovaCB {
    impl = null;

    constructor(api_ref) {
        this.impl = CityBuilder();
    }

    function Start() {
        Sentinel.Log("Starting Nova CityBuilder...");
        this.impl.StartCBN();
        this.impl.SendGoalInfo();
    }

    function Run(ticks) {
        this.impl.ProcessCBN(); 
        
        // Report frequently (every ~1 sec)
        if (ticks % 30 == 0) {
             this.impl.SendStatisticsN(function(id) { return GSCargo.GetCargoLabel(id); });
             this.impl.SendPopulationN();
        }
    }

    function OnEvent(type, ev) {
        this.impl.CheckEvents(ev); 
    }

    function OnAdminEvent(data) {}
}