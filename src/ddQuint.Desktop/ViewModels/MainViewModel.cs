using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.ComponentModel;
using System.IO;
using System.Linq;
using System.Runtime.CompilerServices;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Input;
using ddQuint.Core.Models;
using ddQuint.Desktop.Commands;
using ddQuint.Desktop.Models;
using ddQuint.Desktop.Services;
using Microsoft.Win32;

namespace ddQuint.Desktop.ViewModels
{
    public class MainViewModel : INotifyPropertyChanged, IFilterableViewModel
    {
        private readonly AnalysisService _analysisService;
        private readonly PythonEnvironmentService _pythonService;
        
        private string? _inputFolderPath;
        private string? _templateFilePath;
        private string? _statusMessage = "Ready";
        private bool _isProcessing;
        private double _progressValue;
        private bool _showLogs = true;
        private bool _showFilters = true;
        private bool _hideBufferZone;
        private bool _hideWarnings;
        private string? _plateOverviewImagePath;
        private string _logMessages = "";
        private int _templateDescriptionCount = 4;
        private string? _resultsJsonPath; // path to latest results.json
        
        private ObservableCollection<WellResult> _wells;
        private ObservableCollection<WellResult> _filteredWells;
        private WellResult? _selectedWell;
        private ObservableCollection<WellResult> _selectedWells = new();
        private ObservableCollection<OverviewWell> _overviewWells = new();
        private bool _showOverview;
        private int _overviewColumns = 3;
        private int _multiColumns = 3;
        private int _overviewRows = 3;
        private int _multiRows = 3;
        private double _plotZoom = 1.0;
        private double _gridZoom = 1.0;
        private double _minGridZoom = 0.1;
        private double _overviewGridWidth = 1870.0; // Dynamic width (default fallback)
        private double _overviewGridHeight = 1100.0; // Dynamic height (default fallback)
        private double _multiGridWidth = 800.0;
        private double _multiGridHeight = 600.0;
        
        public MainViewModel()
        {
            try
            {
                LogMessage("MainViewModel constructor started");
                
                LogMessage("Creating AnalysisService...");
                _analysisService = new AnalysisService();
                
                LogMessage("Getting PythonEnvironmentService instance...");
                _pythonService = PythonEnvironmentService.Instance;
                
                LogMessage("Creating collections...");
                _wells = new ObservableCollection<WellResult>();
                _filteredWells = new ObservableCollection<WellResult>();
                
                LogMessage("Loading template description count from settings...");
                LoadTemplateDescriptionCount();
                
                LogMessage("Initializing commands...");
                InitializeCommands();
                
                LogMessage("Subscribing to analysis service events...");
                // Subscribe to analysis service events
                _analysisService.ProgressChanged += OnProgressChanged;
                _analysisService.StatusChanged += OnStatusChanged;
                _analysisService.LogMessageAdded += OnLogMessageAdded;
                _analysisService.WellCompleted += OnWellCompleted;
                
                LogMessage("MainViewModel constructor completed successfully");
            }
            catch (Exception ex)
            {
                var errorMsg = $"FATAL ERROR in MainViewModel constructor: {ex.Message}\nStack: {ex.StackTrace}";
                LogMessage(errorMsg);
                
                try
                {
                    MessageBox.Show(errorMsg, "MainViewModel Creation Error", MessageBoxButton.OK, MessageBoxImage.Error);
                }
                catch
                {
                    // If MessageBox fails, write to file
                    try
                    {
                        File.WriteAllText(Path.Combine(Path.GetTempPath(), "ddquint_viewmodel_error.txt"), errorMsg);
                    }
                    catch { }
                }
                throw;
            }
            
            // Initialize Python environment asynchronously
            _ = InitializePythonEnvironmentAsync();
        }
        
        private async Task InitializePythonEnvironmentAsync()
        {
            try
            {
                await Task.Run(() => _pythonService.Initialize());
                StatusMessage = "Ready - Python environment initialized";
                AddLogMessage("Python environment initialized successfully");
            }
            catch (Exception ex)
            {
                StatusMessage = $"Warning: Python environment initialization failed - {ex.Message}";
                AddLogMessage($"WARNING: Python environment initialization failed: {ex.Message}");
                AddLogMessage("Analysis functionality may not work properly. Please ensure Python 3.9+ is installed with required packages.");
            }
        }
        
        #region Properties
        
        public string? InputFolderPath
        {
            get => _inputFolderPath;
            set
            {
                _inputFolderPath = value;
                OnPropertyChanged();
                OnPropertyChanged(nameof(CanAnalyze));
            }
        }
        
        public string? TemplateFilePath
        {
            get => _templateFilePath;
            set
            {
                _templateFilePath = value;
                OnPropertyChanged();
            }
        }
        
        public int TemplateDescriptionCount
        {
            get => _templateDescriptionCount;
            private set
            {
                _templateDescriptionCount = value;
                OnPropertyChanged();
            }
        }
        
        public string StatusMessage
        {
            get => _statusMessage ?? "Ready";
            set
            {
                _statusMessage = value;
                OnPropertyChanged();
            }
        }
        
        public bool IsProcessing
        {
            get => _isProcessing;
            set
            {
                _isProcessing = value;
                OnPropertyChanged();
                OnPropertyChanged(nameof(CanAnalyze));
            }
        }
        
        public double ProgressValue
        {
            get => _progressValue;
            set
            {
                _progressValue = value;
                OnPropertyChanged();
            }
        }
        
        public bool ShowLogs
        {
            get => _showLogs;
            set
            {
                _showLogs = value;
                OnPropertyChanged();
            }
        }
        
        public bool ShowFilters
        {
            get => _showFilters;
            set
            {
                _showFilters = value;
                OnPropertyChanged();
            }
        }
        
        public bool HideBufferZone
        {
            get => _hideBufferZone;
            set
            {
                _hideBufferZone = value;
                OnPropertyChanged();
                UpdateFilteredWells();
            }
        }
        
        public bool HideWarnings
        {
            get => _hideWarnings;
            set
            {
                _hideWarnings = value;
                OnPropertyChanged();
                UpdateFilteredWells();
            }
        }
        
        public string? PlateOverviewImagePath
        {
            get => _plateOverviewImagePath;
            set
            {
                _plateOverviewImagePath = value;
                OnPropertyChanged();
            }
        }
        
        public string LogMessages
        {
            get => _logMessages;
            set
            {
                _logMessages = value;
                OnPropertyChanged();
            }
        }
        
        public ObservableCollection<WellResult> Wells
        {
            get => _wells;
            set
            {
                _wells = value;
                OnPropertyChanged();
                UpdateFilteredWells();
                
                // Generate overview wells when wells are loaded
                if (_wells != null && _wells.Count > 0)
                {
                    GenerateOverviewWells();
                }
            }
        }
        
        public ObservableCollection<WellResult> FilteredWells
        {
            get => _filteredWells;
            private set
            {
                _filteredWells = value;
                OnPropertyChanged();
            }
        }
        
        public WellResult? SelectedWell
        {
            get => _selectedWell;
            set
            {
                try
                {
                    _selectedWell = value;
                    OnPropertyChanged();
                    OnPropertyChanged(nameof(HasSelectedWell));
                    OnPropertyChanged(nameof(IsMultiSelection));
                    OnPropertyChanged(nameof(ShowMultiView));
                    OnPropertyChanged(nameof(EditButtonText));
                    OnPropertyChanged(nameof(CanEditSelection));
                }
                catch (Exception ex)
                {
                    AddLogMessage($"Error selecting well: {ex.Message}");
                    _selectedWell = null;
                    OnPropertyChanged();
                    OnPropertyChanged(nameof(HasSelectedWell));
                    OnPropertyChanged(nameof(IsMultiSelection));
                    OnPropertyChanged(nameof(ShowMultiView));
                    OnPropertyChanged(nameof(EditButtonText));
                    OnPropertyChanged(nameof(CanEditSelection));
                }
            }
        }
        
        public ObservableCollection<WellResult> SelectedWells
        {
            get => _selectedWells;
            set
            {
                _selectedWells = value ?? new ObservableCollection<WellResult>();
                OnPropertyChanged();
                OnPropertyChanged(nameof(IsMultiSelection));
                OnPropertyChanged(nameof(EditButtonText));
                OnPropertyChanged(nameof(CanEditSelection));
                // Keep SelectedWell in sync (first selected when multi)
                if (_selectedWells.Count > 0) SelectedWell = _selectedWells[0];
            }
        }

        public ObservableCollection<OverviewWell> OverviewWells
        {
            get => _overviewWells;
            set
            {
                _overviewWells = value ?? new ObservableCollection<OverviewWell>();
                OnPropertyChanged();
            }
        }

        
        public bool CanAnalyze => !string.IsNullOrEmpty(InputFolderPath) && !IsProcessing;
        public bool HasResults => Wells.Any();
        public bool HasSelectedWell => SelectedWell != null;
        public bool IsMultiSelection => SelectedWells != null && SelectedWells.Count > 1;
        public bool ShowOverview
        {
            get => _showOverview;
            set
            {
                _showOverview = value;
                
                // Reset minimum zoom when switching away from overview to prevent interference
                if (!value)
                {
                    _minGridZoom = 0.1; // Reset to default minimum
                    AddLogMessage($"🔍 MinGridZoom reset to default (0.1) when exiting overview");
                }
                
                OnPropertyChanged();
                OnPropertyChanged(nameof(ShowMultiView));
                // Generate appropriate wells based on current view mode
                GenerateCurrentViewWells();
            }
        }

        public bool ShowMultiView => !ShowOverview && IsMultiSelection;

