using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using System.Threading.Tasks;
using System.ComponentModel;
using ddQuint.Core.Models;
using ddQuint.Desktop.Services;
using Newtonsoft.Json;

namespace ddQuint.Desktop.Services
{
    public class AnalysisService
    {
        private readonly PythonEnvironmentService _pythonService;

        public event EventHandler<string>? LogMessageAdded;
        public event EventHandler<ProgressChangedEventArgs>? ProgressChanged;
        public event EventHandler<string>? StatusChanged;
        public event EventHandler<WellResult>? WellCompleted;

        public AnalysisService()
        {
            _pythonService = PythonEnvironmentService.Instance;
        }

        private void OnLogMessageAdded(string message)
        {
            LogMessageAdded?.Invoke(this, message);
            // Mirror analysis logs to unified debug log file
            DebugLogService.LogMessage(message);
        }
        
        private void OnProgressChanged(double progress)
        {
            var percentProgress = (int)(progress * 100);
            ProgressChanged?.Invoke(this, new ProgressChangedEventArgs(percentProgress, null));
        }
        
        private void OnStatusChanged(string status)
        {
            StatusChanged?.Invoke(this, status);
        }
        
        private void OnWellCompleted(WellResult well)
        {
            WellCompleted?.Invoke(this, well);
        }

        public async Task<AnalysisResult> AnalyzeAsync(string inputFolderPath, string? templateFilePath, int templateDescriptionCount = 4)
        {
            OnLogMessageAdded($"=== AnalysisService.AnalyzeAsync START ===");
            OnLogMessageAdded($"Input folder: {inputFolderPath}");
            OnLogMessageAdded($"Template file: {templateFilePath ?? "null"}");
            OnLogMessageAdded($"Template description count: {templateDescriptionCount}");
            
            var result = await RunAnalysis(inputFolderPath, templateFilePath, templateDescriptionCount);
            
            OnLogMessageAdded($"=== AnalysisService.AnalyzeAsync END ===");
            return result;
        }

        public async Task<AnalysisResult> RunAnalysis(string inputFolderPath, string? templateFilePath, int templateDescriptionCount = 4)
        {
            try
            {
                OnStatusChanged("Starting analysis...");
                OnProgressChanged(0.1);
                OnLogMessageAdded("Starting ddPCR analysis...");
                OnLogMessageAdded($"Input folder: {inputFolderPath}");
                OnLogMessageAdded($"Template file: {templateFilePath ?? "None"}");

                var csvFiles = Directory.GetFiles(inputFolderPath, "*.csv");
                if (csvFiles.Length == 0)
                {
                    throw new InvalidOperationException("No CSV files found in the selected folder.");
                }

                OnLogMessageAdded($"Found {csvFiles.Length} CSV files");
                OnProgressChanged(0.2);

                var tempResultsPath = Path.Combine(Path.GetTempPath(), "ddquint_results_" + Guid.NewGuid().ToString("N"));
                Directory.CreateDirectory(tempResultsPath);
                OnLogMessageAdded($"Created temp results directory: {tempResultsPath}");

                OnStatusChanged("Preparing analysis...");
                OnProgressChanged(0.3);
                
                OnLogMessageAdded("=== CREATING PYTHON ANALYSIS SCRIPT ===");
                OnLogMessageAdded($"About to create analysis script with {csvFiles.Length} CSV files");
                OnLogMessageAdded($"Python service initialized: {_pythonService.IsInitialized}");
                var analysisScript = CreateRealAnalysisScript(inputFolderPath, templateFilePath, tempResultsPath, csvFiles.Length);
                OnLogMessageAdded($"Analysis script created. Length: {analysisScript.Length} characters");
                OnLogMessageAdded("First 500 characters of script:");
                OnLogMessageAdded(analysisScript.Substring(0, Math.Min(500, analysisScript.Length)));
                OnLogMessageAdded("=== END SCRIPT PREVIEW ===");
                
                // Check if Python environment is available
                OnLogMessageAdded($"Python environment status: Initialized = {_pythonService.IsInitialized}");
                if (!_pythonService.IsInitialized)
                {
                    OnStatusChanged("Initializing Python environment...");
                    OnLogMessageAdded("Python environment not available, attempting to initialize...");
                    try
                    {
                        _pythonService.Initialize();
                        OnLogMessageAdded("Python environment initialized successfully");
                    }
                    catch (Exception ex)
                    {
                        OnLogMessageAdded($"Failed to initialize Python environment: {ex.Message}");
                        throw new InvalidOperationException("Python environment is required for analysis but is not available", ex);
                    }
                }

                OnStatusChanged("Running ddPCR analysis...");
                OnProgressChanged(0.5);
                OnLogMessageAdded("=== EXECUTING PYTHON ANALYSIS SCRIPT ===");
                OnLogMessageAdded($"Working directory: {inputFolderPath}");
                OnLogMessageAdded($"About to call _pythonService.ExecutePythonScript...");
                
                // Set up environment variables
                var environmentVariables = new Dictionary<string, string>
                {
                    ["DDQ_TEMPLATE_DESC_COUNT"] = templateDescriptionCount.ToString()
                };
                if (!string.IsNullOrEmpty(templateFilePath))
                {
                    environmentVariables["DDQ_TEMPLATE_PATH"] = templateFilePath;
                }
                
                var combinedOutput = new System.Text.StringBuilder();
                void HandleStdout(string line)
                {
                    combinedOutput.AppendLine(line);
                    OnLogMessageAdded(line);
                    try { DebugLogService.ProcessPythonOutput(line + "\n"); } catch { }
                    try { DebugLogService.LogMessage(line); } catch { }

                    const string prefix = "WELL_RESULT:";
                    const string filePrefix = "PROCESSING_FILE:";
                    if (line.StartsWith(filePrefix))
                    {
                        OnStatusChanged(line);
                        return;
                    }
                    if (line.StartsWith(prefix))
                    {
                        var jsonPart = line.Substring(prefix.Length).Trim();
                        try
                        {
                            var obj = Newtonsoft.Json.Linq.JObject.Parse(jsonPart);
                            var well = new WellResult
                            {
                                WellId = obj.Value<string>("well_id") ?? "",
                                SampleName = obj.Value<string>("sample_name") ?? "",
                                Status = ParseWellStatus(obj.Value<string>("status") ?? ""),
                                PlotImagePath = ConvertToWindowsPath(obj.Value<string>("plot_path")),
                                TotalDroplets = obj.Value<int?>("total_droplets") ?? 0,
                                UsableDroplets = obj.Value<int?>("usable_droplets") ?? 0,
                                NegativeDroplets = obj.Value<int?>("negative_droplets") ?? 0,
                                AnalysisData = obj["analysis_data"]?.ToObject<Dictionary<string, object>>()
                            };

                            var copyNumbersToken = obj["copy_numbers"];
                            if (copyNumbersToken != null && copyNumbersToken.Type == Newtonsoft.Json.Linq.JTokenType.Object)
                            {
                                well.CopyNumbersDictionary = copyNumbersToken.ToObject<Dictionary<string, double>>();
                            }

                            OnWellCompleted(well);
                        }
                        catch (Exception ex)
                        {
                            OnLogMessageAdded($"Failed to parse WELL_RESULT line: {ex.Message}");
                        }
                    }
                }

                void HandleStderr(string line)
                {
                    combinedOutput.AppendLine(line);
                    OnLogMessageAdded(line);
                    try { DebugLogService.LogMessage(line); } catch { }
                }

                var result = await _pythonService.ExecutePythonScript(analysisScript, inputFolderPath, HandleStdout, HandleStderr, persistScript: true, environmentVariables);
                OnLogMessageAdded($"Python execution completed. Exit code: {result.ExitCode}");
                
                if (result.ExitCode != 0)
                {
                    OnLogMessageAdded($"Python analysis failed with exit code {result.ExitCode}");
                    if (!string.IsNullOrWhiteSpace(result.Error))
                    {
                        OnLogMessageAdded($"Python error output:");
                        OnLogMessageAdded(result.Error);
                    }
                    if (!string.IsNullOrWhiteSpace(result.Output))
                    {
                        OnLogMessageAdded($"Python standard output:");
                        OnLogMessageAdded(result.Output);
                    }
                    
                    // Check for specific error types
                    var errorMessage = result.Error + " " + result.Output;
                    if (errorMessage.Contains("timeout"))
                    {
                        throw new InvalidOperationException("Analysis timed out after 5 minutes. This may indicate issues with the data or Python environment.");
                    }
                    else if (errorMessage.Contains("ImportError") || errorMessage.Contains("ModuleNotFoundError"))
                    {
                        throw new InvalidOperationException($"Python module import failed. Please check the bundled Python environment. Error: {result.Error}");
                    }
                    else
                    {
                        throw new InvalidOperationException($"Python analysis failed: {(string.IsNullOrWhiteSpace(result.Error) ? result.Output : result.Error)}");
                    }
                }

                OnLogMessageAdded("Python analysis completed successfully");
                OnLogMessageAdded($"Python output: {result.Output}");

                OnStatusChanged("Processing results...");
                OnProgressChanged(0.8);
                var analysisResult = ParseAnalysisResults(tempResultsPath, result.Output);
                
                OnStatusChanged("Analysis complete");
                OnProgressChanged(1.0);
                OnLogMessageAdded($"Analysis complete - processed {analysisResult.Wells.Count} wells");
                
                return analysisResult;
            }
            catch (Exception ex)
            {
                OnLogMessageAdded($"Analysis failed: {ex.Message}");
                throw;
            }
        }
        
