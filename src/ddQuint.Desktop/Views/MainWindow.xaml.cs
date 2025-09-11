using System;
using System.IO;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Controls.Primitives;
using System.Windows.Input;
using System.Windows.Interop;
using ddQuint.Desktop.ViewModels;
using ddQuint.Desktop.Models;
using System.Linq;
using System.Collections.Generic;
using ddQuint.Core.Models;

namespace ddQuint.Desktop.Views
{
    public partial class MainWindow : Window
    {
        private Popup? _filterPopup;
        private Popup? _settingsPopup;
        private int? _dragAnchorIndex;
        private bool _isDragSelecting;
        private bool _isPanning;
        private Point _panStart;
        private double _panStartH;
        private double _panStartV;
        // Removed legacy multi-grid panning fields (now using native scrolling)
        
        // Physical horizontal mouse wheel support
        private HorizontalWheelHelper? _horizontalWheelHelper;
        
        public MainWindow()
        {
            try
            {
                LogMessage("MainWindow constructor started");
                
                LogMessage("Calling InitializeComponent()...");
                InitializeComponent();
                
                LogMessage("Creating MainViewModel...");
                DataContext = new MainViewModel();
                
                // Initialize physical horizontal wheel support
                LogMessage("Initializing horizontal wheel support...");
                InitializeHorizontalWheelSupport();
                
                // Cleanup on window closing
                this.Closing += (s, e) => {
                    try { _horizontalWheelHelper?.Dispose(); } catch { }
                };
                
                LogMessage("MainWindow constructor completed successfully");
                LogMessage($"Window size: {Width}x{Height}");
                LogMessage($"Window visibility: {Visibility}");
                LogMessage($"Window state: {WindowState}");
            }
            catch (Exception ex)
            {
                var errorMsg = $"FATAL ERROR in MainWindow constructor: {ex.Message}\nStack: {ex.StackTrace}";
                LogMessage(errorMsg);
                
                try
                {
                    MessageBox.Show(errorMsg, "MainWindow Creation Error", MessageBoxButton.OK, MessageBoxImage.Error);
                }
                catch
                {
                    // If MessageBox fails, write to file
                    try
                    {
                        File.WriteAllText(Path.Combine(Path.GetTempPath(), "ddquint_mainwindow_error.txt"), errorMsg);
                    }
                    catch { }
                }
                throw;
            }
        }
        
        private void MenuItem_Exit_Click(object sender, RoutedEventArgs e)
        {
            Application.Current.Shutdown();
        }
        
        private void FolderSelection_MouseLeftButtonDown(object sender, MouseButtonEventArgs e)
        {
            // Handle click on the full-area folder selection zone
            if (DataContext is MainViewModel viewModel)
            {
                // Only open the folder dialog if no input folder has been selected yet
                if (string.IsNullOrWhiteSpace(viewModel.InputFolderPath) &&
                    viewModel.SelectInputFolderCommand.CanExecute(null))
                {
                    viewModel.SelectInputFolderCommand.Execute(null);
                }
            }
        }

        private void SetOverlayBackground(double opacity)
        {
            try
            {
                if (this.FindName("DropOverlay") is System.Windows.Controls.Border overlay)
                {
                    // Use exact RGB(30,30,30) with variable opacity
                    overlay.Background = new System.Windows.Media.SolidColorBrush(System.Windows.Media.Color.FromArgb((byte)(opacity * 255), 30, 30, 30));
                }
            }
            catch { }
        }

        private void DropOverlay_DragEnter(object sender, DragEventArgs e)
        {
            if (IsValidFolderDrag(e))
            {
                e.Effects = DragDropEffects.Copy;
                e.Handled = true;
                SetOverlayBackground(0.8);
            }
            else
            {
                e.Effects = DragDropEffects.None;
            }
        }

        private void DropOverlay_DragOver(object sender, DragEventArgs e)
        {
            if (IsValidFolderDrag(e))
            {
                e.Effects = DragDropEffects.Copy;
                e.Handled = true;
            }
            else
            {
                e.Effects = DragDropEffects.None;
            }
        }

        private void DropOverlay_DragLeave(object sender, DragEventArgs e)
        {
            SetOverlayBackground(0.7);
        }

