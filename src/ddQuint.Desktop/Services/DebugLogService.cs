using System;
using System.IO;
using System.Text;

namespace ddQuint.Desktop.Services
{
    public static class DebugLogService
    {
        private static readonly string LogsFolder = Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData),
            "ddQuint",
            "logs");
        
        private static readonly string LogFilePath = Path.Combine(LogsFolder, "debug.log");
        private static readonly object _lockObject = new object();
        
        /// <summary>
        /// Initialize debug logging directory (matching macOS structure)
        /// </summary>
        public static void Initialize()
        {
            try
            {
                Directory.CreateDirectory(LogsFolder);
                
                // Always create a new log file for each session
                if (File.Exists(LogFilePath))
                {
                    RotateLogFile();
                }
                
                LogMessage("=== NEW DEBUG SESSION STARTED ===");
                LogMessage($"Session started at: {DateTime.Now:yyyy-MM-dd HH:mm:ss}");
                LogMessage($"Process ID: {Environment.ProcessId}");
                LogMessage("Debug logging initialized");
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Warning: Could not initialize debug logging: {ex.Message}");
            }
        }
        
        /// <summary>
        /// Log a message to debug.log with timestamp (matching macOS format)
        /// </summary>
        public static void LogMessage(string message)
        {
            try
            {
                lock (_lockObject)
                {
                    var timestamp = DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss.fff");
                    var logEntry = $"[{timestamp}] {message}\n";
                    
                    Directory.CreateDirectory(LogsFolder);
                    File.AppendAllText(LogFilePath, logEntry, Encoding.UTF8);
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Warning: Could not write to debug log: {ex.Message}");
            }
        }
        
        /// <summary>
        /// Process Python output and extract DDQUINT_LOG lines (matching macOS)
        /// </summary>
        public static void ProcessPythonOutput(string output)
        {
            if (string.IsNullOrEmpty(output)) return;
            
            var lines = output.Split('\n');
            foreach (var line in lines)
            {
                // Log DDQUINT_LOG prefixed lines to debug.log
                if (line.StartsWith("DDQUINT_LOG:"))
                {
                    var logContent = line.Substring("DDQUINT_LOG:".Length).Trim();
                    LogMessage($"Python: {logContent}");
                }
                
                // Also log important debug information
                if (line.Contains("DEBUG:") || line.Contains("Parameters file") || line.Contains("Config initialized"))
                {
                    LogMessage($"Python: {line.Trim()}");
                }
            }
        }
        
        private static void RotateLogFile()
        {
            try
            {
                var timestamp = DateTime.Now.ToString("yyyyMMdd_HHmmss");
                var baseName = $"debug_{timestamp}.log";
                var rotatedPath = Path.Combine(LogsFolder, baseName);
                var counter = 1;
                while (File.Exists(rotatedPath))
                {
                    rotatedPath = Path.Combine(LogsFolder, $"debug_{timestamp}_{counter++}.log");
                }

                // Try to move current log to rotated name; if moving fails (locked), copy+truncate
                try
                {
                    File.Move(LogFilePath, rotatedPath);
                }
                catch
                {
                    try
                    {
                        File.Copy(LogFilePath, rotatedPath, overwrite: true);
                        using var fs = new FileStream(LogFilePath, FileMode.Create, FileAccess.Write, FileShare.ReadWrite);
                    }
                    catch (Exception copyEx)
                    {
                        Console.WriteLine($"Warning: Could not rotate log file via copy/truncate: {copyEx.Message}");
                    }
                }
                
                // Clean up old rotated logs (keep only 5 most recent like macOS)
                CleanupOldLogs();
                
                LogMessage($"Log rotated to debug_{timestamp}.log");
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Warning: Could not rotate log file: {ex.Message}");
            }
        }
        
        private static void CleanupOldLogs()
        {
            try
            {
                var logFiles = Directory.GetFiles(LogsFolder, "debug_*.log");
                if (logFiles.Length <= 5) return;
                
                // Sort by last write time (newest first) for robustness
                Array.Sort(logFiles, (a, b) => File.GetLastWriteTime(b).CompareTo(File.GetLastWriteTime(a)));
                
                // Delete files beyond the first 5
                for (int i = 5; i < logFiles.Length; i++)
                {
                    try
                    {
                        File.Delete(logFiles[i]);
                    }
                    catch
                    {
                        // Ignore deletion errors for individual files
                    }
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Warning: Could not cleanup old logs: {ex.Message}");
            }
        }
        
        public static string GetLogFilePath() => LogFilePath;
    }
}