        /// <summary>
        /// Reprocess a single well with well-specific parameters (matching macOS behavior)
        /// </summary>
        public async Task<List<WellResult>> ReprocessSingleWellAsync(string inputFolderPath, string wellId, string? templateFilePath)
        {
            OnLogMessageAdded($"=== ReprocessSingleWellAsync START for {wellId} ===");
            OnLogMessageAdded($"Input folder: {inputFolderPath}");
            OnLogMessageAdded($"Well ID: {wellId}");
            OnLogMessageAdded($"Template file: {templateFilePath ?? "None"}");
            
            try
            {
                // Find the specific CSV file for this well
                var csvFiles = Directory.GetFiles(inputFolderPath, "*.csv");
                var wellCsvFile = csvFiles.FirstOrDefault(f => 
                {
                    var fileName = Path.GetFileNameWithoutExtension(f);
                    // Try different parsing strategies to match well ID
                    return fileName.Contains(wellId) || 
                           fileName.EndsWith($"_{wellId}") ||
                           fileName.StartsWith($"{wellId}_") ||
                           fileName.Equals(wellId, StringComparison.OrdinalIgnoreCase);
                });
                
                if (wellCsvFile == null)
                {
                    OnLogMessageAdded($"ERROR: Could not find CSV file for well {wellId} in {inputFolderPath}");
                    return new List<WellResult>();
                }
                
                OnLogMessageAdded($"Found CSV file for well {wellId}: {Path.GetFileName(wellCsvFile)}");
                
                // Create temporary output directory
                var tempOutputDir = Path.Combine(Path.GetTempPath(), $"ddquint_single_well_{Guid.NewGuid()}");
                Directory.CreateDirectory(tempOutputDir);
                OnLogMessageAdded($"Created temp output directory: {tempOutputDir}");
                
                // Create focused analysis script for single well
                var singleWellScript = await CreateMacOSStyleSingleWellScript(inputFolderPath, wellId, wellCsvFile, templateFilePath, tempOutputDir);
                
                OnLogMessageAdded($"Single well analysis script generated");
                OnLogMessageAdded($"Script length: {singleWellScript.Length} characters");
                
                // Execute the single well analysis (pass script content, not file path)
                OnLogMessageAdded($"Starting Python execution for single well analysis...");
                var result = await _pythonService.ExecutePythonScript(singleWellScript, tempOutputDir, persistScript: true);
                
                // Parse results
                var wellResults = new List<WellResult>();
                // Prefer UPDATED_RESULT parsing even if exit code is non-zero (macOS tolerance)
                wellResults = ParseSingleWellReprocessingResults(result.Output, wellId, tempOutputDir);
                if (wellResults.Count > 0)
                {
                    OnLogMessageAdded($"Single well analysis produced result(s) despite exit code {result.ExitCode}");
                }
                else if (result.ExitCode != 0)
                {
                    OnLogMessageAdded($"ERROR: Single well analysis failed with exit code {result.ExitCode}: {result.Error}");
                    OnLogMessageAdded($"Python stdout: {result.Output}");
                }
                
                // Keep temp directory so the UI can show the generated plot (match macOS behavior)
                OnLogMessageAdded($"Retained single-well output directory for plots: {tempOutputDir}");
                
                OnLogMessageAdded($"=== ReprocessSingleWellAsync END for {wellId} ===");
                return wellResults;
            }
            catch (Exception ex)
            {
                OnLogMessageAdded($"ERROR in ReprocessSingleWellAsync for {wellId}: {ex.Message}");
                OnLogMessageAdded($"Stack trace: {ex.StackTrace}");
                throw;
            }
        }

        /// <summary>
        /// Create a clean Python script for analyzing a single well using exact macOS approach (CLEAN VERSION)
        /// </summary>
        private async Task<string> CreateMacOSStyleSingleWellScript(string inputFolderPath, string wellId, string wellCsvFile, string? templateFilePath, string outputPath)
        {
            var scriptLines = new List<string>();
            
            // Create global parameters file in input folder (like macOS)
            var globalParameters = ParametersService.LoadGlobalParameters();
            var globalParamsFile = Path.Combine(inputFolderPath, "ddQuint_Parameters.json");
            try 
            {
                var globalJson = JsonConvert.SerializeObject(globalParameters, Formatting.Indented);
                await File.WriteAllTextAsync(globalParamsFile, globalJson);
                OnLogMessageAdded($"Created global parameters file: {globalParamsFile}");
            }
            catch (Exception ex)
            {
                OnLogMessageAdded($"Warning: Could not create global parameters file: {ex.Message}");
            }
            
            // Create well-specific parameters file (like macOS)
            var wellParameters = ParametersService.LoadWellParameters(wellId);
            // Normalize types to ensure ints/floats/bools are proper primitives (match macOS behavior)
            var normalizedWellParameters = ParametersService.NormalizeForWell(wellParameters);
            var wellParamsFile = "";
            if (normalizedWellParameters.Count > 0)
            {
                wellParamsFile = Path.Combine(outputPath, $"ddquint_well_params_{wellId}.json");
                try
                {
                    var wellJson = JsonConvert.SerializeObject(normalizedWellParameters, Formatting.Indented);
                    await File.WriteAllTextAsync(wellParamsFile, wellJson);
                    OnLogMessageAdded($"Created well parameters file: {wellParamsFile} with {normalizedWellParameters.Count} parameters");
                }
                catch (Exception ex)
                {
                    OnLogMessageAdded($"Warning: Could not create well parameters file: {ex.Message}");
                    wellParamsFile = "";
                }
            }
            else
            {
                OnLogMessageAdded($"No well-specific parameters for {wellId} - using global defaults");
            }
            
            // Generate clean Python script (exact macOS style)
            scriptLines.Add("#!/usr/bin/env python3");
            scriptLines.Add("# -*- coding: utf-8 -*-");
            scriptLines.Add("\"\"\"Single well analysis script - Windows using macOS approach\"\"\"");
            scriptLines.Add("");
            
            // Basic imports
            scriptLines.Add("import sys");
            scriptLines.Add("import os"); 
            scriptLines.Add("import json");
            scriptLines.Add("import tempfile");
            scriptLines.Add("import logging");
            scriptLines.Add("");
            
            // Import ddquint (match macOS exactly)
            scriptLines.Add("try:");
            scriptLines.Add("    from ddquint.config.logging_config import setup_logging");
            scriptLines.Add("    from ddquint.config import Config");
            scriptLines.Add("    from ddquint.utils.parameter_editor import load_parameters_if_exist");
            scriptLines.Add("    from ddquint.core.file_processor import process_csv_file");
            scriptLines.Add("    from ddquint.utils.template_parser import parse_template_file as _ptf");
            scriptLines.Add("    try:\n        from ddquint.utils.template_parser import find_template_file as _ftf\n    except Exception:\n        _ftf = None");
            scriptLines.Add("    try:\n        from ddquint.utils.template_parser import get_sample_names as _gsn\n    except Exception:\n        _gsn = None");
            scriptLines.Add("    print('SUCCESS: Successfully imported all ddquint modules')");
            scriptLines.Add("except ImportError as e:");
            scriptLines.Add("    print(f'ERROR: Failed to import ddquint: {e}')");
            scriptLines.Add("    sys.exit(1)");
            scriptLines.Add("");
            
            // Initialize logging (match macOS)
            scriptLines.Add("# Initialize logging (quiet by default to avoid spam)");
            scriptLines.Add("log_file = setup_logging(debug=False)");
            scriptLines.Add("print(f'Logging initialized: {log_file}')");
            scriptLines.Add("");
            scriptLines.Add("# Add stdout handler for real-time output (info level)");
            scriptLines.Add("stdout_handler = logging.StreamHandler(sys.stdout)");
            scriptLines.Add("stdout_handler.setLevel(logging.INFO)");
            scriptLines.Add("stdout_handler.setFormatter(logging.Formatter('DDQUINT_LOG: %(name)s - %(levelname)s - %(message)s'))");
            scriptLines.Add("logging.getLogger().addHandler(stdout_handler)");
            scriptLines.Add("# Reduce noisy modules");
            scriptLines.Add("try:\n    logging.getLogger('ddquint.config').setLevel(logging.INFO)\n    logging.getLogger('matplotlib').setLevel(logging.WARNING)\nexcept Exception as _e:\n    print('WARNING: Failed to tune logger levels:', _e)");
            scriptLines.Add("");
            
            // Initialize config and load global parameters (match macOS exactly)
            var inputFolderPathPython = inputFolderPath.Replace("\\", "/");
            scriptLines.Add("# Initialize config and load global parameters (macOS approach)");
            scriptLines.Add("config = Config.get_instance()");
            scriptLines.Add($"os.chdir(r'{inputFolderPathPython}')  # Change to input folder for ddQuint_Parameters.json");
            // On Windows, ddQuint stores parameters in AppData; point parameter_editor there
            scriptLines.Add("try:");
            scriptLines.Add("    import ddquint.utils.parameter_editor as parameter_editor");
            scriptLines.Add("    if os.name == 'nt':");
            scriptLines.Add("        _base = os.environ.get('APPDATA', os.path.expanduser('~'))");
            scriptLines.Add("        parameter_editor.USER_SETTINGS_DIR = os.path.join(_base, 'ddQuint')");
            scriptLines.Add("        parameter_editor.PARAMETERS_FILE = os.path.join(parameter_editor.USER_SETTINGS_DIR, 'parameters.json')");
            scriptLines.Add("        os.makedirs(parameter_editor.USER_SETTINGS_DIR, exist_ok=True)");
            scriptLines.Add("        print('DEBUG: parameter_editor.USER_SETTINGS_DIR =', parameter_editor.USER_SETTINGS_DIR)");
            scriptLines.Add("        print('DEBUG: parameter_editor.PARAMETERS_FILE =', parameter_editor.PARAMETERS_FILE)");
            scriptLines.Add("except Exception as _e:");
            scriptLines.Add("    print('WARNING: parameter_editor path setup failed:', _e)");
            scriptLines.Add("_param_loaded = False");
            scriptLines.Add("try:");
            scriptLines.Add("    _param_loaded = load_parameters_if_exist(Config)  # Load global parameters from folder");
            scriptLines.Add("except Exception as _e:");
            scriptLines.Add("    print('WARNING: load_parameters_if_exist failed:', _e)");
            scriptLines.Add("print('DDQUINT_LOG: Loaded global parameters from input folder')");
            scriptLines.Add("");
            // Fallback for critical globals if parameters file could not be loaded (e.g. permission denied)
            try
            {
                var fg = new Dictionary<string, object>();
                var normGlobals = ParametersService.LoadGlobalParameters();
                if (normGlobals.TryGetValue("ENABLE_FLUOROPHORE_MIXING", out var mixFlag))
                {
                    fg["ENABLE_FLUOROPHORE_MIXING"] = mixFlag;
                }
                var fgJson = JsonConvert.SerializeObject(fg);
                var fgEscaped = fgJson.Replace("\\", "\\\\").Replace("\"", "\\\"");
                scriptLines.Add($"if not _param_loaded:\n    try:\n        _fg = json.loads(\"{fgEscaped}\")\n        if 'ENABLE_FLUOROPHORE_MIXING' in _fg:\n            Config.ENABLE_FLUOROPHORE_MIXING = bool(_fg['ENABLE_FLUOROPHORE_MIXING'])\n            print('DEBUG: Fallback applied ENABLE_FLUOROPHORE_MIXING =', Config.ENABLE_FLUOROPHORE_MIXING)\n    except Exception as _e:\n        print('WARNING: Failed to apply fallback globals:', _e)");
            }
            catch { }
            
            // Load well-specific parameters if available (match macOS exactly)
            if (!string.IsNullOrEmpty(wellParamsFile))
            {
                var wellParamsPathPython = wellParamsFile.Replace("\\", "/");
                scriptLines.Add("# Load well-specific parameters (macOS approach)");
                scriptLines.Add($"well_params_file = r'{wellParamsPathPython}'");
                scriptLines.Add("if os.path.exists(well_params_file):");
                scriptLines.Add("    with open(well_params_file, 'r') as f:");
                scriptLines.Add("        custom_params = json.load(f)");
                scriptLines.Add($"    print(f'Loaded {{len(custom_params)}} custom parameters: {{list(custom_params.keys())}}')");
                scriptLines.Add($"    config.set_well_context('{wellId}', custom_params)  # Apply well context");
                scriptLines.Add($"    print(f'Set well context for {wellId} with {{len(custom_params)}} parameter overrides')");
                scriptLines.Add("else:");
                scriptLines.Add("    print('No custom parameters file found')");
            }
            else
            {
                scriptLines.Add($"# No well-specific parameters for {wellId}");
            scriptLines.Add($"print('DDQUINT_LOG: Using global parameters only for {wellId}')");
            }
            scriptLines.Add("");
            // One-line confirmation of effective mixing flag
            scriptLines.Add("try:\n    print('DEBUG: Effective ENABLE_FLUOROPHORE_MIXING =', getattr(Config, 'ENABLE_FLUOROPHORE_MIXING', None))\nexcept Exception as _e:\n    print('WARNING: Could not read ENABLE_FLUOROPHORE_MIXING:', _e)");
            scriptLines.Add("");
            
            // Finalize config (match macOS)
            scriptLines.Add("config.finalize_colors()");
            scriptLines.Add("");
            
            // Parse template (match macOS approach). If explicit template not provided, try to find one in the folder.
            var templatePathPython = (templateFilePath ?? "").Replace("\\", "/");
            scriptLines.Add("sample_names = {}");
            if (!string.IsNullOrEmpty(templateFilePath))
            {
                scriptLines.Add($"template_path = r'{templatePathPython}'");
                scriptLines.Add("if template_path and os.path.exists(template_path):");
                scriptLines.Add("    try:");
                scriptLines.Add("        sample_names = _ptf(template_path) or {}");
                scriptLines.Add("        print(f'Template parsed: {len(sample_names)} samples')");
                scriptLines.Add("    except Exception as e:");
                scriptLines.Add("        print(f'Template parsing failed: {e}')");
                scriptLines.Add("        sample_names = {}");
            }
            scriptLines.Add("if not sample_names and _ftf:");
            scriptLines.Add("    try:");
            scriptLines.Add("        _folder = os.path.dirname(csv_file)");
            scriptLines.Add("        found = _ftf(_folder)");
            scriptLines.Add("        if found:");
            scriptLines.Add("            sample_names = _ptf(found) or {}");
            scriptLines.Add("            print(f'Found template automatically: {found}. Parsed {len(sample_names)} samples')");
            scriptLines.Add("    except Exception as e:");
            scriptLines.Add("        print(f'Template auto-detect failed: {e}')");
            scriptLines.Add("");
            
            // Process the CSV file (exact macOS approach)
            var csvPathPython = wellCsvFile.Replace("\\", "/");
            var outputPathPython = outputPath.Replace("\\", "/");
            scriptLines.Add("# Process the CSV file (macOS approach)");
            scriptLines.Add($"csv_file = r'{csvPathPython}'");
            scriptLines.Add($"graphs_dir = r'{outputPathPython}'");
            scriptLines.Add($"print('DEBUG: About to call process_csv_file for well {wellId}')");
            scriptLines.Add("print(f'DEBUG: CSV path: {csv_file}')");
            scriptLines.Add("print(f'DEBUG: graphs_dir: {graphs_dir}')");
            scriptLines.Add("print(f'DEBUG: sample_names: {sample_names}')");
            scriptLines.Add("");
            scriptLines.Add("try:");
            scriptLines.Add("    print('DEBUG: Calling process_csv_file now...')");
            scriptLines.Add("    result = process_csv_file(csv_file, graphs_dir, sample_names, verbose=True)");
            scriptLines.Add("    print('DEBUG: process_csv_file completed successfully')");
            scriptLines.Add("    print(f'DEBUG: result type: {type(result)}')");
            scriptLines.Add("    if result:");
            scriptLines.Add("        print(f'DEBUG: result keys: {list(result.keys()) if isinstance(result, dict) else \"not dict\"}')");
            scriptLines.Add("        ");
            scriptLines.Add("        # Create result for UI (match macOS UPDATED_RESULT format)");
            scriptLines.Add("        if isinstance(result, dict):");
            scriptLines.Add("            # Prepare serializable result");
            scriptLines.Add("            serializable_result = {");
            scriptLines.Add($"                'well': '{wellId}',");
            scriptLines.Add("                'well_id': result.get('well', '{wellId}'),");
            scriptLines.Add("                'sample_name': result.get('sample_name', ''),");
            scriptLines.Add("                'plot_path': result.get('graph_path', ''),");
            scriptLines.Add("                'total_droplets': result.get('total_droplets', 0),");
            scriptLines.Add("                'usable_droplets': result.get('usable_droplets', 0),");
            scriptLines.Add("                'negative_droplets': result.get('negative_droplets', 0),");
            scriptLines.Add("                'copy_numbers': result.get('copy_numbers', {}),");
            scriptLines.Add("                'has_buffer_zone': bool(result.get('has_buffer_zone', False)),");
            scriptLines.Add("                'has_aneuploidy': bool(result.get('has_aneuploidy', False))");
            scriptLines.Add("            }");
            scriptLines.Add("            ");
            scriptLines.Add("            # Add error if present");
            scriptLines.Add("            if result.get('error'):");
            scriptLines.Add("                serializable_result['error'] = str(result.get('error'))");
            scriptLines.Add("            ");
            scriptLines.Add("            # Add all other serializable data");
            scriptLines.Add("            for key, value in result.items():");
            scriptLines.Add("                if key in ['df_filtered', 'df_original']:");
            scriptLines.Add("                    continue  # Skip DataFrames");
            scriptLines.Add("                if key not in serializable_result:");
            scriptLines.Add("                    try:");
            scriptLines.Add("                        json.dumps(value)  # Test serialization");
            scriptLines.Add("                        serializable_result[key] = value");
            scriptLines.Add("                    except (TypeError, ValueError):");
            scriptLines.Add("                        if isinstance(value, (tuple, set)):");
            scriptLines.Add("                            serializable_result[key] = list(value)");
            scriptLines.Add("                        # Skip other non-serializable values");
            scriptLines.Add("            ");
            // Do not synthesize sample_name; let ddquint provide it (matches macOS behavior)
            scriptLines.Add("            ");
            scriptLines.Add("            # Output result for Windows parsing (macOS compatible)");
            scriptLines.Add("            print(f'UPDATED_RESULT:{json.dumps(serializable_result)}')");
            scriptLines.Add("    else:");
            scriptLines.Add("        print('DEBUG: ERROR - process_csv_file returned None!')");
            scriptLines.Add("except Exception as e:");
            scriptLines.Add("    print(f'DEBUG: EXCEPTION in process_csv_file: {str(e)}')");
            scriptLines.Add("    import traceback, sys");
            scriptLines.Add("    traceback.print_exc()");
            scriptLines.Add("    sys.exit(1)");
            scriptLines.Add("");
            scriptLines.Add("print(f'Single well analysis completed for {wellId}')");
            scriptLines.Add("import sys");
            scriptLines.Add("sys.exit(0)");
            
            return string.Join("\n", scriptLines);
        }

