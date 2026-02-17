require("CityBuilder4.nut");

class Sentinel_CBCargo {
    impl = null;

    constructor(api_ref) {
        this.impl = CityBuilder(); 
    }

    function Start() {
        Sentinel.Log("Starting CityBuilder Cargo...");
        Sentinel.SendAdmin({ event = "goaltypeinfo", goalmastergame = 0 }); // 0 = Cargo
        this.impl.Initialize();
    }

    function Run(ticks) {
        this.impl.Process(); 
    }

    function OnEvent(type, ev) {
        this.impl.ProcessEvent(ev);
    }

    function OnAdminEvent(data) {
        // Pass admin commands if the implementation supports it
    }
}