        private void DropOverlay_Drop(object sender, DragEventArgs e)
        {
            try
            {
                var folder = GetFolderFromDrag(e);
                if (!string.IsNullOrWhiteSpace(folder) && Directory.Exists(folder))
                {
                    if (DataContext is MainViewModel vm)
                    {
                        vm.InputFolderPath = folder;
                        // Auto-start analysis if CSV files present
                        var csvs = Directory.GetFiles(folder, "*.csv");
                        if (csvs.Length > 0 && vm.AnalyzeCommand.CanExecute(null))
                        {
                            vm.AnalyzeCommand.Execute(null);
                        }
                    }
                }
            }
            catch { }
            finally
            {
                SetOverlayBackground(0.7);
                e.Handled = true;
            }
        }

        private static bool IsValidFolderDrag(DragEventArgs e)
        {
            if (!e.Data.GetDataPresent(DataFormats.FileDrop)) return false;
            try
            {
                var items = (string[])e.Data.GetData(DataFormats.FileDrop);
                if (items == null || items.Length == 0) return false;
                // Accept if any is a directory, or if a file is present we can use its parent folder
                return items.Any(path => Directory.Exists(path) || File.Exists(path));
            }
            catch { return false; }
        }

        private static string? GetFolderFromDrag(DragEventArgs e)
        {
            if (!e.Data.GetDataPresent(DataFormats.FileDrop)) return null;
            try
            {
                var items = (string[])e.Data.GetData(DataFormats.FileDrop);
                if (items == null || items.Length == 0) return null;
                // Prefer first directory; else take parent of first file
                var dir = items.FirstOrDefault(p => Directory.Exists(p));
                if (!string.IsNullOrWhiteSpace(dir)) return dir;
                var file = items.FirstOrDefault(p => File.Exists(p));
                if (!string.IsNullOrWhiteSpace(file)) return Path.GetDirectoryName(file);
                return null;
            }
            catch { return null; }
        }


        private void EditWellButton_Click(object sender, RoutedEventArgs e)
        {
            if (DataContext is MainViewModel vm && vm.SelectedWell != null)
            {
                try 
                {
                    // Multi-edit support: if multiple wells selected, open in multi mode
                    if (vm.IsMultiSelection && vm.SelectedWells != null && vm.SelectedWells.Count > 1)
                    {
                        LogMessage($"EditWellButton_Click: Opening multi-well parameters for {vm.SelectedWells.Count} wells");
                        var multiParamsWindow = new WellParametersWindow(vm, vm.SelectedWell, vm.SelectedWells.Select(w => w.WellId))
                        {
                            Owner = this
                        };
                        multiParamsWindow.MultiWellParametersApplied += (wellIds, parameters) =>
                        {
                            LogMessage($"EditWellButton_Click: MultiWellParametersApplied for {wellIds.Count()} wells, {parameters.Count} params");
                            vm.OnMultiWellParametersApplied(wellIds, parameters);
                        };
                        multiParamsWindow.ShowDialog();
                        LogMessage($"EditWellButton_Click: Multi-well dialog closed");
                        return;
                    }
                    
                    LogMessage($"EditWellButton_Click: Opening well parameters for {vm.SelectedWell.WellId}");
                    var wellParamsWindow = new WellParametersWindow(vm, vm.SelectedWell)
                    {
                        Owner = this
                    };
                    
                    // Subscribe to the event to handle parameter changes
                    wellParamsWindow.WellParametersApplied += (wellId, parameters) =>
                    {
                        LogMessage($"EditWellButton_Click: WellParametersApplied event fired for {wellId} with {parameters.Count} parameters");
                        // Let the MainViewModel handle the parameter application
                        vm.OnWellParametersApplied(wellId, parameters);
                    };
                    
                    LogMessage($"EditWellButton_Click: Showing dialog");
                    wellParamsWindow.ShowDialog();
                    LogMessage($"EditWellButton_Click: Dialog closed");
                }
                catch (Exception ex)
                {
                    LogMessage($"ERROR in EditWellButton_Click: {ex.Message}");
                    LogMessage($"STACK TRACE: {ex.StackTrace}");
                    MessageBox.Show($"Error opening Well Parameters: {ex.Message}", "Error", 
                                  MessageBoxButton.OK, MessageBoxImage.Error);
                }
            }
            else
            {
                LogMessage($"EditWellButton_Click: Cannot open - DataContext={DataContext?.GetType().Name}, SelectedWell={(DataContext as MainViewModel)?.SelectedWell?.WellId ?? "null"}");
            }
        }