        private string CreateRealAnalysisScript(string inputFolderPath, string? templateFilePath, string outputPath, int csvCount)
        {
            var templatePath = templateFilePath ?? "None";
            var scriptLines = new List<string>();
            
            // Load global parameters from ParametersService
            var globalParameters = ParametersService.LoadGlobalParameters();
            var allWellParameters = ParametersService.GetAllWellParameters();

            // Write macOS-style global parameters file into input folder so Python can load it
            try
            {
                var globalParamsFile = Path.Combine(inputFolderPath, "ddQuint_Parameters.json");
                var globalJson = JsonConvert.SerializeObject(globalParameters, Formatting.Indented);
                File.WriteAllText(globalParamsFile, globalJson);
                OnLogMessageAdded($"Created/updated global parameters file: {globalParamsFile}");
            }
            catch (Exception ex)
            {
                OnLogMessageAdded($"Warning: Could not write ddQuint_Parameters.json: {ex.Message}");
            }
            
            // Add Python script content line by line to avoid f-string issues
            scriptLines.Add("import sys");
            scriptLines.Add("import os");
            scriptLines.Add("import json");
            scriptLines.Add("import datetime");
            scriptLines.Add("import io");
            scriptLines.Add("");
            scriptLines.Add("# Add the ddquint package path from environment variable");
            scriptLines.Add("ddquint_path = os.environ.get('PYTHONPATH')");
            scriptLines.Add("if ddquint_path and os.path.exists(ddquint_path):");
            scriptLines.Add("    sys.path.insert(0, ddquint_path)");
            scriptLines.Add("    print(f'Added ddquint path to sys.path: {ddquint_path}')");
            scriptLines.Add("else:");
            scriptLines.Add("    print(f'Warning: PYTHONPATH not set or invalid: {ddquint_path}')");
            scriptLines.Add("    # Fallback: try to find ddquint relative to script");
            scriptLines.Add("    script_dir = os.path.dirname(os.path.abspath(__file__))");
            scriptLines.Add("    fallback_paths = [");
            scriptLines.Add("        os.path.join(script_dir, 'Python'),");
            scriptLines.Add("        os.path.join(script_dir, '..', 'Python'),");
            scriptLines.Add("        os.path.join(script_dir, '..', '..', 'Python')");
            scriptLines.Add("    ]");
            scriptLines.Add("    for fallback in fallback_paths:");
            scriptLines.Add("        if os.path.exists(fallback):");
            scriptLines.Add("            sys.path.insert(0, fallback)");
            scriptLines.Add("            ddquint_path = fallback");
            scriptLines.Add("            print(f'Using fallback ddquint path: {fallback}')");
            scriptLines.Add("            break");
            scriptLines.Add("");
            scriptLines.Add("# Debug: Print current environment");
            scriptLines.Add("print('=== Python Environment Debug ===')");
            scriptLines.Add("print(f'Python version: {sys.version}')");
            scriptLines.Add("print(f'Python executable: {sys.executable}')");
            scriptLines.Add("print(f'Current working directory: {os.getcwd()}')");
            scriptLines.Add("print(f'Script file: {__file__}')");
            scriptLines.Add("print(f'PYTHONPATH: {os.environ.get(\"PYTHONPATH\", \"Not set\")}')");
            scriptLines.Add("print(f'sys.path (first 5): {sys.path[:5]}')");
            scriptLines.Add("print('=================================')");
            scriptLines.Add("");
            // Ensure we can always restore CWD even if early failure happens
            scriptLines.Add("original_cwd = os.getcwd()");
            scriptLines.Add("try:");
            scriptLines.Add("    from ddquint.core.file_processor import process_directory");
            scriptLines.Add("    from ddquint.utils.template_parser import parse_template_file, get_sample_names");
            // macOS updated structure no longer requires composite; plotting moved
            scriptLines.Add("    # from ddquint.core.plotting import create_well_plot  # plotting available if needed");
            scriptLines.Add("    from ddquint.config.logging_config import setup_logging");
            scriptLines.Add("    print('SUCCESS: Successfully imported all ddquint modules')");
            scriptLines.Add("except ImportError as e:");
            scriptLines.Add("    print('ERROR: Error importing ddquint modules:', e)");
            scriptLines.Add("    print('Debug information:')");
            scriptLines.Add("    print('  sys.path:', sys.path)");
            scriptLines.Add("    print('  Current directory:', os.getcwd())");
            scriptLines.Add("    print('  PYTHONPATH:', os.environ.get('PYTHONPATH', 'Not set'))");
            scriptLines.Add("    ");
            scriptLines.Add("    # List available modules for debugging");
            scriptLines.Add("    if ddquint_path and os.path.exists(ddquint_path):");
            scriptLines.Add("        print(f'  Contents of {ddquint_path}:')");
            scriptLines.Add("        try:");
            scriptLines.Add("            for item in os.listdir(ddquint_path):");
            scriptLines.Add("                item_path = os.path.join(ddquint_path, item)");
            scriptLines.Add("                is_dir = os.path.isdir(item_path)");
            scriptLines.Add("                print(f'    - {item}{\"/\" if is_dir else \"\"}')");
            scriptLines.Add("                if item == 'ddquint' and is_dir:");
            scriptLines.Add("                    print('    Contents of ddquint module:')");
            scriptLines.Add("                    for subitem in os.listdir(item_path):");
            scriptLines.Add("                        print('      - ' + subitem)");
            scriptLines.Add("        except Exception as list_ex:");
            scriptLines.Add("            print('    Error listing directory: ' + str(list_ex))");
            scriptLines.Add("    else:");
            scriptLines.Add("        print('  ddquint_path does not exist: ' + str(ddquint_path))");
            scriptLines.Add("    ");
            scriptLines.Add("    import traceback");
            scriptLines.Add("    traceback.print_exc()");
            scriptLines.Add("    sys.exit(1)");
            scriptLines.Add("");
            scriptLines.Add("# Set paths via placeholders replaced from C#");
            scriptLines.Add($"input_folder = r'{inputFolderPath.Replace("\\", "\\\\")}'");
            scriptLines.Add($"output_folder = r'{outputPath.Replace("\\", "\\\\")}'");
            scriptLines.Add($"template_file = r'{templatePath.Replace("\\", "\\\\")}'");
            scriptLines.Add("if (not template_file) or template_file == 'None':");
            scriptLines.Add("    template_file = None");
            scriptLines.Add("");
            scriptLines.Add("print('Input folder:', input_folder)");
            scriptLines.Add("print('Output folder:', output_folder)");  
            scriptLines.Add("print('Template file:', template_file)");
            scriptLines.Add("");
            scriptLines.Add("# Ensure output directory exists");
            scriptLines.Add("os.makedirs(output_folder, exist_ok=True)");
            scriptLines.Add("");
            scriptLines.Add("try:");
            scriptLines.Add("    # Setup logging for ddquint analysis (single-log policy)");
            scriptLines.Add("    import logging");
            scriptLines.Add("    os.environ['DDQUINT_NO_FILE_LOG'] = '1'");
            scriptLines.Add("    log_file_path = setup_logging(debug=False)");
            scriptLines.Add("    print('SUCCESS: Logging initialized. Log file: ' + str(log_file_path))");
            scriptLines.Add("    # Reduce noisy DEBUG logs to improve performance and clarity");
            scriptLines.Add("    try:");
            scriptLines.Add("        logging.getLogger('ddquint.config').setLevel(logging.INFO)");
            scriptLines.Add("        logging.getLogger('matplotlib').setLevel(logging.WARNING)");
            scriptLines.Add("    except Exception as _e:");
            scriptLines.Add("        print('WARNING: Failed to tune logger levels:', _e)");
            scriptLines.Add("    ");
            // Avoid duplicate logs: rely on setup_logging's console handler only
            scriptLines.Add("    ");
            scriptLines.Add("    # Force immediate log entry");
            scriptLines.Add("    logger = logging.getLogger('ddquint.analysis')");
            scriptLines.Add("    logger.info('=== ddQuint Windows Analysis Started ===')");
            scriptLines.Add("    logger.info('Input folder: ' + str(input_folder))");
            scriptLines.Add("    logger.info('Output folder: ' + str(output_folder))");
            scriptLines.Add("    logger.info('Template file: ' + str(template_file))");
            scriptLines.Add("    logger.info('Python version: ' + str(sys.version))");
            scriptLines.Add("    logger.info('PYTHONPATH: ' + str(os.environ.get('PYTHONPATH', 'Not set')))");
            scriptLines.Add("    print('SUCCESS: Initial log entries written')");
            scriptLines.Add("    ");
            scriptLines.Add("    # Initialize config and load parameters (macOS approach)");
            scriptLines.Add("    from ddquint.config import Config");
            scriptLines.Add("    from ddquint.utils.parameter_editor import load_parameters_if_exist");
            scriptLines.Add("    from ddquint.core.file_processor import process_csv_file");
            scriptLines.Add("    # Load global parameters from ddQuint_Parameters.json in the input folder");
            scriptLines.Add("    import os");
            scriptLines.Add("    _cwd_before_params = os.getcwd()");
            scriptLines.Add("    try:");
            scriptLines.Add("        os.chdir(input_folder)");
            // On Windows, point parameter_editor to AppData path where the UI saves parameters
            scriptLines.Add("        try:");
            scriptLines.Add("            import ddquint.utils.parameter_editor as parameter_editor");
            scriptLines.Add("            if os.name == 'nt':");
            scriptLines.Add("                _base = os.environ.get('APPDATA', os.path.expanduser('~'))");
            scriptLines.Add("                parameter_editor.USER_SETTINGS_DIR = os.path.join(_base, 'ddQuint')");
            scriptLines.Add("                parameter_editor.PARAMETERS_FILE = os.path.join(parameter_editor.USER_SETTINGS_DIR, 'parameters.json')");
            scriptLines.Add("                os.makedirs(parameter_editor.USER_SETTINGS_DIR, exist_ok=True)");
            scriptLines.Add("                print('DEBUG: parameter_editor.USER_SETTINGS_DIR =', parameter_editor.USER_SETTINGS_DIR)");
            scriptLines.Add("                print('DEBUG: parameter_editor.PARAMETERS_FILE =', parameter_editor.PARAMETERS_FILE)");
            scriptLines.Add("        except Exception as _e:");
            scriptLines.Add("            print('WARNING: parameter_editor path setup failed:', _e)");
            scriptLines.Add("        load_parameters_if_exist(Config)");
            scriptLines.Add("        print('DEBUG: Loaded global parameters from input folder')");
            scriptLines.Add("    finally:");
            scriptLines.Add("        os.chdir(_cwd_before_params)");
            scriptLines.Add("    ");
            scriptLines.Add("    # Now safe to get config instance after parameters are loaded");
            scriptLines.Add("    config = Config.get_instance()");
            scriptLines.Add("    # One-line confirmation of effective mixing flag (debug-friendly, not noisy)");
            scriptLines.Add("    try:");
            scriptLines.Add("        print('DEBUG: Effective ENABLE_FLUOROPHORE_MIXING =', getattr(Config, 'ENABLE_FLUOROPHORE_MIXING', None))");
            scriptLines.Add("    except Exception as _e:");
            scriptLines.Add("        print('WARNING: Could not read ENABLE_FLUOROPHORE_MIXING:', _e)");
            
            // Inject well-specific parameters 
            scriptLines.Add("    # Apply well-specific parameters from Windows ParametersService");
            scriptLines.Add("    well_parameters_map = {");
            foreach (var wellParams in allWellParameters)
            {
                var normalized = ParametersService.NormalizeForWell(wellParams.Value);
                var wellParamsJson = JsonConvert.SerializeObject(normalized);
                var escapedJson = wellParamsJson.Replace("\\", "\\\\").Replace("\"", "\\\"");
                scriptLines.Add($"        '{wellParams.Key}': json.loads(\"{escapedJson}\"),");
            }
            scriptLines.Add("    }");
            scriptLines.Add("    ");
            scriptLines.Add("    # Set up well parameter context in config");
            scriptLines.Add("    for well_id, well_params in well_parameters_map.items():");
            scriptLines.Add("        config._well_parameters[well_id] = well_params");
            scriptLines.Add("        print(f'DEBUG: Loaded {len(well_params)} parameters for well {well_id}')");
            scriptLines.Add("    print(f'DEBUG: Well-specific parameters loaded for {len(well_parameters_map)} wells')");
            scriptLines.Add("    ");
            
            scriptLines.Add("    # Parameters loaded above from input folder (macOS parity)");
            scriptLines.Add("    # Ensure float parameters are actual floats (fix HDBSCAN compatibility)");
            scriptLines.Add("    for _fkey in [");
            scriptLines.Add("        'HDBSCAN_EPSILON', 'TOLERANCE_MULTIPLIER', 'COPY_NUMBER_MULTIPLIER', 'BASE_TARGET_TOLERANCE',");
            scriptLines.Add("        'LOWER_DEVIATION_TARGET', 'UPPER_DEVIATION_TARGET', 'COPY_NUMBER_MEDIAN_DEVIATION_THRESHOLD', 'AMPLITUDE_NON_LINEARITY'");
            scriptLines.Add("    ]:");
            scriptLines.Add("        if hasattr(Config, _fkey):");
            scriptLines.Add("            try:");
            scriptLines.Add("                _v = getattr(Config, _fkey)");
            scriptLines.Add("                if not isinstance(_v, float):");
            scriptLines.Add("                    setattr(Config, _fkey, float(_v))");
            scriptLines.Add("                    print(f'DEBUG: Normalized FLOAT {_fkey} = {getattr(Config, _fkey)}')");
            scriptLines.Add("            except Exception as _e:");
            scriptLines.Add("                print(f'WARNING: Could not normalize FLOAT {_fkey}: {_e}')");
            scriptLines.Add("    ");
            scriptLines.Add("    # Ensure integer parameters are actual integers (fix matplotlib compatibility)");
            scriptLines.Add("    for _ikey in [");
            scriptLines.Add("        'MIN_POINTS_FOR_CLUSTERING','HDBSCAN_MIN_CLUSTER_SIZE','HDBSCAN_MIN_SAMPLES','CHROMOSOME_COUNT',");
            scriptLines.Add("        'MIN_USABLE_DROPLETS','INDIVIDUAL_PLOT_DPI','X_AXIS_MIN','X_AXIS_MAX','Y_AXIS_MIN','Y_AXIS_MAX','X_GRID_INTERVAL','Y_GRID_INTERVAL'");
            scriptLines.Add("    ]:");
            scriptLines.Add("        if hasattr(Config, _ikey):");
            scriptLines.Add("            try:");
            scriptLines.Add("                _v = getattr(Config, _ikey)");
            scriptLines.Add("                if not isinstance(_v, int):");
            scriptLines.Add("                    setattr(Config, _ikey, int(float(_v)))");
            scriptLines.Add("                    print(f'DEBUG: Normalized INT {_ikey} = {getattr(Config, _ikey)}')");
            scriptLines.Add("            except Exception as _e:");
            scriptLines.Add("                print(f'WARNING: Could not normalize INT {_ikey}: {_e}')");
            scriptLines.Add("    ");
            scriptLines.Add("    # Coerce EXPECTED_CENTROIDS to numeric lists if overridden by file params");
            scriptLines.Add("    try:");
            scriptLines.Add("        _ec = Config.get_expected_centroids()");
            scriptLines.Add("        if isinstance(_ec, dict):");
            scriptLines.Add("            _fixed = {}");
            scriptLines.Add("            for k, v in _ec.items():");
            scriptLines.Add("                try:");
            scriptLines.Add("                    if isinstance(v, (list, tuple)):");
            scriptLines.Add("                        _fixed[k] = [float(str(x).replace(',', '.')) for x in v]");
            scriptLines.Add("                    elif isinstance(v, str) and ',' in v:");
            scriptLines.Add("                        _fixed[k] = [float(x.strip().replace(',', '.')) for x in v.split(',')]");
            scriptLines.Add("                except Exception as _e:");
            scriptLines.Add("                    print(f'WARNING: Could not coerce centroid for {k}: {_e}')");
            scriptLines.Add("            if _fixed:");
            scriptLines.Add("                Config.EXPECTED_CENTROIDS = _fixed");
            scriptLines.Add("                print('DEBUG: Coerced EXPECTED_CENTROIDS to numeric lists')");
            scriptLines.Add("                print('DEBUG: Effective EXPECTED_CENTROIDS:', _fixed)");
            scriptLines.Add("    except Exception as _e:");
            scriptLines.Add("        print('WARNING: Failed to coerce EXPECTED_CENTROIDS:', _e)");
            scriptLines.Add("    ");
            scriptLines.Add("    # Debug: Print all current parameter values being used");
            scriptLines.Add("    print('=== PARAMETER VALUES BEING USED IN PYTHON ===')");
            scriptLines.Add("    print(f'HDBSCAN_MIN_CLUSTER_SIZE = {Config.HDBSCAN_MIN_CLUSTER_SIZE}')");
            scriptLines.Add("    print(f'HDBSCAN_MIN_SAMPLES = {Config.HDBSCAN_MIN_SAMPLES}')");
            scriptLines.Add("    print(f'HDBSCAN_EPSILON = {Config.HDBSCAN_EPSILON}')");
            scriptLines.Add("    print(f'MIN_POINTS_FOR_CLUSTERING = {Config.MIN_POINTS_FOR_CLUSTERING}')");
            scriptLines.Add("    print(f'HDBSCAN_METRIC = {Config.HDBSCAN_METRIC}')");
            scriptLines.Add("    print(f'BASE_TARGET_TOLERANCE = {Config.BASE_TARGET_TOLERANCE}')");
            scriptLines.Add("    print(f'CHROMOSOME_COUNT = {Config.CHROMOSOME_COUNT}')");
            scriptLines.Add("    print(f'MIN_USABLE_DROPLETS = {Config.MIN_USABLE_DROPLETS}')");
            scriptLines.Add("    print(f'COPY_NUMBER_MEDIAN_DEVIATION_THRESHOLD = {Config.COPY_NUMBER_MEDIAN_DEVIATION_THRESHOLD}')");
            scriptLines.Add("    print(f'COPY_NUMBER_MULTIPLIER = {Config.COPY_NUMBER_MULTIPLIER}')");
            scriptLines.Add("    print(f'AMPLITUDE_NON_LINEARITY = {getattr(Config, 'AMPLITUDE_NON_LINEARITY', None)}')");
            scriptLines.Add("    print(f'TOLERANCE_MULTIPLIER = {Config.TOLERANCE_MULTIPLIER}')");
            scriptLines.Add("    print(f'ENABLE_FLUOROPHORE_MIXING = {Config.ENABLE_FLUOROPHORE_MIXING}')");
            scriptLines.Add("    print(f'ENABLE_COPY_NUMBER_ANALYSIS = {Config.ENABLE_COPY_NUMBER_ANALYSIS}')");
            scriptLines.Add("    print(f'CLASSIFY_CNV_DEVIATIONS = {Config.CLASSIFY_CNV_DEVIATIONS}')");
            scriptLines.Add("    print('=== END PARAMETER VALUES ===')");
            scriptLines.Add("    ");
            scriptLines.Add("    config.finalize_colors()");
            scriptLines.Add("    print('SUCCESS: Config initialized and parameters loaded')");
            scriptLines.Add("    ");
            scriptLines.Add("    # Parse template if provided, else auto-detect");
            scriptLines.Add("    sample_names = None");
            scriptLines.Add("    if template_file and os.path.exists(template_file):");
            scriptLines.Add("        print('Parsing template file (explicit selection)...')");
            scriptLines.Add("        sample_names = parse_template_file(template_file)");
            scriptLines.Add("        print('Loaded', len(sample_names) if sample_names else 0, 'sample names from template')");
            scriptLines.Add("    else:");
            scriptLines.Add("        try:");
            scriptLines.Add("            print('Attempting to auto-detect template and sample names...')");
            scriptLines.Add("            sample_names = get_sample_names(input_folder)");
            scriptLines.Add("            print('Auto-detected', len(sample_names) if sample_names else 0, 'sample names')");
            scriptLines.Add("        except Exception as e:");
            scriptLines.Add("            print('Auto-detect template failed:', e)");
            scriptLines.Add("            print('Continuing without sample names...')");
            scriptLines.Add("");
            scriptLines.Add("    # Process all CSV files in the directory");
            scriptLines.Add("    print('Starting ddPCR analysis with full clustering and copy number analysis...')");
            scriptLines.Add("    print('Input folder:', input_folder)");
            scriptLines.Add("    print('Output folder:', output_folder)");
            scriptLines.Add("    ");
            scriptLines.Add("    # Set output directory as working directory so graphs are created in the right place");
            scriptLines.Add("    original_cwd = os.getcwd()");
            scriptLines.Add("    os.chdir(output_folder)");
            scriptLines.Add("    ");
            scriptLines.Add("    # Debug: Show well-specific parameters passed from C#");
            scriptLines.Add("    print('=== WELL-SPECIFIC PARAMETER DEBUG ===')");
            scriptLines.Add("    try:");
            scriptLines.Add("        print(f'Well-specific parameters loaded: {len(well_parameters_map)} wells have custom parameters')");
            scriptLines.Add("        for well_id, params in well_parameters_map.items():");
            scriptLines.Add("            print(f'  Well {well_id}: {len(params)} custom parameters')");
            scriptLines.Add("            for key, value in params.items():");
            scriptLines.Add("                print(f'    {key} = {value}')");
            scriptLines.Add("    except Exception as e:");
            scriptLines.Add("        print(f'ERROR displaying well-specific parameters: {e}')");
            scriptLines.Add("    print('=== END WELL-SPECIFIC DEBUG ===')");
            scriptLines.Add("    ");
            scriptLines.Add("    # Process per-file for progressive updates");
            scriptLines.Add("    results = []");
            scriptLines.Add("    wells_data = []");
            scriptLines.Add("    try:");
            scriptLines.Add("        import glob, re, os");
            scriptLines.Add("        # Match macOS sorting exactly: use glob of full paths + parser key");
            scriptLines.Add("        csv_files = glob.glob(os.path.join(input_folder, '*.csv'))");
            scriptLines.Add("        # Exclude template file from data processing");
            scriptLines.Add("        if template_file:");
            scriptLines.Add("            template_basename = os.path.basename(template_file)");
            scriptLines.Add("            csv_files = [f for f in csv_files if os.path.basename(f) != template_basename]");
            scriptLines.Add("            print(f'Excluded template file {template_basename} from data processing')");
            scriptLines.Add("        # Robust parser identical to macOS");
            scriptLines.Add("        def parse_well_id_from_filename(filename):");
            scriptLines.Add("            basename = os.path.basename(filename)");
            scriptLines.Add("            name_no_ext = os.path.splitext(basename)[0]");
            scriptLines.Add("            pattern = re.compile(r'(?<![A-Za-z0-9])([A-Ha-h])0?([1-9]|1[0-2])(?![A-Za-z0-9])')");
            scriptLines.Add("            matches = list(pattern.finditer(name_no_ext))");
            scriptLines.Add("            if not matches:");
            scriptLines.Add("                return (999, 999)");
            scriptLines.Add("            m = matches[-1]");
            scriptLines.Add("            row_letter = m.group(1).upper()");
            scriptLines.Add("            col_number = int(m.group(2))");
            scriptLines.Add("            row_number = ord(row_letter) - ord('A') + 1");
            scriptLines.Add("            return (col_number, row_number)");
            scriptLines.Add("        csv_files.sort(key=parse_well_id_from_filename)");
            scriptLines.Add("        total = len(csv_files)");
            scriptLines.Add("        print('Found', total, 'CSV files to process (per-file streaming)')");
            scriptLines.Add("        graphs_dir = output_folder");
            scriptLines.Add("        for idx, csv_path in enumerate(csv_files, 1):");
            scriptLines.Add("            csv_name = os.path.basename(csv_path)");
            scriptLines.Add("            print(f'PROCESSING_FILE: {idx}/{total} {csv_name}')");
            scriptLines.Add("            # Establish per-well context overrides if provided");
            scriptLines.Add("            try:");
            scriptLines.Add("                import re, os");
            scriptLines.Add("                name_no_ext = os.path.splitext(csv_name)[0]");
            scriptLines.Add("                m = list(re.finditer(r'(?<![A-Za-z0-9])([A-Ha-h])0?([1-9]|1[0-2])(?![A-Za-z0-9])', name_no_ext))");
            scriptLines.Add("                well_id = None");
            scriptLines.Add("                if m:");
            scriptLines.Add("                    row_letter = m[-1].group(1).upper()");
            scriptLines.Add("                    col_number = int(m[-1].group(2))");
            scriptLines.Add("                    well_id = f'{row_letter}{col_number:02d}'");
            scriptLines.Add("                if well_id and well_id in well_parameters_map:");
            scriptLines.Add("                    overrides = dict(well_parameters_map.get(well_id, {}))");
            scriptLines.Add("                    # Coerce numeric types in overrides like single-well path");
            scriptLines.Add("                    float_keys = ['HDBSCAN_EPSILON','TOLERANCE_MULTIPLIER','COPY_NUMBER_MULTIPLIER','BASE_TARGET_TOLERANCE','LOWER_DEVIATION_TARGET','UPPER_DEVIATION_TARGET','COPY_NUMBER_MEDIAN_DEVIATION_THRESHOLD','AMPLITUDE_NON_LINEARITY']");
            scriptLines.Add("                    int_keys = ['MIN_POINTS_FOR_CLUSTERING','HDBSCAN_MIN_CLUSTER_SIZE','HDBSCAN_MIN_SAMPLES','CHROMOSOME_COUNT','MIN_USABLE_DROPLETS','INDIVIDUAL_PLOT_DPI','X_AXIS_MIN','X_AXIS_MAX','Y_AXIS_MIN','Y_AXIS_MAX','X_GRID_INTERVAL','Y_GRID_INTERVAL']");
            scriptLines.Add("                    for _k in list(overrides.keys()):\n                        try:\n                            if _k in float_keys: overrides[_k] = float(str(overrides[_k]).replace(',', '.'))\n                            elif _k in int_keys: overrides[_k] = int(float(str(overrides[_k]).replace(',', '.')))\n                        except Exception: pass");
            scriptLines.Add("                    # Rebuild structured per-well dicts from flat overrides if needed");
            scriptLines.Add("                    ecn, estd = {}, {}");
            scriptLines.Add("                    for k,v in list(overrides.items()):\n                        if k.startswith('EXPECTED_COPY_NUMBERS_'): ecn[k[len('EXPECTED_COPY_NUMBERS_'):]] = v\n                        elif k.startswith('EXPECTED_STANDARD_DEVIATION_'): estd[k[len('EXPECTED_STANDARD_DEVIATION_'):]] = v");
            scriptLines.Add("                    copy_spec = []\n                    try:\n                        all_keys = sorted(set(list(ecn.keys()) + list(estd.keys())), key=lambda x: (0 if x=='Negative' else int(str(x).replace('Chrom','')) if str(x).startswith('Chrom') else 999, str(x)))\n                    except Exception:\n                        all_keys = list(set(list(ecn.keys()) + list(estd.keys())))\n                    for ck in all_keys:\n                        if str(ck).startswith('Chrom'):\n                            ent = {'chrom': ck}\n                            if ck in ecn: ent['expected'] = ecn.get(ck)\n                            if ck in estd: ent['std_dev'] = estd.get(ck)\n                            copy_spec.append(ent)\n                    if copy_spec: overrides['COPY_NUMBER_SPEC'] = copy_spec");
            scriptLines.Add("                    ec = {}\n                    for k,v in list(overrides.items()):\n                        if k.startswith('EXPECTED_CENTROIDS_'):\n                            name = k[len('EXPECTED_CENTROIDS_'):]\n                            try:\n                                parts = [float(str(p).strip().replace(',', '.')) for p in str(v).split(',')]\n                                if len(parts) == 2: ec[name] = parts\n                            except Exception: pass\n                    if ec: overrides['EXPECTED_CENTROIDS'] = ec");
            scriptLines.Add("                    if 'TARGET_NAMES' not in overrides:\n                        tn = {}\n                        for k,v in list(overrides.items()):\n                            if k.startswith('TARGET_NAME_'):\n                                idx = k[len('TARGET_NAME_'):]\n                                tn[f'Target{idx}'] = str(v)\n                        if tn: overrides['TARGET_NAMES'] = tn");
            scriptLines.Add("                    config.set_well_context(well_id, overrides)");
            scriptLines.Add("                    try:\n                        if 'ENABLE_FLUOROPHORE_MIXING' in overrides: Config.ENABLE_FLUOROPHORE_MIXING = bool(overrides['ENABLE_FLUOROPHORE_MIXING'])\n                        if 'CHROMOSOME_COUNT' in overrides: Config.CHROMOSOME_COUNT = int(overrides['CHROMOSOME_COUNT'])\n                        Config.finalize_colors()\n                    except Exception: pass");
            scriptLines.Add("                    print(f'Applied {len(overrides)} overrides for well {well_id}')");
            scriptLines.Add("                else:");
            scriptLines.Add("                    config.clear_well_context()");
            scriptLines.Add("            except Exception as _e:");
            scriptLines.Add("                print(f'Well context error: {_e}')");
            scriptLines.Add("                config.clear_well_context()");
            scriptLines.Add("            try:");
            scriptLines.Add("                result = process_csv_file(csv_path, output_folder, sample_names, verbose=True)");
            scriptLines.Add("                print('Processed', csv_name)");
            scriptLines.Add("            except Exception as e:");
            scriptLines.Add("                import traceback");
            scriptLines.Add("                print('ERROR processing', csv_name, ':', e)");
            scriptLines.Add("                traceback.print_exc()");
            scriptLines.Add("                result = {'well': os.path.splitext(csv_name)[0], 'error': str(e)}");
            scriptLines.Add("            # Build well_data for host UI and append immediately");
            scriptLines.Add("            status = 'Normal'");
            scriptLines.Add("            if result.get('has_aneuploidy', False):");
            scriptLines.Add("                status = 'Deviation'");
            scriptLines.Add("            elif result.get('has_buffer_zone', False):");
            scriptLines.Add("                status = 'BufferZone'");
            scriptLines.Add("            elif result.get('error'):");
            scriptLines.Add("                status = 'Warning'");
            scriptLines.Add("            ");
            scriptLines.Add("            well_data = {");
            scriptLines.Add("                'well_id': result.get('well', 'Unknown'),");
            scriptLines.Add("                'sample_name': result.get('sample_name', ''),");
            scriptLines.Add("                'status': status,");
            scriptLines.Add("                'plot_path': result.get('graph_path'),");
            scriptLines.Add("                'copy_numbers': result.get('copy_numbers', {}),");
            scriptLines.Add("                'total_droplets': result.get('total_droplets', 0),");
            scriptLines.Add("                'usable_droplets': result.get('usable_droplets', 0),");
            scriptLines.Add("                'negative_droplets': result.get('negative_droplets', 0),");
            scriptLines.Add("                'analysis_data': {");
            scriptLines.Add("                    'has_aneuploidy': result.get('has_aneuploidy', False),");
            scriptLines.Add("                    'has_buffer_zone': result.get('has_buffer_zone', False),");
            scriptLines.Add("                    'counts': result.get('counts', {}),");
            scriptLines.Add("                    'copy_number_states': result.get('copy_number_states', {}),");
            scriptLines.Add("                    'target_mapping': str(result.get('target_mapping', {}))");
            scriptLines.Add("                }");
            scriptLines.Add("            }");
            scriptLines.Add("            if result.get('error'):");
            scriptLines.Add("                well_data['error'] = result['error']");
            scriptLines.Add("            print('WELL_RESULT:', json.dumps(well_data))");
            scriptLines.Add("            wells_data.append(well_data)");
            scriptLines.Add("            results.append(result)");
            scriptLines.Add("            # Extra debug");
            scriptLines.Add("            print('Well', well_data['well_id'] + ':', well_data['status'] + ',', well_data['total_droplets'], 'droplets')");
            scriptLines.Add("            ");
            
            // Close the try: add a catch to avoid SyntaxError on fast failures
            scriptLines.Add("    except Exception as e:");
            scriptLines.Add("        print('FATAL: Failure during per-file processing setup:', e)");
            scriptLines.Add("        import traceback");
            scriptLines.Add("        traceback.print_exc()");
            scriptLines.Add("    ");
            scriptLines.Add("    # Skip composite plate overview generation for better performance");
            scriptLines.Add("    plate_overview_path = None");
            scriptLines.Add("    print('SKIPPING: Composite plate overview generation to improve performance')");
            scriptLines.Add("    ");
            // wells_data and results already built in per-file loop above
            scriptLines.Add("    ");
            scriptLines.Add("    # Create final results structure");
            scriptLines.Add("    # Save parent directory of input folder per UI expectation");
            scriptLines.Add("    input_folder_saved = os.path.dirname(input_folder) if input_folder else None");
            scriptLines.Add("    final_results = {");
            scriptLines.Add("        'wells': wells_data,");
            scriptLines.Add("        'plate_overview_path': plate_overview_path,");
            scriptLines.Add("        'analysis_timestamp': str(datetime.datetime.now()),");
            scriptLines.Add("        'input_folder': input_folder_saved,");
            scriptLines.Add("        'template_file': template_file,");
            scriptLines.Add("        'total_wells': len(wells_data)");
            scriptLines.Add("    }");
            scriptLines.Add("    ");
            scriptLines.Add("    # Save results to JSON file");
            scriptLines.Add("    results_file = os.path.join(output_folder, 'results.json')");
            scriptLines.Add("    with open(results_file, 'w') as f:");
            scriptLines.Add("        json.dump(final_results, f, indent=2)");
            scriptLines.Add("    ");
            scriptLines.Add("    print('SUCCESS: Analysis completed. Results saved to', results_file)");
            scriptLines.Add("    print('RESULTS_PATH:', results_file)");
            scriptLines.Add("    print('Processed', len(wells_data), 'wells')");
            scriptLines.Add("    print('Plate overview:', plate_overview_path if plate_overview_path else 'Not created')");
            scriptLines.Add("    ");
            scriptLines.Add("except Exception as e:");
            scriptLines.Add("    print('ERROR: Analysis failed:', e)");
            scriptLines.Add("    import traceback");
            scriptLines.Add("    traceback.print_exc()");
            scriptLines.Add("    sys.exit(1)");
            scriptLines.Add("finally:");
            scriptLines.Add("    # Restore original working directory");
            scriptLines.Add("    os.chdir(original_cwd)");
            
            return string.Join("\n", scriptLines);
        }

