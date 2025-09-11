using System;
using System.IO;
using System.Runtime.InteropServices;
using System.Windows;
using ddQuint.Desktop.Services;

namespace ddQuint.Desktop
{
    public class Program
    {
        [DllImport("kernel32.dll", SetLastError = true)]
        [return: MarshalAs(UnmanagedType.Bool)]
        static extern bool AllocConsole();

        [STAThread]
        public static void Main(string[] args)
        {
            try
            {
                // Allocate a console for this GUI application for debugging
                #if DEBUG
                AllocConsole();
                #endif
                
                // Initialize unified debug logging (writes to %APPDATA%/ddQuint/logs/debug.log)
                DebugLogService.Initialize();

                // Set up file logging
                SetupFileLogging();
                
                LogMessage("=== ddQuint Application Starting ===");
                LogMessage($"Arguments: {string.Join(" ", args)}");
                LogMessage($"Working Directory: {Environment.CurrentDirectory}");
                LogMessage($"Executable Location: {System.Reflection.Assembly.GetExecutingAssembly().Location}");

                LogMessage("Creating App instance...");
                var app = new App();
                
                LogMessage("Initializing components...");
                app.InitializeComponent();
                
                LogMessage("Starting application run loop...");
                var result = app.Run();
                
                LogMessage($"Application exited with code: {result}");
            }
            catch (Exception ex)
            {
                var errorMsg = $"FATAL ERROR in Main: {ex.Message}\nStack: {ex.StackTrace}";
                LogMessage(errorMsg);
                
                try
                {
                    MessageBox.Show(errorMsg, "Application Startup Error", MessageBoxButton.OK, MessageBoxImage.Error);
                }
                catch
                {
                    // If even MessageBox fails, write to a file
                    try
                    {
                        File.WriteAllText(Path.Combine(Path.GetTempPath(), "ddquint_fatal_error.txt"), errorMsg);
                    }
                    catch { }
                }
                Environment.Exit(1);
            }
        }
        
        private static void SetupFileLogging()
        {
            try
            {
                var logPath = Path.Combine(Path.GetTempPath(), "ddquint_startup.log");
                LogMessage($"Log file: {logPath}");
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Failed to setup file logging: {ex.Message}");
            }
        }
        
        private static void LogMessage(string message)
        {
            // Always mirror to unified debug log
            DebugLogService.LogMessage(message);

            // Also echo to console for immediate visibility
            var timestamp = DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss.fff");
            Console.WriteLine($"[{timestamp}] {message}");

            // Keep the original temp file for quick startup tracing
            try
            {
                var logPath = Path.Combine(Path.GetTempPath(), "ddquint_startup.log");
                File.AppendAllText(logPath, $"[{timestamp}] {message}" + Environment.NewLine);
            }
            catch { }
        }
    }
}
