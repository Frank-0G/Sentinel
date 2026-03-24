<?php
require_once 'db_config.php';

// Initialize variables
$results = [];
$search_term = $_GET['q'] ?? '';
$search_field = $_GET['field'] ?? 'all';
$search_type = $_GET['type'] ?? 'all';
$search_source = $_GET['source'] ?? 'all'; // NEW: Source Filter
$search_server = $_GET['server'] ?? 'all';
$search_client = $_GET['client'] ?? '';
$date_from = $_GET['from'] ?? '';
$date_to = $_GET['to'] ?? '';
$limit = $_GET['limit'] ?? 500;
$is_export = isset($_GET['export']);

// --- 1. Fetch Available Server IDs ---
$server_options = [];
try {
    $stmt = $pdo->query("SELECT DISTINCT server_id FROM openttd_chat_log ORDER BY server_id ASC");
    $server_options = $stmt->fetchAll(PDO::FETCH_COLUMN);
} catch (Exception $e) { }

// --- 2. Fetch Available Player Names (for Autocomplete) ---
$player_options = [];
try {
    $stmt = $pdo->query("SELECT DISTINCT client_name FROM openttd_chat_log ORDER BY client_name ASC LIMIT 2000");
    $player_options = $stmt->fetchAll(PDO::FETCH_COLUMN);
} catch (Exception $e) { }

// --- 3. Build the Main Query ---
$sql = "SELECT * FROM openttd_chat_log WHERE 1=1";
$params = [];

// Server Filter
if ($search_server !== 'all' && $search_server !== '') {
    $sql .= " AND server_id = ?";
    $params[] = $search_server;
}

// Source Filter (NEW)
if ($search_source !== 'all' && $search_source !== '') {
    $sql .= " AND source = ?";
    $params[] = $search_source;
}

// Specific Player Filter (Dropdown)
if (!empty($search_client)) {
    $sql .= " AND client_name = ?";
    $params[] = $search_client;
}

// Text Search Filter (General)
if (!empty($search_term)) {
    if ($search_field === 'message') {
        $sql .= " AND message LIKE ?";
        $params[] = "%$search_term%";
    } elseif ($search_field === 'company_name') {
        $sql .= " AND company_name LIKE ?";
        $params[] = "%$search_term%";
    } elseif ($search_field === 'client_ip') {
        $sql .= " AND client_ip LIKE ?";
        $params[] = "%$search_term%";
    } else {
        $sql .= " AND (client_name LIKE ? OR message LIKE ? OR company_name LIKE ? OR client_ip LIKE ?)";
        $params[] = "%$search_term%";
        $params[] = "%$search_term%";
        $params[] = "%$search_term%";
        $params[] = "%$search_term%";
    }
}

// Type Filter
if ($search_type !== 'all') {
    $sql .= " AND chat_type = ?";
    $params[] = $search_type;
}

// Date Filters
if (!empty($date_from)) {
    $sql .= " AND datetime >= ?";
    $params[] = $date_from;
}

if (!empty($date_to)) {
    $sql .= " AND datetime <= ?";
    $params[] = $date_to;
}

$sql .= " ORDER BY id DESC";

if (!$is_export) {
    $sql .= " LIMIT " . (int)$limit;
}

// Execute
try {
    $stmt = $pdo->prepare($sql);
    $stmt->execute($params);
    $results = $stmt->fetchAll();
} catch (Exception $e) {
    $error = $e->getMessage();
}

// --- EXPORT LOGIC ---
if ($is_export) {
    $filename = "chatlog_export_" . date('Y-m-d_H-i') . ".txt";
    header('Content-Type: text/plain');
    header('Content-Disposition: attachment; filename="' . $filename . '"');
    
    foreach ($results as $row) {
        $type = strtoupper($row['chat_type']);
        $src = isset($row['source']) ? "[{$row['source']}]" : "[GAME]"; // Default to GAME for old logs
        $company = $row['company_name'] ? "[{$row['company_name']}] " : "";
        $target = $row['target_name'] && $row['target_name'] != 'All' ? "(-> {$row['target_name']}) " : "";
        $srv = "[S{$row['server_id']}]";
        $auth = $row['is_logged_in'] ? "[AUTH]" : "";
        
        echo "{$srv} [{$row['datetime']}] {$src} {$auth} [{$type}] {$company}{$row['client_name']} ({$row['client_ip']}) {$target}: {$row['message']}\r\n";
    }
    exit;
}
?>