        // Handle multi-well parameter application as a batch
        public async void OnMultiWellParametersApplied(IEnumerable<string> wellIds, Dictionary<string, object> updatedParameters)
        {
            try
            {
                var ids = wellIds?.Distinct().ToList() ?? new List<string>();
                AddLogMessage($"=== OnMultiWellParametersApplied START ===");
                AddLogMessage($"Batch parameters updated for {ids.Count} wells");
                if (updatedParameters != null)
                {
                    foreach (var p in updatedParameters)
                        AddLogMessage($"  MULTI CHANGED: {p.Key} = {p.Value}");
                }

                if (!string.IsNullOrEmpty(InputFolderPath) && ids.Count > 0)
                {
                    StatusMessage = $"Reprocessing {ids.Count} wells...";
                    await ReprocessMultipleWellsAsync(ids);
                }
                else
                {
                    AddLogMessage("No input folder or no wells provided for batch reprocess");
                }

                AddLogMessage($"=== OnMultiWellParametersApplied END ===");
            }
            catch (Exception ex)
            {
                StatusMessage = $"Error in multi-well reprocess: {ex.Message}";
                AddLogMessage($"ERROR in OnMultiWellParametersApplied: {ex.Message}");
            }
        }

        private async Task ReprocessMultipleWellsAsync(IEnumerable<string> wellIds)
        {
            try
            {
                IsProcessing = true;
                var ids = wellIds.Distinct().ToList();
                foreach (var id in ids)
                {
                    try
                    {
                        var analysisResults = await _analysisService.ReprocessSingleWellAsync(InputFolderPath!, id, TemplateFilePath);
                        if (analysisResults != null && analysisResults.Count > 0)
                        {
                            var updatedWell = analysisResults.First();
                            Application.Current.Dispatcher.Invoke(() =>
                            {
                                var idx = Wells.ToList().FindIndex(w => w.WellId == id);
                                if (idx >= 0) Wells[idx] = updatedWell;
                            });
                        }
                    }
                    catch (Exception ex)
                    {
                        AddLogMessage($"Reprocess failed for {id}: {ex.Message}");
                    }
                }
                Application.Current.Dispatcher.Invoke(UpdateFilteredWells);
                StatusMessage = $"Reprocessed {ids.Count} wells";
            }
            finally
            {
                IsProcessing = false;
            }
        }

        // Dynamic UI helpers for edit button
        public string EditButtonText
        {
            get
            {
                if (IsMultiSelection)
                {
                    var count = SelectedWells?.Count ?? 0;
                    return count > 1 ? $"Edit {count} Wells" : "Edit This Well";
                }
                return "Edit This Well";
            }
        }

        public bool CanEditSelection
        {
            get
            {
                if (IsMultiSelection)
                {
                    return SelectedWells != null && SelectedWells.Count > 1 && SelectedWells.All(w => w.HasData);
                }
                return SelectedWell?.HasData == true;
            }
        }

        public int OverviewColumns
        {
            get => _overviewColumns;
            set { if (_overviewColumns != value) { _overviewColumns = value; OnPropertyChanged(); } }
        }

        public int MultiColumns
        {
            get => _multiColumns;
            set { if (_multiColumns != value) { _multiColumns = value; OnPropertyChanged(); } }
        }

        public int OverviewRows
        {
            get => _overviewRows;
            set { if (_overviewRows != value) { _overviewRows = value; OnPropertyChanged(); } }
        }

        public int MultiRows
        {
            get => _multiRows;
            set { if (_multiRows != value) { _multiRows = value; OnPropertyChanged(); } }
        }

        public double PlotZoom
        {
            get => _plotZoom;
            set { if (Math.Abs(_plotZoom - value) > 0.0001) { _plotZoom = value; OnPropertyChanged(); } }
        }

        public double GridZoom
        {
            get => _gridZoom;
            set 
            { 
                // Enforce minimum and maximum zoom limits
                double clampedValue = Math.Max(_minGridZoom, Math.Min(5.0, value));
                if (Math.Abs(_gridZoom - clampedValue) > 0.0001) 
                { 
                    var caller = new System.Diagnostics.StackTrace().GetFrame(1)?.GetMethod()?.Name ?? "Unknown";
                    if (clampedValue != value)
                    {
                        AddLogMessage($"🔍 GridZoom clamped from {value:F3} to {clampedValue:F3} (min={_minGridZoom:F3}) - called from {caller}");
                    }
                    else
                    {
                        AddLogMessage($"🔍 GridZoom changing from {_gridZoom:F3} to {clampedValue:F3} - called from {caller}");
                    }
                    _gridZoom = clampedValue; 
                    OnPropertyChanged(); 
                    OnPropertyChanged(nameof(ScrollableWidth));
                    OnPropertyChanged(nameof(ScrollableHeight));
                    // Both views now use the same zoom, so notify current dimensions
                    OnPropertyChanged(nameof(CurrentGridWidth));
                    OnPropertyChanged(nameof(CurrentGridHeight));
                } 
            }
        }

        // Dynamic dimensions based on actual grid layout (using existing fields above)
        
        // Unified scrollable dimensions - use current active grid dimensions
        public double ScrollableWidth => Math.Max(CurrentGridWidth, CurrentGridWidth * GridZoom);
        public double ScrollableHeight => Math.Max(CurrentGridHeight, CurrentGridHeight * GridZoom);
        
        // Current grid dimensions switch based on active view
        public double CurrentGridWidth => ShowOverview ? _overviewGridWidth : _multiGridWidth;
        public double CurrentGridHeight => ShowOverview ? _overviewGridHeight : _multiGridHeight;

        public void SetMinGridZoom(double minZoom)
        {
            _minGridZoom = Math.Max(0.1, minZoom);
            AddLogMessage($"🔍 MinGridZoom set to {_minGridZoom:F3}");
        }

        // MultiZoom removed - now using unified GridZoom for both views

        public double OverviewGridWidth
        {
            get => _overviewGridWidth;
            set { if (Math.Abs(_overviewGridWidth - value) > 0.1) { _overviewGridWidth = value; OnPropertyChanged(); } }
        }

        public double OverviewGridHeight
        {
            get => _overviewGridHeight;
            set { if (Math.Abs(_overviewGridHeight - value) > 0.1) { _overviewGridHeight = value; OnPropertyChanged(); } }
        }

        public double MultiGridWidth
        {
            get => _multiGridWidth;
            set { if (Math.Abs(_multiGridWidth - value) > 0.1) { _multiGridWidth = value; OnPropertyChanged(); } }
        }

        public double MultiGridHeight
        {
            get => _multiGridHeight;
            set { if (Math.Abs(_multiGridHeight - value) > 0.1) { _multiGridHeight = value; OnPropertyChanged(); } }
        }
        
        #endregion
        
        #region Commands
        
        public ICommand SelectInputFolderCommand { get; private set; } = null!;
        public ICommand SelectTemplateFileCommand { get; private set; } = null!;
        public ICommand AnalyzeCommand { get; private set; } = null!;
        public ICommand ExportResultsCommand { get; private set; } = null!; // Excel-only (menu)
        public ICommand ExportAllCommand { get; private set; } = null!;
        public ICommand ShowGlobalParametersCommand { get; private set; } = null!;
        public ICommand EditSelectedWellCommand { get; private set; } = null!;
        public ICommand ShowTemplateCreatorCommand { get; private set; } = null!;
        public ICommand ShowAboutCommand { get; private set; } = null!;
        public ICommand ShowFilterOptionsCommand { get; private set; } = null!;
        public ICommand ShowHelpCommand { get; private set; } = null!;
        
        private void InitializeCommands()
        {
            SelectInputFolderCommand = new RelayCommand(SelectInputFolder);
            SelectTemplateFileCommand = new RelayCommand(SelectTemplateFile);
            AnalyzeCommand = new AsyncRelayCommand(AnalyzeAsync, () => CanAnalyze);
            ExportResultsCommand = new RelayCommand(ExportResults, () => HasResults); // Excel-only
            ExportAllCommand = new RelayCommand(ExportAll, () => HasResults);
            ShowGlobalParametersCommand = new RelayCommand(ShowGlobalParameters);
            EditSelectedWellCommand = new RelayCommand(EditSelectedWell, () => HasSelectedWell);
            ShowTemplateCreatorCommand = new RelayCommand(ShowTemplateCreator);
            ShowAboutCommand = new RelayCommand(ShowAbout);
            ShowFilterOptionsCommand = new RelayCommand(ShowFilterOptions);
            ShowHelpCommand = new RelayCommand(ShowHelp);
        }
        
        #endregion

        #region Selection helpers (called from view)
        public void SetSelectedWells(IEnumerable<WellResult> wells)
        {
            _selectedWells.Clear();
            foreach (var w in wells)
            {
                _selectedWells.Add(w);
            }
            OnPropertyChanged(nameof(SelectedWells));
            OnPropertyChanged(nameof(IsMultiSelection));
            OnPropertyChanged(nameof(ShowMultiView));
            SelectedWell = _selectedWells.FirstOrDefault();
            
            // Generate appropriate wells for current view mode
            GenerateCurrentViewWells();
        }
        #endregion
        
        #region Command Implementations
        
