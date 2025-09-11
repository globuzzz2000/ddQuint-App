using System;
using System.Globalization;
using System.IO;
using System.Windows.Data;
using System.Windows.Media.Imaging;

namespace ddQuint.Desktop.Converters
{
    // Loads an image from a file path with decode width to reduce memory and improve overview performance
    public class ThumbnailImageConverter : IValueConverter
    {
        public object? Convert(object value, Type targetType, object parameter, CultureInfo culture)
        {
            try
            {
                var path = value as string;
                if (string.IsNullOrWhiteSpace(path) || !File.Exists(path)) return null;

                int decodeWidth = 0;
                if (parameter != null && int.TryParse(parameter.ToString(), out var w) && w > 0)
                {
                    decodeWidth = w;
                }
                var bi = new BitmapImage();
                bi.BeginInit();
                bi.CacheOption = BitmapCacheOption.OnLoad; // allow file to be released
                bi.CreateOptions = BitmapCreateOptions.IgnoreColorProfile; // speed
                if (decodeWidth > 0) bi.DecodePixelWidth = decodeWidth;
                bi.UriSource = new Uri(path, UriKind.Absolute);
                bi.EndInit();
                bi.Freeze();
                return bi;
            }
            catch
            {
                return null;
            }
        }

        public object ConvertBack(object value, Type targetType, object parameter, CultureInfo culture) => throw new NotImplementedException();
    }
}

