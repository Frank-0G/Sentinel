require("main.nut");
require("../../api.nut");

class Sentinel_Statistics {
    impl = null;

    constructor(data) {
        // Instantiate the Statistics implementation with a SentinelAPI object
        this.impl = Statistics(SentinelAPI());
    }

    function Start() {
        this.impl.Start();
    }

    function Run(ticks) {
        this.impl.Run(ticks);
    }

    function OnEvent(type, ev) {
        // Forward events if the plugin needs them
        if ("OnEvent" in this.impl) {
            this.impl.OnEvent(type, ev);
        }
    }

    function OnAdminEvent(data) {
        // Forward admin events (commands)
        if ("OnAdminEvent" in this.impl) {
            this.impl.OnAdminEvent(data);
        }
    }
}