        private void SelectInputFolder()
        {
            AddLogMessage("=== SelectInputFolder CALLED ===");
            try
            {
                // Close popup immediately when dialog opens
                OnClosePopupRequested();
                
                var dialog = new System.Windows.Forms.FolderBrowserDialog()
                {
                    Description = "Select folder containing QX Manager CSV files",
                    ShowNewFolderButton = false,
                    RootFolder = Environment.SpecialFolder.MyComputer
                };
                // Choose sensible default start folder, preferring persisted last directory like macOS:
                // 1) Use LastDir_InputFolder if available
                // 2) Else, if current InputFolderPath contains CSVs, start at its parent
                // 3) Else, use current InputFolderPath
                try
                {
                    var last = GetLastDirectory("LastDir_InputFolder");
                    if (!string.IsNullOrWhiteSpace(last))
                    {
                        dialog.SelectedPath = last;
                    }
                    else if (!string.IsNullOrWhiteSpace(InputFolderPath) && Directory.Exists(InputFolderPath))
                    {
                        var hasCsv = Directory.GetFiles(InputFolderPath, "*.csv").Length > 0;
                        var startPath = hasCsv ? Directory.GetParent(InputFolderPath)?.FullName : InputFolderPath;
                        if (!string.IsNullOrWhiteSpace(startPath) && Directory.Exists(startPath))
                        {
                            dialog.SelectedPath = startPath;
                        }
                    }
                }
                catch { /* ignore */ }
                
                AddLogMessage("About to show folder selection dialog...");
                var result = dialog.ShowDialog();
                AddLogMessage($"Dialog result: {result}");
                
                if (result == System.Windows.Forms.DialogResult.OK)
                {
                    var selectedDirectory = dialog.SelectedPath;
                    AddLogMessage($"User selected directory: {selectedDirectory}");
                    if (!string.IsNullOrEmpty(selectedDirectory))
                    {
                        InputFolderPath = selectedDirectory;
                        // Offer to apply parameters if a ddQuint_Parameters.json file exists (macOS parity)
                        TryApplyParametersFromFolder(InputFolderPath);
                        // Persist last used input folder
                        SetLastDirectory(InputFolderPath, "LastDir_InputFolder");
                        StatusMessage = $"Selected input folder: {Path.GetFileName(InputFolderPath)}";
                        AddLogMessage($"Input folder selected: {InputFolderPath}");
                        
                        // Check for CSV files
                        var csvFiles = Directory.GetFiles(InputFolderPath, "*.csv");
                        AddLogMessage($"Found {csvFiles.Length} CSV files in selected folder");
                        
                        if (csvFiles.Length == 0)
                        {
                            MessageBox.Show(
                                "No CSV files found in the selected folder. Please select a folder containing QX Manager CSV files.",
                                "No CSV Files Found",
                                MessageBoxButton.OK,
                                MessageBoxImage.Warning);
                        }
                        else
                        {
                            // Auto-start analysis when CSV files are present
                            AddLogMessage("Auto-starting analysis...");
                            if (AnalyzeCommand.CanExecute(null))
                            {
                                AnalyzeCommand.Execute(null);
                            }
                        }
                    }
                }
            }
            catch (Exception ex)
            {
                StatusMessage = $"Error selecting folder: {ex.Message}";
                AddLogMessage($"ERROR selecting folder: {ex.Message}");
                MessageBox.Show($"Error selecting folder: {ex.Message}", "Error", 
                               MessageBoxButton.OK, MessageBoxImage.Error);
            }
        }
        
        private void SelectTemplateFile()
        {
            // Close popup immediately when dialog opens
            OnClosePopupRequested();
            
            var dialog = new OpenFileDialog()
            {
                Title = "Select QX Manager Template File",
                Filter = "CSV Files (*.csv)|*.csv|All Files (*.*)|*.*",
                CheckFileExists = true
            };
            
            try
            {
                var last = GetLastDirectory("LastDir_TemplateFile");
                if (!string.IsNullOrWhiteSpace(last) && Directory.Exists(last))
                {
                    dialog.InitialDirectory = last;
                }
            }
            catch { }
            
            if (dialog.ShowDialog() == true)
            {
                TemplateFilePath = dialog.FileName;
                try { SetLastDirectory(Path.GetDirectoryName(TemplateFilePath), "LastDir_TemplateFile"); } catch { }
                StatusMessage = $"Selected template: {Path.GetFileName(TemplateFilePath)}";
                AddLogMessage($"Template file selected: {TemplateFilePath}");
                
                // If we have a valid input folder and existing results, re-run analysis to apply template changes
                if (!string.IsNullOrEmpty(InputFolderPath) && HasResults && !IsProcessing)
                {
                    AddLogMessage($"Template changed - reanalyzing existing data with new template...");
                    // Clear previous results before reanalysis (on UI thread)
                    Application.Current.Dispatcher.Invoke(() =>
                    {
                        Wells.Clear();
                        FilteredWells.Clear();
                        SelectedWell = null;
                        OnPropertyChanged(nameof(HasResults));
                        PlateOverviewImagePath = null;
                    });
                    
                    _ = AnalyzeAsync();
                }
                else if (!HasResults)
                {
                    AddLogMessage("Template file selected. Select an input folder with CSV data files to begin analysis.");
                }
                else if (string.IsNullOrEmpty(InputFolderPath))
                {
                    AddLogMessage("Template file selected. No input folder set - template will be used when analysis is run.");
                }
            }
        }

        private void TryApplyParametersFromFolder(string folderPath)
        {
            try
            {
                var paramsFile = Path.Combine(folderPath, "ddQuint_Parameters.json");
                if (!File.Exists(paramsFile)) return;
                var result = MessageBox.Show(
                    "The selected folder contains a 'ddQuint_Parameters.json' file.\n\nApply these parameters before analysis?",
                    "Parameters file found",
                    MessageBoxButton.YesNo,
                    MessageBoxImage.Question);
                if (result != MessageBoxResult.Yes) return;

                var text = File.ReadAllText(paramsFile);
                var obj = Newtonsoft.Json.Linq.JObject.Parse(text);

                // Globals
                if (obj["global_parameters"] is Newtonsoft.Json.Linq.JObject g)
                {
                    var dict = g.ToObject<Dictionary<string, object>>() ?? new();
                    // Normalize to export shape to avoid duplicate CN dicts and bad types
                    var prepared = ParametersService.PrepareForExport(dict);
                    ParametersService.SaveGlobalParameters(prepared);
                    var confirm = ParametersService.LoadGlobalParameters();
                    AddLogMessage($"Applied globals from bundle. ENABLE_FLUOROPHORE_MIXING now: {confirm.GetValueOrDefault("ENABLE_FLUOROPHORE_MIXING", true)} CHROMOSOME_COUNT: {confirm.GetValueOrDefault("CHROMOSOME_COUNT", 0)}");
                }
                // Wells
                if (obj["well_parameters"] is Newtonsoft.Json.Linq.JObject wp)
                {
                    foreach (var p in wp)
                    {
                        var wellId = p.Key;
                        var vals = (p.Value as Newtonsoft.Json.Linq.JObject)?.ToObject<Dictionary<string, object>>() ?? new();
                        ParametersService.SaveWellParameters(wellId, vals);
                    }
                }
                // Template fields
                var tdc = obj["template_description_count"]?.ToObject<int?>();
                if (tdc.HasValue && tdc.Value >= 1 && tdc.Value <= 4) SetTemplateDescriptionCount(tdc.Value);
                var tpl = obj["template_file"]?.ToObject<string>();
                if (!string.IsNullOrWhiteSpace(tpl) && File.Exists(tpl)) TemplateFilePath = tpl;

                AddLogMessage("Applied parameters from folder ddQuint_Parameters.json");
            }
            catch (Exception ex)
            {
                AddLogMessage($"Failed to apply parameters from folder: {ex.Message}");
            }
        }
        
        private async Task AnalyzeAsync()
        {
            try
            {
                AddLogMessage($"=== AnalyzeAsync START ===");
                AddLogMessage($"InputFolderPath: {InputFolderPath ?? "null"}");
                AddLogMessage($"TemplateFilePath: {TemplateFilePath ?? "null"}");
                
                IsProcessing = true;
                StatusMessage = "Analyzing files...";
                
                // Clear previous results (ensure on UI thread)
                Application.Current.Dispatcher.Invoke(() =>
                {
                    Wells.Clear();
                    FilteredWells.Clear();
                    SelectedWell = null;
                    OnPropertyChanged(nameof(HasResults));
                    PlateOverviewImagePath = null;
                });
                
                AddLogMessage("About to call AnalysisService.AnalyzeAsync");
                
                // Run analysis (wells will be added progressively via OnWellCompleted event)
                var results = await _analysisService.AnalyzeAsync(InputFolderPath!, TemplateFilePath, TemplateDescriptionCount);
                
                AddLogMessage($"AnalysisService.AnalyzeAsync completed. Results: Wells={results.Wells.Count}, PlateOverview={results.PlateOverviewImagePath ?? "null"}");
                
                // Set plate overview image path
                PlateOverviewImagePath = results.PlateOverviewImagePath;
                // Store results.json path for exports
                try { _resultsJsonPath = results.ResultsJsonPath; } catch { _resultsJsonPath = null; }
                // Note: Do NOT update InputFolderPath from analysis results - it should only be set by user selection
                
                // Generate overview wells
                GenerateOverviewWells();

                StatusMessage = $"Analysis completed: {Wells.Count} wells processed";
                AddLogMessage($"Analysis completed successfully. {Wells.Count} wells processed.");
                AddLogMessage($"=== AnalyzeAsync END ===");
            }
            catch (Exception ex)
            {
                StatusMessage = $"Analysis failed: {ex.Message}";
                AddLogMessage($"ERROR in AnalyzeAsync: {ex.Message}");
                AddLogMessage($"STACK TRACE: {ex.StackTrace}");
                MessageBox.Show($"Analysis failed: {ex.Message}", "Error", 
                               MessageBoxButton.OK, MessageBoxImage.Error);
            }
            finally
            {
                IsProcessing = false;
                ProgressValue = 0;
                Application.Current.Dispatcher.Invoke(() =>
                {
                    UpdateFilteredWells();
                });
                AddLogMessage($"AnalyzeAsync finally block completed. IsProcessing={IsProcessing}");
            }
        }
        
