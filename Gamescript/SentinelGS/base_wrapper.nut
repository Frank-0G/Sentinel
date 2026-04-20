/**
 * Sentinel Base Wrapper
 * Provides common functionality for wrapping vanilla GameScripts.
 */

class SentinelBaseWrapper
{
    impl = null;
    kernel = null;

    constructor(_kernel) {
        this.kernel = _kernel;
    }

    function Start() {
        if (this.impl != null) this.impl.Start();
    }

    function Run(ticks) {
        if (this.impl != null) this.impl.Run(ticks);
    }

    function OnEvent(type, ev) {
        if (this.impl != null) this.impl.OnEvent(type, ev);
    }

    function OnAdminEvent(data) {
        // Handle common metadata requests
        if ("command" in data && data.command == "requestinfo") {
            this.SyncMetadata();
        }
    }

    // --- Helper for shimmed GS to communicate back ---
    
    function Log(msg) { Sentinel.Log(msg); }
    
    function SendToController(data) {
        // Sync with Kernel
        if ("event" in data) {
            if (data.event == "companyprogress") {
                this.kernel.UpdateCompanyProgress(data.company, data.value, data.progress);
            } else if (data.event == "goaltypeinfo") {
                this.kernel.UpdateGoalMetadata(9, data.target_value, "EUR", "Goal");
            }
        }
        
        // Forward to Admin
        Sentinel.SendAdmin(data);
    }

    function SyncMetadata() {
        // To be overridden by specific wrappers
    }
}
