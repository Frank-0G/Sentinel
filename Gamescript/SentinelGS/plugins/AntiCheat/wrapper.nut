require("main.nut");

class Sentinel_AntiCheat {
    impl = null;

    constructor(data) {
        this.impl = AntiCheat(SentinelAPI());
    }

    function Start() {
        this.impl.Start();
    }

    function Run(ticks) {
        this.impl.Run(ticks);
    }

    function check_crossing(c_id, comp_id, tiles) {
        this.impl.check_crossing(c_id, comp_id, tiles);
    }
}
