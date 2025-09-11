namespace ddQuint.Core.Models
{
    public class AnalysisResult
    {
        public List<WellResult> Wells { get; set; } = new();
        public string? PlateOverviewImagePath { get; set; }
        public Dictionary<string, object>? GlobalParameters { get; set; }
        public DateTime AnalysisTimestamp { get; set; } = DateTime.Now;
        public string? InputFolderPath { get; set; }
        public string? TemplateFilePath { get; set; }
        // Path to the results.json produced by analysis (for exports)
        public string? ResultsJsonPath { get; set; }
    }
}
