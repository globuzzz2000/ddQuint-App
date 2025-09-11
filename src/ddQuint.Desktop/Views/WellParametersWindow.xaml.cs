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
using ddQuint.Core.Models;

namespace ddQuint.Desktop.Views
{
    public partial class WellParametersWindow : Window
    {
        private MainViewModel _mainViewModel;
        private WellResult _wellResult;
        private List<string> _multiWellIds = new List<string>();
        private Dictionary<string, object> _parameters = new Dictionary<string, object>();
        private Dictionary<string, object> _globalParameters = new Dictionary<string, object>();
        private Dictionary<string, Control> _parameterControls = new Dictionary<string, Control>();
        private bool _suppressMixingHandler = false;
        
        // Event for notifying when well parameters are applied
        public event Action<string, Dictionary<string, object>>? WellParametersApplied;
        // Event for notifying when multi-well parameters are applied in batch
        public event Action<IEnumerable<string>, Dictionary<string, object>>? MultiWellParametersApplied;

        // Helper method to format decimal values with invariant culture
        private string FormatValueForDisplay(object value)
        {
            if (value == null) return "";
            if (value is double dVal) return dVal.ToString(CultureInfo.InvariantCulture);
            if (value is float fVal) return fVal.ToString(CultureInfo.InvariantCulture);
            return value.ToString() ?? "";
        }
        
        public WellParametersWindow(MainViewModel mainViewModel, WellResult wellResult)
        {
            InitializeComponent();
            _mainViewModel = mainViewModel;
            _wellResult = wellResult;
            
            // Set window title instead of removed UI elements
            this.Title = $"Well Parameters - {wellResult.WellId}";
            if (!string.IsNullOrEmpty(wellResult.SampleName))
            {
                this.Title = $"Well Parameters - {wellResult.WellId} ({wellResult.SampleName})";
            }
        }

        // Multi-well constructor: opens on first well's parameters, applies to all on save
        public WellParametersWindow(MainViewModel mainViewModel, WellResult baseWell, IEnumerable<string> multiWellIds)
        {
            InitializeComponent();
            _mainViewModel = mainViewModel;
            _wellResult = baseWell;
            _multiWellIds = multiWellIds?.Distinct().ToList() ?? new List<string>();

            int count = Math.Max(1, _multiWellIds.Count);
            this.Title = count > 1
                ? $"Well Parameters - {count} Wells"
                : $"Well Parameters - {baseWell.WellId}";
        }

        private void Window_Loaded(object sender, RoutedEventArgs e)
        {
            LoadParameters();
            BuildParameterUI();
        }

        private void LoadParameters()
        {
            // Load global parameters as base
            _globalParameters = ParametersService.LoadGlobalParameters();
            
            // Start with global parameters
            _parameters = new Dictionary<string, object>(_globalParameters);
            
            // Load and apply well-specific overrides
            var wellSpecificParams = ParametersService.LoadWellParameters(_wellResult.WellId);
            foreach (var kvp in wellSpecificParams)
            {
                _parameters[kvp.Key] = kvp.Value;
            }
            
            System.Diagnostics.Debug.WriteLine($"[WellParametersWindow] Loaded {_globalParameters.Count} global parameters and {wellSpecificParams.Count} well-specific parameters for well {_wellResult.WellId}");
            
            // Debug: Show what was loaded
            var appDataFolder = Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData);
            var ddquintFolder = Path.Combine(appDataFolder, "ddQuint");
            var parametersFile = Path.Combine(ddquintFolder, "parameters.json");
            var logFile = Path.Combine(ddquintFolder, "logs", "debug.log");
            
            var debugInfo = new List<string>
            {
                $"=== Well Parameter Loading Debug - {DateTime.Now:yyyy-MM-dd HH:mm:ss} ===",
                $"Well ID: {_wellResult.WellId}",
                $"AppData folder: {appDataFolder}",
                $"ddQuint folder: {ddquintFolder}",
                $"Parameters file: {parametersFile}",
                $"Global parameters loaded: {_globalParameters.Count}",
                $"Well-specific parameters loaded: {wellSpecificParams.Count}",
                $"Total parameters in window: {_parameters.Count}"
            };
            
