require("main.nut");
require("../../api.nut");

class Sentinel_CompanyValue {
    impl = null;

    constructor(data) {
        // Instantiate the CompanyValue implementation
        // It expects an API object. We use SentinelAPI defined in api.nut.
        this.impl = CompanyValue(SentinelAPI());
    }

    function Start() {
        Sentinel.Log("Starting Company Value Mode...");
        // Send goal type info (4 = Company Value)
        Sentinel.SendAdmin({ event = "goaltypeinfo", goalmastergame = 4 });
        this.impl.Start();
    }

    function Run(ticks) {
        this.impl.Run(ticks);
    }

    function OnEvent(type, ev) {
        // CompanyValue main.nut has OnMessage(info), but standard loop calls OnEvent(type, ev).
        // Since CompanyValue logic seems self-contained or relies on specific messages,
        // we might not need to forward generic events unless it expects them.
        // Checking main.nut again:
        // function OnMessage(info) { this.UpdateScoreboard(); }
        // It seems simpler than full event handling.
        // If we want it to react to events, we'd need to adapt.
        // For now, let's just forward if it had OnEvent, but it doesn't.
        // However, OnMessage seems to take 'info'.
        
        // Let's leave it empty for now as CompanyValue logic (in main.nut) mainly runs on ticks or OnMessage.
        // If SendToController sends a message back?
        // Actually, main.nut OnMessage just updates scoreboard.
    }

    function OnAdminEvent(data) {
        // Pass if needed
    }

    function SendGoalInfo() {
        if (this.impl != null && "SendGoalInfo" in this.impl) this.impl.SendGoalInfo();
    }
}
