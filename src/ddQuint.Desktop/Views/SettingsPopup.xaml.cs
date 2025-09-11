using System;
using System.Windows;
using System.Windows.Controls;
using ddQuint.Desktop.ViewModels;

namespace ddQuint.Desktop.Views
{
    public partial class SettingsPopup : UserControl
    {
        public SettingsPopup()
        {
            InitializeComponent();
            DataContextChanged += OnDataContextChanged;
            // Close the settings popup whenever a leaf menu item is clicked (matches macOS feel)
            // Use routed event to capture all MenuItem clicks within this control
            AddHandler(System.Windows.Controls.MenuItem.ClickEvent, new RoutedEventHandler(OnAnyMenuItemClick), true);
        }
        
        private void OnDataContextChanged(object sender, DependencyPropertyChangedEventArgs e)
        {
            if (e.OldValue is MainViewModel oldVm)
            {
                oldVm.ClosePopupRequested -= OnClosePopupRequested;
            }
            
            if (e.NewValue is MainViewModel newVm)
            {
                newVm.ClosePopupRequested += OnClosePopupRequested;
            }
        }
        
        private void OnClosePopupRequested(object? sender, EventArgs e)
        {
            CloseSettingsPopup();
        }

        private void Close_Click(object sender, RoutedEventArgs e)
        {
            // Close main window (acts as File > Close)
            if (DataContext is MainViewModel vm) { vm.ClearAnalysis(); }
            CloseSettingsPopup();
        }

        private void SetDescCount_Click(object sender, RoutedEventArgs e)
        {
            if (sender is MenuItem mi && int.TryParse(mi.Tag?.ToString(), out int count))
            {
                // Toggle checkmarks within sibling items
                if (mi.Parent is MenuItem parent && parent.HasItems)
                {
                    foreach (var item in parent.Items)
                    {
                        if (item is MenuItem m)
                            m.IsChecked = Equals(m, mi);
                    }
                }

                // Forward to VM if it exposes a handler
                if (DataContext is MainViewModel vm)
                {
                    try
                    {
                        var method = vm.GetType().GetMethod("SetTemplateDescriptionCount");
                        method?.Invoke(vm, new object[] { count });
                    }
                    catch { }
                }
                
                // Close the settings popup after selection
                CloseSettingsPopup();
            }
        }
        
        private void CloseSettingsPopup()
        {
            // Find the parent popup and close it
            var parent = this.Parent;
            while (parent != null)
            {
                if (parent is System.Windows.Controls.Primitives.Popup popup)
                {
                    popup.IsOpen = false;
                    break;
                }
                parent = LogicalTreeHelper.GetParent(parent);
            }
        }

        private void ExportPlots_Click(object sender, RoutedEventArgs e)
        {
            if (DataContext is MainViewModel vm)
            {
                vm.ExportPlots();
            }
            CloseSettingsPopup();
        }

        private void ExportParameters_Click(object sender, RoutedEventArgs e)
        {
            if (DataContext is MainViewModel vm)
            {
                vm.ExportParameters();
            }
            CloseSettingsPopup();
        }

        private void LoadParameters_Click(object sender, RoutedEventArgs e)
        {
            if (DataContext is MainViewModel vm)
            {
                vm.LoadParameters();
            }
            CloseSettingsPopup();
        }

        private void OnAnyMenuItemClick(object sender, RoutedEventArgs e)
        {
            // Only close on leaf items (no submenu), to avoid closing when expanding a submenu header
            if (e.OriginalSource is System.Windows.Controls.MenuItem mi)
            {
                if (!mi.HasItems)
                {
                    CloseSettingsPopup();
                }
            }
        }

        private void OnLeafMenuItemClick(object sender, RoutedEventArgs e)
        {
            // Explicit closer for leaf MenuItems that use Command bindings
            CloseSettingsPopup();
        }
    }
}
