using System;
using System.IO;
using System.Windows;
using ddQuint.Desktop.Services;

namespace ddQuint.Desktop
{
    public partial class App : Application
    {
        protected override void OnStartup(StartupEventArgs e)
        {
            try
            {
                LogMessage("App.OnStartup called");
                base.OnStartup(e);
                
                LogMessage("Clearing caches...");
                // Clear all caches on app launch (similar to macOS version)
                ClearAllCaches();
                
                LogMessage("Starting Python environment initialization on background thread...");
                System.Threading.Tasks.Task.Run(() =>
                {
                    try
                    {
                        InitializePythonEnvironment();
                    }
                    catch (Exception ex)
                    {
                        LogMessage($"Background Python init error: {ex.Message}");
                    }
                });
                
                LogMessage("App.OnStartup completed successfully");
            }
            catch (Exception ex)
            {
                var errorMsg = $"FATAL ERROR in OnStartup: {ex.Message}\nStack: {ex.StackTrace}";
                LogMessage(errorMsg);
                
                MessageBox.Show(errorMsg, "Application Startup Error", MessageBoxButton.OK, MessageBoxImage.Error);
                Environment.Exit(1);
            }
        }
        
        protected override void OnExit(ExitEventArgs e)
        {
            // Cleanup on exit
            base.OnExit(e);
        }
        
        private void ClearAllCaches()
        {
            try
            {
                var tempPath = Path.GetTempPath();
                var ddquintTempPath = Path.Combine(tempPath, "ddquint");
                
                // Clear temp plot files
                if (Directory.Exists(ddquintTempPath))
                {
                    var plotFiles = Directory.GetFiles(ddquintTempPath, "ddquint_plot_*.png");
                    foreach (var file in plotFiles)
                    {
                        try
                        {
                            File.Delete(file);
                            LogMessage($"CACHE_CLEAR: Removed temp plot: {file}");
                        }
                        catch (Exception ex)
                        {
                            LogMessage($"CACHE_CLEAR: Error removing {file}: {ex.Message}");
                        }
                    }
                }
                
                // Clear analysis plots directory
                var analysisPlotPath = Path.Combine(ddquintTempPath, "analysis_plots");
                if (Directory.Exists(analysisPlotPath))
                {
                    try
                    {
                        Directory.Delete(analysisPlotPath, true);
                        LogMessage($"CACHE_CLEAR: Removed analysis plots directory: {analysisPlotPath}");
                    }
                    catch (Exception ex)
                    {
                        LogMessage($"CACHE_CLEAR: Error removing analysis plots directory: {ex.Message}");
                    }
                }
                
                // Clear parameter temp files
                var paramFiles = Directory.GetFiles(tempPath, "ddquint_params_*.json");
                foreach (var file in paramFiles)
                {
                    try
                    {
                        File.Delete(file);
                        LogMessage($"CACHE_CLEAR: Removed param file: {file}");
                    }
                    catch (Exception ex)
                    {
                        LogMessage($"CACHE_CLEAR: Error removing param file {file}: {ex.Message}");
                    }
                }
                
                LogMessage("CACHE_CLEAR: Cache clearing completed");
            }
            catch (Exception ex)
            {
                LogMessage($"CACHE_CLEAR: Error during cache clearing: {ex.Message}");
            }
        }
        
        private void InitializePythonEnvironment()
        {
            try
            {
                LogMessage("Creating Python service instance...");
                // Initialize Python bridge
                var pythonService = PythonEnvironmentService.Instance;
                
                LogMessage("Calling Python service Initialize()...");
                pythonService.Initialize();
                
                LogMessage("Python environment initialized successfully");
            }
            catch (Exception ex)
            {
                LogMessage($"Error initializing Python environment: {ex.Message}");
                LogMessage($"Stack trace: {ex.StackTrace}");
                
                // Don't show modal dialog during startup - just log the error
                // The application should still open so user can see what's wrong
                LogMessage("Application will continue without Python environment.");
                LogMessage("Analysis features will be disabled until Python is properly configured.");
            }
        }
        
        private static void LogMessage(string message)
        {
            var timestamp = DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss.fff");
            var logEntry = $"[{timestamp}] APP: {message}";
            
            // Write to console
            Console.WriteLine(logEntry);
            
            // Write to file
            try
            {
                var logPath = Path.Combine(Path.GetTempPath(), "ddquint_startup.log");
                File.AppendAllText(logPath, logEntry + Environment.NewLine);
            }
            catch
            {
                // Ignore file logging errors
            }
        }
    }
}
