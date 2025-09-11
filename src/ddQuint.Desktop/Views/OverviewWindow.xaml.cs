using System.Collections.Generic;
using System.Linq;
using System.Windows;
using System.Windows.Input;
using ddQuint.Core.Models;
using ddQuint.Desktop.ViewModels;

namespace ddQuint.Desktop.Views
{
    public partial class OverviewWindow : Window
    {
        private readonly MainViewModel _vm;
        private readonly List<WellResult> _items;

        public OverviewWindow(MainViewModel vm, IEnumerable<WellResult> wells)
        {
            InitializeComponent();
            _vm = vm;
            _items = wells?.ToList() ?? new List<WellResult>();
            Title = _items.Count > 1 ? $"Overview - {_items.Count} Wells" : "Overview";
            Items.ItemsSource = _items;
        }

        private void ScrollViewer_PreviewMouseWheel(object sender, MouseWheelEventArgs e)
        {
            if (sender is System.Windows.Controls.ScrollViewer scrollViewer)
            {
                scrollViewer.ScrollToVerticalOffset(scrollViewer.VerticalOffset - (e.Delta * 0.5));
                e.Handled = true;
            }
        }
    }
}

