using System;
using System.Globalization;
using System.Linq;
using System.Windows.Data;

namespace ddQuint.Desktop.Converters
{
    public class BooleanAndConverter : IMultiValueConverter
    {
        public object Convert(object[] values, Type targetType, object parameter, CultureInfo culture)
        {
            if (values == null || values.Length == 0) return false;
            try
            {
                return values.All(v =>
                {
                    if (v is bool b) return b;
                    if (bool.TryParse(v?.ToString() ?? "false", out var parsed)) return parsed;
                    return false;
                });
            }
            catch { return false; }
        }

        public object[] ConvertBack(object value, Type[] targetTypes, object parameter, CultureInfo culture)
        {
            throw new NotImplementedException();
        }
    }
}

