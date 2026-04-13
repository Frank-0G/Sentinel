require("main.nut");
require("../../api.nut");

class Sentinel_CompanyValueGS4 {
    impl = null;

    constructor(data) {
        // Instantiate the CompanyValue implementation
        // It expects an API object. We use SentinelAPI defined in api.nut.
        this.impl = CompanyValueGS4(SentinelAPI());
    }

    function Start() {
        Sentinel.Log("Starting Company Value Mode...");
        Sentinel.SendAdmin({ event = "goaltypeinfo", goalmastergame = 9 }); //ScriptGoal
        this.impl.Start();
    }

    function Run(ticks) {
        this.impl.Run(ticks);
    }

    function OnEvent(type, ev) {
        this.impl.OnEvent(type, ev);
    }

    function OnAdminEvent(data) {
        // Pass if needed
    }

    function SendGoalInfo() {
        if (this.impl != null && "SendGoalInfo" in this.impl) this.impl.SendGoalInfo();
    }
}
