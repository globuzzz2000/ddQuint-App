using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using ddQuint.Desktop.ViewModels;
using ddQuint.Desktop.Services;

namespace ddQuint.Desktop.Views
{
    public partial class GlobalParametersWindow : Window
    {
        private MainViewModel _mainViewModel;
        private Dictionary<string, object> _parameters = new Dictionary<string, object>();
        private Dictionary<string, Control> _parameterControls = new Dictionary<string, Control>();
        private bool _suppressMixingHandler = false; // prevent re-entrancy when reverting selection
        
        // Event for notifying when parameters are applied
        public event Action<Dictionary<string, object>>? ParametersApplied;

        // Helper method to format decimal values with invariant culture
        private string FormatValueForDisplay(object value)
        {
            if (value == null) return "";
            if (value is double dVal) return dVal.ToString(CultureInfo.InvariantCulture);
            if (value is float fVal) return fVal.ToString(CultureInfo.InvariantCulture);
            return value.ToString() ?? "";
        }
        
        public GlobalParametersWindow(MainViewModel mainViewModel)
        {
            InitializeComponent();
            _mainViewModel = mainViewModel;
            
            // Enable window dragging
            this.MouseLeftButtonDown += (sender, e) => this.DragMove();
        }

        private void Window_Loaded(object sender, RoutedEventArgs e)
        {
            LoadParameters();
            BuildParameterUI();
        }

        private void LoadParameters()
        {
            // Load parameters from persistent storage
            _parameters = ParametersService.LoadGlobalParameters();
            
            // Debug: Show what was loaded
            var appDataFolder = Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData);
            var ddquintFolder = Path.Combine(appDataFolder, "ddQuint");
            var parametersFile = Path.Combine(ddquintFolder, "parameters.json");
            var logFile = Path.Combine(ddquintFolder, "logs", "debug.log");
            
            var debugInfo = new List<string>
            {
                $"=== Parameter Loading Debug - {DateTime.Now:yyyy-MM-dd HH:mm:ss} ===",
                $"AppData folder: {appDataFolder}",
                $"ddQuint folder: {ddquintFolder}",
                $"Parameters file: {parametersFile}",
                $"AppData folder exists: {Directory.Exists(appDataFolder)}",
                $"ddQuint folder exists: {Directory.Exists(ddquintFolder)}",
                $"Parameters file exists: {File.Exists(parametersFile)}",
                $"Loaded {_parameters.Count} parameters"
            };
            
            if (_parameters.Count > 0)
            {
                debugInfo.Add($"All parameters:");
                
                // Show all parameters and values
                foreach (var kvp in _parameters)
                {
                    debugInfo.Add($"  {kvp.Key} = {kvp.Value}");
                }
            }
            
            // Also show the raw JSON content
            if (File.Exists(parametersFile))
            {
                try
                {
                    var jsonContent = File.ReadAllText(parametersFile);
                    debugInfo.Add("Raw JSON content:");
                    debugInfo.Add(jsonContent);
                }
                catch (Exception ex)
                {
                    debugInfo.Add($"Could not read JSON content: {ex.Message}");
                }
            }
            
            debugInfo.Add("=====================================");
            debugInfo.Add("");
            
            // Write to debug output
            foreach (var line in debugInfo)
            {
                System.Diagnostics.Debug.WriteLine(line);
            }
            
