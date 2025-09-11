using System;
using System.Globalization;
using System.Windows.Data;

namespace ddQuint.Desktop.Converters
{
    public class MultiplyConverter : IValueConverter
    {
        public object Convert(object value, Type targetType, object parameter, CultureInfo culture)
        {
            if (value == null) return 0d;
            double v;
            try { v = System.Convert.ToDouble(value, CultureInfo.InvariantCulture); } catch { return 0d; }
            double factor = 1.0;
            if (parameter != null)
            {
                try { factor = System.Convert.ToDouble(parameter, CultureInfo.InvariantCulture); } catch { }
            }
            return v * factor;
        }

        public object ConvertBack(object value, Type targetType, object parameter, CultureInfo culture)
        {
            throw new NotImplementedException();
        }
    }
}