            if (wellSpecificParams.Count > 0)
            {
                debugInfo.Add($"Well-specific parameter overrides:");
                foreach (var kvp in wellSpecificParams)
                {
                    debugInfo.Add($"  {kvp.Key} = {kvp.Value}");
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
                System.Diagnostics.Debug.WriteLine($"Well debug log written to: {logFile}");
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"Failed to write well debug log: {ex.Message}");
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

            // Build each tab with exact same structure as GlobalParametersWindow
            BuildHDBSCANTab();
            BuildCentroidsTab();
            BuildCopyNumberTab();
            BuildVisualizationTab();
            BuildGeneralTab();
        }

        // Exact same methods as GlobalParametersWindow, but operating on well parameters
        private void BuildHDBSCANTab()
        {
            AddTitleAndDescription(HDBSCANPanel, "HDBSCAN Clustering Parameters", 
                                 "Configure clustering parameters for droplet classification.");

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

            if (_parameters.ContainsKey("BASE_TARGET_TOLERANCE"))
            {
                var control = CreateParameterControl("BASE_TARGET_TOLERANCE", _parameters["BASE_TARGET_TOLERANCE"]);
                CentroidsPanel.Children.Add(control);
                StoreParameterControl("BASE_TARGET_TOLERANCE", control);
            }

            if (_parameters.ContainsKey("CHROMOSOME_COUNT"))
            {
                var control = CreateParameterControl("CHROMOSOME_COUNT", _parameters["CHROMOSOME_COUNT"]);
                CentroidsPanel.Children.Add(control);
                StoreParameterControl("CHROMOSOME_COUNT", control);
            }

            // Amplitude Non-linearity (show only when fluorophore mixing is disabled; align with macOS)
            if (_parameters.ContainsKey("AMPLITUDE_NON_LINEARITY"))
            {
                var amplitudeControl = CreateParameterControl("AMPLITUDE_NON_LINEARITY", _parameters["AMPLITUDE_NON_LINEARITY"]);
                CentroidsPanel.Children.Add(amplitudeControl);
                StoreParameterControl("AMPLITUDE_NON_LINEARITY", amplitudeControl);
                UpdateAmplitudeNonLinearityVisibility();
            }

            AddSectionHeader(CentroidsPanel, "Expected Centroid Position");
            
            // Same centroid building logic as GlobalParametersWindow, but accept in-memory dictionaries too
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
                        if (centroidsObj.TryGetValue("Negative", out var negVal))
                        {
                            var negativeCoords = FormatCoords(negVal);
                            var control = CreateParameterControl("EXPECTED_CENTROIDS_Negative", negativeCoords);
                            CentroidsPanel.Children.Add(control);
                            StoreParameterControl("EXPECTED_CENTROIDS_Negative", control);
                        }

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
                // Fallback to flattened format
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

        private void BuildCopyNumberTab()
        {
            AddTitleAndDescription(CopyNumberPanel, "Copy Number Analysis Settings", 
                                 "Configure copy number analysis and classification parameters.");

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

            var spacer = new Border { Height = 20 };
            CopyNumberPanel.Children.Add(spacer);
            
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

            AddSectionHeader(CopyNumberPanel, "Expected Copy Numbers by Chromosome");

            // Preload flattened values from structured sources if available
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

            AddSectionHeader(GeneralPanel, "Target Names");
            
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

        // Copy all the helper methods from GlobalParametersWindow exactly
        private void AddTitleAndDescription(StackPanel panel, string title, string description)
        {
            var titleBlock = new TextBlock
            {
                Text = title,
                FontSize = 16,
                FontWeight = FontWeights.Bold,
                Foreground = Brushes.White,
                Margin = new Thickness(0, 0, 0, 10)
            };
            panel.Children.Add(titleBlock);

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

        private void AddDynamicCopyNumberRows()
        {
            var chromosomeCount = _parameters.ContainsKey("CHROMOSOME_COUNT") ? 
                                Convert.ToInt32(_parameters["CHROMOSOME_COUNT"]) : 5;
                                
            if (chromosomeCount <= 5)
            {
                for (int i = 1; i <= chromosomeCount; i++)
                {
                    var copyNumParam = $"EXPECTED_COPY_NUMBERS_Chrom{i}";
                    var stdDevParam = $"EXPECTED_STANDARD_DEVIATION_Chrom{i}";
                    // Ensure defaults if missing
                    if (!_parameters.ContainsKey(copyNumParam)) { _parameters[copyNumParam] = "1.0"; }
                    if (!_parameters.ContainsKey(stdDevParam)) { _parameters[stdDevParam] = "0.1"; }
                    
                    var rowGrid = CreateTwoColumnParameterRow(copyNumParam, _parameters[copyNumParam], 
                                                             stdDevParam, _parameters[stdDevParam]);
                    CopyNumberPanel.Children.Add(rowGrid);
                }
            }
            else
            {
                AddMultiColumnCopyNumberRows(chromosomeCount);
            }
        }

        private void AddMultiColumnCopyNumberRows(int chromosomeCount)
        {
            const int chromsPerColumn = 5;
            var totalCnColumns = (chromosomeCount + chromsPerColumn - 1) / chromsPerColumn;
            
            var masterGrid = new Grid();
            masterGrid.Margin = new Thickness(0, 6, 0, 0);
            
            // CN1, CN1 textbox, (small gap), CN2, CN2 textbox, (big gap), SD1 label, SD1 textbox, (small gap), SD2 label, SD2 textbox, (stretch)
            masterGrid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(80) });
            masterGrid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(80) });
            if (totalCnColumns > 1)
            {
                masterGrid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(12) });
                masterGrid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(80) });
                masterGrid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(80) });
            }
            masterGrid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(40) });
            masterGrid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(55) });
            masterGrid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(80) });
            if (totalCnColumns > 1)
            {
                masterGrid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(12) });
                masterGrid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(55) });
                masterGrid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(80) });
            }
            masterGrid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
            
            for (int row = 0; row < chromsPerColumn; row++)
            {
                masterGrid.RowDefinitions.Add(new RowDefinition { Height = new GridLength(30) });
            }
            
            for (int i = 1; i <= chromosomeCount; i++)
            {
                var copyNumParam = $"EXPECTED_COPY_NUMBERS_Chrom{i}";
                var stdDevParam = $"EXPECTED_STANDARD_DEVIATION_Chrom{i}";
                
                if (!_parameters.ContainsKey(copyNumParam))
                {
                    _parameters[copyNumParam] = "1.0";
                }
                if (!_parameters.ContainsKey(stdDevParam))
                {
                    _parameters[stdDevParam] = "0.1";
                }
                
                var cnColumnIndex = (i - 1) / chromsPerColumn;
                var positionInColumn = (i - 1) % chromsPerColumn;
                
                var cnLabel = new TextBlock
                {
                    Text = $"Target {i}:",
                    VerticalAlignment = VerticalAlignment.Center,
                    Foreground = Brushes.White,
                    FontSize = 11
                };
                Grid.SetRow(cnLabel, positionInColumn);
                Grid.SetColumn(cnLabel, cnColumnIndex == 0 ? 0 : 3);
                masterGrid.Children.Add(cnLabel);
                
                var cnTextBox = new TextBox
                {
                    Text = FormatValueForDisplay(_parameters[copyNumParam]),
                    Style = (Style)Application.Current.Resources["DarkParameterTextBox"],
                    Width = 80,
                    HorizontalAlignment = HorizontalAlignment.Left,
                    VerticalAlignment = VerticalAlignment.Center
                };
                Grid.SetRow(cnTextBox, positionInColumn);
                Grid.SetColumn(cnTextBox, cnColumnIndex == 0 ? 1 : 4);
                masterGrid.Children.Add(cnTextBox);
                _parameterControls[copyNumParam] = cnTextBox;
                
                // SD1 label starts at column 6 with this layout
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
            }
            
            CopyNumberPanel.Children.Add(masterGrid);
        }

        private Grid CreateTwoColumnParameterRow(string leftKey, object leftValue, string rightKey, object rightValue)
        {
            var rowGrid = new Grid();
            rowGrid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(100) });
            rowGrid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(80) });
            rowGrid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(55) });
            rowGrid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(80) });
            rowGrid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
            rowGrid.Margin = new Thickness(0, 6, 0, 0);
            rowGrid.Height = 24;

            var leftLabel = new TextBlock
            {
                Text = GetDisplayName(leftKey),
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
            _parameterControls[leftKey!] = leftTextBox;
            if (!string.IsNullOrWhiteSpace(leftTip)) leftTextBox.ToolTip = leftTip;

            var rightLabel = new TextBlock
            {
                Text = GetDisplayName(rightKey),
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
            _parameterControls[rightKey!] = rightTextBox;
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
            // Preserve existing values for already-defined targets
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
                        _parameterControls.Remove(key);
                }
            }

            // Ensure defaults exist for all targets up to targetCount (preserve existing)
            for (int i = 1; i <= targetCount; i++)
            {
                var centroidKey = $"EXPECTED_CENTROIDS_Chrom{i}";
                if (!_parameters.ContainsKey(centroidKey))
                {
                    // Try structured EXPECTED_CENTROIDS
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
                                _parameters[centroidKey] = FormatCoords(v);
                        }
                        catch { }
                    }
                    if (!_parameters.ContainsKey(centroidKey))
                        _parameters[centroidKey] = $"{1500 + i * 500},{2000 + i * 300}";
                }

                var targetNameKey = $"TARGET_NAME_{i}";
                if (!_parameters.ContainsKey(targetNameKey))
                {
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
                for (int i = CentroidsPanel.Children.Count - 1; i > headerIndex; i--)
                {
                    CentroidsPanel.Children.RemoveAt(i);
                }

                // Ensure Negative is present in parameter map
                if (!_parameters.ContainsKey("EXPECTED_CENTROIDS_Negative"))
                {
                    _parameters["EXPECTED_CENTROIDS_Negative"] = "1000,900"; // macOS-aligned default
                }

                if (_parameters.ContainsKey("EXPECTED_CENTROIDS_Negative"))
                {
                    var control = CreateParameterControl("EXPECTED_CENTROIDS_Negative", _parameters["EXPECTED_CENTROIDS_Negative"]);
                    CentroidsPanel.Children.Add(control);
                    StoreParameterControl("EXPECTED_CENTROIDS_Negative", control);
                }
                
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
                for (int i = CopyNumberPanel.Children.Count - 1; i > headerIndex; i--)
                {
                    CopyNumberPanel.Children.RemoveAt(i);
                }

                var chromosomeCount = _parameters.ContainsKey("CHROMOSOME_COUNT") ? 
                                    Convert.ToInt32(_parameters["CHROMOSOME_COUNT"]) : 5;
                
                if (chromosomeCount <= 5)
                {
                    for (int i = 1; i <= chromosomeCount; i++)
                    {
                        var copyNumParam = $"EXPECTED_COPY_NUMBERS_Chrom{i}";
                        var stdDevParam = $"EXPECTED_STANDARD_DEVIATION_Chrom{i}";
                        
                        var rowGrid = CreateTwoColumnParameterRow(copyNumParam, _parameters[copyNumParam], 
                                                                 stdDevParam, _parameters[stdDevParam]);
                        CopyNumberPanel.Children.Add(rowGrid);
                    }
                }
                else
                {
                    AddMultiColumnCopyNumberRows(chromosomeCount);
                }
            }
        }

        private void UpdateDynamicTargetNamesSection()
        {
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
                for (int i = GeneralPanel.Children.Count - 1; i > headerIndex; i--)
                {
                    GeneralPanel.Children.RemoveAt(i);
                }

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

            var label = new TextBlock
            {
                Text = GetDisplayName(key),
                VerticalAlignment = VerticalAlignment.Center,
                Foreground = Brushes.White,
                FontSize = 11
            };
            Grid.SetColumn(label, 0);
            grid.Children.Add(label);
            var tip = ParameterTooltips.Get(key ?? string.Empty);
            if (!string.IsNullOrWhiteSpace(tip)) label.ToolTip = tip;

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
            else if (!string.IsNullOrEmpty(key) && (key.Contains("METRIC") || key.Contains("METHOD")))
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
                var allowUpTo = GetEnableFluorophoreMixing() ? 10 : 4;
                for (int i = 1; i <= allowUpTo; i++) comboBox.Items.Add(i.ToString());
                comboBox.SelectedItem = value?.ToString();
                
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
                if (!string.IsNullOrWhiteSpace(tip)) inputControl.ToolTip = tip;
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
                UpdateCentroidsForTargetCount(currentVal);
            }
        }

        private void UpdateAmplitudeNonLinearityVisibility()
        {
            var isMixingEnabled = GetEnableFluorophoreMixing();
            if (_parameterControls.TryGetValue("AMPLITUDE_NON_LINEARITY", out var ampInput))
            {
                if (ampInput.Parent is Grid row)
                {
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
                    ampInput.Visibility = isMixingEnabled ? Visibility.Collapsed : Visibility.Visible;
                }
            }
        }

        private string GetDisplayName(string key)
        {
            // Same display names as GlobalParametersWindow
            var displayNames = new Dictionary<string, string>
            {
                // HDBSCAN
                {"HDBSCAN_MIN_CLUSTER_SIZE", "Min Cluster Size:"},
                {"HDBSCAN_MIN_SAMPLES", "Min Samples:"},
                {"HDBSCAN_EPSILON", "Epsilon:"},
                {"MIN_POINTS_FOR_CLUSTERING", "Min Points for Clustering:"},
                {"HDBSCAN_METRIC", "Distance Metric:"},
                {"HDBSCAN_CLUSTER_SELECTION_METHOD", "Cluster Selection Method:"},
                
                // Expected Centroids
                {"BASE_TARGET_TOLERANCE", "Target Tolerance:"},
                {"CHROMOSOME_COUNT", "Number of Targets:"},
                {"AMPLITUDE_NON_LINEARITY", "Amplitude Non-linearity:"},
                {"EXPECTED_CENTROIDS_Negative", "Negative:"},
                
                // Copy Number
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
                
                // General
                {"ENABLE_FLUOROPHORE_MIXING", "Enable Fluorophore Mixing"},
                {"ENABLE_COPY_NUMBER_ANALYSIS", "Do copy number analysis?"},
                {"CLASSIFY_CNV_DEVIATIONS", "Classify copy number deviations?"}
            };

            if (displayNames.ContainsKey(key))
                return displayNames[key];
                
            if (key.StartsWith("EXPECTED_CENTROIDS_Chrom"))
            {
                var chromNumber = key.Substring("EXPECTED_CENTROIDS_Chrom".Length);
                return $"Target {chromNumber}:";
            }
            
            if (key.StartsWith("TARGET_NAME_"))
            {
                var targetNumber = key.Substring("TARGET_NAME_".Length);
                return $"Target {targetNumber}:";
            }
            
            if (key.StartsWith("EXPECTED_COPY_NUMBERS_Chrom"))
            {
                var chromNumber = key.Substring("EXPECTED_COPY_NUMBERS_Chrom".Length);
                return $"Target {chromNumber}:";
            }
            
            if (key.StartsWith("EXPECTED_STANDARD_DEVIATION_Chrom"))
            {
                var chromNumber = key.Substring("EXPECTED_STANDARD_DEVIATION_Chrom".Length);
                return $"SD {chromNumber}:";
            }
            
            return key;
        }

        private void ResetParametersButton_Click(object sender, RoutedEventArgs e)
        {
            // Reset Parameters: Remove all well-specific overrides (matches macOS resetWellParameters)
            var result = MessageBox.Show(
                $"Remove all custom parameters for well {_wellResult.WellId}?\n\nThis will revert the well to use global parameter settings.",
                "Reset Well Parameters",
                MessageBoxButton.YesNo,
                MessageBoxImage.Question);
                
            if (result == MessageBoxResult.Yes)
            {
                try
                {
                    // Remove all well-specific parameters
                    ParametersService.SaveWellParameters(_wellResult.WellId, new Dictionary<string, object>());
                    
                    // Close the window and notify of parameter change
                    WellParametersApplied?.Invoke(_wellResult.WellId, new Dictionary<string, object>());
                    
                    DialogResult = true;
                    Close();
                }
                catch (Exception ex)
                {
                    MessageBox.Show($"Error resetting parameters: {ex.Message}", "Error", 
                                  MessageBoxButton.OK, MessageBoxImage.Error);
                }
            }
        }

        private void RestoreDefaultsButton_Click(object sender, RoutedEventArgs e)
        {
            // No confirmation; restore defaults for the current tab only (macOS behavior)
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
                    ApplyDefaultsToPanel(CentroidsPanel, defaults, new[] { "BASE_TARGET_TOLERANCE","CHROMOSOME_COUNT","AMPLITUDE_NON_LINEARITY" });
                    if (_parameters.TryGetValue("CHROMOSOME_COUNT", out var ccObj) && int.TryParse(ccObj.ToString(), out var cc))
                    {
                        UpdateCentroidsForTargetCount(cc);
                    }
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
                    UpdateDynamicCentroidsSection();
                }
                else if (header.Contains("Copy Number", StringComparison.OrdinalIgnoreCase))
                {
                    var keys = new[] { "MIN_USABLE_DROPLETS","COPY_NUMBER_MEDIAN_DEVIATION_THRESHOLD","COPY_NUMBER_MULTIPLIER","TOLERANCE_MULTIPLIER","LOWER_DEVIATION_TARGET","UPPER_DEVIATION_TARGET" };
                    ApplyDefaultsToPanel(CopyNumberPanel, defaults, keys);
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
                    }
                    UpdateDynamicCopyNumberSection();
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
                    if (defaults.TryGetValue("TARGET_NAMES", out var tn) && tn is Dictionary<string, object> tnd)
                    {
                        for (int i = 1; i <= 10; i++)
                        {
                            var k = $"TARGET_NAME_{i}";
                            if (_parameterControls.ContainsKey(k))
                            {
                                var def = tnd.TryGetValue($"Target{i}", out var v) ? v?.ToString() : $"Target{i}";
                                SetIfPresent(k, def);
                            }
                        }
                    }
                    UpdateDynamicTargetNamesSection();
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
            // Update backing parameter map so dynamic UI sections use up-to-date values
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

        private Dictionary<string, object> GetParameterDifferences(Dictionary<string, object> wellParams, Dictionary<string, object> globalParams)
        {
            var differences = new Dictionary<string, object>();
            
            foreach (var kvp in wellParams)
            {
                var key = kvp.Key;
                var wellValue = kvp.Value;
                
                if (!globalParams.ContainsKey(key))
                {
                    // Parameter doesn't exist in global, so it's a difference
                    differences[key] = wellValue;
                    continue;
                }
                
                var globalValue = globalParams[key];
                
                // Deep comparison for complex parameters
                if (!AreParameterValuesEqual(wellValue, globalValue))
                {
                    differences[key] = wellValue;
                }
            }
            
            return differences;
        }

        private bool AreParameterValuesEqual(object? value1, object? value2)
        {
            if (value1 == null && value2 == null) return true;
            if (value1 == null || value2 == null) return false;
            
            // Handle structured parameters (EXPECTED_CENTROIDS, COPY_NUMBER_SPEC, TARGET_NAMES)
            if (value1 is Dictionary<string, object> dict1 && value2 is Dictionary<string, object> dict2)
            {
                if (dict1.Count != dict2.Count) return false;
                
                foreach (var kvp in dict1)
                {
                    if (!dict2.ContainsKey(kvp.Key) || !AreParameterValuesEqual(kvp.Value, dict2[kvp.Key]))
                        return false;
                }
                return true;
            }
            
            if (value1 is List<Dictionary<string, object>> list1 && value2 is List<Dictionary<string, object>> list2)
            {
                if (list1.Count != list2.Count) return false;
                
                for (int i = 0; i < list1.Count; i++)
                {
                    if (!AreParameterValuesEqual(list1[i], list2[i]))
                        return false;
                }
                return true;
            }
            
            if (value1 is double[] arr1 && value2 is double[] arr2)
            {
                return arr1.SequenceEqual(arr2);
            }
            
            // Handle numeric comparisons with tolerance for floating point precision
            if (value1 is double d1 && value2 is double d2)
            {
                return Math.Abs(d1 - d2) < 1e-10;
            }
            
            if (value1 is float f1 && value2 is float f2)
            {
                return Math.Abs(f1 - f2) < 1e-7;
            }
            
            // Default comparison
            return value1.Equals(value2);
        }

        private void ApplyButton_Click(object sender, RoutedEventArgs e)
        {
            // Apply: Save only parameters that differ from global defaults
            var updatedParameters = new Dictionary<string, object>();
            
            foreach (var kvp in _parameterControls)
            {
                var key = kvp.Key;
                var control = kvp.Value;
                
                object? newValue = null;
                
                if (control is TextBox textBox)
                {
                    newValue = textBox.Text;
                }
                else if (control is ComboBox comboBox)
                {
                    if (key.Contains("ENABLE_") || key.Contains("CLASSIFY_") || key.Contains("USE_"))
                    {
                        newValue = comboBox.SelectedItem?.ToString() == "Yes";
                    }
                    else
                    {
                        newValue = comboBox.SelectedItem?.ToString();
                    }
                }
                
                if (newValue != null)
                {
                    updatedParameters[key] = newValue;
                }
            }

            // Convert flat parameter structure to the structured format expected by Python backend
            var structuredParameters = ConvertToStructuredParameters(updatedParameters);
            var structuredGlobalParams = ConvertToStructuredParameters(_globalParameters);
            
            // Only store parameters that differ from global defaults
            var differentialParameters = GetParameterDifferences(structuredParameters, structuredGlobalParams);
            
            // Determine target wells (single or multi)
            var targets = (_multiWellIds != null && _multiWellIds.Count > 1)
                ? _multiWellIds
                : new List<string> { _wellResult.WellId };

            // Save parameters for each target well
            foreach (var wellId in targets)
            {
                ParametersService.SaveWellParameters(wellId, differentialParameters);
            }

            // Notify appropriately
            if (targets.Count > 1)
            {
                MultiWellParametersApplied?.Invoke(targets, differentialParameters);
            }
            else
            {
                WellParametersApplied?.Invoke(_wellResult.WellId, differentialParameters);
            }
            
            DialogResult = true;
            Close();
        }

        private void CancelButton_Click(object sender, RoutedEventArgs e)
        {
            DialogResult = false;
            Close();
        }
        
        private Dictionary<string, object> GetDefaultParameters()
        {
            // Return the same default parameters as ParametersService
            return new Dictionary<string, object>
            {
                {"HDBSCAN_MIN_CLUSTER_SIZE", 4},
                {"HDBSCAN_MIN_SAMPLES", 70},
                {"HDBSCAN_EPSILON", 0.06},
                {"MIN_POINTS_FOR_CLUSTERING", 50},
                {"HDBSCAN_METRIC", "euclidean"},
                {"HDBSCAN_CLUSTER_SELECTION_METHOD", "eom"},
                
                {"BASE_TARGET_TOLERANCE", 750.0},
                {"CHROMOSOME_COUNT", 5},
                {"EXPECTED_CENTROIDS_Negative", "1000,900"},
                {"EXPECTED_CENTROIDS_Chrom1", "1000,2300"},
                {"EXPECTED_CENTROIDS_Chrom2", "1800,2200"},
                {"EXPECTED_CENTROIDS_Chrom3", "2400,1750"},
                {"EXPECTED_CENTROIDS_Chrom4", "3100,1300"},
                {"EXPECTED_CENTROIDS_Chrom5", "3500,900"},
                
                {"MIN_USABLE_DROPLETS", 3000},
                {"COPY_NUMBER_MEDIAN_DEVIATION_THRESHOLD", 0.15},
                {"COPY_NUMBER_MULTIPLIER", 4.0},
                {"TOLERANCE_MULTIPLIER", 3.0},
                {"LOWER_DEVIATION_TARGET", 0.75},
                {"UPPER_DEVIATION_TARGET", 1.25},
                
                {"X_AXIS_MIN", 0},
                {"X_AXIS_MAX", 3000},
                {"Y_AXIS_MIN", 0},
                {"Y_AXIS_MAX", 5000},
                {"X_GRID_INTERVAL", 500},
                {"Y_GRID_INTERVAL", 1000},
                {"INDIVIDUAL_PLOT_DPI", 300},
                
                {"ENABLE_FLUOROPHORE_MIXING", true},
                {"AMPLITUDE_NON_LINEARITY", 1.0},
                {"ENABLE_COPY_NUMBER_ANALYSIS", true},
                {"CLASSIFY_CNV_DEVIATIONS", true}
            };
        }
    }
}