        // Single well reprocessing method matching macOS behavior
        private async Task ReprocessSingleWellAsync(string wellId)
        {
            try
            {
                AddLogMessage($"=== ReprocessSingleWellAsync START for {wellId} ===");
                IsProcessing = true;
                
                // Find the specific well to reprocess
                var wellToProcess = Wells.FirstOrDefault(w => w.WellId == wellId);
                if (wellToProcess == null)
                {
                    AddLogMessage($"ERROR: Well {wellId} not found in current results");
                    StatusMessage = $"Error: Well {wellId} not found";
                    return;
                }
                
                AddLogMessage($"Found well {wellId} to reprocess. Status: {wellToProcess.Status}");
                StatusMessage = $"Reprocessing well {wellId}...";
                
                // Call AnalysisService to reprocess just this specific well
                if (string.IsNullOrEmpty(InputFolderPath))
                {
                    AddLogMessage($"ERROR: InputFolderPath is null or empty for well {wellId}");
                    StatusMessage = $"Error: No input folder set";
                    return;
                }
                
                var analysisResults = await _analysisService.ReprocessSingleWellAsync(
                    InputFolderPath, 
                    wellId, 
                    TemplateFilePath);
                
                if (analysisResults != null && analysisResults.Count > 0)
                {
                    // Update only the specific well in the results
                    Application.Current.Dispatcher.Invoke(() =>
                    {
                        var updatedWell = analysisResults.FirstOrDefault();
                        if (updatedWell != null)
                        {
                            // Find and replace the well in the Wells collection
                            var existingWellIndex = Wells.ToList().FindIndex(w => w.WellId == wellId);
                            if (existingWellIndex >= 0)
                            {
                                Wells[existingWellIndex] = updatedWell;
                                AddLogMessage($"Well {wellId} updated in collection at index {existingWellIndex}");
                                
                                // Update selected well if it's the one we just processed
                                if (SelectedWell?.WellId == wellId)
                                {
                                    SelectedWell = updatedWell;
                                    AddLogMessage($"Updated SelectedWell to reprocessed well {wellId}");
                                }
                            }
                            
                            UpdateFilteredWells();
                            StatusMessage = $"Well {wellId} reprocessed successfully with custom parameters";
                            AddLogMessage($"Well {wellId} reprocessing completed successfully");
                        }
                    });
                }
                else
                {
                    StatusMessage = $"Error reprocessing well {wellId}";
                    AddLogMessage($"ERROR: No results returned from single well analysis for {wellId}");
                }
            }
            catch (Exception ex)
            {
                StatusMessage = $"Error reprocessing well {wellId}: {ex.Message}";
                AddLogMessage($"ERROR in ReprocessSingleWellAsync for {wellId}: {ex.Message}");
                AddLogMessage($"STACK TRACE: {ex.StackTrace}");
            }
            finally
            {
                IsProcessing = false;
                AddLogMessage($"=== ReprocessSingleWellAsync END for {wellId} ===");
            }
        }
        
        private async void ExportResults()
        {
            // Export Excel results (matches macOS Export Excel Results...)
            try
            {
                if (!HasResults)
                {
                    MessageBox.Show("No results to export. Please analyze a folder first.", "Export", MessageBoxButton.OK, MessageBoxImage.Information);
                    return;
                }

                // Pick save location
                var sfd = new Microsoft.Win32.SaveFileDialog
                {
                    Title = "Export Excel Results",
                    Filter = "Excel Workbook (*.xlsx)|*.xlsx|All Files (*.*)|*.*",
                    FileName = "ddQuint_Results.xlsx"
                };
                try
                {
                    var last = GetLastDirectory("LastDir_ExcelExport");
                    if (!string.IsNullOrWhiteSpace(last) && Directory.Exists(last))
                        sfd.InitialDirectory = last;
                }
                catch { }

                if (sfd.ShowDialog() != true) return;

                var savePath = sfd.FileName;
                try { SetLastDirectory(Path.GetDirectoryName(savePath), "LastDir_ExcelExport"); } catch { }

                // Discover output folder and results.json from any plot
                // Prefer the explicit results.json from the latest analysis (if available)
                var resultsJson = _resultsJsonPath ?? TryGetResultsJsonPath();
                if (string.IsNullOrWhiteSpace(resultsJson) || !File.Exists(resultsJson))
                {
                    MessageBox.Show("Could not locate results.json from the current analysis.", "Export", MessageBoxButton.OK, MessageBoxImage.Warning);
                    return;
                }

                StatusMessage = "Exporting Excel...";

                // Calculate maximum target count for proper Excel columns (matching macOS)
                var maxTargetCount = GetMaxTargetCount();

                // Create temp results file from current wells (matching macOS cached results approach)
                var tempDir = Path.GetTempPath();
                var tempResultsFile = Path.Combine(tempDir, $"ddquint_cached_results_{Guid.NewGuid():N}.json");
                
                try
                {
                    // Convert current Wells to JSON format expected by Python
                    var results = Wells.Select(well => new Dictionary<string, object>
                    {
                        ["well_id"] = well.WellId,
                        ["well"] = well.WellId, // Python expects 'well' key
                        ["sample_name"] = well.SampleName ?? "",
                        ["status"] = well.Status.ToString(),
                        ["total_droplets"] = well.TotalDroplets,
                        ["usable_droplets"] = well.UsableDroplets,
                        ["negative_droplets"] = well.NegativeDroplets,
                        ["copy_numbers"] = well.CopyNumbersDictionary ?? new Dictionary<string, double>(),
                        ["has_aneuploidy"] = well.AnalysisData?.GetValueOrDefault("has_aneuploidy", false) ?? false,
                        ["has_buffer_zone"] = well.AnalysisData?.GetValueOrDefault("has_buffer_zone", false) ?? false,
                        ["copy_number_states"] = well.AnalysisData?.GetValueOrDefault("copy_number_states") ?? new Dictionary<string, object>(),
                        ["analysis_data"] = well.AnalysisData ?? new Dictionary<string, object>()
                    }).ToList();

                    var json = Newtonsoft.Json.JsonConvert.SerializeObject(results, Newtonsoft.Json.Formatting.Indented);
                    File.WriteAllText(tempResultsFile, json);
                    AddLogMessage($"Created temp results file: {tempResultsFile}");
                }
                catch (Exception ex)
                {
                    StatusMessage = $"Excel export failed: {ex.Message}";
                    MessageBox.Show($"Failed to create temp results file: {ex.Message}", "Export Failed", MessageBoxButton.OK, MessageBoxImage.Error);
                    return;
                }

                // Build Python script using macOS approach with load_parameters_if_exist
                var script = $@"
import sys, os, json, traceback

try:
    # Initialize config properly (matching macOS approach)
    from ddquint.config import Config
    from ddquint.utils.parameter_editor import load_parameters_if_exist
    
    config = Config.get_instance()
    load_parameters_if_exist(Config)
    config.finalize_colors()
    
    # Import create_list_report
    from ddquint.core import create_list_report
    
    # Load cached results from temp file (matching macOS approach)
    with open(r'''{tempResultsFile}''', 'r') as f:
        results = json.load(f)
    
    print(f'DEBUG: Loaded {{len(results)}} cached results for Excel export')
    
    # Export to Excel using cached results with max target count (matching macOS)
    create_list_report(results, r'''{savePath}''', {maxTargetCount})
    print('EXCEL_EXPORT_SUCCESS_CACHED')
    
    # Clean up temp file
    os.remove(r'''{tempResultsFile}''')
    
except Exception as e:
    print('EXPORT_ERROR:', e)
    traceback.print_exc()
    sys.exit(1)
";

                var exec = await _pythonService.ExecutePythonScript(script, workingDirectory: null, persistScript: false);
                if (exec.ExitCode == 0 && (exec.Output.Contains("EXCEL_EXPORT_SUCCESS") || exec.Output.Contains("EXCEL_EXPORT_SUCCESS_CACHED")))
                {
                    StatusMessage = $"Excel export completed: {System.IO.Path.GetFileName(savePath)}";
                    // Do not open or pop any dialogs on success
                }
                else
                {
                    StatusMessage = "Excel export failed";
                    AddLogMessage($"Excel export error - Exit code: {exec.ExitCode}, Output: {exec.Output}, Error: {exec.Error}");
                    MessageBox.Show("Excel export failed. See logs for details.", "Export Failed", MessageBoxButton.OK, MessageBoxImage.Error);
                }
            }
            catch (Exception ex)
            {
                StatusMessage = $"Excel export failed: {ex.Message}";
                MessageBox.Show($"Export failed: {ex.Message}", "Export Failed", MessageBoxButton.OK, MessageBoxImage.Error);
            }
        }

        // Export all well plots to a folder
        public void ExportPlots()
        {
            try
            {
                if (!HasResults)
                {
                    MessageBox.Show("No results to export.", "Export Plots", MessageBoxButton.OK, MessageBoxImage.Information);
                    return;
                }

                // Choose export folder
                var dialog = new System.Windows.Forms.FolderBrowserDialog()
                {
                    Description = "Select folder to export plots",
                    ShowNewFolderButton = true,
                    RootFolder = Environment.SpecialFolder.MyComputer
                };
                try
                {
                    var last = GetLastDirectory("LastDir_PlotsExport");
                    if (!string.IsNullOrWhiteSpace(last)) dialog.SelectedPath = last;
                }
                catch { }

                if (dialog.ShowDialog() != System.Windows.Forms.DialogResult.OK) return;
                var exportFolder = dialog.SelectedPath;
                try { SetLastDirectory(exportFolder, "LastDir_PlotsExport"); } catch { }

                var graphsDir = TryGetGraphsDirectory();
                if (string.IsNullOrWhiteSpace(graphsDir) || !Directory.Exists(graphsDir))
                {
                    MessageBox.Show("Could not locate generated plots.", "Export Plots", MessageBoxButton.OK, MessageBoxImage.Warning);
                    return;
                }

                int copied = 0;
                foreach (var png in Directory.EnumerateFiles(graphsDir, "*.png"))
                {
                    try
                    {
                        var name = Path.GetFileName(png);
                        var dest = Path.Combine(exportFolder, name);
                        File.Copy(png, dest, overwrite: true);
                        copied++;
                    }
                    catch { }
                }

                StatusMessage = $"Exported {copied} plots";
                MessageBox.Show($"Exported {copied} plot image(s).", "Export Plots", MessageBoxButton.OK, MessageBoxImage.Information);
            }
            catch (Exception ex)
            {
                StatusMessage = $"Plot export failed: {ex.Message}";
                MessageBox.Show($"Plot export failed: {ex.Message}", "Export Plots", MessageBoxButton.OK, MessageBoxImage.Error);
            }
        }