<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>OpenTTD Chat Search</title>
    <style>
        :root {
            --bg-color: #1e1e1e;
            --text-color: #e0e0e0;
            --table-bg: #252526;
            --border-color: #3e3e42;
            --accent: #007acc;
            --success: #4ec9b0;
            --warning: #ce9178;
            --danger: #f44336;
        }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: var(--bg-color); color: var(--text-color); margin: 0; padding: 20px; }
        h1 { margin-bottom: 20px; border-bottom: 1px solid var(--border-color); padding-bottom: 10px; }
        
        .search-box { background: var(--table-bg); padding: 20px; border-radius: 5px; margin-bottom: 20px; display: flex; flex-wrap: wrap; gap: 15px; align-items: flex-end; border: 1px solid var(--border-color); }
        .form-group { display: flex; flex-direction: column; }
        label { margin-bottom: 5px; font-size: 0.9em; color: #aaa; }
        input, select { background: #333; border: 1px solid var(--border-color); color: white; padding: 8px; border-radius: 4px; min-width: 150px; }
        button { background: var(--accent); color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer; font-weight: bold; }
        button:hover { background: #0062a3; }
        button.download-btn { background: var(--success); color: black; }
        button.download-btn:hover { background: #3da892; }

        table { width: 100%; border-collapse: collapse; font-size: 0.95em; }
        th, td { padding: 10px; text-align: left; border-bottom: 1px solid var(--border-color); }
        th { background: #333; color: white; position: sticky; top: 0; }
        tr:hover { background: #2a2d2e; }
        
        .badge { padding: 2px 6px; border-radius: 3px; font-size: 0.8em; font-weight: bold; }
        .type-PUBLIC { background: #2e7d32; color: white; }
        .type-TEAM { background: #1565c0; color: white; }
        .type-PRIVATE { background: #c62828; color: white; }
        
        .src-GAME { background: #555; color: #fff; padding: 2px 4px; border-radius: 3px; font-size: 0.8em; }
        .src-IRC { background: #9c27b0; color: #fff; padding: 2px 4px; border-radius: 3px; font-size: 0.8em; }
        .src-ADMIN { background: #d32f2f; color: #fff; padding: 2px 4px; border-radius: 3px; font-size: 0.8em; }
        .src-DISCORD { background: #5865F2; color: #fff; padding: 2px 4px; border-radius: 3px; font-size: 0.8em; }

        .auth-yes { color: var(--success); font-weight: bold; }
        .auth-no { color: var(--danger); font-weight: bold; }
        
        .ip-addr { font-family: monospace; color: #aaa; }
        .no-results { text-align: center; padding: 50px; color: #777; }
        .srv-badge { background: #444; color: #fff; padding: 2px 5px; border-radius: 3px; font-size: 0.85em; }
    </style>
</head>
<body>

<h1>OpenTTD Chat Log Search</h1>

<form method="GET" class="search-box">
    <div class="form-group">
        <label>Server ID</label>
        <select name="server">
            <option value="all">ALL Servers</option>
            <?php foreach ($server_options as $sid): ?>
                <option value="<?php echo htmlspecialchars($sid); ?>" <?php echo $search_server == $sid ? 'selected' : ''; ?>>
                    Server #<?php echo htmlspecialchars($sid); ?>
                </option>
            <?php endforeach; ?>
        </select>
    </div>

    <div class="form-group">
        <label>Player Name (Select or Type)</label>
        <input list="players" name="client" value="<?php echo htmlspecialchars($search_client); ?>" placeholder="Start typing name...">
        <datalist id="players">
            <?php foreach ($player_options as $pname): ?>
                <option value="<?php echo htmlspecialchars($pname); ?>">
            <?php endforeach; ?>
        </datalist>
    </div>
    
    <div class="form-group">
        <label>Source</label>
        <select name="source">
            <option value="all" <?php echo $search_source == 'all' ? 'selected' : ''; ?>>Any Source</option>
            <option value="GAME" <?php echo $search_source == 'GAME' ? 'selected' : ''; ?>>In-Game</option>
            <option value="IRC" <?php echo $search_source == 'IRC' ? 'selected' : ''; ?>>IRC !say</option>
            <option value="ADMIN" <?php echo $search_source == 'ADMIN' ? 'selected' : ''; ?>>Admin !say</option>
            <option value="DISCORD" <?php echo $search_source == 'DISCORD' ? 'selected' : ''; ?>>Discord</option>
        </select>
    </div>

    <div class="form-group">
        <label>Message Type</label>
        <select name="type">
            <option value="all" <?php echo $search_type == 'all' ? 'selected' : ''; ?>>Any Type</option>
            <option value="PUBLIC" <?php echo $search_type == 'PUBLIC' ? 'selected' : ''; ?>>Public Chat</option>
            <option value="TEAM" <?php echo $search_type == 'TEAM' ? 'selected' : ''; ?>>Team Chat</option>
            <option value="PRIVATE" <?php echo $search_type == 'PRIVATE' ? 'selected' : ''; ?>>Private Message</option>
        </select>
    </div>

    <div class="form-group">
        <label>Search Text (Msg/IP/Company)</label>
        <input type="text" name="q" value="<?php echo htmlspecialchars($search_term); ?>" placeholder="Contains...">
    </div>

    <div class="form-group">
        <label>Field Context</label>
        <select name="field">
            <option value="all" <?php echo $search_field == 'all' ? 'selected' : ''; ?>>All Fields</option>
            <option value="message" <?php echo $search_field == 'message' ? 'selected' : ''; ?>>Message Body</option>
            <option value="company_name" <?php echo $search_field == 'company_name' ? 'selected' : ''; ?>>Company Name</option>
            <option value="client_ip" <?php echo $search_field == 'client_ip' ? 'selected' : ''; ?>>IP Address</option>
        </select>
    </div>

    <div class="form-group">
        <label>From Date</label>
        <input type="datetime-local" name="from" value="<?php echo htmlspecialchars($date_from); ?>">
    </div>

    <div class="form-group">
        <label>To Date</label>
        <input type="datetime-local" name="to" value="<?php echo htmlspecialchars($date_to); ?>">
    </div>

    <div class="form-group">
        <label>Limit</label>
        <select name="limit">
            <option value="100" <?php echo $limit == 100 ? 'selected' : ''; ?>>100</option>
            <option value="500" <?php echo $limit == 500 ? 'selected' : ''; ?>>500</option>
            <option value="1000" <?php echo $limit == 1000 ? 'selected' : ''; ?>>1000</option>
        </select>
    </div>

    <div class="form-group">
        <label>&nbsp;</label>
        <button type="submit">Search</button>
    </div>
    
    <div class="form-group" style="margin-left: auto;">
        <label>&nbsp;</label>
        <button type="submit" name="export" value="1" class="download-btn">Download .TXT</button>
    </div>
</form>

<?php if (isset($error)): ?>
    <div style="color: var(--danger); padding: 20px;"><?php echo $error; ?></div>
<?php endif; ?>

<table>
    <thead>
        <tr>
            <th width="80">Server</th>
            <th width="80">Source</th> <th width="150">Time</th>
            <th width="80">Type</th>
            <th>Company</th>
            <th>Player</th>
            <th>Auth</th>
            <th>Target</th>
            <th>Message</th>
        </tr>
    </thead>
    <tbody>
        <?php if (empty($results)): ?>
            <tr><td colspan="9" class="no-results">No chats found matching your criteria.</td></tr>
        <?php else: ?>
            <?php foreach ($results as $row): ?>
                <tr>
                    <td><span class="srv-badge">#<?php echo htmlspecialchars($row['server_id']); ?></span></td>
                    
                    <td>
                        <?php 
                        $src = isset($row['source']) ? $row['source'] : 'GAME';
                        echo "<span class='src-{$src}'>{$src}</span>"; 
                        ?>
                    </td>
                    
                    <td><?php echo date('M d, H:i:s', strtotime($row['datetime'])); ?></td>
                    <td>
                        <span class="badge type-<?php echo $row['chat_type']; ?>">
                            <?php echo $row['chat_type']; ?>
                        </span>
                    </td>
                    <td><?php echo htmlspecialchars($row['company_name']); ?></td>
                    <td>
                        <strong><?php echo htmlspecialchars($row['client_name']); ?></strong><br>
                        <span class="ip-addr"><?php echo $row['client_ip']; ?></span>
                    </td>
                    <td>
                        <?php if ($row['is_logged_in']): ?>
                            <span class="auth-yes">&#10003; Yes</span>
                        <?php else: ?>
                            <span class="auth-no">&#10007; No</span>
                        <?php endif; ?>
                    </td>
                    <td>
                        <?php if($row['target_name'] != 'All') echo htmlspecialchars($row['target_name']); ?>
                    </td>
                    <td><?php echo htmlspecialchars($row['message']); ?></td>
                </tr>
            <?php endforeach; ?>
        <?php endif; ?>
    </tbody>
</table>

</body>
</html>