        private static string ToPythonLiteral(object? value)
        {
            if (value == null) return "None";

            switch (value)
            {
                case bool b:
                    return b ? "True" : "False";
                case string s:
                    // Escape backslashes and single quotes for Python literal
                    var escaped = s.Replace("\\", "\\\\").Replace("'", "\\'");
                    return $"'{escaped}'";
                case sbyte or byte or short or ushort or int or uint or long or ulong:
                    return Convert.ToString(value, System.Globalization.CultureInfo.InvariantCulture)!;
                case float or double or decimal:
                    return Convert.ToString(value, System.Globalization.CultureInfo.InvariantCulture)!;
                case Dictionary<string, object>[] dictArray:
                    // Handle COPY_NUMBER_SPEC array specifically
                    var items = new List<string>();
                    foreach (var dict in dictArray)
                    {
                        var dictItems = new List<string>();
                        foreach (var kvp in dict)
                        {
                            var key = kvp.Key;
                            var val = ToPythonLiteral(kvp.Value);
                            dictItems.Add($"'{key}': {val}");
                        }
                        items.Add($"{{{string.Join(", ", dictItems)}}}");
                    }
                    return $"[{string.Join(", ", items)}]";
                case IEnumerable<Dictionary<string, object>> dictList:
                    // Also handle lists of dictionaries (e.g., List<Dictionary<string,object>>)
                    var listItems = new List<string>();
                    foreach (var dict in dictList)
                    {
                        var dictItems = new List<string>();
                        foreach (var kvp in dict)
                        {
                            var key = kvp.Key;
                            var val = ToPythonLiteral(kvp.Value);
                            dictItems.Add($"'{key}': {val}");
                        }
                        listItems.Add($"{{{string.Join(", ", dictItems)}}}");
                    }
                    return $"[{string.Join(", ", listItems)}]";
                default:
                    // Try JSON serialization for other complex types
                    try
                    {
                        var json = JsonConvert.SerializeObject(value, Formatting.None);
                        var escapedJson = json.Replace("\\", "\\\\").Replace("\"", "\\\"");
                        return $"json.loads(\"{escapedJson}\")";
                    }
                    catch (Exception)
                    {
                        // If JSON serialization fails, convert to string
                        var stringValue = value.ToString() ?? "";
                        var escapedStr = stringValue.Replace("\\", "\\\\").Replace("'", "\\'");
                        return $"'{escapedStr}'";
                    }
            }
        }
        
        
        private string? ExtractWellIdFromFilename(string fileName)
        {
            // Use same pattern as macOS version: _A05_Amplitude
            var match = System.Text.RegularExpressions.Regex.Match(fileName, @"_([A-H][0-9]{1,2})_Amplitude");
            if (match.Success)
            {
                var wellId = match.Groups[1].Value;
                return FormatWellId(wellId);
            }
            return null;
        }
        
