using System.ComponentModel;

namespace ddQuint.Core.Models
{
    public enum WellStatus
    {
        Normal,
        BufferZone,
        Deviation,
        Warning,
        Edited
    }
    
    public class WellResult : INotifyPropertyChanged
    {
        private string _wellId = "";
        private string _sampleName = "";
        private WellStatus _status;
        private string? _plotImagePath;
        private bool _isEdited;
        
        // Cache for parsed indices
        private int? _rowIndexCache;
        private int? _columnIndexCache;
        
        public string WellId
        {
            get => _wellId;
            set
            {
                _wellId = value;
                OnPropertyChanged(nameof(WellId));
                OnPropertyChanged(nameof(DisplayName));
            }
        }
        
        public string SampleName
        {
            get => _sampleName;
            set
            {
                _sampleName = value;
                OnPropertyChanged(nameof(SampleName));
                OnPropertyChanged(nameof(DisplayName));
            }
        }
        
        public WellStatus Status
        {
            get => _status;
            set
            {
                _status = value;
                OnPropertyChanged(nameof(Status));
            }
        }
        
        public string? PlotImagePath
        {
            get => _plotImagePath;
            set
            {
                _plotImagePath = value;
                OnPropertyChanged(nameof(PlotImagePath));
                OnPropertyChanged(nameof(HasData));
            }
        }
        
        public bool IsEdited
        {
            get => _isEdited;
            set
            {
                _isEdited = value;
                OnPropertyChanged(nameof(IsEdited));
            }
        }
        
        // Computed properties
        public string DisplayName => string.IsNullOrEmpty(SampleName) ? WellId : $"{WellId}: {SampleName}";
        
        // True when a plot was generated for this well (proxy for has_data)
        public bool HasData => !string.IsNullOrWhiteSpace(PlotImagePath);

        // Row index from WellId (A=1, B=2, ...), 0 if unknown
        public int RowIndex
        {
            get
            {
                if (_rowIndexCache.HasValue) return _rowIndexCache.Value;
                if (string.IsNullOrWhiteSpace(WellId)) return 0;
                // Expect formats like A01, B12, etc.
                char c = WellId.Trim()[0];
                int val = char.IsLetter(c) ? (char.ToUpperInvariant(c) - 'A' + 1) : 0;
                _rowIndexCache = val;
                return val;
            }
        }

        // Column index from WellId (01..12 typical), 0 if unknown
        public int ColumnIndex
        {
            get
            {
                if (_columnIndexCache.HasValue) return _columnIndexCache.Value;
                if (string.IsNullOrWhiteSpace(WellId)) return 0;
                // Extract trailing digits
                var digits = new string(WellId.Where(char.IsDigit).ToArray());
                if (int.TryParse(digits, out int col))
                {
                    _columnIndexCache = col;
                    return col;
                }
                return 0;
            }
        }

        // Combined index for column-first sorting (sort by column, then row)
        public int ColumnFirstIndex => (ColumnIndex * 100) + RowIndex;

        // Combined index for row-first sorting (sort by row, then column)
        public int RowFirstIndex => (RowIndex * 100) + ColumnIndex;
        
        // Analysis results
        public double[]? CopyNumbers { get; set; }
        public Dictionary<string, double>? CopyNumbersDictionary { get; set; }
        public string[]? Classifications { get; set; }
        public Dictionary<string, object>? AnalysisData { get; set; }
        public int TotalDroplets { get; set; }
        public int UsableDroplets { get; set; }
        public int NegativeDroplets { get; set; }
        
        public event PropertyChangedEventHandler? PropertyChanged;
        
        protected virtual void OnPropertyChanged(string propertyName)
        {
            PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(propertyName));
        }
    }
}
