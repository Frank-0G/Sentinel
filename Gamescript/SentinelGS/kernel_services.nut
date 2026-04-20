/**
 * Sentinel Kernel Services
 * Shared utilities for formatting, progress bars, and scoreboard management.
 */

class KernelServices
{
    /**
     * Generates an ASCII progress bar.
     * @param progress The progress percentage (0-100).
     * @param length The total length of the bar (default 50).
     * @param filledChar The character for the filled portion.
     * @param emptyChar The character for the empty portion.
     * @return The formatted progress bar string.
     */
    static function GetProgressBar(progress, length = 50, filledChar = "/", emptyChar = "-")
    {
        if (progress > 100) progress = 100;
        if (progress < 0) progress = 0;
        
        local filledLen = (progress * length) / 100;
        local emptyLen = length - filledLen;
        
        local bar = "[";
        for (local i = 0; i < filledLen; i++) bar += filledChar;
        for (local i = 0; i < emptyLen; i++) bar += emptyChar;
        bar += "]";
        
        return bar;
    }

    /**
     * Formats a large number with dots as thousands separators (Sentinel standard).
     * @param value The number to format.
     * @return The formatted string.
     */
    static function FormatNumber(value)
    {
        local s = value.tostring();
        local res = "";
        local count = 0;
        
        for (local i = s.len() - 1; i >= 0; i--) {
            if (count > 0 && count % 3 == 0) res = "," + res;
            res = s.slice(i, i + 1) + res;
            count++;
        }
        return res;
    }

    /**
     * Maps a company color index to a human-readable name.
     */
    static function GetColorName(colorIdx)
    {
        local colors = [
            "Dark Blue", "Pale Green", "Pink", "Yellow", "Red", "Light Blue", "Green", "Dark Green",
            "Blue", "Cream", "Mauve", "Purple", "Orange", "Brown", "Grey", "White"
        ];
        if (colorIdx >= 0 && colorIdx < colors.len()) return colors[colorIdx];
        return "Color " + colorIdx.tostring();
    }

    /**
     * Maps a currency code to its standard OpenTTD multiplier (Base unit is Pound).
     * @param code ISO currency code (e.g., EUR, USD).
     * @return The multiplier (float).
     */
    static function GetCurrencyMultiplier(code)
    {
        local rates = {
            GBP = 1.0,
            USD = 1.6,
            EUR = 2.0,
            JPY = 202.0,
            ATS = 13.76,
            BEF = 40.33,
            CHF = 2.45,
            CZK = 46.52,
            DEM = 1.95,
            DKK = 7.46,
            ESP = 166.38,
            FIM = 5.94,
            FRF = 6.55,
            GRD = 340.75,
            HUF = 265.41,
            ISK = 129.5,
            ITL = 1936.27,
            NLG = 2.22,
            NOK = 8.16,
            PLN = 4.41,
            PTE = 200.48,
            RUB = 43.6,
            SEK = 9.17,
            TRY = 1.61
        };
        
        code = code.tostring().toupper();
        if (code in rates) return rates[code];
        return 1.0;
    }
}
