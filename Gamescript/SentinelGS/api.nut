class SentinelAPI
{
    function SendToController(data_table) { GSAdmin.Send(data_table); }
    function Log(msg) { GSLog.Info("[SentinelGS] " + msg); }
    function ChatPublic(msg) { this.SendToController({ command = "chat", text = msg }); }
    function ChatPrivate(company, msg) { this.SendToController({ command = "chat", text = "[Info Co" + (company+1) + "] " + msg }); }
    function SQL_Write(query, params) { this.SendToController({ command = "sql_write", query = query, params = params }); }
    function UpdateScoreboard(company, population, townName) { this.SendToController({ event = "claimed", company = company, town = townName, population = population }); }
}