        private void GlobalParametersButton_Click(object sender, RoutedEventArgs e)
        {
            if (DataContext is MainViewModel vm)
            {
                try 
                {
                    LogMessage("GlobalParametersButton_Click: Opening Global Parameters window");
                    
                    var globalParamsWindow = new GlobalParametersWindow(vm)
                    {
                        Owner = this
                    };
                    
                    // Subscribe to the ParametersApplied event to trigger reprocessing
                    globalParamsWindow.ParametersApplied += (parameters) =>
                    {
                        LogMessage($"GlobalParametersButton_Click: ParametersApplied event fired with {parameters.Count} parameters");
                        // Call the MainViewModel method directly to handle parameter application
                        vm.OnGlobalParametersApplied(parameters);
                    };
                    
                    LogMessage("GlobalParametersButton_Click: Showing dialog");
                    globalParamsWindow.ShowDialog();
                    LogMessage("GlobalParametersButton_Click: Dialog closed");
                }
                catch (Exception ex)
                {
                    LogMessage($"ERROR in GlobalParametersButton_Click: {ex.Message}");
                    LogMessage($"STACK TRACE: {ex.StackTrace}");
                    MessageBox.Show($"Error opening Global Parameters: {ex.Message}", "Error", 
                                  MessageBoxButton.OK, MessageBoxImage.Error);
                }
            }
            else
            {
                LogMessage($"GlobalParametersButton_Click: Cannot open - DataContext is null or not MainViewModel");
            }
        }

        private void FilterButton_Click(object sender, RoutedEventArgs e)
        {
            if (_filterPopup != null && _filterPopup.IsOpen)
            {
                _filterPopup.IsOpen = false;
                return;
            }

            if (_filterPopup == null)
            {
                var filterContent = new FilterPopup();
                filterContent.DataContext = DataContext; // Share the same ViewModel

                _filterPopup = new Popup
                {
                    Child = filterContent,
                    PlacementTarget = FilterButton,
                    Placement = PlacementMode.Bottom,
                    HorizontalOffset = 0,
                    VerticalOffset = 5,
                    AllowsTransparency = true,
                    PopupAnimation = PopupAnimation.Fade,
                    StaysOpen = true
                };
            }

            _filterPopup.IsOpen = true;
        }

        private void SettingsButton_Click(object sender, RoutedEventArgs e)
        {
            if (_settingsPopup != null && _settingsPopup.IsOpen)
            {
                _settingsPopup.IsOpen = false;
                return;
            }

            if (_settingsPopup == null)
            {
                var settings = new SettingsPopup();
                settings.DataContext = DataContext;

                _settingsPopup = new System.Windows.Controls.Primitives.Popup
                {
                    Child = settings,
                    PlacementTarget = SettingsButton,
                    Placement = System.Windows.Controls.Primitives.PlacementMode.Bottom,
                    HorizontalOffset = 0,
                    VerticalOffset = 5,
                    AllowsTransparency = true,
                    PopupAnimation = System.Windows.Controls.Primitives.PopupAnimation.Fade,
                    StaysOpen = true
                };
            }

            _settingsPopup.IsOpen = true;
        }

        private void HelpButton_Click(object sender, RoutedEventArgs e)
        {
            if (DataContext is MainViewModel vm)
            {
                if (vm.ShowHelpCommand.CanExecute(null))
                {
                    vm.ShowHelpCommand.Execute(null);
                }
            }
        }

        private void OverviewButton_Click(object sender, RoutedEventArgs e)
        {
            if (DataContext is MainViewModel vm)
            {
                // Show overview mode and deselect all wells (macOS parity)
                vm.ShowOverview = true;
                try { this.WellsList.UnselectAll(); } catch { }
                vm.SelectedWells = new System.Collections.ObjectModel.ObservableCollection<WellResult>();
                vm.SelectedWell = null;
                
                // Implement fit-to-width zoom like macOS - use higher priority and longer delay
                Dispatcher.BeginInvoke(() => 
                {
                    // Add small delay to ensure layout is complete
                    System.Threading.Tasks.Task.Delay(50).ContinueWith(_ => 
                    {
                        Dispatcher.Invoke(() => SetOverviewFitToWidth());
                    });
                }, System.Windows.Threading.DispatcherPriority.Loaded);
            }
        }

        private void WellsList_SelectionChanged(object sender, System.Windows.Controls.SelectionChangedEventArgs e)
        {
            if (DataContext is MainViewModel vm && sender is System.Windows.Controls.ListBox lb)
            {
                var sel = lb.SelectedItems.Cast<ddQuint.Core.Models.WellResult>().ToList();
                vm.SetSelectedWells(sel);
                // If overview is on and a well was selected, exit overview to focus the selection
                if (vm.ShowOverview && sel.Count > 0)
                {
                    vm.ShowOverview = false;
                }
                // Reset zoom when selection changes (but not in overview mode)
                if (!vm.ShowOverview)
                {
                    ResetZoomForCurrentView(vm);
                    UpdateGridLayout(vm);
                }
            }
        }

