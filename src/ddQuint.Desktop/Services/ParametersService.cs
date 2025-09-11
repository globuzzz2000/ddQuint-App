using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;
using System.Globalization;

namespace ddQuint.Desktop.Services
{
    public class ParametersService
    {
        private static readonly string AppDataFolder = Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData), 
            "ddQuint");
        private static readonly string ParametersFilePath = Path.Combine(AppDataFolder, "parameters.json");

        // Helpers: robust type coercion and normalization to align with macOS semantics
        private static double ToDouble(object? v, double fallback = 0.0)
        {
            try
            {
                if (v == null) return fallback;
                if (v is double d) return d;
                if (v is float f) return (double)f;
                if (v is int i) return i;
                if (v is long l) return l;
                if (v is string s)
                {
                    s = s.Trim();
                    if (string.IsNullOrEmpty(s) || s == "-") return fallback;
                    s = s.Replace(',', '.');
                    if (double.TryParse(s, NumberStyles.Any, CultureInfo.InvariantCulture, out var dv))
                        return dv;
                }
            }
            catch { }
            return fallback;
        }

        private static int ToInt(object? v, int fallback = 0)
        {
            try
            {
                if (v == null) return fallback;
                if (v is int i) return i;
                if (v is long l) return (int)l;
                if (v is double d) return (int)d;
                if (v is float f) return (int)f;
                if (v is string s)
                {
                    s = s.Trim();
                    if (string.IsNullOrEmpty(s) || s == "-") return fallback;
                    s = s.Replace(',', '.');
                    if (double.TryParse(s, NumberStyles.Any, CultureInfo.InvariantCulture, out var dv))
                        return (int)dv;
                }
            }
            catch { }
            return fallback;
        }

        private static bool ToBool(object? v, bool fallback = false)
        {
            try
            {
                if (v is bool b) return b;
                if (v is string s)
                {
                    s = s.Trim().ToLowerInvariant();
                    if (s == "true" || s == "1" || s == "yes" || s == "on") return true;
                    if (s == "false" || s == "0" || s == "no" || s == "off") return false;
                }
            }
            catch { }
            return fallback;
        }

        private static Dictionary<string, object> NormalizeParameters(Dictionary<string, object> parameters)
        {
            var normalized = new Dictionary<string, object>(parameters);

            // Coerce primitive types to ensure consistency
            string[] intKeys = {
                "HDBSCAN_MIN_CLUSTER_SIZE","HDBSCAN_MIN_SAMPLES","MIN_POINTS_FOR_CLUSTERING",
                "CHROMOSOME_COUNT","INDIVIDUAL_PLOT_DPI","X_AXIS_MIN","X_AXIS_MAX","Y_AXIS_MIN",
                "Y_AXIS_MAX","X_GRID_INTERVAL","Y_GRID_INTERVAL","MIN_USABLE_DROPLETS"
            };
            string[] floatKeys = {
                "HDBSCAN_EPSILON","BASE_TARGET_TOLERANCE","TOLERANCE_MULTIPLIER","COPY_NUMBER_MULTIPLIER",
                "LOWER_DEVIATION_TARGET","UPPER_DEVIATION_TARGET","COPY_NUMBER_MEDIAN_DEVIATION_THRESHOLD",
                "AMPLITUDE_NON_LINEARITY"
            };
            string[] boolKeys = {
                "ENABLE_COPY_NUMBER_ANALYSIS","CLASSIFY_CNV_DEVIATIONS","ENABLE_FLUOROPHORE_MIXING"
            };

            foreach (var k in intKeys)
            {
                if (normalized.TryGetValue(k, out var v)) normalized[k] = ToInt(v);
            }
            foreach (var k in floatKeys)
            {
                if (normalized.TryGetValue(k, out var v)) normalized[k] = ToDouble(v);
            }
            foreach (var k in boolKeys)
            {
                if (normalized.TryGetValue(k, out var v)) normalized[k] = ToBool(v);
            }

            return normalized;
        }

        private static Dictionary<string, object> RemoveLegacyParameters(Dictionary<string, object> parameters)
        {
            // Remove deprecated/legacy parameters that cause Python warnings
            var legacyKeys = new[] {
                "USE_PLOIDY_TERMINOLOGY", // Deprecated parameter causing warnings
            };

            var cleaned = new Dictionary<string, object>(parameters);
            foreach (var legacyKey in legacyKeys)
            {
                if (cleaned.Remove(legacyKey))
                {
                    System.Diagnostics.Debug.WriteLine($"[ParametersService] Removed legacy parameter: {legacyKey}");
                }
            }

            return cleaned;
        }

        // Expose normalization for callers that need runtime-safe types
        public static Dictionary<string, object> NormalizeForWell(Dictionary<string, object> parameters)
        {
            return NormalizeParameters(parameters);
        }

        private static object ConvertJsonElementToObject(JsonElement element)
        {
            return element.ValueKind switch
            {
                JsonValueKind.True => true,
                JsonValueKind.False => false,
                JsonValueKind.Number => element.TryGetInt32(out var intVal) ? intVal : element.GetDouble(),
                JsonValueKind.String => element.GetString() ?? "",
                JsonValueKind.Array => element.EnumerateArray().Select(e => ConvertJsonElementToObject(e)).ToArray(),
                JsonValueKind.Object => element.EnumerateObject().ToDictionary(prop => prop.Name, prop => ConvertJsonElementToObject(prop.Value)),
                _ => element.ToString()
            };
        }

        private static object ConvertJTokenToObject(Newtonsoft.Json.Linq.JToken token)
        {
            switch (token.Type)
            {
                case Newtonsoft.Json.Linq.JTokenType.Object:
                    var dict = new Dictionary<string, object>();
                    foreach (var prop in token.Children<Newtonsoft.Json.Linq.JProperty>())
                    {
                        dict[prop.Name] = ConvertJTokenToObject(prop.Value);
                    }
                    return dict;
                case Newtonsoft.Json.Linq.JTokenType.Array:
                    return token.Children().Select(child => ConvertJTokenToObject(child)).ToArray();
                case Newtonsoft.Json.Linq.JTokenType.String:
                    return token.ToObject<string>() ?? "";
                case Newtonsoft.Json.Linq.JTokenType.Integer:
                    return token.ToObject<int>();
                case Newtonsoft.Json.Linq.JTokenType.Float:
                    return token.ToObject<double>();
                case Newtonsoft.Json.Linq.JTokenType.Boolean:
                    return token.ToObject<bool>();
                case Newtonsoft.Json.Linq.JTokenType.Null:
                    return null!;
                default:
                    return token.ToString();
            }
        }

        private static Dictionary<string, object> ConvertJsonElementsToParameters(Dictionary<string, JsonElement> savedParameters)
        {
            var parameters = new Dictionary<string, object>();
            
            foreach (var kvp in savedParameters)
            {
                var key = kvp.Key;
                var jsonValue = kvp.Value;
                
                object paramValue = jsonValue.ValueKind switch
                {
                    JsonValueKind.True => true,
                    JsonValueKind.False => false,
                    JsonValueKind.Number => jsonValue.TryGetInt32(out var intVal) ? intVal : jsonValue.GetDouble(),
                    JsonValueKind.String => jsonValue.GetString() ?? "",
                    JsonValueKind.Array when key == "COPY_NUMBER_SPEC" => 
                        jsonValue.EnumerateArray().Select(elem => 
                        {
                            var dict = new Dictionary<string, object>();
                            foreach (var prop in elem.EnumerateObject())
                            {
                                dict[prop.Name] = prop.Value.ValueKind switch
                                {
                                    JsonValueKind.Number => prop.Value.TryGetInt32(out var i) ? (object)i : (object)prop.Value.GetDouble(),
                                    JsonValueKind.String => (object)(prop.Value.GetString() ?? ""),
                                    JsonValueKind.True => true,
                                    JsonValueKind.False => false,
                                    _ => prop.Value.ToString()
                                };
                            }
                            return dict;
                        }).ToArray(),
                    JsonValueKind.Array => jsonValue.EnumerateArray().Select(e => 
                        e.ValueKind == JsonValueKind.Number ? (object)(e.TryGetInt32(out var i) ? i : e.GetDouble()) : 
                        e.ValueKind == JsonValueKind.String ? (object)(e.GetString() ?? "") : (object)e.ToString()).ToArray(),
                    JsonValueKind.Object when key == "TARGET_NAMES" =>
                        jsonValue.EnumerateObject().ToDictionary(prop => prop.Name, prop => (object)(prop.Value.GetString() ?? "")),
                    JsonValueKind.Object when key == "EXPECTED_CENTROIDS" =>
                        jsonValue.EnumerateObject().ToDictionary(prop => prop.Name, prop => (object)prop.Value.EnumerateArray().Select(e => e.GetDouble()).ToArray()),
                    JsonValueKind.Object => jsonValue.ToString(),
                    _ => jsonValue.ToString()
                };
                parameters[key] = paramValue;
            }
            
            return parameters;
        }

        public static Dictionary<string, object> LoadGlobalParameters()
        {
            var timestamp = DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss");
            System.Diagnostics.Debug.WriteLine($"[ParametersService] LoadGlobalParameters called at {timestamp}");
            System.Diagnostics.Debug.WriteLine($"[ParametersService] AppDataFolder: {AppDataFolder}");
            System.Diagnostics.Debug.WriteLine($"[ParametersService] ParametersFilePath: {ParametersFilePath}");
            
            // Also log to debug log file for Windows analysis visibility
            DebugLogService.LogMessage($"=== LoadGlobalParameters START ===");
            DebugLogService.LogMessage($"Called at: {timestamp}");
            DebugLogService.LogMessage($"AppData folder: {AppDataFolder}");
            DebugLogService.LogMessage($"Parameters file: {ParametersFilePath}");
            DebugLogService.LogMessage($"Parameters file exists: {File.Exists(ParametersFilePath)}");
            
            // Default parameters using modern structured format (matching macOS)
            var defaultParameters = new Dictionary<string, object>
            {
                // HDBSCAN Clustering parameters
                {"HDBSCAN_MIN_CLUSTER_SIZE", 4},
                {"HDBSCAN_MIN_SAMPLES", 70},
                {"HDBSCAN_EPSILON", 0.06},
                {"MIN_POINTS_FOR_CLUSTERING", 50},
                {"HDBSCAN_METRIC", "euclidean"},
                {"HDBSCAN_CLUSTER_SELECTION_METHOD", "eom"},
                
                // Basic parameters
                {"BASE_TARGET_TOLERANCE", 750.0},
                {"CHROMOSOME_COUNT", 5},
                
                // Expected centroids (structured format)
                {"EXPECTED_CENTROIDS", new Dictionary<string, object>
                {
                    {"Negative", new double[] {1000, 900}},
                    {"Chrom1",   new double[] {1000, 2300}},
                    {"Chrom2",   new double[] {1800, 2200}},
                    {"Chrom3",   new double[] {2400, 1750}},
                    {"Chrom4",   new double[] {3100, 1300}},
                    {"Chrom5",   new double[] {3500, 900}}
                }},
                
                // Target names (structured format)
                {"TARGET_NAMES", new Dictionary<string, object>()},
                
                // Copy number specification (structured format)
                {"COPY_NUMBER_SPEC", new Dictionary<string, object>[]
                {
                    new Dictionary<string, object> {{"chrom", "Chrom1"}, {"expected", 1.0}, {"std_dev", 0.03}},
                    new Dictionary<string, object> {{"chrom", "Chrom2"}, {"expected", 1.0}, {"std_dev", 0.03}},
                    new Dictionary<string, object> {{"chrom", "Chrom3"}, {"expected", 1.0}, {"std_dev", 0.03}},
                    new Dictionary<string, object> {{"chrom", "Chrom4"}, {"expected", 1.0}, {"std_dev", 0.03}},
                    new Dictionary<string, object> {{"chrom", "Chrom5"}, {"expected", 1.0}, {"std_dev", 0.03}}
                }},
                
                // Copy number parameters
                {"MIN_USABLE_DROPLETS", 3000},
                {"COPY_NUMBER_MEDIAN_DEVIATION_THRESHOLD", 0.15},
                {"COPY_NUMBER_MULTIPLIER", 4.0},
                {"TOLERANCE_MULTIPLIER", 3.0},
                {"LOWER_DEVIATION_TARGET", 0.75},
                {"UPPER_DEVIATION_TARGET", 1.25},
                
                // Visualization
                {"X_AXIS_MIN", 0},
                {"X_AXIS_MAX", 3000},
                {"Y_AXIS_MIN", 0},
                {"Y_AXIS_MAX", 5000},
                {"X_GRID_INTERVAL", 500},
                {"Y_GRID_INTERVAL", 1000},
                {"INDIVIDUAL_PLOT_DPI", 300},
                
                // General settings
                {"ENABLE_FLUOROPHORE_MIXING", true},
                {"AMPLITUDE_NON_LINEARITY", 1.0},
                {"ENABLE_COPY_NUMBER_ANALYSIS", true},
                {"CLASSIFY_CNV_DEVIATIONS", true}
            };

            try
            {
                System.Diagnostics.Debug.WriteLine($"[ParametersService] File exists: {File.Exists(ParametersFilePath)}");
                if (File.Exists(ParametersFilePath))
                {
                    System.Diagnostics.Debug.WriteLine($"[ParametersService] Reading file: {ParametersFilePath}");
                    var json = File.ReadAllText(ParametersFilePath);
                    System.Diagnostics.Debug.WriteLine($"[ParametersService] JSON content length: {json.Length}");
                    System.Diagnostics.Debug.WriteLine($"[ParametersService] JSON preview: {json.Substring(0, Math.Min(200, json.Length))}...");
                    
                    // Use Newtonsoft.Json to match macOS behavior exactly  
                    Dictionary<string, object>? savedParameters = null;
                    
                    try
                    {
                        var rootObj = Newtonsoft.Json.Linq.JObject.Parse(json);
                        
                        // Check if this is a parameter bundle (has global_parameters wrapper)
                        if (rootObj.ContainsKey("global_parameters"))
                        {
                            DebugLogService.LogMessage("Found parameter bundle format (macOS export)");
                            var globalParams = rootObj["global_parameters"] as Newtonsoft.Json.Linq.JObject;
                            if (globalParams != null)
                            {
                                savedParameters = new Dictionary<string, object>();
                                foreach (var prop in globalParams.Properties())
                                {
                                    savedParameters[prop.Name] = ConvertJTokenToObject(prop.Value);
                                }
                            }
                            
                            // Also load well parameters if present in bundle
                            if (rootObj.ContainsKey("well_parameters") && rootObj["well_parameters"] is Newtonsoft.Json.Linq.JObject wellParamsObj)
                            {
                                try
                                {
                                    foreach (var wellProp in wellParamsObj.Properties())
                                    {
                                        if (wellProp.Value is Newtonsoft.Json.Linq.JObject wellParams)
                                        {
                                            var wellDict = new Dictionary<string, object>();
                                            foreach (var paramProp in wellParams.Properties())
                                            {
                                                wellDict[paramProp.Name] = ConvertJTokenToObject(paramProp.Value);
                                            }
                                            SaveWellParameters(wellProp.Name, wellDict);
                                        }
                                    }
                                    DebugLogService.LogMessage($"Loaded well parameter sets from bundle");
                                }
                                catch (Exception ex)
                                {
                                    DebugLogService.LogMessage($"Warning: Could not load well parameters from bundle: {ex.Message}");
                                }
                            }
                        }
                        else
                        {
                            // Direct parameters format (flat JSON like macOS)
                            DebugLogService.LogMessage("Found direct parameters format");
                            savedParameters = new Dictionary<string, object>();
                            foreach (var prop in rootObj.Properties())
                            {
                                savedParameters[prop.Name] = ConvertJTokenToObject(prop.Value);
                            }
                        }
                    }
                    catch (Exception parseEx)
                    {
                        DebugLogService.LogMessage($"Error parsing JSON: {parseEx.Message}");
                        System.Diagnostics.Debug.WriteLine($"[ParametersService] JSON parsing error: {parseEx.Message}");
                        return defaultParameters;
                    }
                    
                    System.Diagnostics.Debug.WriteLine($"[ParametersService] Deserialized {savedParameters?.Count ?? 0} parameters");
                    
                    if (savedParameters == null)
                    {
                        System.Diagnostics.Debug.WriteLine("[ParametersService] Deserialization returned null, using defaults");
                        return defaultParameters;
                    }
                    
                    // Parameters already converted by ConvertJTokenToObject
                    var parameters = savedParameters;
                    
                    // Add any defaults that weren't in the JSON file
                    foreach (var kvp in defaultParameters)
                    {
                        if (!parameters.ContainsKey(kvp.Key))
                        {
                            parameters[kvp.Key] = kvp.Value;
                        }
                    }
                    
                    System.Diagnostics.Debug.WriteLine($"[ParametersService] Returning merged parameters: {parameters.Count} total");
                    
                    // Normalize structure and types
                    parameters = NormalizeParameters(parameters);
                    
                    // Remove legacy parameters that cause warnings
                    parameters = RemoveLegacyParameters(parameters);

                    // Debug log the final merged parameters
                    DebugLogService.LogMessage($"Merged parameters count: {parameters.Count}");
                    DebugLogService.LogMessage("Final merged parameters:");
                    foreach (var param in parameters.OrderBy(p => p.Key))
                    {
                        var valueStr = param.Value is double dVal ? dVal.ToString(CultureInfo.InvariantCulture) :
                                      param.Value is float fVal ? fVal.ToString(CultureInfo.InvariantCulture) : 
                                      param.Value?.ToString() ?? "";
                        DebugLogService.LogMessage($"  {param.Key} = {valueStr}");
                    }
                    DebugLogService.LogMessage($"=== LoadGlobalParameters END ===");
                    
                    return parameters;
                }
                else
                {
                    // Try fallback location used by older exports
                    var fallbackFolder = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments), "ddQuint");
                    var fallbackFile = Path.Combine(fallbackFolder, "parameters.json");
                    DebugLogService.LogMessage($"Parameters fallback file: {fallbackFile}");
                    DebugLogService.LogMessage($"Parameters fallback exists: {File.Exists(fallbackFile)}");
                    if (File.Exists(fallbackFile))
                    {
                        try
                        {
                            var parameters = LoadParametersFromFile(fallbackFile);
                            DebugLogService.LogMessage($"Loaded parameters from fallback: {parameters.Count}");
                            DebugLogService.LogMessage($"=== LoadGlobalParameters END ===");
                            return parameters;
                        }
                        catch (Exception ex2)
                        {
                            System.Diagnostics.Debug.WriteLine($"[ParametersService] Fallback load failed: {ex2.Message}");
                            DebugLogService.LogMessage($"Fallback load failed: {ex2.Message}");
                        }
                    }
                    System.Diagnostics.Debug.WriteLine($"[ParametersService] Parameters file does not exist, returning defaults");
                }
            }
            catch (Exception ex)
            {
                // Log error and try fallback location before using defaults
                System.Diagnostics.Debug.WriteLine($"[ParametersService] Error loading parameters: {ex.Message}");
                System.Diagnostics.Debug.WriteLine($"[ParametersService] Exception details: {ex}");
                Console.WriteLine($"Error loading parameters: {ex.Message}");

                try
                {
                    var fallbackFolder = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments), "ddQuint");
                    var fallbackFile = Path.Combine(fallbackFolder, "parameters.json");
                    DebugLogService.LogMessage($"Parameters fallback file (catch): {fallbackFile}");
                    if (File.Exists(fallbackFile))
                    {
                        var parameters = LoadParametersFromFile(fallbackFile);
                        DebugLogService.LogMessage($"Loaded parameters from fallback (catch): {parameters.Count}");
                        DebugLogService.LogMessage($"=== LoadGlobalParameters END ===");
                        return parameters;
                    }
                }
                catch (Exception fallbackEx)
                {
                    DebugLogService.LogMessage($"Fallback loading also failed: {fallbackEx.Message}");
                }
            }

            System.Diagnostics.Debug.WriteLine($"[ParametersService] Returning default parameters: {defaultParameters.Count} total");
            
            // Debug log the default parameters
            DebugLogService.LogMessage($"Using default parameters count: {defaultParameters.Count}");
            DebugLogService.LogMessage("Default parameters:");
            foreach (var param in defaultParameters.OrderBy(p => p.Key))
            {
                var valueStr = param.Value is double dVal ? dVal.ToString(CultureInfo.InvariantCulture) :
                              param.Value is float fVal ? fVal.ToString(CultureInfo.InvariantCulture) : 
                              param.Value?.ToString() ?? "";
                DebugLogService.LogMessage($"  {param.Key} = {valueStr}");
            }
            DebugLogService.LogMessage($"=== LoadGlobalParameters END (defaults) ===");
            
            return defaultParameters;
        }

        public static void SaveGlobalParameters(Dictionary<string, object> parameters)
        {
            var timestamp = DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss");
            System.Diagnostics.Debug.WriteLine($"[ParametersService] SaveGlobalParameters called with {parameters.Count} parameters at {timestamp}");
            System.Diagnostics.Debug.WriteLine($"[ParametersService] Target folder: {AppDataFolder}");
            System.Diagnostics.Debug.WriteLine($"[ParametersService] Target file: {ParametersFilePath}");
            
            // Debug log the save operation
            DebugLogService.LogMessage($"=== SaveGlobalParameters START ===");
            DebugLogService.LogMessage($"Called at: {timestamp}");
            DebugLogService.LogMessage($"Parameters to save: {parameters.Count}");
            foreach (var param in parameters.OrderBy(p => p.Key))
            {
                DebugLogService.LogMessage($"  SAVE: {param.Key} = {param.Value}");
            }
            DebugLogService.LogMessage($"Target file: {ParametersFilePath}");
            
            try
            {
                // Ensure the directory exists
                System.Diagnostics.Debug.WriteLine($"[ParametersService] Creating directory: {AppDataFolder}");
                Directory.CreateDirectory(AppDataFolder);
                System.Diagnostics.Debug.WriteLine($"[ParametersService] Directory exists: {Directory.Exists(AppDataFolder)}");
                
                // Check if file exists and its attributes
                if (File.Exists(ParametersFilePath))
                {
                    var fileInfo = new FileInfo(ParametersFilePath);
                    System.Diagnostics.Debug.WriteLine($"[ParametersService] File exists, size: {fileInfo.Length} bytes");
                    System.Diagnostics.Debug.WriteLine($"[ParametersService] File attributes: {fileInfo.Attributes}");
                    System.Diagnostics.Debug.WriteLine($"[ParametersService] File is read-only: {fileInfo.IsReadOnly}");
                    
                    // Try to clear read-only attribute if set
                    if (fileInfo.IsReadOnly)
                    {
                        System.Diagnostics.Debug.WriteLine($"[ParametersService] Removing read-only attribute");
                        fileInfo.IsReadOnly = false;
                    }
                }
                
                // Normalize parameters before serializing
                parameters = NormalizeParameters(parameters);
                
                // Remove legacy parameters that cause warnings
                parameters = RemoveLegacyParameters(parameters);

                // Use Newtonsoft.Json to match macOS behavior exactly
                var json = Newtonsoft.Json.JsonConvert.SerializeObject(parameters, Newtonsoft.Json.Formatting.Indented);
                
                System.Diagnostics.Debug.WriteLine($"[ParametersService] JSON length: {json.Length}");
                System.Diagnostics.Debug.WriteLine($"[ParametersService] Writing to: {ParametersFilePath}");
                
                // Use more robust file writing with retry logic
                int maxRetries = 3;
                for (int retry = 0; retry < maxRetries; retry++)
                {
                    try
                    {
                        // Write to a temporary file first, then move it (atomic operation)
                        var tempFile = ParametersFilePath + ".tmp";
                        File.WriteAllText(tempFile, json);
                        
                        // Delete the original file if it exists
                        if (File.Exists(ParametersFilePath))
                        {
                            File.Delete(ParametersFilePath);
                        }
                        
                        // Move the temp file to the final location
                        File.Move(tempFile, ParametersFilePath);
                        break; // Success, exit retry loop
                    }
                    catch (IOException ex) when (retry < maxRetries - 1)
                    {
                        System.Diagnostics.Debug.WriteLine($"[ParametersService] Retry {retry + 1}: {ex.Message}");
                        System.Threading.Thread.Sleep(100); // Wait 100ms before retry
                    }
                }
                
                System.Diagnostics.Debug.WriteLine($"[ParametersService] File written successfully");
                System.Diagnostics.Debug.WriteLine($"[ParametersService] File exists after write: {File.Exists(ParametersFilePath)}");
                System.Diagnostics.Debug.WriteLine($"[ParametersService] File size: {new FileInfo(ParametersFilePath).Length} bytes");
                
                // Debug log success
                DebugLogService.LogMessage($"Parameters saved successfully");
                DebugLogService.LogMessage($"File exists: {File.Exists(ParametersFilePath)}");
                DebugLogService.LogMessage($"File size: {new FileInfo(ParametersFilePath).Length} bytes");
                DebugLogService.LogMessage($"=== SaveGlobalParameters END ===");
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"[ParametersService] Error saving parameters: {ex.Message}");
                System.Diagnostics.Debug.WriteLine($"[ParametersService] Exception details: {ex}");
                
                // Try fallback location in user's Documents folder
                try
                {
                    var fallbackFolder = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments), "ddQuint");
                    var fallbackFile = Path.Combine(fallbackFolder, "parameters.json");
                    
                    System.Diagnostics.Debug.WriteLine($"[ParametersService] Trying fallback location: {fallbackFile}");
                    Directory.CreateDirectory(fallbackFolder);
                    
                    var json = Newtonsoft.Json.JsonConvert.SerializeObject(parameters, Newtonsoft.Json.Formatting.Indented);
                    File.WriteAllText(fallbackFile, json);
                    
                    System.Diagnostics.Debug.WriteLine($"[ParametersService] Successfully saved to fallback location");
                    Console.WriteLine($"Parameters saved to fallback location: {fallbackFile}");
                    return; // Success with fallback
                }
                catch (Exception fallbackEx)
                {
                    System.Diagnostics.Debug.WriteLine($"[ParametersService] Fallback also failed: {fallbackEx.Message}");
                }
                
                Console.WriteLine($"Error saving parameters: {ex.Message}");
                Console.WriteLine($"Please check that the application has write permissions to: {ParametersFilePath}");
                throw;
            }
        }

        // Produce a normalized parameter dictionary suitable for export/sharing
        public static Dictionary<string, object> PrepareForExport(Dictionary<string, object> parameters)
        {
            var normalized = NormalizeParameters(parameters);

            // Remove legacy dictionaries and any flattened CN/SD keys to avoid duplicating formats
            var keysToRemove = normalized.Keys
                .Where(k => k == "EXPECTED_COPY_NUMBERS" || k == "EXPECTED_STANDARD_DEVIATION"
                            || k.StartsWith("EXPECTED_COPY_NUMBERS_", StringComparison.Ordinal)
                            || k.StartsWith("EXPECTED_STANDARD_DEVIATION_", StringComparison.Ordinal))
                .ToList();
            foreach (var k in keysToRemove)
            {
                normalized.Remove(k);
            }
            return normalized;
        }

        // Static storage for well-specific parameters (matches macOS wellParametersMap)
        private static Dictionary<string, Dictionary<string, object>> _wellParametersMap = new Dictionary<string, Dictionary<string, object>>();

        public static Dictionary<string, object> LoadWellParameters(string wellId)
        {
            if (_wellParametersMap.ContainsKey(wellId))
            {
                return new Dictionary<string, object>(_wellParametersMap[wellId]);
            }
            return new Dictionary<string, object>();
        }

        public static void SaveWellParameters(string wellId, Dictionary<string, object> parameters)
        {
            var timestamp = DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss");
            DebugLogService.LogMessage($"=== SaveWellParameters START ===");
            DebugLogService.LogMessage($"Called at: {timestamp}");
            DebugLogService.LogMessage($"Well ID: {wellId}");
            DebugLogService.LogMessage($"Parameters count: {parameters.Count}");
            
            if (parameters.Count == 0)
            {
                // Remove well parameters if empty (matches macOS behavior)
                _wellParametersMap.Remove(wellId);
                System.Diagnostics.Debug.WriteLine($"[ParametersService] Removed well-specific parameters for {wellId}");
                DebugLogService.LogMessage($"REMOVED well-specific parameters for {wellId} (empty parameters)");
            }
            else
            {
                _wellParametersMap[wellId] = new Dictionary<string, object>(parameters);
                System.Diagnostics.Debug.WriteLine($"[ParametersService] Saved {parameters.Count} well-specific parameters for {wellId}");
                DebugLogService.LogMessage($"SAVED {parameters.Count} well-specific parameters for {wellId}:");
                foreach (var param in parameters.OrderBy(p => p.Key))
                {
                    DebugLogService.LogMessage($"  WELL {wellId}: {param.Key} = {param.Value}");
                }
            }
            
            DebugLogService.LogMessage($"Total wells with parameters: {_wellParametersMap.Count}");
            DebugLogService.LogMessage($"=== SaveWellParameters END ===");
        }

        public static Dictionary<string, Dictionary<string, object>> GetAllWellParameters()
        {
            return new Dictionary<string, Dictionary<string, object>>(_wellParametersMap);
        }

        public static void ClearAllWellParameters()
        {
            _wellParametersMap.Clear();
            System.Diagnostics.Debug.WriteLine("[ParametersService] Cleared all well-specific parameters");
        }

        // Load parameters from a specific file path (for manual file selection)
        public static Dictionary<string, object> LoadParametersFromFile(string filePath)
        {
            var timestamp = DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss");
            DebugLogService.LogMessage($"=== LoadParametersFromFile START ===");
            DebugLogService.LogMessage($"Called at: {timestamp}");
            DebugLogService.LogMessage($"File path: {filePath}");
            DebugLogService.LogMessage($"File exists: {File.Exists(filePath)}");
            
            System.Diagnostics.Debug.WriteLine($"[LoadParametersFromFile] START - File: {filePath}");
            Console.WriteLine($"[LoadParametersFromFile] START - File: {filePath}");

            if (!File.Exists(filePath))
            {
                DebugLogService.LogMessage("File not found");
                throw new FileNotFoundException($"Parameter file not found: {filePath}");
            }

            try
            {
                var json = File.ReadAllText(filePath);
                DebugLogService.LogMessage($"JSON content length: {json.Length}");
                
                // Try to parse as parameter bundle first (macOS format), then fall back to direct parameters
                Dictionary<string, JsonElement>? savedParameters = null;
                
                var rootObj = JsonSerializer.Deserialize<Dictionary<string, JsonElement>>(json, new JsonSerializerOptions
                {
                    ReadCommentHandling = JsonCommentHandling.Skip,
                    AllowTrailingCommas = true
                });
                
                // Check if this is a parameter bundle (has global_parameters wrapper)
                if (rootObj != null)
                {
                    DebugLogService.LogMessage($"LoadParametersFromFile: Found JSON object with {rootObj.Count} keys: {string.Join(", ", rootObj.Keys)}");
                    if (rootObj.ContainsKey("global_parameters"))
                    {
                        DebugLogService.LogMessage("Found parameter bundle format (macOS export)");
                        var globalParamsElement = rootObj["global_parameters"];
                        savedParameters = JsonSerializer.Deserialize<Dictionary<string, JsonElement>>(
                            globalParamsElement.GetRawText(), new JsonSerializerOptions
                            {
                                ReadCommentHandling = JsonCommentHandling.Skip,
                                AllowTrailingCommas = true
                            });
                        
                    // Also load well parameters if present in bundle
                    if (rootObj.ContainsKey("well_parameters"))
                    {
                        try
                        {
                            var wellParamsElement = rootObj["well_parameters"];
                            var wellParamsDict = JsonSerializer.Deserialize<Dictionary<string, Dictionary<string, JsonElement>>>(
                                wellParamsElement.GetRawText(), new JsonSerializerOptions
                                {
                                    ReadCommentHandling = JsonCommentHandling.Skip,
                                    AllowTrailingCommas = true
                                });
                                
                            if (wellParamsDict != null)
                            {
                                foreach (var wellKvp in wellParamsDict)
                                {
                                    var wellParams = new Dictionary<string, object>();
                                    foreach (var paramKvp in wellKvp.Value)
                                    {
                                        wellParams[paramKvp.Key] = ConvertJsonElementToObject(paramKvp.Value);
                                    }
                                    SaveWellParameters(wellKvp.Key, wellParams);
                                }
                                DebugLogService.LogMessage($"Loaded {wellParamsDict.Count} well parameter sets from bundle");
                            }
                        }
                        catch (Exception ex)
                        {
                            DebugLogService.LogMessage($"Warning: Could not load well parameters from bundle: {ex.Message}");
                        }
                    }
                    }
                    else
                    {
                        // Direct parameters format
                        DebugLogService.LogMessage("LoadParametersFromFile: Found direct parameters format");
                        savedParameters = rootObj;
                    }
                }

                if (savedParameters == null)
                {
                    DebugLogService.LogMessage("No parameters found in file");
                    throw new InvalidOperationException("No valid parameters found in file");
                }

                // Convert JSON parameters using shared logic
                var parameters = ConvertJsonElementsToParameters(savedParameters);
                
                // Normalize structure and types
                parameters = NormalizeParameters(parameters);
                
                DebugLogService.LogMessage($"Successfully loaded {parameters.Count} parameters from file");
                DebugLogService.LogMessage($"=== LoadParametersFromFile END ===");
                
                return parameters;
            }
            catch (Exception ex)
            {
                DebugLogService.LogMessage($"Error loading parameters from file: {ex.Message}");
                DebugLogService.LogMessage($"=== LoadParametersFromFile END (ERROR) ===");
                throw;
            }
        }
    }
}