        // Export current parameter bundle (global + well-specific)
        public void ExportParameters()
        {
            try
            {
                var sfd = new Microsoft.Win32.SaveFileDialog
                {
                    Title = "Export Parameters",
                    Filter = "JSON Files (*.json)|*.json|All Files (*.*)|*.*",
                    FileName = "ddQuint_Parameters.json"
                };
                try
                {
                    var last = GetLastDirectory("LastDir_ParametersExport");
                    if (!string.IsNullOrWhiteSpace(last) && Directory.Exists(last)) sfd.InitialDirectory = last;
                }
                catch { }

                if (sfd.ShowDialog() != true) return;
                var savePath = sfd.FileName;
                try { SetLastDirectory(Path.GetDirectoryName(savePath), "LastDir_ParametersExport"); } catch { }

                var globals = ParametersService.PrepareForExport(ParametersService.LoadGlobalParameters());
                var wells = ParametersService.GetAllWellParameters();
                var bundle = new Dictionary<string, object?>
                {
                    ["global_parameters"] = globals,
                    ["well_parameters"] = wells,
                    ["template_description_count"] = TemplateDescriptionCount,
                    ["template_file"] = string.IsNullOrWhiteSpace(TemplateFilePath) ? null : TemplateFilePath,
                    ["export_date"] = DateTime.UtcNow.ToString("o"),
                    ["source"] = "ddQuint Windows App"
                };

                try
                {
                    // Ensure directory exists and handle file access
                    Directory.CreateDirectory(Path.GetDirectoryName(savePath)!);
                    if (File.Exists(savePath))
                    {
                        File.SetAttributes(savePath, FileAttributes.Normal); // Remove read-only
                    }
                    
                    var json = Newtonsoft.Json.JsonConvert.SerializeObject(bundle, Newtonsoft.Json.Formatting.Indented);
                    File.WriteAllText(savePath, json);
                    StatusMessage = "Parameters exported";
                    MessageBox.Show($"Parameters exported to: {savePath}", "Export Parameters", MessageBoxButton.OK, MessageBoxImage.Information);
                }
                catch (Exception fileEx)
                {
                    StatusMessage = $"Parameters export failed: {fileEx.Message}";
                    MessageBox.Show($"Failed to write to {savePath}:\n{fileEx.Message}", "Export Parameters", MessageBoxButton.OK, MessageBoxImage.Error);
                    return;
                }
            }
            catch (Exception ex)
            {
                StatusMessage = $"Parameters export failed: {ex.Message}";
                MessageBox.Show($"Failed to export parameters: {ex.Message}", "Export Parameters", MessageBoxButton.OK, MessageBoxImage.Error);
            }
        }

        // Load parameter bundle and optionally re-run analysis
        public void LoadParameters()
        {
            try
            {
                var ofd = new Microsoft.Win32.OpenFileDialog
                {
                    Title = "Load Parameters",
                    Filter = "JSON Files (*.json)|*.json|All Files (*.*)|*.*",
                    CheckFileExists = true
                };
                try
                {
                    var last = GetLastDirectory("LastDir_ParametersImport");
                    if (!string.IsNullOrWhiteSpace(last) && Directory.Exists(last)) ofd.InitialDirectory = last;
                }
                catch { }

                if (ofd.ShowDialog() != true) return;
                var loadPath = ofd.FileName;
                try { SetLastDirectory(Path.GetDirectoryName(loadPath), "LastDir_ParametersImport"); } catch { }

                // Use the new LoadParametersFromFile method which handles both bundle and direct formats
                try
                {
                    var parameters = ParametersService.LoadParametersFromFile(loadPath);
                    ParametersService.SaveGlobalParameters(parameters);
                    StatusMessage = "Parameters loaded successfully";
                    AddLogMessage($"Loaded {parameters.Count} parameters from file: {Path.GetFileName(loadPath)}");
                }
                catch (Exception paramEx)
                {
                    // Fall back to the old loading method for legacy files
                    AddLogMessage($"Primary load method failed, trying legacy format: {paramEx.Message}");
                    
                    var text = File.ReadAllText(loadPath);
                    var obj = Newtonsoft.Json.Linq.JObject.Parse(text);

                    // Globals
                    if (obj["global_parameters"] is Newtonsoft.Json.Linq.JObject g)
                    {
                        // Convert JSON while preserving structured data
                        var dict = new Dictionary<string, object>();
                        foreach (var prop in g.Properties())
                        {
                            dict[prop.Name] = ConvertJTokenToObject(prop.Value);
                        }
                        ParametersService.SaveGlobalParameters(dict);
                        AddLogMessage("Loaded global parameters using legacy method");
                    }
                    else
                    {
                        // Try loading as direct parameters
                        var dict = new Dictionary<string, object>();
                        foreach (var prop in obj.Properties())
                        {
                            dict[prop.Name] = ConvertJTokenToObject(prop.Value);
                        }
                        if (dict.Count > 0)
                        {
                            ParametersService.SaveGlobalParameters(dict);
                            AddLogMessage("Loaded parameters as direct format using legacy method");
                        }
                        else
                        {
                            throw new InvalidOperationException("No valid parameters found in file");
                        }
                    }
                    
                    // Wells (only if bundle format)
                    if (obj["well_parameters"] is Newtonsoft.Json.Linq.JObject wp)
                    {
                        foreach (var p in wp)
                        {
                            var wellId = p.Key;
                            var vals = (p.Value as Newtonsoft.Json.Linq.JObject)?.ToObject<Dictionary<string, object>>() ?? new();
                            ParametersService.SaveWellParameters(wellId, vals);
                        }
                        AddLogMessage($"Loaded well-specific parameters for {wp.Count} wells");
                    }
                    
                    // Template fields (only if bundle format)
                    var tdc = obj["template_description_count"]?.ToObject<int?>();
                    if (tdc.HasValue && tdc.Value >= 1 && tdc.Value <= 4) SetTemplateDescriptionCount(tdc.Value);
                    var tpl = obj["template_file"]?.ToObject<string>();
                    if (!string.IsNullOrWhiteSpace(tpl) && File.Exists(tpl)) TemplateFilePath = tpl;

                    StatusMessage = "Parameters loaded (legacy method)";
                }

                // If a folder is selected and not processing, re-run analysis to apply
                if (!string.IsNullOrEmpty(InputFolderPath) && !IsProcessing)
                {
                    // Clear prior results and re-run
                    Application.Current.Dispatcher.Invoke(() =>
                    {
                        Wells.Clear();
                        FilteredWells.Clear();
                        SelectedWell = null;
                        OnPropertyChanged(nameof(HasResults));
                        PlateOverviewImagePath = null;
                    });
                    _ = AnalyzeAsync();
                }
                else
                {
                    AddLogMessage("Parameters loaded. Run analysis to apply settings.");
                }
            }
            catch (Exception ex)
            {
                StatusMessage = $"Failed to load parameters: {ex.Message}";
                MessageBox.Show($"Failed to load parameters: {ex.Message}", "Load Parameters", MessageBoxButton.OK, MessageBoxImage.Error);
                AddLogMessage($"ERROR loading parameters: {ex.Message}");
            }
        }

        private object ConvertJTokenToObject(Newtonsoft.Json.Linq.JToken token)
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

        private string? TryGetGraphsDirectory()
        {
            try
            {
                var plot = Wells.FirstOrDefault(w => !string.IsNullOrWhiteSpace(w.PlotImagePath))?.PlotImagePath;
                if (string.IsNullOrWhiteSpace(plot)) return null;
                var graphs = Path.GetDirectoryName(plot);
                return graphs;
            }
            catch { return null; }
        }

        private string? TryGetResultsJsonPath()
        {
            try
            {
                var graphs = TryGetGraphsDirectory();
                if (string.IsNullOrWhiteSpace(graphs)) return null;
                var output = Directory.GetParent(graphs)?.FullName;
                if (string.IsNullOrWhiteSpace(output)) return null;
                var results = Path.Combine(output, "results.json");
                return results;
            }
            catch { return null; }
        }

        private int GetMaxTargetCount()
        {
            // Calculate maximum chromosome count across all wells (matching macOS implementation)
            
            // Start with global parameter default
            var globalParams = ParametersService.LoadGlobalParameters();
            var maxTargetCount = globalParams.TryGetValue("CHROMOSOME_COUNT", out var globalChromCount) 
                ? Convert.ToInt32(globalChromCount) : 5;
            AddLogMessage($"Global CHROMOSOME_COUNT: {maxTargetCount}");
            
            // Check well-specific parameter overrides
            var allWellParams = ParametersService.GetAllWellParameters();
            foreach (var (wellId, wellParams) in allWellParams)
            {
                if (wellParams.TryGetValue("CHROMOSOME_COUNT", out var wellChromCount))
                {
                    var wellCount = Convert.ToInt32(wellChromCount);
                    maxTargetCount = Math.Max(maxTargetCount, wellCount);
                    AddLogMessage($"Well {wellId} has {wellCount} targets, max so far: {maxTargetCount}");
                }
            }
            
            // Also check actual well results for chromosome data (in case processing created more targets than configured)
            foreach (var well in Wells)
            {
                if (well.CopyNumbersDictionary != null)
                {
                    var actualChromCount = well.CopyNumbersDictionary.Keys.Count(k => k.StartsWith("Chrom"));
                    if (actualChromCount > 0)
                    {
                        maxTargetCount = Math.Max(maxTargetCount, actualChromCount);
                        AddLogMessage($"Well {well.WellId} has {actualChromCount} actual targets, max so far: {maxTargetCount}");
                    }
                }
            }
            
            AddLogMessage($"Maximum target count across all wells: {maxTargetCount}");
            return maxTargetCount;
        }

