using System.ComponentModel;

namespace ddQuint.Desktop.ViewModels
{
    public interface IFilterableViewModel : INotifyPropertyChanged
    {
        bool HideBufferZone { get; set; }
        bool HideWarnings { get; set; }
    }
}