        private void PlotContainer_SizeChanged(object sender, SizeChangedEventArgs e)
        {
            if (DataContext is MainViewModel vm && sender is FrameworkElement fe)
            {
                UpdateGridLayout(vm);
            }
        }

        private void UpdateGridLayout(MainViewModel vm)
        {
            // Calculate responsive grid layout based on available width
            double availableWidth = PlotContainer.ActualWidth;
            if (availableWidth <= 0) return;

            // Overview grid layout (plate-style): use plate column/row counts from data
            int overviewCount = vm.Wells?.Count ?? 0;
            if (overviewCount > 0)
            {
                int maxCol = 1;
                int maxRow = 1;
                var allWells = vm.Wells ?? new System.Collections.ObjectModel.ObservableCollection<WellResult>();
                foreach (var w in allWells)
                {
                    if (w.ColumnIndex > maxCol) maxCol = w.ColumnIndex;
                    if (w.RowIndex > maxRow) maxRow = w.RowIndex;
                }
                vm.OverviewColumns = Math.Max(1, maxCol);
                vm.OverviewRows = Math.Max(1, maxRow);

                // Note: OverviewGrid dimensions are now calculated dynamically in GenerateOverviewWells()
                // Overview grid dimensions are no longer calculated here

                // Set initial zoom to max that shows all columns - skip for overview (has its own zoom logic)
                if (vm.ShowOverview)
                {
                    // Overview zoom is handled separately in SetOverviewFitToWidth
                }
            }

            // Multi-selection fit-to-width (now handled by ViewModel)
            if (vm.IsMultiSelection)
            {
                vm.SetMultiViewFitToWidth(availableWidth);
            }
        }

        private void ResetZoomForCurrentView(MainViewModel vm)
        {
            // Use a small delay to ensure layout is complete
            Dispatcher.BeginInvoke(() =>
            {
                double availableWidth = PlotContainer.ActualWidth;
                if (availableWidth <= 0) return;

                if (vm.ShowOverview)
                {
                    // Overview zoom is handled separately in SetOverviewFitToWidth - don't interfere
                }
                else if (vm.IsMultiSelection)
                {
                    // Reset zoom for multi-selection mode
                    vm.SetMultiViewFitToWidth(availableWidth);
                }
                else
                {
                    // Single plot view - reset to fit
                    vm.PlotZoom = 1.0;
                }
            }, System.Windows.Threading.DispatcherPriority.Loaded);
        }

        private void SetOverviewFitToWidth()
        {
            if (DataContext is MainViewModel vm && OverviewScroller != null)
            {
                double containerWidth = vm.OverviewGridWidth; // Dynamic grid width
                double visibleWidth = OverviewScroller.ViewportWidth;
                
                if (visibleWidth > 0 && containerWidth > 0)
                {
                    double fitToWidthZoom = visibleWidth / containerWidth;
                    
                    // Use reflection to access private AddLogMessage method
                    var addLogMethod = typeof(MainViewModel).GetMethod("AddLogMessage", 
                        System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance);
                    addLogMethod?.Invoke(vm, new object[] { $"🎯 SetOverviewFitToWidth: viewport={visibleWidth:F1}px, container={containerWidth:F1}px, zoom={fitToWidthZoom:F3}" });
                    
                    // Set the minimum zoom to the fit-to-width value (prevent zooming out beyond this)
                    vm.SetMinGridZoom(fitToWidthZoom);
                    
                    // Set initial zoom to fit width
                    vm.GridZoom = fitToWidthZoom;
                    
                    // Scroll to top-left (0,0) like macOS
                    OverviewScroller.ScrollToHorizontalOffset(0);
                    OverviewScroller.ScrollToVerticalOffset(0);
                }
                else
                {
                    // Use reflection to access private AddLogMessage method
                    var addLogMethod = typeof(MainViewModel).GetMethod("AddLogMessage", 
                        System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance);
                    addLogMethod?.Invoke(vm, new object[] { $"🎯 SetOverviewFitToWidth: Invalid viewport size {visibleWidth:F1}px, skipping" });
                }
            }
        }