        private string FormatWellId(string wellId)
        {
            // Format to standard A01 format (ensure two-digit column)
            var match = System.Text.RegularExpressions.Regex.Match(wellId.ToUpper(), @"^([A-H])(\d{1,2})$");
            if (match.Success)
            {
                var row = match.Groups[1].Value;
                var col = int.Parse(match.Groups[2].Value);
                if (col >= 1 && col <= 12)
                {
                    return $"{row}{col:00}";
                }
            }
            return wellId; // Return as-is if can't format
        }
        
        private string? ConvertToWindowsPath(string? path)
        {
            if (string.IsNullOrEmpty(path))
                return null;
                
            // Convert forward slashes to backslashes and verify file exists
            var windowsPath = path.Replace('/', Path.DirectorySeparatorChar);
            
            if (File.Exists(windowsPath))
            {
                OnLogMessageAdded($"Found image file: {windowsPath}");
                return windowsPath;
            }
            else
            {
                OnLogMessageAdded($"Image file not found: {windowsPath}");
                return null;
            }
        }
        
        private AnalysisResult ParseAnalysisResults(string tempResultsPath, string pythonOutput)
        {
            try
            {
                // Find the results file path from Python output
                var lines = pythonOutput.Split('\n');
                var resultsLine = lines.FirstOrDefault(l => l.StartsWith("RESULTS_PATH:"));
                
                string resultsFilePath;
                if (resultsLine != null)
                {
                    resultsFilePath = resultsLine.Replace("RESULTS_PATH:", "").Trim();
                }
                else
                {
                    // Fallback to expected location
                    resultsFilePath = Path.Combine(tempResultsPath, "results.json");
                }
                
                if (!File.Exists(resultsFilePath))
                {
                    throw new FileNotFoundException($"Results file not found: {resultsFilePath}");
                }
                
                // Read and parse results
                var jsonContent = File.ReadAllText(resultsFilePath);
                var pythonResults = JsonConvert.DeserializeObject<dynamic>(jsonContent)!;
                
                var analysisResult = new AnalysisResult
                {
                    PlateOverviewImagePath = ConvertToWindowsPath(pythonResults.plate_overview_path?.ToString()),
                    InputFolderPath = pythonResults.input_folder,
                    TemplateFilePath = pythonResults.template_file
                };
                // Capture the location of results.json for export usage
                try { analysisResult.ResultsJsonPath = resultsFilePath; } catch { }
                
                // Parse well results
                foreach (var wellResult in pythonResults.wells)
                {
                    var well = new WellResult
                    {
                        WellId = wellResult.well_id?.ToString() ?? "",
                        SampleName = wellResult.sample_name?.ToString() ?? "",
                        Status = ParseWellStatus(wellResult.status?.ToString() ?? ""),
                        PlotImagePath = ConvertToWindowsPath(wellResult.plot_path?.ToString()),
                        TotalDroplets = ConvertToInt(wellResult.total_droplets),
                        UsableDroplets = ConvertToInt(wellResult.usable_droplets),
                        NegativeDroplets = ConvertToInt(wellResult.negative_droplets)
                    };
                    try
                    {
                        var allOverrides = ParametersService.GetAllWellParameters();
                        well.IsEdited = allOverrides.ContainsKey(well.WellId) && (allOverrides[well.WellId]?.Count ?? 0) > 0;
                    }
                    catch { }
                    
                    // Parse copy numbers if available
                    if (wellResult.copy_numbers != null)
                    {
                        try
                        {
                            var copyNumbers = wellResult.copy_numbers;
                            well.CopyNumbersDictionary = new Dictionary<string, double>();
                            
                            if (copyNumbers is Newtonsoft.Json.Linq.JObject copyObj)
                            {
                                foreach (var kvp in copyObj)
                                {
                                    if (double.TryParse(kvp.Value?.ToString(), out double value))
                                    {
                                        well.CopyNumbersDictionary[kvp.Key] = value;
                                    }
                                }
                            }
                            else if (copyNumbers is System.Collections.IEnumerable enumerable)
                            {
                                foreach (var copyNumber in enumerable)
                                {
                                    var name = GetPropertyValue(copyNumber, "Name")?.ToString();
                                    var valueStr = GetPropertyValue(copyNumber, "Value")?.ToString();
                                    if (name != null && double.TryParse(valueStr, out double value))
                                    {
                                        well.CopyNumbersDictionary[name] = value;
                                    }
                                }
                            }
                        }
                        catch (Exception ex)
                        {
                            OnLogMessageAdded($"Warning: Failed to parse copy numbers for well {well.WellId}: {ex.Message}");
                        }
                    }
                    
                    analysisResult.Wells.Add(well);
                }
                
                OnLogMessageAdded($"Successfully parsed {analysisResult.Wells.Count} well results");
                return analysisResult;
            }
            catch (Exception ex)
            {
                OnLogMessageAdded($"Failed to parse analysis results: {ex.Message}");
                throw new InvalidOperationException($"Failed to parse analysis results: {ex.Message}", ex);
            }
        }
        