        // Combined export: Excel + parameters + plots (like macOS Export All)
        private async void ExportAll()
        {
            try
            {
                if (!HasResults)
                {
                    MessageBox.Show("No results to export.", "Export", MessageBoxButton.OK, MessageBoxImage.Information);
                    return;
                }

                // Select export folder
                var dialog = new System.Windows.Forms.FolderBrowserDialog()
                {
                    Description = "Select folder to export Excel, parameters, and plots",
                    ShowNewFolderButton = true,
                    RootFolder = Environment.SpecialFolder.MyComputer
                };
                try
                {
                    var last = GetLastDirectory("LastDir_ExportAll");
                    if (!string.IsNullOrWhiteSpace(last)) dialog.SelectedPath = last;
                }
                catch { }

                if (dialog.ShowDialog() != System.Windows.Forms.DialogResult.OK) return;
                var exportFolder = dialog.SelectedPath;
                try { SetLastDirectory(exportFolder, "LastDir_ExportAll"); } catch { }

                // Resolve results.json
                var resultsJson = _resultsJsonPath ?? TryGetResultsJsonPath();
                if (string.IsNullOrWhiteSpace(resultsJson) || !File.Exists(resultsJson))
                {
                    MessageBox.Show("Could not locate results.json from the current analysis.", "Export", MessageBoxButton.OK, MessageBoxImage.Warning);
                    return;
                }

                // Targets
                var excelPath = Path.Combine(exportFolder, "ddQuint_Results.xlsx");
                var paramsPath = Path.Combine(exportFolder, "ddQuint_Parameters.json");
                var graphsFolder = Path.Combine(exportFolder, "Graphs");

                StatusMessage = "Exporting (1/3): Excel...";

                // Calculate maximum target count for proper Excel columns (matching macOS)
                var maxTargetCount = GetMaxTargetCount();

                // Create temp results file from current wells (matching macOS cached results approach)
                var tempDir = Path.GetTempPath();
                var tempResultsFile = Path.Combine(tempDir, $"ddquint_export_all_results_{Guid.NewGuid():N}.json");
                
                try
                {
                    // Convert current Wells to JSON format expected by Python
                    var results = Wells.Select(well => new Dictionary<string, object>
                    {
                        ["well_id"] = well.WellId,
                        ["well"] = well.WellId, // Python expects 'well' key
                        ["sample_name"] = well.SampleName ?? "",
                        ["status"] = well.Status.ToString(),
                        ["total_droplets"] = well.TotalDroplets,
                        ["usable_droplets"] = well.UsableDroplets,
                        ["negative_droplets"] = well.NegativeDroplets,
                        ["copy_numbers"] = well.CopyNumbersDictionary ?? new Dictionary<string, double>(),
                        ["has_aneuploidy"] = well.AnalysisData?.GetValueOrDefault("has_aneuploidy", false) ?? false,
                        ["has_buffer_zone"] = well.AnalysisData?.GetValueOrDefault("has_buffer_zone", false) ?? false,
                        ["copy_number_states"] = well.AnalysisData?.GetValueOrDefault("copy_number_states") ?? new Dictionary<string, object>(),
                        ["analysis_data"] = well.AnalysisData ?? new Dictionary<string, object>()
                    }).ToList();

                    var json = Newtonsoft.Json.JsonConvert.SerializeObject(results, Newtonsoft.Json.Formatting.Indented);
                    File.WriteAllText(tempResultsFile, json);
                    AddLogMessage($"Created temp results file for export all: {tempResultsFile}");
                }
                catch (Exception ex)
                {
                    StatusMessage = "Export failed during Excel step (temp file creation)";
                    MessageBox.Show($"Failed to create temp results file: {ex.Message}", "Export Failed", MessageBoxButton.OK, MessageBoxImage.Error);
                    return;
                }

                // Excel export via Python using macOS approach
                var script = $@"
import sys, os, json, traceback

try:
    # Initialize config properly (matching macOS approach)
    from ddquint.config import Config
    from ddquint.utils.parameter_editor import load_parameters_if_exist
    
    config = Config.get_instance()
    load_parameters_if_exist(Config)
    config.finalize_colors()
    
    # Import create_list_report
    from ddquint.core import create_list_report
    
    # Load cached results from temp file (matching macOS approach)
    with open(r'''{tempResultsFile}''', 'r') as f:
        results = json.load(f)
    
    print(f'DEBUG: Loaded {{len(results)}} cached results for Excel export (Export All)')
    
    # Export to Excel using cached results with max target count (matching macOS)
    create_list_report(results, r'''{excelPath}''', {maxTargetCount})
    print('EXCEL_EXPORT_SUCCESS_CACHED_ALL')
    
    # Clean up temp file
    os.remove(r'''{tempResultsFile}''')
    
except Exception as e:
    print('EXPORT_ERROR:', e)
    traceback.print_exc()
    sys.exit(1)
";
                var execExcel = await _pythonService.ExecutePythonScript(script, workingDirectory: null, persistScript: false);
                if (!(execExcel.ExitCode == 0 && (execExcel.Output.Contains("EXCEL_EXPORT_SUCCESS") || execExcel.Output.Contains("EXCEL_EXPORT_SUCCESS_CACHED"))))
                {
                    StatusMessage = "Export failed during Excel step";
                    AddLogMessage($"Excel export error (Export All) - Exit code: {execExcel.ExitCode}, Output: {execExcel.Output}, Error: {execExcel.Error}");
                    MessageBox.Show("Excel export failed. See logs for details.", "Export Failed", MessageBoxButton.OK, MessageBoxImage.Error);
                    return;
                }

                StatusMessage = "Exporting (2/3): Parameters...";
                // Parameters export
                try
                {
                    var globals = ParametersService.LoadGlobalParameters();
                    var wells = ParametersService.GetAllWellParameters();
                    var bundle = new Dictionary<string, object?>
                    {
                        ["global_parameters"] = globals,
                        ["well_parameters"] = wells,
                        ["template_description_count"] = TemplateDescriptionCount,
                        ["template_file"] = string.IsNullOrWhiteSpace(TemplateFilePath) ? null : TemplateFilePath,
                        ["export_date"] = DateTime.UtcNow.ToString("o"),
                        ["source"] = "ddQuint Windows App"
                    };
                    Directory.CreateDirectory(exportFolder);
                    
                    // Handle file access properly
                    if (File.Exists(paramsPath))
                    {
                        File.SetAttributes(paramsPath, FileAttributes.Normal); // Remove read-only
                    }
                    
                    var json = Newtonsoft.Json.JsonConvert.SerializeObject(bundle, Newtonsoft.Json.Formatting.Indented);
                    File.WriteAllText(paramsPath, json);
                }
                catch (Exception ex)
                {
                    StatusMessage = "Export failed during parameters step";
                    MessageBox.Show($"Parameters export failed: {ex.Message}", "Export Failed", MessageBoxButton.OK, MessageBoxImage.Error);
                    return;
                }

                StatusMessage = "Exporting (3/3): Plots...";
                // Plots export
                try
                {
                    Directory.CreateDirectory(graphsFolder);
                    var graphsDir = TryGetGraphsDirectory();
                    if (!string.IsNullOrWhiteSpace(graphsDir) && Directory.Exists(graphsDir))
                    {
                        foreach (var png in Directory.EnumerateFiles(graphsDir, "*.png"))
                        {
                            var name = Path.GetFileName(png);
                            var dest = Path.Combine(graphsFolder, name);
                            File.Copy(png, dest, overwrite: true);
                        }
                    }
                }
                catch (Exception ex)
                {
                    StatusMessage = "Export failed during plots step";
                    MessageBox.Show($"Plots export failed: {ex.Message}", "Export Failed", MessageBoxButton.OK, MessageBoxImage.Error);
                    return;
                }

                StatusMessage = "Export completed";
            }
            catch (Exception ex)
            {
                StatusMessage = $"Export failed: {ex.Message}";
                MessageBox.Show($"Export failed: {ex.Message}", "Export Failed", MessageBoxButton.OK, MessageBoxImage.Error);
            }
        }

        // Wipe current analysis results and reset view state
        public void ClearAnalysis()
        {
            try
            {
                AddLogMessage("Clearing current analysis results...");
                
                // Ensure collection modifications happen on UI thread
                Application.Current.Dispatcher.Invoke(() =>
                {
                    // If processing is ongoing, force stop it (like macOS)
                    if (IsProcessing)
                    {
                        AddLogMessage("WARNING: Analysis was in progress - forcing stop");
                        // Actually terminate the running Python process
                        _pythonService.CancelCurrentProcess();
                        IsProcessing = false;
                        StatusMessage = "Analysis cancelled";
                    }

                    // Clear any well-specific parameter overrides (macOS parity)
                    try
                    {
                        ddQuint.Desktop.Services.ParametersService.ClearAllWellParameters();
                        AddLogMessage("Cleared all well-specific parameter overrides");
                    }
                    catch { }

                    Wells.Clear();
                    FilteredWells.Clear();
                    SelectedWell = null;
                    OnPropertyChanged(nameof(HasResults));
                    PlateOverviewImagePath = null;
                    
                    // Clear input folder path to allow new folder selection
                    InputFolderPath = null;
                    TemplateFilePath = null;
                    
                    StatusMessage = "No folder selected";
                    ProgressValue = 0;
                });
                
                AddLogMessage("Analysis results and paths cleared");
            }
            catch (Exception ex)
            {
                AddLogMessage($"Error while clearing analysis: {ex.Message}");
            }
        }
        
        private void ShowGlobalParameters()
        {
            try
            {
                AddLogMessage("Opening Global Parameters window");
                var globalParamsWindow = new Views.GlobalParametersWindow(this);
                globalParamsWindow.Owner = Application.Current.MainWindow;
                
                // Subscribe to parameter changes to trigger reprocessing
                globalParamsWindow.ParametersApplied += OnGlobalParametersApplied;
                
                globalParamsWindow.ShowDialog();
            }
            catch (Exception ex)
            {
                StatusMessage = $"Error opening Global Parameters: {ex.Message}";
                AddLogMessage($"ERROR opening Global Parameters: {ex.Message}");
                MessageBox.Show($"Error opening Global Parameters: {ex.Message}", "Error", 
                               MessageBoxButton.OK, MessageBoxImage.Error);
            }
        }
        
        private void EditSelectedWell()
        {
            if (SelectedWell == null) return;
            
            try
            {
                AddLogMessage($"Opening Well Parameters window for {SelectedWell.DisplayName}");
                var wellParamsWindow = new Views.WellParametersWindow(this, SelectedWell);
                wellParamsWindow.Owner = Application.Current.MainWindow;
                
                // Subscribe to parameter changes to trigger reprocessing
                wellParamsWindow.WellParametersApplied += OnWellParametersApplied;
                
                wellParamsWindow.ShowDialog();
            }
            catch (Exception ex)
            {
                StatusMessage = $"Error opening Well Parameters: {ex.Message}";
                AddLogMessage($"ERROR opening Well Parameters: {ex.Message}");
                MessageBox.Show($"Error opening Well Parameters: {ex.Message}", "Error", 
                               MessageBoxButton.OK, MessageBoxImage.Error);
            }
        }
        
        private void ShowTemplateCreator()
        {
            try
            {
                AddLogMessage("Opening Template Creator window");
                var win = new Views.TemplateCreatorWindow();
                win.Owner = Application.Current.MainWindow;
                win.ShowDialog();
            }
            catch (Exception ex)
            {
                StatusMessage = $"Error opening Template Creator: {ex.Message}";
                AddLogMessage($"ERROR opening Template Creator: {ex.Message}");
                MessageBox.Show($"Error opening Template Creator: {ex.Message}", "Error",
                               MessageBoxButton.OK, MessageBoxImage.Error);
            }
        }
        