        private void OverviewScroller_PreviewMouseWheel(object sender, MouseWheelEventArgs e)
        {
            if (DataContext is MainViewModel vm && sender is ScrollViewer sv)
            {
                // Handle Ctrl+zoom
                if (Keyboard.Modifiers == ModifierKeys.Control)
                {
                    // Zoom with Ctrl+wheel matching macOS behavior
                    double factor = e.Delta > 0 ? 1.12 : 1.0 / 1.12;
                    double newZoom = Math.Max(0.1, Math.Min(5.0, vm.GridZoom * factor));
                    vm.GridZoom = newZoom;
                    e.Handled = true;
                }
                // Handle Shift+wheel for horizontal scrolling
                else if (Keyboard.Modifiers == ModifierKeys.Shift)
                {
                    double scrollSpeed = 48; // Pixels per wheel tick
                    if (e.Delta > 0)
                        sv.ScrollToHorizontalOffset(sv.HorizontalOffset - scrollSpeed);
                    else
                        sv.ScrollToHorizontalOffset(sv.HorizontalOffset + scrollSpeed);
                    e.Handled = true;
                }
                // Let normal wheel events scroll vertically (native behavior)
            }
        }

        // Fallback wheel handling on the Overview host - DISABLED (obsolete, conflicts with OverviewScroller handler)
        private void OverviewHost_PreviewMouseWheel(object sender, MouseWheelEventArgs e)
        {
            // This handler is obsolete - OverviewScroller_PreviewMouseWheel handles all overview scrolling now
        }

        private void OverviewScroller_PreviewMouseDown(object sender, MouseButtonEventArgs e)
        {
            // no-op
        }

        private void OverviewScroller_PreviewMouseMove(object sender, MouseEventArgs e)
        {
            // no-op
        }

        private void OverviewScroller_PreviewMouseUp(object sender, MouseButtonEventArgs e)
        {
            // no-op
        }

        private void VerticalScrollBar_Scroll(object sender, System.Windows.Controls.Primitives.ScrollEventArgs e)
        {
            if (OverviewScroller != null)
            {
                OverviewScroller.ScrollToVerticalOffset(e.NewValue);
            }
        }

        private void HorizontalScrollBar_Scroll(object sender, System.Windows.Controls.Primitives.ScrollEventArgs e)
        {
            if (OverviewScroller != null)
            {
                OverviewScroller.ScrollToHorizontalOffset(e.NewValue);
            }
        }

        private void MultiItem_MouseLeftButtonUp(object sender, MouseButtonEventArgs e)
        {
            if (sender is FrameworkElement element && element.DataContext is OverviewWell multiWell)
            {
                // Select the clicked well and exit multi-view (matching overview behavior)
                if (DataContext is MainViewModel vm && multiWell.WellResult != null)
                {
                    // Set the selected well directly (works even if already selected)
                    vm.SelectedWell = multiWell.WellResult;
                    
                    // Select in the wells list too
                    try 
                    { 
                        var index = vm.FilteredWells.ToList().IndexOf(multiWell.WellResult);
                        if (index >= 0)
                        {
                            WellsList.SelectedIndex = index;
                        }
                    } 
                    catch { }
                    
                    e.Handled = true;
                }
            }
        }

        // Multi grid zoom/pan (unified with overview)
        private void MultiScroller_PreviewMouseWheel(object sender, MouseWheelEventArgs e)
        {
            if (DataContext is MainViewModel vm && sender is ScrollViewer sv)
            {
                // Handle Ctrl+zoom
                if (Keyboard.Modifiers == ModifierKeys.Control)
                {
                    // Zoom with Ctrl+wheel matching macOS behavior (unified GridZoom)
                    double factor = e.Delta > 0 ? 1.12 : 1.0 / 1.12;
                    double newZoom = Math.Max(0.1, Math.Min(5.0, vm.GridZoom * factor));
                    vm.GridZoom = newZoom;
                    e.Handled = true;
                }
                // Handle Shift+wheel for horizontal scrolling
                else if (Keyboard.Modifiers == ModifierKeys.Shift)
                {
                    double scrollSpeed = 48; // Pixels per wheel tick
                    if (e.Delta > 0)
                        sv.ScrollToHorizontalOffset(sv.HorizontalOffset - scrollSpeed);
                    else
                        sv.ScrollToHorizontalOffset(sv.HorizontalOffset + scrollSpeed);
                    e.Handled = true;
                }
                // Let normal wheel events scroll vertically (native behavior)
            }
        }