            // Try to write to log file for persistent debugging
            try
            {
                var logsFolder = Path.Combine(ddquintFolder, "logs");
                if (!Directory.Exists(logsFolder))
                {
                    Directory.CreateDirectory(logsFolder);
                    debugInfo.Insert(-2, $"Created logs folder: {logsFolder}");
                }
                
                File.AppendAllLines(logFile, debugInfo);
                System.Diagnostics.Debug.WriteLine($"Debug log written to: {logFile}");
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"Failed to write debug log: {ex.Message}");
                System.Diagnostics.Debug.WriteLine($"Exception: {ex}");
            }
        }

        private void BuildParameterUI()
        {
            // Clear all panels
            HDBSCANPanel.Children.Clear();
            CentroidsPanel.Children.Clear();
            CopyNumberPanel.Children.Clear();
            VisualizationPanel.Children.Clear();
            GeneralPanel.Children.Clear();
            _parameterControls.Clear();

            // Build each tab with proper structure
            BuildHDBSCANTab();
            BuildCentroidsTab();
            BuildCopyNumberTab();
            BuildVisualizationTab();
            BuildGeneralTab();
        }

        private void BuildHDBSCANTab()
        {
            // Title and instructions
            AddTitleAndDescription(HDBSCANPanel, "HDBSCAN Clustering Parameters", 
                                 "Configure clustering parameters for droplet classification.");

            // Basic parameters
            var basicParams = new List<string> 
            {
                "HDBSCAN_MIN_CLUSTER_SIZE", "HDBSCAN_MIN_SAMPLES", "HDBSCAN_EPSILON", "MIN_POINTS_FOR_CLUSTERING"
            };
            
            foreach (var param in basicParams)
            {
                if (_parameters.ContainsKey(param))
                {
                    var control = CreateParameterControl(param, _parameters[param]);
                    HDBSCANPanel.Children.Add(control);
                    StoreParameterControl(param, control);
                }
            }

            // Advanced Settings section
            AddSectionHeader(HDBSCANPanel, "Advanced Settings");
            var advancedParams = new List<string> { "HDBSCAN_METRIC", "HDBSCAN_CLUSTER_SELECTION_METHOD" };
            
            foreach (var param in advancedParams)
            {
                if (_parameters.ContainsKey(param))
                {
                    var control = CreateParameterControl(param, _parameters[param]);
                    HDBSCANPanel.Children.Add(control);
                    StoreParameterControl(param, control);
                }
            }
        }

        private void BuildCentroidsTab()
        {
            AddTitleAndDescription(CentroidsPanel, "Expected Centroids Configuration", 
                                 "Define expected centroid positions for targets. Format: HEX, FAM");

            // Target tolerance first
            if (_parameters.ContainsKey("BASE_TARGET_TOLERANCE"))
            {
                var control = CreateParameterControl("BASE_TARGET_TOLERANCE", _parameters["BASE_TARGET_TOLERANCE"]);
                CentroidsPanel.Children.Add(control);
                StoreParameterControl("BASE_TARGET_TOLERANCE", control);
            }

            // Number of targets
            if (_parameters.ContainsKey("CHROMOSOME_COUNT"))
            {
                var control = CreateParameterControl("CHROMOSOME_COUNT", _parameters["CHROMOSOME_COUNT"]);
                CentroidsPanel.Children.Add(control);
                StoreParameterControl("CHROMOSOME_COUNT", control);
            }

            // Amplitude Non-linearity (shown only when fluorophore mixing is disabled; matches macOS placement)
            if (_parameters.ContainsKey("AMPLITUDE_NON_LINEARITY"))
            {
                var amplitudeControl = CreateParameterControl("AMPLITUDE_NON_LINEARITY", _parameters["AMPLITUDE_NON_LINEARITY"]);
                CentroidsPanel.Children.Add(amplitudeControl);
                StoreParameterControl("AMPLITUDE_NON_LINEARITY", amplitudeControl);
                UpdateAmplitudeNonLinearityVisibility();
            }

            // Expected Centroid Position section
            AddSectionHeader(CentroidsPanel, "Expected Centroid Position");
            
            // Extract centroids from structured EXPECTED_CENTROIDS object (support in-memory dict)
            if (_parameters.ContainsKey("EXPECTED_CENTROIDS"))
            {
                try 
                {
                    Dictionary<string, object>? centroidsObj = null;
                    if (_parameters["EXPECTED_CENTROIDS"] is Dictionary<string, object> dict)
                    {
                        centroidsObj = dict;
                    }
                    else
                    {
                        var centroidsJson = _parameters["EXPECTED_CENTROIDS"]?.ToString();
                        if (!string.IsNullOrWhiteSpace(centroidsJson) && centroidsJson.TrimStart().StartsWith("{"))
                        {
                            centroidsObj = System.Text.Json.JsonSerializer.Deserialize<Dictionary<string, object>>(centroidsJson);
                        }
                    }

                    if (centroidsObj != null)
                    {
                        // Add Negative control first
                        if (centroidsObj.TryGetValue("Negative", out var negVal))
                        {
                            var negativeCoords = FormatCoords(negVal);
                            var control = CreateParameterControl("EXPECTED_CENTROIDS_Negative", negativeCoords);
                            CentroidsPanel.Children.Add(control);
                            StoreParameterControl("EXPECTED_CENTROIDS_Negative", control);
                        }
                        
                        // Add chromosome targets dynamically based on chromosome count
                        var chromosomeCount = _parameters.ContainsKey("CHROMOSOME_COUNT") ? 
                                            Convert.ToInt32(_parameters["CHROMOSOME_COUNT"]) : 4;
                        
                        for (int i = 1; i <= chromosomeCount; i++)
                        {
                            var chromKey = $"Chrom{i}";
                            if (centroidsObj.TryGetValue(chromKey, out var cVal))
                            {
                                var chromCoords = FormatCoords(cVal);
                                var param = $"EXPECTED_CENTROIDS_Chrom{i}";
                                var control = CreateParameterControl(param, chromCoords);
                                CentroidsPanel.Children.Add(control);
                                StoreParameterControl(param, control);
                            }
                        }
                        return;
                    }
                }
                catch (Exception ex)
                {
                    System.Diagnostics.Debug.WriteLine($"Error parsing EXPECTED_CENTROIDS: {ex.Message}");
                }
            }
            else
            {
                // Fallback to old flattened format if structured version doesn't exist
                if (_parameters.ContainsKey("EXPECTED_CENTROIDS_Negative"))
                {
                    var control = CreateParameterControl("EXPECTED_CENTROIDS_Negative", _parameters["EXPECTED_CENTROIDS_Negative"]);
                    CentroidsPanel.Children.Add(control);
                    StoreParameterControl("EXPECTED_CENTROIDS_Negative", control);
                }
                
                var chromosomeCount = _parameters.ContainsKey("CHROMOSOME_COUNT") ? 
                                    Convert.ToInt32(_parameters["CHROMOSOME_COUNT"]) : 4;
                                    
                for (int i = 1; i <= chromosomeCount; i++)
                {
                    var param = $"EXPECTED_CENTROIDS_Chrom{i}";
                    if (_parameters.ContainsKey(param))
                    {
                        var control = CreateParameterControl(param, _parameters[param]);
                        CentroidsPanel.Children.Add(control);
                        StoreParameterControl(param, control);
                    }
                }
            }
        }

        private void BuildCopyNumberTab()
        {
            AddTitleAndDescription(CopyNumberPanel, "Copy Number Analysis Settings", 
                                 "Configure copy number analysis and classification parameters.");

            // General Parameters (exactly as in macOS)
            var generalParams = new List<string> 
            {
                "MIN_USABLE_DROPLETS", "COPY_NUMBER_MEDIAN_DEVIATION_THRESHOLD", "COPY_NUMBER_MULTIPLIER"
            };
            
            foreach (var param in generalParams)
            {
                if (_parameters.ContainsKey(param))
                {
                    var control = CreateParameterControl(param, _parameters[param]);
                    CopyNumberPanel.Children.Add(control);
                    StoreParameterControl(param, control);
                }
            }

            // Add extra spacing before aneuploidy parameters (matching macOS)
            var spacer = new Border { Height = 20 };
            CopyNumberPanel.Children.Add(spacer);
            
            // Aneuploidy parameters (no subheading, starts directly)
            var aneuploidyParams = new List<string> 
            {
                "TOLERANCE_MULTIPLIER", "LOWER_DEVIATION_TARGET", "UPPER_DEVIATION_TARGET"
            };
            
            foreach (var param in aneuploidyParams)
            {
                if (_parameters.ContainsKey(param))
                {
                    var control = CreateParameterControl(param, _parameters[param]);
                    CopyNumberPanel.Children.Add(control);
                    StoreParameterControl(param, control);
                }
            }

            // Expected Copy Numbers section
            AddSectionHeader(CopyNumberPanel, "Expected Copy Numbers by Chromosome");
            
            // Seed flattened values from structured objects if present
            try
            {
                if (_parameters.TryGetValue("COPY_NUMBER_SPEC", out var specVal))
                {
                    foreach (var entry in EnumerateCopyNumberSpec(specVal))
                    {
                        if (entry.TryGetValue("chrom", out var chromObj))
                        {
                            var chrom = chromObj?.ToString() ?? string.Empty;
                            if (chrom.StartsWith("Chrom"))
                            {
                                var idx = chrom.Substring(5);
                                var cnKey = $"EXPECTED_COPY_NUMBERS_Chrom{idx}";
                                var sdKey = $"EXPECTED_STANDARD_DEVIATION_Chrom{idx}";
                                if (entry.TryGetValue("expected", out var expObj)) _parameters[cnKey] = expObj;
                                if (entry.TryGetValue("std_dev", out var sdObj)) _parameters[sdKey] = sdObj;
                            }
                        }
                    }
                }
                else
                {
                    if (_parameters.TryGetValue("EXPECTED_COPY_NUMBERS", out var ecnObj) && ecnObj is Dictionary<string, object> ecn)
                    {
                        foreach (var kv in ecn)
                        {
                            if (kv.Key.StartsWith("Chrom"))
                            {
                                var idx = kv.Key.Substring(5);
                                _parameters[$"EXPECTED_COPY_NUMBERS_Chrom{idx}"] = kv.Value;
                            }
                        }
                    }
                    if (_parameters.TryGetValue("EXPECTED_STANDARD_DEVIATION", out var esdObj) && esdObj is Dictionary<string, object> esd)
                    {
                        foreach (var kv in esd)
                        {
                            if (kv.Key.StartsWith("Chrom"))
                            {
                                var idx = kv.Key.Substring(5);
                                _parameters[$"EXPECTED_STANDARD_DEVIATION_Chrom{idx}"] = kv.Value;
                            }
                        }
                    }
                }
            }
            catch { }
            
            // Add dynamic copy number rows
            AddDynamicCopyNumberRows();
        }

        private static IEnumerable<Dictionary<string, object>> EnumerateCopyNumberSpec(object? specVal)
        {
            if (specVal is Dictionary<string, object>[] strongArray)
            {
                foreach (var d in strongArray) yield return d;
                yield break;
            }
            if (specVal is object[] objArray)
            {
                foreach (var o in objArray)
                {
                    if (o is Dictionary<string, object> d) yield return d;
                }
                yield break;
            }
            if (specVal is System.Collections.IEnumerable any)
            {
                foreach (var o in any)
                {
                    if (o is Dictionary<string, object> d) yield return d;
                }
            }
        }

        private void BuildVisualizationTab()
        {
            AddTitleAndDescription(VisualizationPanel, "Visualization Settings", 
                                 "Configure plot axis limits, grid settings, and output resolution.");

            // Plot Axis Limits section
            AddSectionHeader(VisualizationPanel, "Plot Axis Limits");
            var axisParams = new List<string> { "X_AXIS_MIN", "X_AXIS_MAX", "Y_AXIS_MIN", "Y_AXIS_MAX", "X_GRID_INTERVAL", "Y_GRID_INTERVAL" };
            
            foreach (var param in axisParams)
            {
                if (_parameters.ContainsKey(param))
                {
                    var control = CreateParameterControl(param, _parameters[param]);
                    VisualizationPanel.Children.Add(control);
                    StoreParameterControl(param, control);
                }
            }

            // Resolution section
            AddSectionHeader(VisualizationPanel, "Resolution");
            var dpiParams = new List<string> { "INDIVIDUAL_PLOT_DPI" };
            
            foreach (var param in dpiParams)
            {
                if (_parameters.ContainsKey(param))
                {
                    var control = CreateParameterControl(param, _parameters[param]);
                    VisualizationPanel.Children.Add(control);
                    StoreParameterControl(param, control);
                }
            }
        }

        private void BuildGeneralTab()
        {
            AddTitleAndDescription(GeneralPanel, "General Settings", 
                                 "Configure general application settings and analysis behavior.");

            // Analysis Settings section
            AddSectionHeader(GeneralPanel, "Analysis Settings");
            
            var analysisParams = new List<string> 
            {
                "ENABLE_FLUOROPHORE_MIXING", "ENABLE_COPY_NUMBER_ANALYSIS", "CLASSIFY_CNV_DEVIATIONS"
            };
            
            foreach (var param in analysisParams)
            {
                if (_parameters.ContainsKey(param))
                {
                    var control = CreateParameterControl(param, _parameters[param]);
                    GeneralPanel.Children.Add(control);
                    StoreParameterControl(param, control);
                }
            }

            // Target Names section
            AddSectionHeader(GeneralPanel, "Target Names");
            
            // Extract target names from structured TARGET_NAMES object
            var chromosomeCount = _parameters.ContainsKey("CHROMOSOME_COUNT") ? 
                                Convert.ToInt32(_parameters["CHROMOSOME_COUNT"]) : 5;
            
            if (_parameters.ContainsKey("TARGET_NAMES"))
            {
                try 
                {
                    Dictionary<string, object>? tn = null;
                    if (_parameters["TARGET_NAMES"] is Dictionary<string, object> objDict)
                    {
                        tn = objDict;
                    }
                    else if (_parameters["TARGET_NAMES"] is Dictionary<string, string> strDict)
                    {
                        tn = strDict.ToDictionary(k => k.Key, v => (object)v.Value);
                    }
                    else
                    {
                        var targetNamesJson = _parameters["TARGET_NAMES"]?.ToString();
                        if (!string.IsNullOrWhiteSpace(targetNamesJson) && targetNamesJson.TrimStart().StartsWith("{"))
                        {
                            tn = System.Text.Json.JsonSerializer.Deserialize<Dictionary<string, object>>(targetNamesJson);
                        }
                    }

                    if (tn != null)
                    {
                        for (int i = 1; i <= chromosomeCount; i++)
                        {
                            var targetKey = $"Target{i}";
                            var targetNameParam = $"TARGET_NAME_{i}";
                            var targetName = tn.ContainsKey(targetKey) ? tn[targetKey]?.ToString() ?? $"Target {i}" : $"Target {i}";
                            var control = CreateParameterControl(targetNameParam, targetName);
                            GeneralPanel.Children.Add(control);
                            StoreParameterControl(targetNameParam, control);
                        }
                        return;
                    }
                }
                catch (Exception ex)
                {
                    System.Diagnostics.Debug.WriteLine($"Error parsing TARGET_NAMES: {ex.Message}");
                }
            }
            else
            {
                // Fallback to individual target name parameters if structured version doesn't exist
                for (int i = 1; i <= chromosomeCount; i++)
                {
                    var targetNameParam = $"TARGET_NAME_{i}";
                    // Add default target name if not present
                    if (!_parameters.ContainsKey(targetNameParam))
                    {
                        _parameters[targetNameParam] = $"Target {i}";
                    }
                    
                    var control = CreateParameterControl(targetNameParam, _parameters[targetNameParam]);
                    GeneralPanel.Children.Add(control);
                    StoreParameterControl(targetNameParam, control);
                }
            }
        }

        private void AddTitleAndDescription(StackPanel panel, string title, string description)
        {
            // Title
            var titleBlock = new TextBlock
            {
                Text = title,
                FontSize = 16,
                FontWeight = FontWeights.Bold,
                Foreground = Brushes.White,
                Margin = new Thickness(0, 0, 0, 10)
            };
            panel.Children.Add(titleBlock);

            // Description
            var descBlock = new TextBlock
            {
                Text = description,
                FontSize = 12,
                Foreground = Brushes.Gray,
                Margin = new Thickness(20, 0, 0, 20),
                TextWrapping = TextWrapping.Wrap
            };
            panel.Children.Add(descBlock);
        }

        private void AddSectionHeader(StackPanel panel, string header)
        {
            var headerBlock = new TextBlock
            {
                Text = header,
                FontSize = 14,
                FontWeight = FontWeights.Bold,
                Foreground = Brushes.White,
                Margin = new Thickness(0, 20, 0, 10)
            };
            panel.Children.Add(headerBlock);
        }

        private static string FormatCoords(object? coords)
        {
            try
            {
                if (coords == null) return string.Empty;
                if (coords is double[] dd)
                {
                    return string.Join(",", dd.Select(d => d.ToString(System.Globalization.CultureInfo.InvariantCulture)));
                }
                if (coords is float[] ff)
                {
                    return string.Join(",", ff.Select(d => d.ToString(System.Globalization.CultureInfo.InvariantCulture)));
                }
                if (coords is object[] oo)
                {
                    return string.Join(",", oo.Select(o => Convert.ToDouble(o, System.Globalization.CultureInfo.InvariantCulture).ToString(System.Globalization.CultureInfo.InvariantCulture)));
                }
                if (coords is System.Collections.IEnumerable en && coords is not string)
                {
                    var parts = new System.Collections.Generic.List<string>();
                    foreach (var item in en)
                    {
                        if (item == null) continue;
                        if (item is double d)
                            parts.Add(d.ToString(System.Globalization.CultureInfo.InvariantCulture));
                        else if (item is float f)
                            parts.Add(f.ToString(System.Globalization.CultureInfo.InvariantCulture));
                        else
                            parts.Add(Convert.ToDouble(item, System.Globalization.CultureInfo.InvariantCulture).ToString(System.Globalization.CultureInfo.InvariantCulture));
                    }
                    return string.Join(",", parts);
                }
                var s = coords.ToString() ?? string.Empty;
                return s;
            }
            catch
            {
                return coords?.ToString() ?? string.Empty;
            }
        }

        private void AddDynamicCopyNumberRows()
        {
            var chromosomeCount = _parameters.ContainsKey("CHROMOSOME_COUNT") ? 
                                Convert.ToInt32(_parameters["CHROMOSOME_COUNT"]) : 5;
                                
            if (chromosomeCount <= 5)
            {
                // Simple layout for 5 or fewer chromosomes
                for (int i = 1; i <= chromosomeCount; i++)
                {
                    var copyNumParam = $"EXPECTED_COPY_NUMBERS_Chrom{i}";
                    var stdDevParam = $"EXPECTED_STANDARD_DEVIATION_Chrom{i}";
                    
                    // Add default values if not present
                    if (!_parameters.ContainsKey(copyNumParam))
                    {
                        _parameters[copyNumParam] = "1.0";
                    }
                    if (!_parameters.ContainsKey(stdDevParam))
                    {
                        _parameters[stdDevParam] = "0.1";
                    }
                    
                    // Create a two-column row for copy number + standard deviation
                    var rowGrid = CreateTwoColumnParameterRow(copyNumParam, _parameters[copyNumParam], 
                                                             stdDevParam, _parameters[stdDevParam]);
                    CopyNumberPanel.Children.Add(rowGrid);
                }
            }
            else
            {
                // Multi-column layout for more than 5 chromosomes
                AddMultiColumnCopyNumberRows(chromosomeCount);
            }
        }

        private void AddMultiColumnCopyNumberRows(int chromosomeCount)
        {
            const int chromsPerColumn = 5;
            var totalCnColumns = (chromosomeCount + chromsPerColumn - 1) / chromsPerColumn;
            
            // Create a master grid that can accommodate multiple columns
            var masterGrid = new Grid();
            masterGrid.Margin = new Thickness(0, 6, 0, 0);
            
            // Define columns with improved spacing:
            // CN1, CN1 textbox, (small gap), CN2, CN2 textbox, (big gap), SD1 label, SD1 textbox, (small gap), SD2 label, SD2 textbox, (stretch)
            masterGrid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(80) });  // 0: CN1 label
            masterGrid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(80) });  // 1: CN1 textbox
            if (totalCnColumns > 1)
            {
                masterGrid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(12) }); // 2: small gap between CN columns
                masterGrid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(80) }); // 3: CN2 label
                masterGrid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(80) }); // 4: CN2 textbox
            }
            masterGrid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(40) });  // 5 or after CN2: big gap between CN and SD
            masterGrid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(55) });  // SD1 label
            masterGrid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(80) });  // SD1 textbox
            if (totalCnColumns > 1)
            {
                masterGrid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(12) });  // small gap between SD columns
                masterGrid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(55) });  // SD2 label
                masterGrid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(80) });  // SD2 textbox
            }
            masterGrid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) }); // Remaining space
            
            // Add rows (maximum 5 rows for 5 chromosomes per column)
            for (int row = 0; row < chromsPerColumn; row++)
            {
                masterGrid.RowDefinitions.Add(new RowDefinition { Height = new GridLength(30) });
            }
            
            // Add chromosome controls
            for (int i = 1; i <= chromosomeCount; i++)
            {
                var copyNumParam = $"EXPECTED_COPY_NUMBERS_Chrom{i}";
                var stdDevParam = $"EXPECTED_STANDARD_DEVIATION_Chrom{i}";
                
                // Add default values if not present
                if (!_parameters.ContainsKey(copyNumParam))
                {
                    _parameters[copyNumParam] = "1.0";
                }
                if (!_parameters.ContainsKey(stdDevParam))
                {
                    _parameters[stdDevParam] = "0.1";
                }
                
                // Calculate position
                var cnColumnIndex = (i - 1) / chromsPerColumn;  // 0 for first column, 1 for second
                var positionInColumn = (i - 1) % chromsPerColumn;
                
                // Copy Number controls
                var cnLabel = new TextBlock
                {
                    Text = $"Target {i}:",
                    VerticalAlignment = VerticalAlignment.Center,
                    Foreground = Brushes.White,
                    FontSize = 11
                };
                Grid.SetRow(cnLabel, positionInColumn);
                Grid.SetColumn(cnLabel, cnColumnIndex == 0 ? 0 : 3); // CN1 at col 0, CN2 at col 3
                masterGrid.Children.Add(cnLabel);
                var cnKey = $"EXPECTED_COPY_NUMBERS_Chrom{i}";
                var cnTip = ParameterTooltips.Get(cnKey ?? string.Empty);
                if (!string.IsNullOrWhiteSpace(cnTip)) cnLabel.ToolTip = cnTip;
                
                var cnTextBox = new TextBox
                {
                    Text = FormatValueForDisplay(_parameters[copyNumParam]),
                    Style = (Style)Application.Current.Resources["DarkParameterTextBox"],
                    Width = 80,
                    HorizontalAlignment = HorizontalAlignment.Left,
                    VerticalAlignment = VerticalAlignment.Center
                };
                Grid.SetRow(cnTextBox, positionInColumn);
                Grid.SetColumn(cnTextBox, cnColumnIndex == 0 ? 1 : 4); // CN1 textbox at col 1, CN2 at col 4
                masterGrid.Children.Add(cnTextBox);
                _parameterControls[copyNumParam] = cnTextBox;
                if (!string.IsNullOrWhiteSpace(cnTip)) cnTextBox.ToolTip = cnTip;
                
                // Standard Deviation controls - positioned after CN columns + gap
                // With this layout SD1 label starts at col 6
                var sdLabelColBase = 6;
                var sdLabel = new TextBlock
                {
                    Text = $"SD {i}:",
                    VerticalAlignment = VerticalAlignment.Center,
                    Foreground = Brushes.White,
                    FontSize = 11
                };
                Grid.SetRow(sdLabel, positionInColumn);
                Grid.SetColumn(sdLabel, cnColumnIndex == 0 ? sdLabelColBase : sdLabelColBase + 3);
                masterGrid.Children.Add(sdLabel);
                var sdKey = $"EXPECTED_STANDARD_DEVIATION_Chrom{i}";
                var sdTip = ParameterTooltips.Get(sdKey ?? string.Empty);
                if (!string.IsNullOrWhiteSpace(sdTip)) sdLabel.ToolTip = sdTip;
                
                var sdTextBox = new TextBox
                {
                    Text = FormatValueForDisplay(_parameters[stdDevParam]),
                    Style = (Style)Application.Current.Resources["DarkParameterTextBox"],
                    Width = 80,
                    HorizontalAlignment = HorizontalAlignment.Left,
                    VerticalAlignment = VerticalAlignment.Center
                };
                Grid.SetRow(sdTextBox, positionInColumn);
                Grid.SetColumn(sdTextBox, cnColumnIndex == 0 ? sdLabelColBase + 1 : sdLabelColBase + 4);
                masterGrid.Children.Add(sdTextBox);
                _parameterControls[stdDevParam] = sdTextBox;
                if (!string.IsNullOrWhiteSpace(sdTip)) sdTextBox.ToolTip = sdTip;
            }
            
            CopyNumberPanel.Children.Add(masterGrid);
        }

        private Grid CreateTwoColumnParameterRow(string leftKey, object leftValue, string rightKey, object rightValue)
        {
            var rowGrid = new Grid();
            rowGrid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(100) }); // Left label  
            rowGrid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(80) });  // Left textbox
            rowGrid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(55) });  // Right label (matching macOS SD width)
            rowGrid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(80) });  // Right textbox
            rowGrid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) }); // Remaining space
            rowGrid.Margin = new Thickness(0, 6, 0, 0);
            rowGrid.Height = 24;

            // Left parameter (copy number)
            var leftLabel = new TextBlock
            {
                Text = GetDisplayName(leftKey?.ToString() ?? ""),
                VerticalAlignment = VerticalAlignment.Center,
                Foreground = Brushes.White,
                FontSize = 11
            };
            Grid.SetColumn(leftLabel, 0);
            rowGrid.Children.Add(leftLabel);
            var leftTip = ParameterTooltips.Get(leftKey ?? string.Empty);
            if (!string.IsNullOrWhiteSpace(leftTip)) leftLabel.ToolTip = leftTip;

            var leftTextBox = new TextBox
            {
                Text = FormatValueForDisplay(leftValue),
                Style = (Style)Application.Current.Resources["DarkParameterTextBox"],
                Width = 80,
                HorizontalAlignment = HorizontalAlignment.Left,
                VerticalAlignment = VerticalAlignment.Center
            };
            Grid.SetColumn(leftTextBox, 1);
            rowGrid.Children.Add(leftTextBox);
            if (leftKey != null) _parameterControls[leftKey] = leftTextBox;
            if (!string.IsNullOrWhiteSpace(leftTip)) leftTextBox.ToolTip = leftTip;

            // Right parameter (standard deviation)
            var rightLabel = new TextBlock
            {
                Text = GetDisplayName(rightKey?.ToString() ?? ""),
                VerticalAlignment = VerticalAlignment.Center,
                Foreground = Brushes.White,
                FontSize = 11,
                Margin = new Thickness(12, 0, 0, 0)
            };
            Grid.SetColumn(rightLabel, 2);
            rowGrid.Children.Add(rightLabel);
            var rightTip = ParameterTooltips.Get(rightKey ?? string.Empty);
            if (!string.IsNullOrWhiteSpace(rightTip)) rightLabel.ToolTip = rightTip;

            var rightTextBox = new TextBox
            {
                Text = FormatValueForDisplay(rightValue),
                Style = (Style)Application.Current.Resources["DarkParameterTextBox"],
                Width = 80,
                HorizontalAlignment = HorizontalAlignment.Left,
                VerticalAlignment = VerticalAlignment.Center
            };
            Grid.SetColumn(rightTextBox, 3);
            rowGrid.Children.Add(rightTextBox);
            if (rightKey != null) _parameterControls[rightKey] = rightTextBox;
            if (!string.IsNullOrWhiteSpace(rightTip)) rightTextBox.ToolTip = rightTip;

            return rowGrid;
        }

        private void StoreParameterControl(string key, Grid controlGrid)
        {
            if (controlGrid.Children.Count > 1 && controlGrid.Children[1] is Control inputControl)
            {
                _parameterControls[key] = inputControl;
            }
        }

        private void ChromosomeCountChanged(object sender, SelectionChangedEventArgs e)
        {
            if (sender is ComboBox comboBox && comboBox.SelectedItem != null)
            {
                if (int.TryParse(comboBox.SelectedItem.ToString(), out int newCount))
                {
                    UpdateCentroidsForTargetCount(newCount);
                }
            }
        }

        private void UpdateCentroidsForTargetCount(int targetCount)
        {
            // Preserve existing target values when changing count
            var oldCount = _parameters.ContainsKey("CHROMOSOME_COUNT")
                ? Convert.ToInt32(_parameters["CHROMOSOME_COUNT"]) : 0;
            _parameters["CHROMOSOME_COUNT"] = targetCount;

            // Remove entries only beyond new count
            for (int i = targetCount + 1; i <= Math.Max(oldCount, targetCount) + 8; i++)
            {
                var removeKeys = new[]
                {
                    $"EXPECTED_CENTROIDS_Chrom{i}",
                    $"TARGET_NAME_{i}",
                    $"EXPECTED_COPY_NUMBERS_Chrom{i}",
                    $"EXPECTED_STANDARD_DEVIATION_Chrom{i}"
                };
                foreach (var key in removeKeys)
                {
                    if (_parameters.Remove(key) && _parameterControls.ContainsKey(key))
                    {
                        _parameterControls.Remove(key);
                    }
                }
            }

            // Ensure defaults exist for all targets up to targetCount (preserve existing)
            for (int i = 1; i <= targetCount; i++)
            {
                var centroidKey = $"EXPECTED_CENTROIDS_Chrom{i}";
                if (!_parameters.ContainsKey(centroidKey))
                {
                    // Try structured EXPECTED_CENTROIDS first
                    if (_parameters.TryGetValue("EXPECTED_CENTROIDS", out var centroidsObj))
                    {
                        try
                        {
                            Dictionary<string, object>? dict = centroidsObj as Dictionary<string, object>;
                            if (dict == null)
                            {
                                var json = centroidsObj?.ToString();
                                if (!string.IsNullOrWhiteSpace(json) && json!.TrimStart().StartsWith("{"))
                                    dict = System.Text.Json.JsonSerializer.Deserialize<Dictionary<string, object>>(json);
                            }
                            if (dict != null && dict.TryGetValue($"Chrom{i}", out var v))
                            {
                                _parameters[centroidKey] = FormatCoords(v);
                            }
                        }
                        catch { }
                    }
                    if (!_parameters.ContainsKey(centroidKey))
                        _parameters[centroidKey] = $"{1500 + i * 500},{2000 + i * 300}";
                }

                var targetNameKey = $"TARGET_NAME_{i}";
                if (!_parameters.ContainsKey(targetNameKey))
                {
                    // Try structured TARGET_NAMES
                    if (_parameters.TryGetValue("TARGET_NAMES", out var tnObj))
                    {
                        try
                        {
                            Dictionary<string, object>? dict = tnObj as Dictionary<string, object>;
                            if (dict == null)
                            {
                                var json = tnObj?.ToString();
                                if (!string.IsNullOrWhiteSpace(json) && json!.TrimStart().StartsWith("{"))
                                    dict = System.Text.Json.JsonSerializer.Deserialize<Dictionary<string, object>>(json);
                            }
                            if (dict != null && dict.TryGetValue($"Target{i}", out var v))
                                _parameters[targetNameKey] = v?.ToString() ?? $"Target {i}";
                        }
                        catch { }
                    }
                    if (!_parameters.ContainsKey(targetNameKey))
                        _parameters[targetNameKey] = $"Target {i}";
                }

                var copyNumKey = $"EXPECTED_COPY_NUMBERS_Chrom{i}";
                if (!_parameters.ContainsKey(copyNumKey))
                {
                    // Try COPY_NUMBER_SPEC or structured EXPECTED_COPY_NUMBERS
                    if (_parameters.TryGetValue("COPY_NUMBER_SPEC", out var specObj) && specObj is Dictionary<string, object>[] specArray)
                    {
                        var entry = specArray.FirstOrDefault(e => e.TryGetValue("chrom", out var c) && (c?.ToString() == $"Chrom{i}"));
                        if (entry != null && entry.TryGetValue("expected", out var expVal))
                            _parameters[copyNumKey] = FormatValueForDisplay(expVal);
                    }
                    if (!_parameters.ContainsKey(copyNumKey) && _parameters.TryGetValue("EXPECTED_COPY_NUMBERS", out var ecnObj) && ecnObj is Dictionary<string, object> ecn)
                    {
                        if (ecn.TryGetValue($"Chrom{i}", out var v)) _parameters[copyNumKey] = FormatValueForDisplay(v);
                    }
                    if (!_parameters.ContainsKey(copyNumKey)) _parameters[copyNumKey] = "1.0";
                }

                var stdDevKey = $"EXPECTED_STANDARD_DEVIATION_Chrom{i}";
                if (!_parameters.ContainsKey(stdDevKey))
                {
                    if (_parameters.TryGetValue("COPY_NUMBER_SPEC", out var specObj2) && specObj2 is Dictionary<string, object>[] specArray2)
                    {
                        var entry = specArray2.FirstOrDefault(e => e.TryGetValue("chrom", out var c) && (c?.ToString() == $"Chrom{i}"));
                        if (entry != null && entry.TryGetValue("std_dev", out var sdVal))
                            _parameters[stdDevKey] = FormatValueForDisplay(sdVal);
                    }
                    if (!_parameters.ContainsKey(stdDevKey) && _parameters.TryGetValue("EXPECTED_STANDARD_DEVIATION", out var esdObj) && esdObj is Dictionary<string, object> esd)
                    {
                        if (esd.TryGetValue($"Chrom{i}", out var v)) _parameters[stdDevKey] = FormatValueForDisplay(v);
                    }
                    if (!_parameters.ContainsKey(stdDevKey)) _parameters[stdDevKey] = "0.1";
                }
            }

            UpdateDynamicCentroidsSection();
            UpdateDynamicCopyNumberSection();
            UpdateDynamicTargetNamesSection();
        }

        private void UpdateDynamicCentroidsSection()
        {
            // Find the header "Expected Centroid Position" and remove all children after it
            int headerIndex = -1;
            for (int i = 0; i < CentroidsPanel.Children.Count; i++)
            {
                if (CentroidsPanel.Children[i] is TextBlock tb && tb.Text == "Expected Centroid Position")
                {
                    headerIndex = i;
                    break;
                }
            }

            if (headerIndex >= 0)
            {
                // Remove all controls after the header
                for (int i = CentroidsPanel.Children.Count - 1; i > headerIndex; i--)
                {
                    CentroidsPanel.Children.RemoveAt(i);
                }

                // Ensure Negative is present in parameter map
                if (!_parameters.ContainsKey("EXPECTED_CENTROIDS_Negative"))
                {
                    _parameters["EXPECTED_CENTROIDS_Negative"] = "1000,900"; // macOS-aligned default
                }

                // Add Negative control
                if (_parameters.ContainsKey("EXPECTED_CENTROIDS_Negative"))
                {
                    var control = CreateParameterControl("EXPECTED_CENTROIDS_Negative", _parameters["EXPECTED_CENTROIDS_Negative"]);
                    CentroidsPanel.Children.Add(control);
                    StoreParameterControl("EXPECTED_CENTROIDS_Negative", control);
                }
                
                // Add chromosome targets
                var chromosomeCount = _parameters.ContainsKey("CHROMOSOME_COUNT") ? 
                                    Convert.ToInt32(_parameters["CHROMOSOME_COUNT"]) : 5;
                                    
                for (int i = 1; i <= chromosomeCount; i++)
                {
                    var param = $"EXPECTED_CENTROIDS_Chrom{i}";
                    if (_parameters.ContainsKey(param))
                    {
                        var control = CreateParameterControl(param, _parameters[param]);
                        CentroidsPanel.Children.Add(control);
                        StoreParameterControl(param, control);
                    }
                }
            }
        }

        private void UpdateDynamicCopyNumberSection()
        {
            // Find the header "Expected Copy Numbers by Chromosome" and remove all children after it
            int headerIndex = -1;
            for (int i = 0; i < CopyNumberPanel.Children.Count; i++)
            {
                if (CopyNumberPanel.Children[i] is TextBlock tb && tb.Text == "Expected Copy Numbers by Chromosome")
                {
                    headerIndex = i;
                    break;
                }
            }

            if (headerIndex >= 0)
            {
                // Remove all controls after the header
                for (int i = CopyNumberPanel.Children.Count - 1; i > headerIndex; i--)
                {
                    CopyNumberPanel.Children.RemoveAt(i);
                }

                // Add dynamic copy number rows using appropriate layout
                var chromosomeCount = _parameters.ContainsKey("CHROMOSOME_COUNT") ? 
                                    Convert.ToInt32(_parameters["CHROMOSOME_COUNT"]) : 5;
                
                if (chromosomeCount <= 5)
                {
                    // Simple layout for 5 or fewer chromosomes
                    for (int i = 1; i <= chromosomeCount; i++)
                    {
                        var copyNumParam = $"EXPECTED_COPY_NUMBERS_Chrom{i}";
                        var stdDevParam = $"EXPECTED_STANDARD_DEVIATION_Chrom{i}";
                        // Ensure defaults if missing
                        if (!_parameters.ContainsKey(copyNumParam)) _parameters[copyNumParam] = "1.0";
                        if (!_parameters.ContainsKey(stdDevParam)) _parameters[stdDevParam] = "0.1";

                        var rowGrid = CreateTwoColumnParameterRow(copyNumParam, _parameters[copyNumParam], 
                                                                 stdDevParam, _parameters[stdDevParam]);
                        CopyNumberPanel.Children.Add(rowGrid);
                    }
                }
                else
                {
                    // Multi-column layout for more than 5 chromosomes
                    AddMultiColumnCopyNumberRows(chromosomeCount);
                }
            }
        }

        private void UpdateDynamicTargetNamesSection()
        {
            // Find the header "Target Names" and remove all children after it
            int headerIndex = -1;
            for (int i = 0; i < GeneralPanel.Children.Count; i++)
            {
                if (GeneralPanel.Children[i] is TextBlock tb && tb.Text == "Target Names")
                {
                    headerIndex = i;
                    break;
                }
            }

            if (headerIndex >= 0)
            {
                // Remove all controls after the header
                for (int i = GeneralPanel.Children.Count - 1; i > headerIndex; i--)
                {
                    GeneralPanel.Children.RemoveAt(i);
                }

                // Add target name fields - single column layout (matching macOS)
                var chromosomeCount = _parameters.ContainsKey("CHROMOSOME_COUNT") ? 
                                    Convert.ToInt32(_parameters["CHROMOSOME_COUNT"]) : 5;
                                    
                for (int i = 1; i <= chromosomeCount; i++)
                {
                    var targetNameParam = $"TARGET_NAME_{i}";
                    if (!_parameters.ContainsKey(targetNameParam))
                    {
                        _parameters[targetNameParam] = $"Target {i}";
                    }
                    var control = CreateParameterControl(targetNameParam, _parameters[targetNameParam]);
                    GeneralPanel.Children.Add(control);
                    StoreParameterControl(targetNameParam, control);
                }
            }
        }

        private Grid CreateParameterControl(string key, object value)
        {
            var grid = new Grid();
            grid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(200) });
            grid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
            grid.Margin = new Thickness(0, 6, 0, 0);
            grid.Height = 24;

            // Parameter label
            var label = new TextBlock
            {
                Text = GetDisplayName(key?.ToString() ?? ""),
                VerticalAlignment = VerticalAlignment.Center,
                Foreground = Brushes.White,
                FontSize = 11
            };
            Grid.SetColumn(label, 0);
            grid.Children.Add(label);
            // Tooltip for label/input
            var tooltipText = ParameterTooltips.Get(key ?? string.Empty);
            if (!string.IsNullOrWhiteSpace(tooltipText))
            {
                label.ToolTip = tooltipText;
            }

            // Parameter input control
            Control? inputControl = null;
            
            if (value is bool boolValue)
            {
                inputControl = new ComboBox
                {
                    Width = 100,
                    HorizontalAlignment = HorizontalAlignment.Left,
                    Style = (Style)Application.Current.Resources["DarkParameterComboBox"]
                };
                var comboBox = (ComboBox)inputControl;
                comboBox.Items.Add("Yes");
                comboBox.Items.Add("No");
                comboBox.SelectedItem = boolValue ? "Yes" : "No";

                // Special handling: toggling fluorophore mixing impacts CHROMOSOME_COUNT options
                if (key == "ENABLE_FLUOROPHORE_MIXING")
                {
                    comboBox.SelectionChanged += (s, e) =>
                    {
                        if (_suppressMixingHandler) return;

                        var prevEnabled = GetEnableFluorophoreMixing();
                        var desiredEnabled = comboBox.SelectedItem?.ToString() == "Yes";
                        if (desiredEnabled == prevEnabled) return;

                        string title, message;
                        if (!desiredEnabled)
                        {
                            title = "Disable Fluorophore Mixing?";
                            message = "Non-mixing mode limits targets to 1–4. It assumes targets are detected through a single fluorophore each and that target combinations are deconvoluted.";
                        }
                        else
                        {
                            title = "Enable Fluorophore Mixing?";
                            message = "Mixing mode enables detection of multiple targets with unique fluorophore mixes and will only consider single-target positive droplets. Multi-target positives cannot be deconvoluted.";
                        }

                        var resp = MessageBox.Show(message, title, MessageBoxButton.OKCancel, MessageBoxImage.Warning);
                        if (resp != MessageBoxResult.OK)
                        {
                            try
                            {
                                _suppressMixingHandler = true;
                                comboBox.SelectedItem = prevEnabled ? "Yes" : "No";
                            }
                            finally
                            {
                                _suppressMixingHandler = false;
                            }
                            return;
                        }

                        _parameters["ENABLE_FLUOROPHORE_MIXING"] = desiredEnabled;
                        UpdateChromosomeCountOptions(desiredEnabled);
                        UpdateAmplitudeNonLinearityVisibility();
                    };
                }
            }
            else if (key?.Contains("METRIC") == true || key?.Contains("METHOD") == true)
            {
                inputControl = new ComboBox
                {
                    Width = 150,
                    HorizontalAlignment = HorizontalAlignment.Left,
                    Style = (Style)Application.Current.Resources["DarkParameterComboBox"]
                };
                var comboBox = (ComboBox)inputControl;
                
                if (key.Contains("METRIC"))
                {
                    comboBox.Items.Add("euclidean");
                    comboBox.Items.Add("manhattan");
                    comboBox.Items.Add("chebyshev");
                    comboBox.Items.Add("minkowski");
                }
                else if (key.Contains("METHOD"))
                {
                    comboBox.Items.Add("eom");
                    comboBox.Items.Add("leaf");
                }
                
                comboBox.SelectedItem = value?.ToString();
            }
            else if (key == "CHROMOSOME_COUNT")
            {
                inputControl = new ComboBox
                {
                    Width = 100,
                    HorizontalAlignment = HorizontalAlignment.Left,
                    Style = (Style)Application.Current.Resources["DarkParameterComboBox"]
                };
                var comboBox = (ComboBox)inputControl;
                // Populate based on current mixing mode (non-mixing: limit to 1..4)
                var allowUpTo = GetEnableFluorophoreMixing() ? 10 : 4;
                for (int i = 1; i <= allowUpTo; i++) comboBox.Items.Add(i.ToString());
                comboBox.SelectedItem = value?.ToString();
                
                // Add event handler for dynamic UI updates
                comboBox.SelectionChanged += ChromosomeCountChanged;
            }
            else
            {
                inputControl = new TextBox
                {
                    Width = 200,
                    HorizontalAlignment = HorizontalAlignment.Left,
                    Text = FormatValueForDisplay(value),
                    Style = (Style)Application.Current.Resources["DarkParameterTextBox"]
                };
            }

            if (inputControl != null)
            {
                Grid.SetColumn(inputControl, 1);
                if (!string.IsNullOrWhiteSpace(tooltipText))
                {
                    inputControl.ToolTip = tooltipText;
                }
                grid.Children.Add(inputControl);
            }

            return grid;
        }

        private bool GetEnableFluorophoreMixing()
        {
            try
            {
                if (_parameters.TryGetValue("ENABLE_FLUOROPHORE_MIXING", out var v))
                {
                    if (v is bool b) return b;
                    var s = v?.ToString()?.Trim();
                    if (!string.IsNullOrEmpty(s)) return s.Equals("true", StringComparison.OrdinalIgnoreCase) || s.Equals("yes", StringComparison.OrdinalIgnoreCase);
                }
            }
            catch { }
            return true; // default enabled
        }

        private void UpdateChromosomeCountOptions(bool mixingEnabled)
        {
            if (_parameterControls.TryGetValue("CHROMOSOME_COUNT", out var ctrl) && ctrl is ComboBox combo)
            {
                var currentSel = combo.SelectedItem?.ToString();
                int.TryParse(currentSel, out var currentVal);
                var maxVal = mixingEnabled ? 10 : 4;
                combo.Items.Clear();
                for (int i = 1; i <= maxVal; i++) combo.Items.Add(i.ToString());
                if (currentVal < 1) currentVal = 1;
                if (currentVal > maxVal) currentVal = maxVal;
                combo.SelectedItem = currentVal.ToString();
                // Ensure backing parameters and dynamic sections reflect the new cap
                UpdateCentroidsForTargetCount(currentVal);
            }
        }

        private string GetDisplayName(string key)
        {
            // Convert parameter keys to human-readable names (exactly from macOS Swift code)
            var displayNames = new Dictionary<string, string>
            {
                // HDBSCAN (from Swift code)
                {"HDBSCAN_MIN_CLUSTER_SIZE", "Min Cluster Size:"},
                {"HDBSCAN_MIN_SAMPLES", "Min Samples:"},
                {"HDBSCAN_EPSILON", "Epsilon:"},
                {"MIN_POINTS_FOR_CLUSTERING", "Min Points for Clustering:"},
                {"HDBSCAN_METRIC", "Distance Metric:"},
                {"HDBSCAN_CLUSTER_SELECTION_METHOD", "Cluster Selection Method:"},
                
                // Expected Centroids
                {"BASE_TARGET_TOLERANCE", "Target Tolerance:"},
                {"CHROMOSOME_COUNT", "Number of Targets:"},
                {"EXPECTED_CENTROIDS_Negative", "Negative:"},
                
                // Copy Number (from Swift code)
                {"MIN_USABLE_DROPLETS", "Min Usable Droplets:"},
                {"COPY_NUMBER_MEDIAN_DEVIATION_THRESHOLD", "Median Deviation Threshold:"},
                {"COPY_NUMBER_MULTIPLIER", "Copy Number Multiplier:"},
                {"TOLERANCE_MULTIPLIER", "Tolerance Multiplier:"},
                {"LOWER_DEVIATION_TARGET", "Lower deviation target:"},
                {"UPPER_DEVIATION_TARGET", "Upper deviation target:"},
                
                // Visualization
                {"X_AXIS_MIN", "X-Axis Min:"},
                {"X_AXIS_MAX", "X-Axis Max:"},
                {"Y_AXIS_MIN", "Y-Axis Min:"},
                {"Y_AXIS_MAX", "Y-Axis Max:"},
                {"X_GRID_INTERVAL", "X-Grid Interval:"},
                {"Y_GRID_INTERVAL", "Y-Grid Interval:"},
                {"INDIVIDUAL_PLOT_DPI", "Plot DPI:"},
                
                // General (from Swift code - exactly as shown)
                {"ENABLE_FLUOROPHORE_MIXING", "Enable Fluorophore Mixing"},
                {"AMPLITUDE_NON_LINEARITY", "Amplitude Non-linearity:"},
                {"ENABLE_COPY_NUMBER_ANALYSIS", "Do copy number analysis?"},
                {"CLASSIFY_CNV_DEVIATIONS", "Classify copy number deviations?"}
            };

            if (displayNames.ContainsKey(key))
                return displayNames[key];
                
            // Handle dynamic chromosome target naming
            if (key.StartsWith("EXPECTED_CENTROIDS_Chrom"))
            {
                var chromNumber = key.Substring("EXPECTED_CENTROIDS_Chrom".Length);
                return $"Target {chromNumber}:";
            }
            
            // Handle dynamic target names
            if (key.StartsWith("TARGET_NAME_"))
            {
                var targetNumber = key.Substring("TARGET_NAME_".Length);
                return $"Target {targetNumber}:";
            }
            
            // Handle dynamic copy numbers
            if (key.StartsWith("EXPECTED_COPY_NUMBERS_Chrom"))
            {
                var chromNumber = key.Substring("EXPECTED_COPY_NUMBERS_Chrom".Length);
                return $"Target {chromNumber}:";
            }
            
            // Handle dynamic standard deviations
            if (key.StartsWith("EXPECTED_STANDARD_DEVIATION_Chrom"))
            {
                var chromNumber = key.Substring("EXPECTED_STANDARD_DEVIATION_Chrom".Length);
                return $"SD {chromNumber}:";
            }
            
            return key;
        }

        private void ApplyButton_Click(object sender, RoutedEventArgs e)
        {
            // Collect values from controls and apply them
            var updatedParameters = new Dictionary<string, object>();
            
            foreach (var kvp in _parameterControls)
            {
                var key = kvp.Key;
                var control = kvp.Value;
                
                if (control is TextBox textBox)
                {
                    updatedParameters[key] = textBox.Text;
                }
                else if (control is ComboBox comboBox)
                {
                    if (key.Contains("ENABLE_") || key.Contains("CLASSIFY_") || key.Contains("USE_"))
                    {
                        updatedParameters[key] = comboBox.SelectedItem?.ToString() == "Yes";
                    }
                    else
                    {
                        var selectedValue = comboBox.SelectedItem?.ToString();
                        if (selectedValue != null)
                        {
                            updatedParameters[key] = selectedValue;
                        }
                    }
                }
            }

            // Convert flat parameter structure to the structured format expected by Python backend
            var structuredParameters = ConvertToStructuredParameters(updatedParameters);

            // Save parameters to persistent storage
            ParametersService.SaveGlobalParameters(structuredParameters);
            
            // Notify that parameters have been applied (triggers reprocessing)
            ParametersApplied?.Invoke(structuredParameters);
            
            DialogResult = true;
            Close();
        }

        private void CancelButton_Click(object sender, RoutedEventArgs e)
        {
            DialogResult = false;
            Close();
        }

        private Dictionary<string, object> ConvertToStructuredParameters(Dictionary<string, object> flatParameters)
        {
            var structured = new Dictionary<string, object>(flatParameters);
            
            // Structure EXPECTED_CENTROIDS
            var centroids = new Dictionary<string, object>();
            var centroidKeys = flatParameters.Keys.Where(k => k.StartsWith("EXPECTED_CENTROIDS_")).ToList();
            
            foreach (var key in centroidKeys)
            {
                var chromName = key.Substring("EXPECTED_CENTROIDS_".Length);
                var value = flatParameters[key]?.ToString() ?? "";
                
                if (!string.IsNullOrWhiteSpace(value))
                {
                    // Parse "x, y" format
                    var parts = value.Split(',').Select(p => p.Trim()).ToArray();
                    if (parts.Length == 2 && 
                        double.TryParse(parts[0], NumberStyles.Float, CultureInfo.InvariantCulture, out var x) &&
                        double.TryParse(parts[1], NumberStyles.Float, CultureInfo.InvariantCulture, out var y))
                    {
                        centroids[chromName] = new double[] { x, y };
                    }
                }
                
                // Remove the flat key
                structured.Remove(key);
            }
            
            if (centroids.Count > 0)
            {
                structured["EXPECTED_CENTROIDS"] = centroids;
            }
            
            // Structure COPY_NUMBER_SPEC
            var copyNumberSpec = new List<Dictionary<string, object>>();
            // A) From COPY_NUMBER_SPEC_* inputs
            var copyNumberKeys = flatParameters.Keys.Where(k => k.StartsWith("COPY_NUMBER_SPEC_") && 
                                                                (k.EndsWith("_expected") || k.EndsWith("_std_dev"))).ToList();
            var chromosomes = copyNumberKeys.Select(k => {
                var chromPart = k.Substring("COPY_NUMBER_SPEC_".Length);
                if (chromPart.EndsWith("_expected"))
                    return chromPart.Substring(0, chromPart.Length - "_expected".Length);
                if (chromPart.EndsWith("_std_dev"))
                    return chromPart.Substring(0, chromPart.Length - "_std_dev".Length);
                return null;
            }).Where(c => c != null).Distinct().ToList();
            foreach (var chrom in chromosomes)
            {
                var expectedKey = $"COPY_NUMBER_SPEC_{chrom}_expected";
                var stdDevKey = $"COPY_NUMBER_SPEC_{chrom}_std_dev";
                var expectedStr = flatParameters.ContainsKey(expectedKey) ? flatParameters[expectedKey]?.ToString() : null;
                var stdDevStr = flatParameters.ContainsKey(stdDevKey) ? flatParameters[stdDevKey]?.ToString() : null;
                if (!string.IsNullOrWhiteSpace(expectedStr) || !string.IsNullOrWhiteSpace(stdDevStr))
                {
                    var spec = new Dictionary<string, object> { ["chrom"] = chrom ?? "" };
                    if (double.TryParse(expectedStr, NumberStyles.Float, CultureInfo.InvariantCulture, out var expectedVal)) spec["expected"] = expectedVal;
                    if (double.TryParse(stdDevStr, NumberStyles.Float, CultureInfo.InvariantCulture, out var stdDevVal)) spec["std_dev"] = stdDevVal;
                    copyNumberSpec.Add(spec);
                }
                structured.Remove(expectedKey);
                structured.Remove(stdDevKey);
            }
            // B) From EXPECTED_COPY_NUMBERS_ChromX / EXPECTED_STANDARD_DEVIATION_ChromX inputs
            var cnChroms = flatParameters.Keys
                .Where(k => k.StartsWith("EXPECTED_COPY_NUMBERS_Chrom"))
                .Select(k => k.Substring("EXPECTED_COPY_NUMBERS_Chrom".Length))
                .ToHashSet();
            var sdChroms = flatParameters.Keys
                .Where(k => k.StartsWith("EXPECTED_STANDARD_DEVIATION_Chrom"))
                .Select(k => k.Substring("EXPECTED_STANDARD_DEVIATION_Chrom".Length))
                .ToHashSet();
            var allChroms = cnChroms.Union(sdChroms).ToList();
            foreach (var idx in allChroms)
            {
                var cnKey = $"EXPECTED_COPY_NUMBERS_Chrom{idx}";
                var sdKey = $"EXPECTED_STANDARD_DEVIATION_Chrom{idx}";
                var spec = new Dictionary<string, object> { ["chrom"] = $"Chrom{idx}" };
                if (flatParameters.TryGetValue(cnKey, out var cnVal) && double.TryParse(cnVal?.ToString(), NumberStyles.Float, CultureInfo.InvariantCulture, out var cnD))
                    spec["expected"] = cnD;
                if (flatParameters.TryGetValue(sdKey, out var sdVal) && double.TryParse(sdVal?.ToString(), NumberStyles.Float, CultureInfo.InvariantCulture, out var sdD))
                    spec["std_dev"] = sdD;
                if (spec.Count > 1) copyNumberSpec.Add(spec);
                structured.Remove(cnKey);
                structured.Remove(sdKey);
            }
            
            if (copyNumberSpec.Count > 0)
            {
                structured["COPY_NUMBER_SPEC"] = copyNumberSpec;
            }
            
            // Structure TARGET_NAMES separately
            var targetNames = new Dictionary<string, object>();
            var targetNameKeys = flatParameters.Keys.Where(k => k.StartsWith("TARGET_NAME_")).ToList();
            
            foreach (var key in targetNameKeys)
            {
                var targetIndex = key.Substring("TARGET_NAME_".Length);
                var value = flatParameters[key]?.ToString() ?? "";
                
                if (!string.IsNullOrWhiteSpace(value))
                {
                    // Match macOS/Python expectation: keys like "Target1", "Target2", ...
                    targetNames[$"Target{targetIndex}"] = value;
                }
                
                // Remove the flat key
                structured.Remove(key);
            }
            
            if (targetNames.Count > 0)
            {
                structured["TARGET_NAMES"] = targetNames;
            }
            
            return structured;
        }

        private void RestoreDefaultsButton_Click(object sender, RoutedEventArgs e)
        {
            // No confirmation; restore defaults for current tab only (macOS behavior)
            try
            {
                var defaults = GetDefaultParameters();
                RestoreDefaultsForCurrentTab(defaults);
            }
            catch (Exception ex)
            {
                MessageBox.Show($"Error restoring defaults: {ex.Message}", "Error", 
                              MessageBoxButton.OK, MessageBoxImage.Error);
            }
        }

        private void RestoreDefaultsForCurrentTab(Dictionary<string, object> defaults)
        {
            if (ParametersTabControl?.SelectedItem is TabItem tab)
            {
                var header = tab.Header?.ToString() ?? string.Empty;
                if (header.Contains("HDBSCAN", StringComparison.OrdinalIgnoreCase))
                {
                    var keys = new[] { "HDBSCAN_MIN_CLUSTER_SIZE","HDBSCAN_MIN_SAMPLES","HDBSCAN_EPSILON","MIN_POINTS_FOR_CLUSTERING","HDBSCAN_METRIC","HDBSCAN_CLUSTER_SELECTION_METHOD" };
                    ApplyDefaultsToPanel(HDBSCANPanel, defaults, keys);
                }
                else if (header.Contains("Centroid", StringComparison.OrdinalIgnoreCase))
                {
                    // base tolerance, chromosome count, amplitude non-linearity and expected centroids rows
                    ApplyDefaultsToPanel(CentroidsPanel, defaults, new[] { "BASE_TARGET_TOLERANCE","CHROMOSOME_COUNT","AMPLITUDE_NON_LINEARITY" });
                    // Adjust dynamic rows to match current CHROMOSOME_COUNT
                    if (_parameters.TryGetValue("CHROMOSOME_COUNT", out var ccObj) && int.TryParse(ccObj.ToString(), out var cc))
                    {
                        UpdateCentroidsForTargetCount(cc);
                    }
                    // Seed centroid rows from structured defaults where controls exist
                    if (defaults.TryGetValue("EXPECTED_CENTROIDS", out var ec) && ec is Dictionary<string, object> ecd)
                    {
                        SetIfPresent("EXPECTED_CENTROIDS_Negative", FormatCoords(ecd.TryGetValue("Negative", out var neg) ? neg : null));
                        for (int i = 1; i <= 10; i++)
                        {
                            var key = $"EXPECTED_CENTROIDS_Chrom{i}";
                            if (_parameterControls.ContainsKey(key) && ecd.TryGetValue($"Chrom{i}", out var val))
                            {
                                SetIfPresent(key, FormatCoords(val));
                            }
                        }
                    }
                }
                else if (header.Contains("Copy Number", StringComparison.OrdinalIgnoreCase))
                {
                    var keys = new[] { "MIN_USABLE_DROPLETS","COPY_NUMBER_MEDIAN_DEVIATION_THRESHOLD","COPY_NUMBER_MULTIPLIER","TOLERANCE_MULTIPLIER","LOWER_DEVIATION_TARGET","UPPER_DEVIATION_TARGET" };
                    ApplyDefaultsToPanel(CopyNumberPanel, defaults, keys);
                    // Seed per-chromosome expected/std from COPY_NUMBER_SPEC where present
                    if (defaults.TryGetValue("COPY_NUMBER_SPEC", out var specVal))
                    {
                        foreach (var entry in EnumerateCopyNumberSpec(specVal))
                        {
                            if (entry.TryGetValue("chrom", out var chromObj))
                            {
                                var chrom = chromObj?.ToString() ?? string.Empty;
                                if (chrom.StartsWith("Chrom"))
                                {
                                    var idx = chrom.Substring(5);
                                    SetIfPresent($"EXPECTED_COPY_NUMBERS_Chrom{idx}", entry.TryGetValue("expected", out var exp) ? FormatValueForDisplay(exp) : null);
                                    SetIfPresent($"EXPECTED_STANDARD_DEVIATION_Chrom{idx}", entry.TryGetValue("std_dev", out var sd) ? FormatValueForDisplay(sd) : null);
                                }
                            }
                        }
                        // Rebuild dynamic copy number rows to reflect defaults
                        UpdateDynamicCopyNumberSection();
                    }
                }
                else if (header.Contains("Visualization", StringComparison.OrdinalIgnoreCase))
                {
                    var keys = new[] { "X_AXIS_MIN","X_AXIS_MAX","Y_AXIS_MIN","Y_AXIS_MAX","X_GRID_INTERVAL","Y_GRID_INTERVAL","INDIVIDUAL_PLOT_DPI" };
                    ApplyDefaultsToPanel(VisualizationPanel, defaults, keys);
                }
                else if (header.Contains("General", StringComparison.OrdinalIgnoreCase))
                {
                    var keys = new[] { "ENABLE_FLUOROPHORE_MIXING","ENABLE_COPY_NUMBER_ANALYSIS","CLASSIFY_CNV_DEVIATIONS" };
                    try { _suppressMixingHandler = true; ApplyDefaultsToPanel(GeneralPanel, defaults, keys); }
                    finally { _suppressMixingHandler = false; }
                    // Target names if controls exist
                    if (defaults.TryGetValue("TARGET_NAMES", out var tn) && tn is Dictionary<string, object> tnd)
                    {
                        for (int i = 1; i <= 10; i++)
                        {
                            var k = $"TARGET_NAME_{i}";
                            if (_parameterControls.ContainsKey(k))
                            {
                                var def = tnd.TryGetValue($"Target{i}", out var v) ? v?.ToString() : $"Target {i}";
                                SetIfPresent(k, def);
                            }
                        }
                    }
                }
            }
        }

        private void ApplyDefaultsToPanel(Panel panel, Dictionary<string, object> defaults, IEnumerable<string> keys)
        {
            foreach (var key in keys)
            {
                if (_parameterControls.TryGetValue(key, out var ctrl))
                {
                    if (GetAncestorPanel(ctrl) != panel) continue;
                    if (defaults.TryGetValue(key, out var defVal))
                    {
                        SetControlValue(key, ctrl, defVal);
                    }
                }
            }
        }

        private Panel? GetAncestorPanel(Control ctrl)
        {
            if (ctrl.Parent is Grid g && g.Parent is Panel p) return p;
            return null;
        }

        private void SetIfPresent(string key, object? value)
        {
            if (value == null) return;
            // Always update backing parameter map so subsequent dynamic row rebuilds use the right values
            _parameters[key] = value;
            if (_parameterControls.TryGetValue(key, out var ctrl))
            {
                SetControlValue(key, ctrl, value);
            }
        }

        private void SetControlValue(string key, Control ctrl, object value)
        {
            _parameters[key] = value;
            if (ctrl is TextBox tb)
            {
                tb.Text = FormatValueForDisplay(value);
            }
            else if (ctrl is ComboBox cb)
            {
                // Boolean combos use Yes/No
                if (key.StartsWith("ENABLE_") || key.StartsWith("CLASSIFY_"))
                {
                    var b = (value is bool bv) ? bv : value.ToString()?.Equals("true", StringComparison.OrdinalIgnoreCase) == true;
                    cb.SelectedItem = b ? "Yes" : "No";
                }
                else
                {
                    cb.SelectedItem = value?.ToString();
                }
            }
        }
        
        private Dictionary<string, object> GetDefaultParameters()
        {
            // Return structured default parameters (matching modern format)
            return new Dictionary<string, object>
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
        }

        private void UpdateAmplitudeNonLinearityVisibility()
        {
            // Show the parameter only when mixing is DISABLED (macOS behavior)
            var isMixingEnabled = GetEnableFluorophoreMixing();

            if (_parameterControls.TryGetValue("AMPLITUDE_NON_LINEARITY", out var ampInput))
            {
                // Toggle the entire row (Grid) so label and input hide together
                if (ampInput.Parent is Grid row)
                {
                    // Ensure the row is placed in the Centroids panel, before the header
                    if (row.Parent is Panel currentParent && currentParent != CentroidsPanel)
                    {
                        currentParent.Children.Remove(row);
                        int headerIndex = -1;
                        for (int i = 0; i < CentroidsPanel.Children.Count; i++)
                        {
                            if (CentroidsPanel.Children[i] is TextBlock tb && tb.Text == "Expected Centroid Position")
                            {
                                headerIndex = i;
                                break;
                            }
                        }
                        if (headerIndex >= 0)
                            CentroidsPanel.Children.Insert(headerIndex, row);
                        else
                            CentroidsPanel.Children.Add(row);
                    }

                    row.Visibility = isMixingEnabled ? Visibility.Collapsed : Visibility.Visible;
                }
                else
                {
                    // Fallback: toggle input control if parent not Grid
                    ampInput.Visibility = isMixingEnabled ? Visibility.Collapsed : Visibility.Visible;
                }
            }
        }
    }
}