        /// <summary>
        /// Parse single well reprocessing results using macOS-compatible UPDATED_RESULT output
        /// </summary>
        private List<WellResult> ParseSingleWellReprocessingResults(string output, string wellId, string tempOutputDir)
        {
            var wellResults = new List<WellResult>();
            
            try
            {
                OnLogMessageAdded($"Parsing single well reprocessing output for {wellId}");
                OnLogMessageAdded($"Looking for UPDATED_RESULT in output...");
                
                // Look for UPDATED_RESULT: line like macOS does
                var lines = output.Split('\n', StringSplitOptions.RemoveEmptyEntries);
                foreach (var line in lines)
                {
                    var trimmedLine = line.Trim();
                    if (trimmedLine.StartsWith("UPDATED_RESULT:"))
                    {
                        var jsonPart = trimmedLine.Substring("UPDATED_RESULT:".Length);
                        OnLogMessageAdded($"Found UPDATED_RESULT JSON: {jsonPart.Substring(0, Math.Min(200, jsonPart.Length))}...");
                        
                        try
                        {
                            var resultData = JsonConvert.DeserializeObject<Dictionary<string, object>>(jsonPart);
                            if (resultData != null)
                            {
                                // Convert to WellResult using same logic as macOS determineWellStatus
                                var wellResult = new WellResult
                                {
                                    WellId = resultData.ContainsKey("well_id") ? resultData["well_id"]?.ToString() ?? wellId : wellId,
                                    SampleName = resultData.ContainsKey("sample_name") ? resultData["sample_name"]?.ToString() ?? "" : "",
                                    Status = DetermineWellStatusFromReprocessResult(resultData, wellId),
                                    PlotImagePath = ConvertToWindowsPath(resultData.ContainsKey("plot_path") ? resultData["plot_path"]?.ToString() : null),
                                    TotalDroplets = ConvertToInt(resultData.ContainsKey("total_droplets") ? resultData["total_droplets"] : 0),
                                    UsableDroplets = ConvertToInt(resultData.ContainsKey("usable_droplets") ? resultData["usable_droplets"] : 0),
                                    NegativeDroplets = ConvertToInt(resultData.ContainsKey("negative_droplets") ? resultData["negative_droplets"] : 0),
                                    CopyNumbersDictionary = new Dictionary<string, double>()
                                };
                                
                                // Check if well has been edited
                                try
                                {
                                    var allOverrides = ParametersService.GetAllWellParameters();
                                    wellResult.IsEdited = allOverrides.ContainsKey(wellId) && (allOverrides[wellId]?.Count ?? 0) > 0;
                                }
                                catch { }
                                
                                // Parse copy numbers if available
                                if (resultData.TryGetValue("copy_numbers", out var copyNumbersObj))
                                {
                                    try
                                    {
                                        var copyNumbersDict = JsonConvert.DeserializeObject<Dictionary<string, object>>(copyNumbersObj.ToString() ?? "{}");
                                        if (copyNumbersDict != null)
                                        {
                                            foreach (var kvp in copyNumbersDict)
                                            {
                                                if (double.TryParse(kvp.Value?.ToString(), out double value))
                                                {
                                                    wellResult.CopyNumbersDictionary[kvp.Key] = value;
                                                }
                                            }
                                        }
                                    }
                                    catch (Exception ex)
                                    {
                                        OnLogMessageAdded($"Warning: Could not parse copy numbers for {wellId}: {ex.Message}");
                                    }
                                }
                                
                                wellResults.Add(wellResult);
                                OnLogMessageAdded($"Successfully parsed reprocessing result for {wellId} with status: {wellResult.Status}");
                                break; // Found the result we need
                            }
                        }
                        catch (Exception ex)
                        {
                            OnLogMessageAdded($"ERROR: Failed to parse UPDATED_RESULT JSON for {wellId}: {ex.Message}");
                        }
                    }
                }
                
                if (wellResults.Count == 0)
                {
                    OnLogMessageAdded($"WARNING: No UPDATED_RESULT found in output, falling back to generic parsing");
                    // Fallback to generic parsing if UPDATED_RESULT not found
                    var fallbackResult = ParseAnalysisResults(tempOutputDir, output);
                    wellResults.AddRange(fallbackResult.Wells);
                }
            }
            catch (Exception ex)
            {
                OnLogMessageAdded($"ERROR in ParseSingleWellReprocessingResults: {ex.Message}");
                // Final fallback
                var fallbackResult = ParseAnalysisResults(tempOutputDir, output);
                wellResults.AddRange(fallbackResult.Wells);
            }
            
            return wellResults;
        }
        