        private void OverviewItems_PreviewMouseLeftButtonUp(object sender, MouseButtonEventArgs e)
        {
            // Handle clicking on overview items to select wells and exit overview
            if (DataContext is MainViewModel vm && e.OriginalSource is FrameworkElement element)
            {
                var overviewWell = element.DataContext as OverviewWell;
                if (overviewWell?.WellResult != null)
                {
                    // Select the well and exit overview mode (matching macOS behavior)
                    vm.SelectedWell = overviewWell.WellResult;
                    vm.ShowOverview = false; // exit overview
                    
                    // Select in the wells list too
                    try 
                    { 
                        var index = vm.FilteredWells.ToList().IndexOf(overviewWell.WellResult);
                        if (index >= 0)
                        {
                            WellsList.SelectedIndex = index;
                        }
                    } 
                    catch { }
                    
                    e.Handled = true;
                }
            }
        }

        private void OverviewItem_MouseLeftButtonUp(object sender, MouseButtonEventArgs e)
        {
            // Handle clicking directly on overview items
            if (DataContext is MainViewModel vm && sender is FrameworkElement element)
            {
                var overviewWell = element.DataContext as OverviewWell;
                if (overviewWell?.WellResult != null)
                {
                    // Select the well and exit overview mode (matching macOS behavior)
                    vm.SelectedWell = overviewWell.WellResult;
                    vm.ShowOverview = false; // exit overview
                    
                    // Select in the wells list too
                    try 
                    { 
                        var index = vm.FilteredWells.ToList().IndexOf(overviewWell.WellResult);
                        if (index >= 0)
                        {
                            WellsList.SelectedIndex = index;
                        }
                    } 
                    catch { }
                    
                    e.Handled = true;
                }
            }
        }

        private void MultiScroller_PreviewMouseDown(object sender, MouseButtonEventArgs e)
        {
            // no-op - use native scrolling like OverviewScroller
        }

        private void MultiScroller_PreviewMouseMove(object sender, MouseEventArgs e)
        {
            // no-op - use native scrolling like OverviewScroller
        }

        private void MultiScroller_PreviewMouseUp(object sender, MouseButtonEventArgs e)
        {
            // no-op - use native scrolling like OverviewScroller
        }

        private void SinglePlotScroller_PreviewMouseWheel(object sender, MouseWheelEventArgs e)
        {
            if (DataContext is MainViewModel vm && sender is System.Windows.Controls.ScrollViewer sv)
            {
                // Only zoom when Ctrl key is held, otherwise allow normal scrolling
                if (Keyboard.Modifiers == ModifierKeys.Control)
                {
                    double factor = e.Delta > 0 ? 1.12 : 1.0 / 1.12;
                    vm.PlotZoom = Math.Max(0.5, Math.Min(5.0, vm.PlotZoom * factor));
                    sv.UpdateLayout();
                    e.Handled = true;
                }
                // If Ctrl is not held, don't handle the event - let it scroll normally
            }
        }

        private void SinglePlotScroller_PreviewMouseDown(object sender, MouseButtonEventArgs e)
        {
            if (sender is System.Windows.Controls.ScrollViewer sv)
            {
                // Middle button panning (common on Windows)
                if (e.MiddleButton == MouseButtonState.Pressed)
                {
                    _isPanning = true;
                    _panStart = e.GetPosition(sv);
                    _panStartH = sv.HorizontalOffset;
                    _panStartV = sv.VerticalOffset;
                    sv.CaptureMouse();
                    Mouse.OverrideCursor = Cursors.Hand;
                    e.Handled = true;
                }
            }
        }

        private void SinglePlotScroller_PreviewMouseMove(object sender, MouseEventArgs e)
        {
            if (_isPanning && sender is System.Windows.Controls.ScrollViewer sv)
            {
                var p = e.GetPosition(sv);
                var dx = p.X - _panStart.X;
                var dy = p.Y - _panStart.Y;
                sv.ScrollToHorizontalOffset(_panStartH - dx);
                sv.ScrollToVerticalOffset(_panStartV - dy);
                e.Handled = true;
            }
        }

        private void SinglePlotScroller_PreviewMouseUp(object sender, MouseButtonEventArgs e)
        {
            if (_isPanning && sender is System.Windows.Controls.ScrollViewer sv)
            {
                _isPanning = false;
                if (sv.IsMouseCaptured) sv.ReleaseMouseCapture();
                Mouse.OverrideCursor = null;
                e.Handled = true;
            }
        }

