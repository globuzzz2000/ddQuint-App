using System;
using System.ComponentModel;
using System.Runtime.CompilerServices;
using ddQuint.Core.Models;

namespace ddQuint.Desktop.Models
{
    public class OverviewWell : INotifyPropertyChanged
    {
        private string _wellId = string.Empty;
        private string? _thumbnailImagePath;
        private double _x;
        private double _y;
        private WellResult? _wellResult;

        public string WellId
        {
            get => _wellId;
            set
            {
                if (_wellId != value)
                {
                    _wellId = value;
                    OnPropertyChanged();
                }
            }
        }

        public string? ThumbnailImagePath
        {
            get => _thumbnailImagePath;
            set
            {
                if (_thumbnailImagePath != value)
                {
                    _thumbnailImagePath = value;
                    OnPropertyChanged();
                }
            }
        }

        public double X
        {
            get => _x;
            set
            {
                if (Math.Abs(_x - value) > 0.1)
                {
                    _x = value;
                    OnPropertyChanged();
                }
            }
        }

        public double Y
        {
            get => _y;
            set
            {
                if (Math.Abs(_y - value) > 0.1)
                {
                    _y = value;
                    OnPropertyChanged();
                }
            }
        }

        public WellResult? WellResult
        {
            get => _wellResult;
            set
            {
                if (_wellResult != value)
                {
                    _wellResult = value;
                    OnPropertyChanged();
                }
            }
        }

        private double _scaledX;
        private double _scaledY;

        public double ScaledX
        {
            get => _scaledX;
            set
            {
                if (Math.Abs(_scaledX - value) > 0.1)
                {
                    _scaledX = value;
                    OnPropertyChanged();
                }
            }
        }

        public double ScaledY
        {
            get => _scaledY;
            set
            {
                if (Math.Abs(_scaledY - value) > 0.1)
                {
                    _scaledY = value;
                    OnPropertyChanged();
                }
            }
        }

        public event PropertyChangedEventHandler? PropertyChanged;

        protected virtual void OnPropertyChanged([CallerMemberName] string? propertyName = null)
        {
            PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(propertyName));
        }
    }
}