        private void ShowAbout()
        {
            var aboutMessage = @"ddQuint - Digital Droplet PCR Analysis
Version 0.1.0 (Windows)

A native Windows application for analyzing multiplex digital droplet PCR (ddPCR) data with a focus on copy number deviation detection.

© ddQuint Project
Licensed under Creative Commons Attribution–NonCommercial 4.0 International (CC BY-NC 4.0)";
            
            MessageBox.Show(aboutMessage, "About ddQuint", 
                           MessageBoxButton.OK, MessageBoxImage.Information);
        }
        
        private void ShowFilterOptions()
        {
            AddLogMessage("UI: Opening Filter Options window");
            var filterWindow = new Views.FilterOptionsWindow(this);
            filterWindow.Owner = Application.Current.MainWindow;
            filterWindow.ShowDialog();
        }
        
        private void ShowHelp()
        {
            AddLogMessage("UI: Opening Help window");
            var helpWindow = new Views.HelpWindow();
            helpWindow.Owner = Application.Current.MainWindow;
            helpWindow.Show();
        }
        
        #endregion
        
        #region Event Handlers
        
        private void OnProgressChanged(object? sender, ProgressChangedEventArgs e)
        {
            Application.Current.Dispatcher.Invoke(() =>
            {
                ProgressValue = e.ProgressPercentage;
            });
        }
        
        private void OnStatusChanged(object? sender, string message)
        {
            Application.Current.Dispatcher.Invoke(() =>
            {
                // Only update status if we're actually processing (prevent leaks from cancelled/lingering processes)
                if (!IsProcessing)
                {
                    AddLogMessage($"Ignoring status update (not processing): {message}");
                    return;
                }
                
                // Normalize status text to match macOS wording
                if (!string.IsNullOrWhiteSpace(message) && message.StartsWith("PROCESSING_FILE:", StringComparison.OrdinalIgnoreCase))
                {
                    try
                    {
                        // Format: PROCESSING_FILE: idx/total filename
                        var parts = message.Split(' ', StringSplitOptions.RemoveEmptyEntries);
                        // parts[1] should be idx/total
                        if (parts.Length >= 2)
                        {
                            var progress = parts[1];
                            StatusMessage = $"Progress: {progress} files processed";
                            return;
                        }
                    }
                    catch { }
                }
                StatusMessage = message;
            });
        }
        
        private void OnLogMessageAdded(object? sender, string message)
        {
            Application.Current.Dispatcher.Invoke(() =>
            {
                AddLogMessage(message);
            });
        }
        
        private void OnWellCompleted(object? sender, WellResult well)
        {
            Application.Current.Dispatcher.Invoke(() =>
            {
                Wells.Add(well);
                OnPropertyChanged(nameof(HasResults));
                UpdateFilteredWells();
                
                // Auto-select first well if none selected
                if (SelectedWell == null && Wells.Count == 1)
                {
                    SelectedWell = well;
                }
                
                AddLogMessage($"Well {well.WellId} completed and added to display");
            });
        }
        
        public async void OnGlobalParametersApplied(Dictionary<string, object> updatedParameters)
        {
            try
            {
                AddLogMessage($"=== OnGlobalParametersApplied START ===");
                AddLogMessage($"Global parameters updated - {updatedParameters.Count} parameters changed");
                
                // Log all changed parameters for debugging
                foreach (var param in updatedParameters)
                {
                    AddLogMessage($"  CHANGED: {param.Key} = {param.Value}");
                }
                
                AddLogMessage($"Current state: InputFolderPath={InputFolderPath ?? "null"}, IsProcessing={IsProcessing}");
                AddLogMessage("Triggering reprocessing with new parameters...");
                
                // If we have existing data and input folder, reprocess automatically
                if (!string.IsNullOrEmpty(InputFolderPath) && !IsProcessing)
                {
                    AddLogMessage("CONDITIONS MET: Starting automatic reanalysis");
                    StatusMessage = "Parameters changed - reprocessing analysis...";
                    await AnalyzeAsync();
                }
                else if (IsProcessing)
                {
                    AddLogMessage("DEFERRED: Currently processing, parameters will apply after completion");
                    StatusMessage = "Parameters updated - will apply after current analysis completes";
                }
                else
                {
                    AddLogMessage("QUEUED: No current data, parameters will apply to next analysis");
                    StatusMessage = "Global parameters updated - next analysis will use new settings";
                }
                
                AddLogMessage($"=== OnGlobalParametersApplied END ===");
            }
            catch (Exception ex)
            {
                StatusMessage = $"Error reprocessing after parameter change: {ex.Message}";
                AddLogMessage($"ERROR in OnGlobalParametersApplied: {ex.Message}");
                AddLogMessage($"STACK TRACE: {ex.StackTrace}");
            }
        }
        
        public async void OnWellParametersApplied(string wellId, Dictionary<string, object> updatedParameters)
        {
            try
            {
                AddLogMessage($"=== OnWellParametersApplied START ===");
                var changedCount = updatedParameters?.Count ?? 0;
                AddLogMessage($"Well {wellId} parameters updated - {changedCount} parameters changed");
                // Mark the well as edited in the current list immediately (square indicator)
                try
                {
                    var w = Wells.FirstOrDefault(wl => wl.WellId == wellId);
                    if (w != null)
                    {
                        w.IsEdited = (updatedParameters?.Count ?? 0) > 0;
                    }
                }
                catch { }
                
                // Log all changed parameters for debugging
                if (updatedParameters != null)
                {
                    foreach (var param in updatedParameters)
                    {
                        AddLogMessage($"  WELL {wellId} CHANGED: {param.Key} = {param.Value}");
                    }
                }
                
                AddLogMessage($"Current state: InputFolderPath={InputFolderPath ?? "null"}, IsProcessing={IsProcessing}");
                AddLogMessage($"Well {wellId} triggering reprocessing with new well-specific parameters...");
                
                // If we have existing data and input folder, reprocess only this specific well
                if (!string.IsNullOrEmpty(InputFolderPath) && !IsProcessing)
                {
                    AddLogMessage($"WELL {wellId} CONDITIONS MET: Starting single well reanalysis (matching macOS behavior)");
                    StatusMessage = $"Well {wellId} parameters changed - reprocessing well...";
                    await ReprocessSingleWellAsync(wellId);
                }
                else if (IsProcessing)
                {
                    AddLogMessage($"WELL {wellId} DEFERRED: Currently processing, parameters will apply after completion");
                    StatusMessage = $"Well {wellId} parameters updated - will apply after current analysis completes";
                }
                else
                {
                    AddLogMessage($"WELL {wellId} QUEUED: No current data, parameters will apply to next analysis");
                    StatusMessage = $"Well {wellId} parameters updated - next analysis will use new settings";
                }
                
                AddLogMessage($"=== OnWellParametersApplied END ===");
            }
            catch (Exception ex)
            {
                StatusMessage = $"Error reprocessing after well parameter change: {ex.Message}";
                AddLogMessage($"ERROR in OnWellParametersApplied: {ex.Message}");
                AddLogMessage($"STACK TRACE: {ex.StackTrace}");
            }
        }
        
        #endregion
        
        #region Helper Methods
        
        private void UpdateFilteredWells()
        {
            // Preserve current selection by WellId
            var currentSelectedId = SelectedWell?.WellId;

            var filtered = Wells.AsEnumerable();
            
            if (HideBufferZone)
            {
                filtered = filtered.Where(w => w.Status != WellStatus.BufferZone);
            }
            
            if (HideWarnings)
            {
                filtered = filtered.Where(w => w.Status != WellStatus.Warning);
            }
            
            // Column-first ordering to match macOS list ordering
            filtered = filtered.OrderBy(w => w.ColumnFirstIndex);
            
            FilteredWells.Clear();
            foreach (var well in filtered)
            {
                FilteredWells.Add(well);
            }

            // Restore selection if possible
            if (!string.IsNullOrEmpty(currentSelectedId))
            {
                var match = FilteredWells.FirstOrDefault(w => string.Equals(w.WellId, currentSelectedId, StringComparison.OrdinalIgnoreCase));
                if (match != null)
                {
                    SelectedWell = match;
                }
            }
        }
        
        private void AddLogMessage(string message)
        {
            var timestamp = DateTime.Now.ToString("HH:mm:ss");
            LogMessages += $"[{timestamp}] {message}\n";
        }
        
        private static void LogMessage(string message)
        {
            var timestamp = DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss.fff");
            var logEntry = $"[{timestamp}] VIEWMODEL: {message}";
            
            // Write to console
            Console.WriteLine(logEntry);
            
            // Write to file
            try
            {
                var logPath = Path.Combine(Path.GetTempPath(), "ddquint_startup.log");
                File.AppendAllText(logPath, logEntry + Environment.NewLine);
            }
            catch
            {
                // Ignore file logging errors
            }
        }
        
        #endregion
        
        #region Template Description Count Management
        
        private void LoadTemplateDescriptionCount()
        {
            try
            {
                var settings = Properties.Settings.Default;
                var savedCount = settings.TemplateDescriptionCount;
                if (savedCount >= 1 && savedCount <= 4)
                {
                    _templateDescriptionCount = savedCount;
                    LogMessage($"Loaded persisted Template Description Count: {savedCount}");
                }
                else
                {
                    LogMessage($"No valid persisted Template Description Count found; using default: {_templateDescriptionCount}");
                }
            }
            catch (Exception ex)
            {
                LogMessage($"Error loading template description count: {ex.Message}");
            }
        }
        