        private void WellsList_PreviewMouseLeftButtonDown(object sender, MouseButtonEventArgs e)
        {
            if (sender is System.Windows.Controls.ListBox lb)
            {
                // Ensure the list gains keyboard focus so arrow keys work
                if (!lb.IsKeyboardFocusWithin)
                {
                    lb.Focus();
                }
                var point = e.GetPosition(lb);
                var element = lb.InputHitTest(point) as DependencyObject;
                while (element != null && element is not System.Windows.Controls.ListBoxItem)
                {
                    element = System.Windows.Media.VisualTreeHelper.GetParent(element);
                }
                if (element is System.Windows.Controls.ListBoxItem item)
                {
                    _dragAnchorIndex = lb.ItemContainerGenerator.IndexFromContainer(item);
                    _isDragSelecting = true;
                    lb.CaptureMouse();
                }
                else
                {
                    _dragAnchorIndex = null;
                    _isDragSelecting = false;
                }
            }
        }

        private void WellsList_PreviewMouseMove(object sender, MouseEventArgs e)
        {
            if (!_isDragSelecting || _dragAnchorIndex == null) return;
            if (sender is System.Windows.Controls.ListBox lb && e.LeftButton == MouseButtonState.Pressed)
            {
                var point = e.GetPosition(lb);
                var element = lb.InputHitTest(point) as DependencyObject;
                while (element != null && element is not System.Windows.Controls.ListBoxItem)
                {
                    element = System.Windows.Media.VisualTreeHelper.GetParent(element);
                }
                if (element is System.Windows.Controls.ListBoxItem currentItem)
                {
                    int currentIndex = lb.ItemContainerGenerator.IndexFromContainer(currentItem);
                    if (currentIndex >= 0)
                    {
                        int start = Math.Min(_dragAnchorIndex.Value, currentIndex);
                        int end = Math.Max(_dragAnchorIndex.Value, currentIndex);
                        lb.SelectedItems.Clear();
                        for (int i = start; i <= end; i++)
                        {
                            if (lb.ItemContainerGenerator.ContainerFromIndex(i) is System.Windows.Controls.ListBoxItem li)
                            {
                                li.IsSelected = true;
                            }
                            else
                            {
                                var itemObj = lb.Items[i];
                                lb.SelectedItems.Add(itemObj);
                            }
                        }
                    }
                }
            }
        }

        private void WellsList_PreviewMouseLeftButtonUp(object sender, MouseButtonEventArgs e)
        {
            if (sender is System.Windows.Controls.ListBox lb)
            {
                if (lb.IsMouseCaptured) lb.ReleaseMouseCapture();
            }
            _isDragSelecting = false;
            _dragAnchorIndex = null;
        }

        private void WellsList_PreviewKeyDown(object sender, KeyEventArgs e)
        {
            if (sender is not System.Windows.Controls.ListBox lb) return;
            if (lb.Items.Count == 0) return;

            int current = lb.SelectedIndex;
            if (e.Key == Key.Down)
            {
                int next = current < 0 ? 0 : Math.Min(current + 1, lb.Items.Count - 1);
                if (next != current)
                {
                    lb.SelectedIndex = next;
                    lb.ScrollIntoView(lb.SelectedItem);
                    e.Handled = true;
                }
            }
            else if (e.Key == Key.Up)
            {
                int prev = current < 0 ? 0 : Math.Max(current - 1, 0);
                if (prev != current)
                {
                    lb.SelectedIndex = prev;
                    lb.ScrollIntoView(lb.SelectedItem);
                    e.Handled = true;
                }
            }
        }

        private void Window_Loaded(object sender, RoutedEventArgs e)
        {
            LogMessage("Window_Loaded event fired");
            LogMessage($"Window actual size: {ActualWidth}x{ActualHeight}");
            LogMessage($"Window is visible: {IsVisible}");
            LogMessage($"Window state: {WindowState}");
            
            // Force the window to show and activate
            try
            {
                Show();
                Activate();
                Focus();
                LogMessage("Explicitly called Show(), Activate(), and Focus()");
                // Handle outside clicks to close popups when StaysOpen=true
                this.PreviewMouseDown += OnWindowPreviewMouseDown;
            }
            catch (Exception ex)
            {
                LogMessage($"Error in Window_Loaded: {ex.Message}");
            }
        }

        private void Window_Activated(object sender, EventArgs e)
        {
            LogMessage("Window_Activated event fired");
            LogMessage($"Window topmost: {Topmost}");
            LogMessage($"Window focus: {IsFocused}");
        }

