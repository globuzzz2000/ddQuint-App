using System;
using System.Globalization;
using System.Windows.Data;
using System.Windows.Media;
using ddQuint.Core.Models;

namespace ddQuint.Desktop.Converters
{
    public class WellStatusToBrushConverter : IValueConverter
    {
        public object Convert(object value, Type targetType, object parameter, CultureInfo culture)
        {
            if (value is not WellStatus status)
                return new SolidColorBrush(Colors.White);

            return status switch
            {
                WellStatus.Normal => new SolidColorBrush(Color.FromRgb(0xFF, 0xFF, 0xFF)), // #FFFFFF
                WellStatus.BufferZone => new SolidColorBrush(Color.FromRgb(0x66, 0x66, 0x66)), // #666666  
                WellStatus.Deviation => new SolidColorBrush(Color.FromRgb(0xD8, 0x6D, 0xCD)), // #D86DCD
                WellStatus.Warning => new SolidColorBrush(Color.FromRgb(0xFF, 0x00, 0x00)), // #FF0000
                WellStatus.Edited => new SolidColorBrush(Color.FromRgb(0x00, 0x7A, 0xFF)), // Keep blue for edited
                _ => new SolidColorBrush(Colors.White)
            };
        }

        public object ConvertBack(object value, Type targetType, object parameter, CultureInfo culture)
        {
            throw new NotImplementedException();
        }
    }
}