        public void SetTemplateDescriptionCount(int count)
        {
            if (count < 1 || count > 4) return;
            
            TemplateDescriptionCount = count;
            StatusMessage = $"Using {count} sample description field(s)";
            
            // Save to settings
            try
            {
                Properties.Settings.Default.TemplateDescriptionCount = count;
                Properties.Settings.Default.Save();
                LogMessage($"Persisted Template Description Count: {count}");
            }
            catch (Exception ex)
            {
                LogMessage($"Error saving template description count: {ex.Message}");
            }
            
            // If we have a valid input folder and existing results, re-run analysis to apply changes
            if (!string.IsNullOrEmpty(InputFolderPath) && HasResults && !IsProcessing)
            {
                LogMessage($"Template description count changed - reanalyzing existing data...");
                // Clear previous results before reanalysis (on UI thread)
                Application.Current.Dispatcher.Invoke(() =>
                {
                    Wells.Clear();
                    FilteredWells.Clear();
                    SelectedWell = null;
                    OnPropertyChanged(nameof(HasResults));
                    PlateOverviewImagePath = null;
                });
                
                _ = AnalyzeAsync();
            }
            else
            {
                LogMessage("Template description count setting saved.");
            }
        }
        
        #endregion
        
        #region Directory Persistence (like macOS LastURL methods)
        
        private string? GetLastDirectory(string key)
        {
            try
            {
                var settings = Properties.Settings.Default;
                var path = (string?)settings[key];
                return !string.IsNullOrEmpty(path) && Directory.Exists(path) ? path : null;
            }
            catch
            {
                return null;
            }
        }
        
        private void SetLastDirectory(string? path, string key)
        {
            if (string.IsNullOrEmpty(path)) return;
            
            try
            {
                var settings = Properties.Settings.Default;
                settings[key] = path;
                settings.Save();
            }
            catch (Exception ex)
            {
                LogMessage($"Error saving last directory for {key}: {ex.Message}");
            }
        }

        private void GenerateOverviewWells()
        {
            var overviewWells = new ObservableCollection<OverviewWell>();
            
            if (Wells == null || Wells.Count == 0)
            {
                OverviewWells = overviewWells;
                return;
            }
            
            // Calculate actual max columns from well data (matching macOS getMaxColumnCount)
            int maxCol = GetMaxColumnCount();
            int maxRow = 8; // Always A-H (fixed like macOS)
            
            // macOS layout constants (matching OverviewLayout class)
            const double thumbnailSize = 150.0;
            const double thumbnailHeight = thumbnailSize * 0.75; // 112.5
            const double wellLabelHeight = 18.0;
            const double rowHeight = wellLabelHeight + thumbnailHeight; // 130.5
            const double topMargin = 20.0;
            const double leftMargin = 10.0;
            const double horizontalSpacing = thumbnailSize + 5; // 155
            const double verticalSpacing = rowHeight + 2; // 132.5
            const double bottomMargin = 20.0;
            
            // Calculate dynamic dimensions based on actual data
            OverviewGridWidth = leftMargin + maxCol * horizontalSpacing;
            OverviewGridHeight = topMargin + maxRow * verticalSpacing + bottomMargin; // Dynamic height calculation
            
            string[] rows = { "A", "B", "C", "D", "E", "F", "G", "H" };
            
            // Generate wells only for positions that have data (matching macOS behavior)
            for (int row = 0; row < maxRow; row++)
            {
                for (int col = 0; col < maxCol; col++)
                {
                    string wellId = $"{rows[row]}{(col + 1):D2}";
                    
                    // Find corresponding well result
                    var wellResult = Wells.FirstOrDefault(w => w.WellId == wellId);
                    
                    // Only create overview well if data exists (this is the key difference from old approach)
                    if (wellResult != null)
                    {
                        // Calculate position using exact macOS measurements
                        double x = leftMargin + col * horizontalSpacing;
                        double y = topMargin + row * verticalSpacing;
                        
                        var overviewWell = new OverviewWell
                        {
                            WellId = wellId,
                            X = x,
                            Y = y,
                            WellResult = wellResult,
                            ThumbnailImagePath = wellResult.PlotImagePath ?? CreatePlaceholderImage(wellId)
                        };
                        
                        overviewWells.Add(overviewWell);
                    }
                }
            }
            
            OverviewWells = overviewWells;
            
            // Notify UI that dimensions changed (unified properties)
            OnPropertyChanged(nameof(ScrollableWidth));
            OnPropertyChanged(nameof(ScrollableHeight));
            OnPropertyChanged(nameof(CurrentGridWidth));
            OnPropertyChanged(nameof(CurrentGridHeight));
            
            AddLogMessage($"Generated {overviewWells.Count} overview wells for {maxCol} columns x {maxRow} rows (grid: {OverviewGridWidth:F0}x{OverviewGridHeight:F0})");
        }

        private void GenerateCurrentViewWells()
        {
            if (ShowOverview)
            {
                GenerateOverviewWells();
            }
            else if (IsMultiSelection)
            {
                GenerateMultiSelectionWells();
            }
            else
            {
                // Single selection or no selection - clear wells
                OverviewWells = new ObservableCollection<OverviewWell>();
            }
        }

        private void GenerateMultiSelectionWells()
        {
            var wells = new ObservableCollection<OverviewWell>();
            
            if (SelectedWells == null || SelectedWells.Count == 0)
            {
                OverviewWells = wells;
                return;
            }
            
            // Calculate optimal grid dimensions for space utilization
            var gridLayout = CalculateOptimalMultiGrid(SelectedWells.Count);
            int cols = gridLayout.cols;
            int rows = gridLayout.rows;
            
            // macOS layout constants (same as overview)
            const double thumbnailSize = 150.0;
            const double thumbnailHeight = thumbnailSize * 0.75; // 112.5
            const double wellLabelHeight = 18.0;
            const double rowHeight = wellLabelHeight + thumbnailHeight; // 130.5
            const double topMargin = 20.0;
            const double leftMargin = 10.0;
            const double horizontalSpacing = thumbnailSize + 5; // 155
            const double verticalSpacing = rowHeight + 2; // 132.5
            const double bottomMargin = 20.0;
            
            // Update the MultiColumns/MultiRows properties to stay in sync
            MultiColumns = cols;
            MultiRows = rows;
            
            // Calculate dynamic dimensions based on actual grid
            MultiGridWidth = leftMargin + cols * horizontalSpacing;
            MultiGridHeight = topMargin + rows * verticalSpacing + bottomMargin;
            
            // Generate multi-well items
            for (int i = 0; i < SelectedWells.Count; i++)
            {
                var well = SelectedWells[i];
                
                // Calculate position in grid
                int row = i / cols;
                int col = i % cols;
                
                double x = leftMargin + col * horizontalSpacing;
                double y = topMargin + row * verticalSpacing;
                
                var overviewWell = new OverviewWell
                {
                    WellId = well.WellId,
                    X = x,
                    Y = y,
                    WellResult = well,
                    ThumbnailImagePath = well.PlotImagePath ?? CreatePlaceholderImage(well.WellId)
                };
                
                wells.Add(overviewWell);
            }
            
            OverviewWells = wells;
            
            // Notify UI that dimensions changed (unified properties)
            OnPropertyChanged(nameof(ScrollableWidth));
            OnPropertyChanged(nameof(ScrollableHeight));
            OnPropertyChanged(nameof(CurrentGridWidth));
            OnPropertyChanged(nameof(CurrentGridHeight));
            
            AddLogMessage($"Generated {wells.Count} multi-selection wells in {rows} rows x {cols} cols (grid: {MultiGridWidth:F0}x{MultiGridHeight:F0})");
        }

        public void SetMultiViewFitToWidth(double availableWidth)
        {
            if (!IsMultiSelection) return;
            
            // Reserve space for scrollbar
            double usableWidth = Math.Max(0, availableWidth - 10);
            double totalGridWidth = CurrentGridWidth;
            
            if (usableWidth > 0 && totalGridWidth > 0)
            {
                double fill = usableWidth / totalGridWidth;
                GridZoom = Math.Max(0.1, Math.Min(2.0, fill)); // Reasonable zoom limits for multi-view
                AddLogMessage($"🎯 SetMultiViewFitToWidth: usable={usableWidth:F1}px, grid={totalGridWidth:F1}px, zoom={GridZoom:F3}");
            }
        }
        
        private int GetMaxColumnCount()
        {
            // Find the maximum column number from available wells (matching macOS implementation)
            int maxCol = 1;
            if (Wells != null)
            {
                foreach (var well in Wells)
                {
                    if (!string.IsNullOrWhiteSpace(well.WellId) && well.WellId.Length > 1)
                    {
                        string colStr = well.WellId.Substring(1); // Remove first character (row letter)
                        if (int.TryParse(colStr, out int col))
                        {
                            maxCol = Math.Max(maxCol, col);
                        }
                    }
                }
            }
            return maxCol;
        }

        private (int cols, int rows) CalculateOptimalMultiGrid(int wellCount)
        {
            // Use the same logic as MainWindow.xaml.cs UpdateGridLayout for optimal space utilization
            if (wellCount <= 1) return (1, 1);
            if (wellCount <= 4) return (2, (int)Math.Ceiling(wellCount / 2.0));      // 2x2 before any 3-wide
            if (wellCount <= 9) return (3, (int)Math.Ceiling(wellCount / 3.0));       // 5-9 → 3 columns
            if (wellCount <= 16) return (4, (int)Math.Ceiling(wellCount / 4.0));      // 10-16 → 4 columns
            if (wellCount <= 25) return (5, (int)Math.Ceiling(wellCount / 5.0));      // 17-25 → 5 columns
            
            // For larger counts, use square-ish grid
            int cols = (int)Math.Ceiling(Math.Sqrt(wellCount));
            int rows = (int)Math.Ceiling((double)wellCount / cols);
            return (Math.Max(5, cols), rows);
        }

        private string? CreatePlaceholderImage(string wellId)
        {
            // For now, return null - will implement placeholder image generation later
            // This matches the macOS approach of showing placeholder for wells without data
            return null;
        }
        
        #endregion
        
        #region INotifyPropertyChanged
        
        public event PropertyChangedEventHandler? PropertyChanged;
        public event EventHandler? ClosePopupRequested;
        
        protected virtual void OnPropertyChanged([CallerMemberName] string? propertyName = null)
        {
            PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(propertyName));
        }
        
        protected virtual void OnClosePopupRequested()
        {
            ClosePopupRequested?.Invoke(this, EventArgs.Empty);
        }
        
        #endregion

    }
}