        private static void LogMessage(string message)
        {
            var timestamp = DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss.fff");
            var logEntry = $"[{timestamp}] MAINWINDOW: {message}";
            
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
        // Close popups when clicking outside while StaysOpen=true
        private void OnWindowPreviewMouseDown(object? sender, System.Windows.Input.MouseButtonEventArgs e)
        {
            try
            {
                var src = e.OriginalSource as System.Windows.DependencyObject;
                bool overFilterBtn = IsDescendantOf(src, this.FilterButton);
                bool overFilterPopup = (_filterPopup?.Child != null) && IsDescendantOf(src, _filterPopup.Child);
                bool overSettingsBtn = IsDescendantOf(src, this.SettingsButton);
                bool overSettingsPopup = (_settingsPopup?.Child != null) && IsDescendantOf(src, _settingsPopup.Child);

                if (!overFilterBtn && !overFilterPopup && _filterPopup != null && _filterPopup.IsOpen)
                    _filterPopup.IsOpen = false;
                if (!overSettingsBtn && !overSettingsPopup && _settingsPopup != null && _settingsPopup.IsOpen)
                    _settingsPopup.IsOpen = false;
            }
            catch { }
        }

        private static bool IsDescendantOf(System.Windows.DependencyObject? child, System.Windows.DependencyObject ancestor)
        {
            while (child != null)
            {
                if (child == ancestor) return true;
                child = System.Windows.Media.VisualTreeHelper.GetParent(child);
            }
            return false;
        }

        // Physical horizontal mouse wheel support
        private void InitializeHorizontalWheelSupport()
        {
            try
            {
                // Initialize after the window is loaded to ensure HWND exists
                this.Loaded += (s, e) => {
                    try
                    {
                        _horizontalWheelHelper = new HorizontalWheelHelper(OverviewScroller, MultiScroller, this);
                        LogMessage("Physical horizontal wheel support initialized");
                    }
                    catch (Exception ex)
                    {
                        LogMessage($"Failed to initialize horizontal wheel support: {ex.Message}");
                    }
                };
            }
            catch (Exception ex)
            {
                LogMessage($"Error setting up horizontal wheel support: {ex.Message}");
            }
        }

        // Helper class for physical horizontal mouse wheel support
        private class HorizontalWheelHelper
        {
            private const int WM_MOUSEHWHEEL = 0x020E;
            private const double ScrollFactor = 96; // Pixels per wheel tick
            
            private readonly ScrollViewer _overviewScroller;
            private readonly ScrollViewer _multiScroller;
            private readonly HwndSource? _hwndSource;
            private readonly HwndSourceHook _hook;
            
            public HorizontalWheelHelper(ScrollViewer overviewScroller, ScrollViewer multiScroller, Window window)
            {
                _overviewScroller = overviewScroller;
                _multiScroller = multiScroller;
                _hook = WindowProc;
                
                // Get the window's HWND source for message hooking
                _hwndSource = PresentationSource.FromVisual(window) as HwndSource;
                _hwndSource?.AddHook(_hook);
            }
            
            private IntPtr WindowProc(IntPtr hwnd, int msg, IntPtr wParam, IntPtr lParam, ref bool handled)
            {
                if (msg == WM_MOUSEHWHEEL)
                {
                    try
                    {
                        // Extract wheel delta (high-order word of wParam)
                        int delta = (short)((((int)wParam.ToInt64()) >> 16) & 0xFFFF);
                        double scrollAmount = delta * ScrollFactor / 120.0; // 120 = WHEEL_DELTA
                        
                        // Determine which scroller to use based on visibility/focus
                        ScrollViewer? targetScroller = GetActiveScrollViewer();
                        if (targetScroller != null)
                        {
                            double newOffset = targetScroller.HorizontalOffset - scrollAmount;
                            targetScroller.ScrollToHorizontalOffset(Math.Max(0, newOffset));
                            handled = true;
                        }
                    }
                    catch
                    {
                        // Ignore errors in message handling to prevent crashes
                    }
                }
                return IntPtr.Zero;
            }
            
            private ScrollViewer? GetActiveScrollViewer()
            {
                // Check which scroller is visible and should handle the event
                if (_overviewScroller.Visibility == Visibility.Visible)
                    return _overviewScroller;
                if (_multiScroller.Visibility == Visibility.Visible)
                    return _multiScroller;
                return null;
            }
            
            public void Dispose()
            {
                _hwndSource?.RemoveHook(_hook);
            }
        }
    }
}