        /// <summary>
        /// Determine well status from reprocessing result using macOS-compatible logic
        /// </summary>
        private WellStatus DetermineWellStatusFromReprocessResult(Dictionary<string, object> result, string wellName)
        {
            OnLogMessageAdded($"Determining status for well {wellName} from reprocessing result");
            
            // Check for warnings first (red takes priority) - matches macOS logic
            if (result.TryGetValue("error", out var errorObj))
            {
                var errorStr = errorObj?.ToString();
                if (!string.IsNullOrEmpty(errorStr))
                {
                    OnLogMessageAdded($"Found error: {errorStr} -> WARNING");
                    return WellStatus.Warning;
                }
            }
            
            // Check for low droplet count - matches macOS logic
            if (result.TryGetValue("total_droplets", out var totalDropletsObj))
            {
                var totalDroplets = ConvertToInt(totalDropletsObj);
                OnLogMessageAdded($"Total droplets: {totalDroplets}");
                if (totalDroplets < 100)
                {
                    OnLogMessageAdded($"Low droplet count -> WARNING");
                    return WellStatus.Warning;
                }
            }
            
            // Check biological status - prefer nested analysis_data, but also support top-level flags (macOS UPDATED_RESULT)
            if (result.TryGetValue("analysis_data", out var analysisDataObj))
            {
                try
                {
                    var analysisData = JsonConvert.DeserializeObject<Dictionary<string, object>>(analysisDataObj?.ToString() ?? "{}");
                    if (analysisData != null)
                    {
                        // Check for buffer zone
                        if (analysisData.TryGetValue("has_buffer_zone", out var bufferObj))
                        {
                            var hasBuffer = Convert.ToBoolean(bufferObj);
                            OnLogMessageAdded($"has_buffer_zone: {hasBuffer}");
                            if (hasBuffer)
                            {
                                OnLogMessageAdded($"-> BUFFER");
                                return WellStatus.BufferZone;
                            }
                        }
                        
                        // Check for aneuploidy
                        if (analysisData.TryGetValue("has_aneuploidy", out var aneuploidyObj))
                        {
                            var hasAneuploidy = Convert.ToBoolean(aneuploidyObj);
                            OnLogMessageAdded($"has_aneuploidy: {hasAneuploidy}");
                            if (hasAneuploidy)
                            {
                                OnLogMessageAdded($"-> ANEUPLOID (DEVIATION)");
                                return WellStatus.Deviation;
                            }
                        }
                    }
                }
                catch (Exception ex)
                {
                    OnLogMessageAdded($"Warning: Could not parse analysis_data for status determination: {ex.Message}");
                }
            }

            // Fallback to top-level flags if analysis_data absent
            if (result.TryGetValue("has_buffer_zone", out var tlBuffer))
            {
                var hasBuffer = Convert.ToBoolean(tlBuffer);
                OnLogMessageAdded($"(top-level) has_buffer_zone: {hasBuffer}");
                if (hasBuffer) return WellStatus.BufferZone;
            }
            if (result.TryGetValue("has_aneuploidy", out var tlAneu))
            {
                var hasAneu = Convert.ToBoolean(tlAneu);
                OnLogMessageAdded($"(top-level) has_aneuploidy: {hasAneu}");
                if (hasAneu) return WellStatus.Deviation;
            }
            
            // Default to normal (euploid) - matches macOS logic
            OnLogMessageAdded($"-> NORMAL (default)");
            return WellStatus.Normal;
        }

