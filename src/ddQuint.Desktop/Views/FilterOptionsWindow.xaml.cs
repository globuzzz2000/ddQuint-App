using System.Windows;
using ddQuint.Desktop.ViewModels;

namespace ddQuint.Desktop.Views
{
    public partial class FilterOptionsWindow : Window
    {
        private readonly IFilterableViewModel _viewModel;

        public FilterOptionsWindow(IFilterableViewModel viewModel)
        {
            InitializeComponent();
            _viewModel = viewModel;
            DataContext = viewModel;
        }

        private void Apply_Click(object sender, RoutedEventArgs e)
        {
            // The binding will automatically update the ViewModel properties
            DialogResult = true;
            Close();
        }

        private void Cancel_Click(object sender, RoutedEventArgs e)
        {
            DialogResult = false;
            Close();
        }
    }
}