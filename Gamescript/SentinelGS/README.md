# SentinelGS - Modular GameScript Controller

SentinelGS is a high-performance, kernel-based GameScript for OpenTTD. It serves as a central hub for various game modes, providing a standardized bridge between the OpenTTD GameScript API and the Sentinel Controller.

## 🚀 Activation

### For Single Player / Client-hosted Games
1. Open OpenTTD and go to **AI/Game Script Settings**.
2. Click on **Select Game Script**.
3. Choose **SentinelGS** from the list.
4. (Optional) Click **Configure** to adjust settings before starting the game.

### For Dedicated Servers
Since most dedicated servers do not have a GUI, you must configure the script in your `openttd.cfg` file using the single-line parameter format.

1. Locate your `openttd.cfg` (usually in the OpenTTD installation directory or `~/.openttd/`).
2. Find the `[game_scripts]` section and add the script name followed by its parameters:
   ```ini
   [game_scripts]
   SentinelGS = game_mode=1,log_level=0,rtd.congestion.difficulty=2,rtd.town.periodical_expansion.rate=3
   ```

---

## 🎮 Game Modes

SentinelGS uses a modular plugin system. You can switch between game modes using the `game_mode` setting.

### Mode 0: Company Value
The classic "rich man" competition. The goal is for companies to reach the highest company value. This mode is lightweight and focuses on economic performance.

### Mode 1: CityBuilder Classic
A cargo-driven growth mode based on classic CityBuilder rules. Companies compete to grow their home city by delivering required cargos.
* **Features**: Dynamic goals, congestion mechanics, and town expansion bonuses.
* **Requirements**: Works best with standard OpenTTD cargos or FIRS (with compatibility setting enabled).

---

## ⚙️ Configuration

Settings are managed via the standard OpenTTD Script Settings. Below are the available parameters and their effects.

| Parameter | Description | Values |
| :--- | :--- | :--- |
| `log_level` | Debugging output level | `0`: Silent, `1`: Normal |
| `game_mode` | Active game plugin | `0`: Company Value, `1`: CityBuilder |
| `maxpopulation` | Max town pop to claim | `0 - 10000` |
| `rtd.cargogoal.difficulty` | Cargo volume requirements | `0`: Easy, `1`: Normal, `2`: Hard |
| `rtd.congestion.difficulty` | Growth penalty difficulty | `0` (Very Easy) to `6` (Disastrous) |
| `rtd.congestion.effect` | Growth penalty impact | `1` (Off) to `4` (Entirely) |
| `rtd.town.periodical_expansion.rate` | Passive growth rate | `0` (Never) to `4` (Often) |
| `rtd.cargogoal.compatibility`| NewGRF Support | `0`: Default, `1`: FIRS |

**Example `openttd.cfg` entry:**
```ini
[game_scripts]
SentinelGS = game_mode=1,log_level=1,maxpopulation=500
```

---

## 🛠️ Development (Adding New Modes)

SentinelGS is designed to be easily extensible. You can integrate new game logic by creating a plugin.

### Plugin Structure
Plugins are stored in `Gamescript/SentinelGS/plugins/<YourPlugin>/`. At minimum, a plugin requires a `wrapper.nut` file.

### Integration Steps
1. **Create Directory**: Place your logic in a new folder under `plugins/`.
2. **Implement Wrapper**: Create `wrapper.nut` defining a class that follows the Sentinel interface.
3. **Kernel Registration**: Add your mode ID to `main.nut` in the `Start()` method's mode selection logic.

### Wrapper Interface Requirements
Your plugin class should implement the following methods:

```squirrel
class Sentinel_MyPlugin {
    constructor(data) { /* Initialize implementation */ }
    
    function Start() {
        // Called when game starts or mode is selected
        // Recommended: Send goal type to controller
        Sentinel.SendAdmin({ event = "goaltypeinfo", goalmastergame = YOUR_ID });
    }

    function Run(ticks) {
        // Called every game tick
    }

    function OnEvent(type, ev) {
        // Handle OpenTTD GS Events (ET_COMPANY_MERGER, etc.)
    }

    function OnAdminEvent(data) {
        // Handle commands/events from the Python Sentinel Controller
    }

    function SendGoalInfo() {
        // Send current game status to the admin port
    }
}
```

Refer to `plugins/CompanyValue/wrapper.nut` for a clean implementation example.