        private WellStatus ParseWellStatus(string status)
        {
            return status?.ToLowerInvariant() switch
            {
                "normal" => WellStatus.Normal,
                "deviation" => WellStatus.Deviation,
                "bufferzone" => WellStatus.BufferZone,
                "warning" => WellStatus.Warning,
                _ => WellStatus.Normal
            };
        }
        
        private int ConvertToInt(object? value)
        {
            if (value == null) return 0;
            
            if (value is int intValue) return intValue;
            if (value is long longValue) return (int)longValue;
            if (value is double doubleValue) return (int)doubleValue;
            if (value is float floatValue) return (int)floatValue;
            
            if (int.TryParse(value.ToString(), out int result))
                return result;
                
            return 0;
        }
        
        private object? GetPropertyValue(object obj, string propertyName)
        {
            if (obj == null) return null;
            
            try
            {
                var type = obj.GetType();
                var property = type.GetProperty(propertyName);
                return property?.GetValue(obj);
            }
            catch
            {
                return null;
            }
        }

        /// <summary>
        /// Process a single well with custom parameters (matches macOS functionality)
        /// </summary>
        public async Task<WellResult?> ProcessWellAsync(string csvFilePath, string outputFolder, Dictionary<string, object>? wellParameters = null, Dictionary<string, string>? sampleNames = null)
        {
            try
            {
                OnLogMessageAdded($"Processing single well: {Path.GetFileNameWithoutExtension(csvFilePath)}");
                
                // Save well parameters to temporary file if provided
                string? parameterFilePath = null;
                if (wellParameters != null && wellParameters.Count > 0)
                {
                    parameterFilePath = await SaveWellParametersToTempFile(wellParameters);
                    OnLogMessageAdded($"Using {wellParameters.Count} custom parameters for well processing");
                }

                var scriptPath = await CreateWellProcessingScript(csvFilePath, outputFolder, parameterFilePath, sampleNames);
                
                OnStatusChanged($"Processing well {Path.GetFileNameWithoutExtension(csvFilePath)}...");
                
                var result = await _pythonService.ExecutePythonScript(scriptPath);
                
                if (result.ExitCode == 0 && !string.IsNullOrEmpty(result.Output))
                {
                    var wellResult = ParseWellResult(result.Output, csvFilePath);
                    if (wellResult != null)
                    {
                        try
                        {
                            var allOverrides = ParametersService.GetAllWellParameters();
                            wellResult.IsEdited = allOverrides.ContainsKey(wellResult.WellId) && (allOverrides[wellResult.WellId]?.Count ?? 0) > 0;
                        }
                        catch { }
                    }
                    OnLogMessageAdded($"Successfully processed well {wellResult?.WellId}");
                    return wellResult;
                }
                else
                {
                    OnLogMessageAdded($"Failed to process well: {result.Error}");
                    return null;
                }
            }
            catch (Exception ex)
            {
                OnLogMessageAdded($"Error processing well: {ex.Message}");
                return null;
            }
        }

        private async Task<string> SaveWellParametersToTempFile(Dictionary<string, object> parameters)
        {
            var tempFile = Path.GetTempFileName();
            var json = JsonConvert.SerializeObject(parameters, Formatting.Indented);
            await File.WriteAllTextAsync(tempFile, json);
            return tempFile;
        }

        private async Task<string> CreateWellProcessingScript(string csvFilePath, string outputFolder, string? parameterFilePath, Dictionary<string, string>? sampleNames)
        {
            var scriptPath = Path.GetTempFileName() + ".py";
            var scriptLines = new List<string>();
            
            var pythonPath = _pythonService.PythonExecutablePath.Replace("\\", "/");
            var ddquintPath = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "Python").Replace("\\", "/");
            var escapedCsvPath = csvFilePath.Replace("'", "\\'").Replace("\\", "/");
            var escapedOutputFolder = outputFolder.Replace("'", "\\'").Replace("\\", "/");
            var escapedParamFile = parameterFilePath?.Replace("'", "\\'").Replace("\\", "/") ?? "";

            scriptLines.Add("#!/usr/bin/env python3");
            scriptLines.Add("import sys");
            scriptLines.Add("import os");
            scriptLines.Add("import json");
            scriptLines.Add($"sys.path.insert(0, '{ddquintPath}')");
            scriptLines.Add("");
            
            scriptLines.Add("try:");
            scriptLines.Add("    # Initialize config and load global parameters");
            scriptLines.Add("    from ddquint.config import Config");
            scriptLines.Add("    from ddquint.utils.parameter_editor import load_parameters_if_exist");
            scriptLines.Add("    from ddquint.core.file_processor import process_csv_file");
            scriptLines.Add("    ");
            scriptLines.Add("    config = Config.get_instance()");
            scriptLines.Add("    load_parameters_if_exist(Config)");
            scriptLines.Add("    ");
            scriptLines.Add("    # Load well-specific parameters if provided");
            if (!string.IsNullOrEmpty(parameterFilePath))
            {
                scriptLines.Add($"    if os.path.exists('{escapedParamFile}'):");
                scriptLines.Add($"        with open('{escapedParamFile}', 'r') as f:");
                scriptLines.Add("            well_params = json.load(f)");
                scriptLines.Add("        print(f'Loaded {{len(well_params)}} well-specific parameters')");
                scriptLines.Add("        config.set_well_context('current_well', well_params)");
                scriptLines.Add("    else:");
                scriptLines.Add("        config.clear_well_context()");
            }
            else
            {
                scriptLines.Add("    config.clear_well_context()");
            }
            
            scriptLines.Add("    config.finalize_colors()");
            scriptLines.Add("    ");
            
            // Add sample names if provided
            if (sampleNames != null && sampleNames.Count > 0)
            {
                var sampleNamesJson = JsonConvert.SerializeObject(sampleNames);
                scriptLines.Add($"    sample_names = {sampleNamesJson}");
            }
            else
            {
                scriptLines.Add("    sample_names = None");
            }
            
            scriptLines.Add($"    result = process_csv_file('{escapedCsvPath}', '{escapedOutputFolder}', sample_names, verbose=True)");
            scriptLines.Add("    ");
            scriptLines.Add("    # Output result as JSON for parsing");
            scriptLines.Add("    print('RESULT_JSON_START')");
            scriptLines.Add("    print(json.dumps(result))");
            scriptLines.Add("    print('RESULT_JSON_END')");
            scriptLines.Add("    ");
            scriptLines.Add("except Exception as e:");
            scriptLines.Add("    print(f'ERROR: {e}')");
            scriptLines.Add("    import traceback");
            scriptLines.Add("    traceback.print_exc()");

            await File.WriteAllLinesAsync(scriptPath, scriptLines);
            return scriptPath;
        }

        private WellResult? ParseWellResult(string output, string csvFilePath)
        {
            try
            {
                // Extract JSON result from output
                var startMarker = "RESULT_JSON_START";
                var endMarker = "RESULT_JSON_END";
                var startIndex = output.IndexOf(startMarker);
                var endIndex = output.IndexOf(endMarker);
                
                if (startIndex == -1 || endIndex == -1) return null;
                
                var jsonStart = startIndex + startMarker.Length;
                var jsonLength = endIndex - jsonStart;
                var jsonStr = output.Substring(jsonStart, jsonLength).Trim();
                
                var resultData = JsonConvert.DeserializeObject<dynamic>(jsonStr);
                if (resultData == null) return null;

                var wellResult = new WellResult
                {
                    WellId = resultData.well?.ToString() ?? Path.GetFileNameWithoutExtension(csvFilePath),
                    SampleName = resultData.sample_name?.ToString() ?? "",
                    Status = ParseWellStatus(resultData.status?.ToString()),
                    PlotImagePath = resultData.graph_path?.ToString(),
                    TotalDroplets = ConvertToInt(resultData.total_droplets),
                    UsableDroplets = ConvertToInt(resultData.usable_droplets),
                    NegativeDroplets = ConvertToInt(resultData.negative_droplets),
                    CopyNumbersDictionary = new Dictionary<string, double>()
                };

                // Parse copy numbers
                if (resultData.copy_numbers != null)
                {
                    foreach (var kvp in resultData.copy_numbers)
                    {
                        if (double.TryParse(kvp.Value?.ToString(), out double value))
                        {
                            wellResult.CopyNumbersDictionary[kvp.Name] = value;
                        }
                    }
                }

                return wellResult;
            }
            catch (Exception ex)
            {
                OnLogMessageAdded($"Failed to parse well result: {ex.Message}");
                return null;
            }
        }
    }
}
