using System.Windows.Controls;
using System.Windows.Controls.Primitives;

namespace ddQuint.Desktop.Views
{
    public partial class FilterPopup : UserControl
    {
        public FilterPopup()
        {
            InitializeComponent();
        }
        
        // No need for parent popup reference anymore since changes apply immediately
    }
}