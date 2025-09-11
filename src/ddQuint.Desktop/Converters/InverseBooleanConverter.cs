using System;
using System.Globalization;
using System.Windows.Data;

namespace ddQuint.Desktop.Converters
{
    public class InverseBooleanConverter : IValueConverter
    {
        public object Convert(object value, Type targetType, object parameter, CultureInfo culture)
        {
            if (value is bool b) return !b;
            bool parsed;
            if (bool.TryParse(value?.ToString() ?? "false", out parsed)) return !parsed;
            return true;
        }

        public object ConvertBack(object value, Type targetType, object parameter, CultureInfo culture)
        {
            if (value is bool b) return !b;
            bool parsed;
            if (bool.TryParse(value?.ToString() ?? "false", out parsed)) return !parsed;
            return false;
        }
    }
}

