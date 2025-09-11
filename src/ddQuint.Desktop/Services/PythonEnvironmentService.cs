using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Reflection;
using System.Threading;
using System.Threading.Tasks;

namespace ddQuint.Desktop.Services
{
    public class PythonEnvironmentService
    {
        private static PythonEnvironmentService? _instance;
        private static readonly object _lock = new object();
        
        private string? _pythonExecutablePath;
        private string? _ddquintModulePath;
        private string? _pythonArgsPrefix; // e.g., "-3" when using 'py' launcher
        private bool _isInitialized;
        private bool _isInitializing;
        private Process? _currentProcess; // Track running process for cancellation
        
        public static PythonEnvironmentService Instance
        {
            get
            {
                if (_instance == null)
                {
                    lock (_lock)
                    {
                        _instance ??= new PythonEnvironmentService();
                    }
                }
                return _instance;
            }
        }
        
        private PythonEnvironmentService()
        {
        }
        
        public void Initialize()
        {
            if (_isInitialized)
            {
                LogMessage("Already initialized, skipping");
                return;
            }
            lock (_lock)
            {
                if (_isInitialized)
                {
                    LogMessage("Already initialized, skipping");
                    return;
                }
                if (_isInitializing)
                {
                    LogMessage("Initialization already in progress, skipping duplicate call");
                    return;
                }
                _isInitializing = true;
            }
                
            try
            {
                LogMessage("Starting Python environment initialization");
                
                // Find bundled Python environment
                var appDirectory = Path.GetDirectoryName(Assembly.GetExecutingAssembly().Location)!;
                var pythonDirectory = Path.Combine(appDirectory, "Python");
                
                LogMessage($"App directory: {appDirectory}");
                LogMessage($"Python directory: {pythonDirectory}");
                
                // Check for bundled ddquint module (prioritize bundled over system)
                var possibleDdquintPaths = new[]
                {
                    // Bundled Python embedded distribution locations (highest priority)
                    Path.Combine(pythonDirectory, "Lib", "site-packages", "ddquint"),           // Embedded Python site-packages
                    Path.Combine(pythonDirectory, "ddquint"),                                    // Direct in Python folder (fallback)
                    // Legacy venv paths (for backward compatibility)
                    Path.Combine(pythonDirectory, "venv", "Lib", "site-packages", "ddquint"),  // Old venv location
                    Path.Combine(pythonDirectory, "venv", "lib", "python*", "site-packages", "ddquint") // Unix-style paths
                };
                
                string? foundDdquintPath = null;
                foreach (var possiblePath in possibleDdquintPaths)
                {
                    if (possiblePath.Contains("*"))
                    {
                        // Handle wildcard paths
                        var parentDir = Path.GetDirectoryName(possiblePath)!;
                        if (Directory.Exists(parentDir))
                        {
                            var matchingDirs = Directory.GetDirectories(parentDir, "python*", SearchOption.TopDirectoryOnly);
                            foreach (var matchingDir in matchingDirs)
                            {
                                var testPath = Path.Combine(matchingDir, "site-packages", "ddquint");
                                if (Directory.Exists(testPath))
                                {
                                    foundDdquintPath = testPath;
                                    break;
                                }
                            }
                        }
                    }
                    else if (Directory.Exists(possiblePath))
                    {
                        foundDdquintPath = possiblePath;
                        break;
                    }
                }
                
                if (foundDdquintPath != null)
                {
                    // Set the module path to the parent of the ddquint folder for sys.path
                    _ddquintModulePath = Path.GetDirectoryName(foundDdquintPath)!;
                    LogMessage($"✅ Found ddquint module at: {foundDdquintPath}");
                    LogMessage($"Using module path: {_ddquintModulePath}");
                }
                else
                {
                    // Fallback to Python directory
                    _ddquintModulePath = pythonDirectory;
                    LogMessage($"⚠️ ddquint module not found in expected locations");
                    LogMessage("Available directories in Python folder:");
                    if (Directory.Exists(pythonDirectory))
                    {
                        foreach (var dir in Directory.GetDirectories(pythonDirectory, "*", SearchOption.AllDirectories))
                        {
                            if (Path.GetFileName(dir) == "ddquint")
                            {
                                LogMessage($"  - Found ddquint at: {dir}");
                            }
                        }
                    }
                    else
                    {
                        LogMessage($"Python directory does not exist: {pythonDirectory}");
                        throw new FileNotFoundException($"Python directory not found: {pythonDirectory}");
                    }
                }
                
                // Try to find Python executable
                try
                {
                    _pythonExecutablePath = FindPythonExecutable();
                    LogMessage($"Python executable: {_pythonExecutablePath}");
                }
                catch (Exception pyEx)
                {
                    LogMessage($"Failed to find Python executable: {pyEx.Message}");
                    LogMessage("Python functionality will be disabled");
                    _pythonExecutablePath = null;
                }
                
                LogMessage($"ddquint module path: {_ddquintModulePath}");
                
                // Test Python installation only if we found Python executable
                if (!string.IsNullOrWhiteSpace(_pythonExecutablePath))
                {
                    try
                    {
                        TestPythonEnvironment();
                        LogMessage("Python environment test passed");
                    }
                    catch (Exception testEx)
                    {
                        LogMessage($"Python environment test failed: {testEx.Message}");
                        LogMessage("Python functionality may be limited");
                        // Don't fail initialization just because the test failed
                    }
                }
                else
                {
                    LogMessage("Skipping Python environment test (no Python executable found)");
                }
                
                _isInitialized = true;
                LogMessage("Python environment initialized successfully");
            }
            catch (Exception ex)
            {
                LogMessage($"Failed to initialize Python environment: {ex.Message}");
                throw;
            }
            finally
            {
                _isInitializing = false;
            }
        }
        
        private string FindPythonExecutable()
        {
            // First, try bundled Python (highest priority)
            var appDirectory = Path.GetDirectoryName(Assembly.GetExecutingAssembly().Location)!;
            var bundledPythonExe = Path.Combine(appDirectory, "Python", "python.exe");
            var bundledPythonLauncher = Path.Combine(appDirectory, "Python", "python_launcher.bat");
            // Legacy venv location (for backward compatibility)
            var legacyVenvPythonExe = Path.Combine(appDirectory, "Python", "venv", "Scripts", "python.exe");
            
            var possiblePaths = new[]
            {
                // Bundled Python embedded distribution (highest priority)
                bundledPythonExe,
                bundledPythonLauncher,
                // Legacy venv location (for backward compatibility)
                legacyVenvPythonExe,
                
                // System Python (fallback)
                "python",
                "python3",
                "python.exe",
                "python3.exe",
                "py",
                "py.exe",
                Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Microsoft", "WindowsApps", "python.exe"),
                Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Microsoft", "WindowsApps", "python3.exe"),
                Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Programs", "Python", "Python312", "python.exe"),
                Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Programs", "Python", "Python311", "python.exe"),
                Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Programs", "Python", "Python310", "python.exe"),
                Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles), "Python312", "python.exe"),
                Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles), "Python311", "python.exe"),
                Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles), "Python310", "python.exe"),
                Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ProgramFilesX86), "Python312", "python.exe"),
                Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ProgramFilesX86), "Python311", "python.exe"),
                Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ProgramFilesX86), "Python310", "python.exe")
            };
            
            LogMessage($"=== SEARCHING FOR PYTHON EXECUTABLE ===");
            LogMessage($"Checking {possiblePaths.Length} possible Python paths:");
            for (int i = 0; i < possiblePaths.Length; i++)
            {
                LogMessage($"  {i + 1}. {possiblePaths[i]}");
            }
            
            foreach (var path in possiblePaths)
            {
                try
                {
                    LogMessage($"Testing Python path: {path}");
                    if (File.Exists(path))
                    {
                        LogMessage($"  ✓ File exists at: {path}");
                    }
                    else
                    {
                        LogMessage($"  ✗ File not found at: {path}");
                    }
                    var startInfo = BuildProcessStartInfo(path, "--version");
                    LogMessage($"  Attempting to start process: {startInfo.FileName} {startInfo.Arguments}");
                    LogMessage($"  Working directory: {startInfo.WorkingDirectory}");
                    LogMessage($"  UseShellExecute: {startInfo.UseShellExecute}");
                    
                    using var process = Process.Start(startInfo);
                    if (process != null)
                    {
                        LogMessage($"  Process started successfully. PID: {process.Id}");
                        process.WaitForExit(5000); // 5 second timeout
                        LogMessage($"  Process exited with code: {process.ExitCode}");
                        if (process.ExitCode == 0)
                        {
                            var output = process.StandardOutput.ReadToEnd();
                            var err = process.StandardError.ReadToEnd();
                            var verText = string.IsNullOrWhiteSpace(output) ? err : output;
                            if (!string.IsNullOrWhiteSpace(verText) && verText.Contains("Python", StringComparison.OrdinalIgnoreCase))
                            {
                                LogMessage($"Found Python: {verText.Trim()}");
                                var fileName = System.IO.Path.GetFileName(path);
                                // For 'py' launcher, prefer Python 3 if supported, otherwise no prefix
                                if (fileName.StartsWith("py", StringComparison.OrdinalIgnoreCase))
                                {
                                    try
                                    {
                                        var probe = BuildProcessStartInfo(path, "-3 --version");
                                        using var probeProc = Process.Start(probe);
                                        probeProc?.WaitForExit(3000);
                                        _pythonArgsPrefix = (probeProc != null && probeProc.ExitCode == 0) ? "-3" : string.Empty;
                                    }
                                    catch
                                    {
                                        _pythonArgsPrefix = string.Empty;
                                    }
                                }
                                else
                                {
                                    _pythonArgsPrefix = string.Empty;
                                }
                                return path;
                            }
                        }
                    }
                }
                catch (Exception ex)
                {
                    LogMessage($"✗ Exception testing '{path}': {ex.Message}");
                    LogMessage($"   Exception type: {ex.GetType().Name}");
                    if (ex.InnerException != null)
                    {
                        LogMessage($"   Inner exception: {ex.InnerException.Message}");
                    }
                    // Continue to next path
                }
            }
            
            throw new FileNotFoundException("Python executable not found. Please ensure Python 3.9+ is installed and accessible.");
        }

        private static ProcessStartInfo BuildProcessStartInfo(string path, string args)
        {
            var isBatch = path.EndsWith(".bat", StringComparison.OrdinalIgnoreCase) || path.EndsWith(".cmd", StringComparison.OrdinalIgnoreCase);
            if (isBatch)
            {
                return new ProcessStartInfo
                {
                    FileName = "cmd.exe",
                    Arguments = $"/c \"{path}\" {args}",
                    RedirectStandardOutput = true,
                    RedirectStandardError = true,
                    UseShellExecute = false,
                    CreateNoWindow = true,
                    StandardOutputEncoding = System.Text.Encoding.UTF8,
                    StandardErrorEncoding = System.Text.Encoding.UTF8
                };
            }
            else
            {
                return new ProcessStartInfo
                {
                    FileName = path,
                    Arguments = args,
                    RedirectStandardOutput = true,
                    RedirectStandardError = true,
                    UseShellExecute = false,
                    CreateNoWindow = true,
                    StandardOutputEncoding = System.Text.Encoding.UTF8,
                    StandardErrorEncoding = System.Text.Encoding.UTF8
                };
            }
        }
        
        private void TestPythonEnvironment()
        {
            var testScript = @"
import sys
import os
import warnings

# Suppress noisy SyntaxWarning from third-party packages during environment test
warnings.filterwarnings('ignore', category=SyntaxWarning, module=r'hdbscan\\..*')

# Add the Python directory to sys.path
python_dir = r'" + _ddquintModulePath!.Replace("\\", "\\\\") + @"'
sys.path.insert(0, python_dir)

print(f'Python version: {sys.version}')
print(f'Python executable: {sys.executable}')
print(f'Python path: {sys.path[:3]}')  # Show first 3 entries

try:
    import ddquint
    print('SUCCESS: ddquint module imported successfully')
    print(f'ddquint module location: {ddquint.__file__}')
except ImportError as e:
    print(f'ERROR: Failed to import ddquint module: {e}')
    print('Available modules in Python directory:')
    if os.path.exists(python_dir):
        for item in os.listdir(python_dir):
            if os.path.isdir(os.path.join(python_dir, item)) and not item.startswith('.'):
                print(f'  - {item}/')
    sys.exit(1)

# Test required packages
required_packages = ['numpy', 'pandas', 'matplotlib', 'sklearn', 'hdbscan', 'tqdm']
missing_packages = []
for package in required_packages:
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', SyntaxWarning)
            __import__(package)
        print(f'SUCCESS: {package} is available')
    except ImportError:
        print(f'WARNING: {package} is not available')
        missing_packages.append(package)

if missing_packages:
    print(f'Missing packages: {missing_packages}')
    print('Analysis may not work properly without these packages.')
";
            
            var result = ExecutePythonScript(testScript).GetAwaiter().GetResult();
            if (result.ExitCode != 0)
            {
                throw new Exception($"Python environment test failed: {result.Error}");
            }
            
            LogMessage("Python environment test results:");
            LogMessage(result.Output);
        }
        
        public async Task<PythonExecutionResult> ExecutePythonScript(string script, string? workingDirectory = null, bool persistScript = false)
        {
            return await ExecutePythonScript(script, workingDirectory, onStdout: null, onStderr: null, persistScript: persistScript);
        }

        public Task<PythonExecutionResult> ExecutePythonScript(
            string script,
            string? workingDirectory,
            Action<string>? onStdout,
            Action<string>? onStderr,
            bool persistScript = false)
        {
            // Run process on a background thread to avoid blocking UI
            return Task.Run(() => ExecutePythonScriptInternal(script, workingDirectory, onStdout, onStderr, persistScript, null));
        }
        
        public Task<PythonExecutionResult> ExecutePythonScript(
            string script,
            string? workingDirectory,
            Action<string>? onStdout,
            Action<string>? onStderr,
            bool persistScript,
            Dictionary<string, string>? environmentVariables)
        {
            // Run process on a background thread to avoid blocking UI
            return Task.Run(() => ExecutePythonScriptInternal(script, workingDirectory, onStdout, onStderr, persistScript, environmentVariables));
        }

        /// <summary>
        /// Cancel the currently running Python process if any
        /// </summary>
        public void CancelCurrentProcess()
        {
            try
            {
                if (_currentProcess != null && !_currentProcess.HasExited)
                {
                    LogMessage($"Cancelling running Python process (PID: {_currentProcess.Id})");
                    _currentProcess.Kill();
                    _currentProcess = null;
                    LogMessage("Python process cancelled successfully");
                }
                else
                {
                    LogMessage("No running Python process to cancel");
                }
            }
            catch (Exception ex)
            {
                LogMessage($"Error cancelling Python process: {ex.Message}");
            }
        }

        private PythonExecutionResult ExecutePythonScriptInternal(
            string script,
            string? workingDirectory,
            Action<string>? onStdout,
            Action<string>? onStderr,
            bool persistScript,
            Dictionary<string, string>? environmentVariables = null)
        {
            LogMessage("=== EXECUTING PYTHON SCRIPT ===");
            LogMessage($"Python executable path: {_pythonExecutablePath ?? "NULL"}");
            LogMessage($"ddQuint module path: {_ddquintModulePath ?? "NULL"}");
            LogMessage($"Working directory: {workingDirectory ?? "NULL"}");
            LogMessage($"Script length: {script?.Length ?? 0} characters");
            
            // Allow execution during Initialize() as long as paths are set
            if (string.IsNullOrWhiteSpace(_pythonExecutablePath))
            {
                LogMessage("ERROR: Python executable path is not set");
                throw new InvalidOperationException("Python executable path is not set");
            }
            if (string.IsNullOrWhiteSpace(_ddquintModulePath))
            {
                LogMessage("ERROR: Python module path is not set");
                throw new InvalidOperationException("Python module path is not set");
            }
                
            var tempScriptPath = Path.GetTempFileName() + ".py";
            LogMessage($"Creating temporary script file: {tempScriptPath}");
            File.WriteAllText(tempScriptPath, script);
            LogMessage("Temporary script file created successfully");
            
            try
            {
                var args = string.IsNullOrWhiteSpace(_pythonArgsPrefix)
                    ? $"\"{tempScriptPath}\""
                    : $"{_pythonArgsPrefix} \"{tempScriptPath}\"";
                    
                LogMessage($"Building process arguments: {args}");

                var startInfo = BuildProcessStartInfo(_pythonExecutablePath!, args);
                startInfo.WorkingDirectory = workingDirectory ?? Environment.CurrentDirectory;
                
                LogMessage($"Process working directory set to: {startInfo.WorkingDirectory}");
                
                // Inject PYTHONPATH while preserving other environment vars
                startInfo.Environment["PYTHONPATH"] = _ddquintModulePath!;
                startInfo.Environment["PYTHONUNBUFFERED"] = "1";  // Enable real-time output
                startInfo.Environment["PYTHONIOENCODING"] = "utf-8";  // Force UTF-8 encoding to prevent Unicode errors on Windows
                
                // Set matplotlib cache directory to AppData instead of user home to avoid C:\Users\username\.matplotlib  
                // On Windows, matplotlib uses HOME/.matplotlib, so we need to override the HOME variable
                var appDataPath = Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData);
                var ddQuintAppData = Path.Combine(appDataPath, "ddQuint");
                Directory.CreateDirectory(ddQuintAppData); // Ensure directory exists
                startInfo.Environment["HOME"] = ddQuintAppData;
                startInfo.Environment["MPLCONFIGDIR"] = Path.Combine(ddQuintAppData, "matplotlib");
                
                // Add custom environment variables
                if (environmentVariables != null)
                {
                    foreach (var kvp in environmentVariables)
                    {
                        startInfo.Environment[kvp.Key] = kvp.Value;
                        LogMessage($"  {kvp.Key} = {kvp.Value}");
                    }
                }
                
                LogMessage($"Environment variables set:");
                LogMessage($"  PYTHONPATH = {_ddquintModulePath}");
                LogMessage($"  PYTHONUNBUFFERED = 1");
                LogMessage($"  PYTHONIOENCODING = utf-8");
                LogMessage($"  HOME = {ddQuintAppData}");
                LogMessage($"  MPLCONFIGDIR = {Path.Combine(ddQuintAppData, "matplotlib")}");
                LogMessage($"About to start Python process: {_pythonExecutablePath} {args}");

                var process = Process.Start(startInfo);
                
                if (process == null)
                {
                    LogMessage("CRITICAL ERROR: Process.Start returned null!");
                    throw new InvalidOperationException("Failed to start Python process");
                }
                
                // Store reference for cancellation
                _currentProcess = process;
                LogMessage($"Python process started successfully. PID: {process.Id}");
                
                // Read output and error asynchronously to prevent deadlocks
                var outputBuilder = new System.Text.StringBuilder();
                var errorBuilder = new System.Text.StringBuilder();

                if (onStdout != null)
                {
                    process.OutputDataReceived += (s, e) =>
                    {
                        if (e.Data == null) return;
                        try { onStdout(e.Data); } catch { }
                        outputBuilder.AppendLine(e.Data);
                    };
                    process.BeginOutputReadLine();
                }
                else
                {
                    // Fallback: still capture output
                    process.OutputDataReceived += (s, e) =>
                    {
                        if (e.Data != null) outputBuilder.AppendLine(e.Data);
                    };
                    process.BeginOutputReadLine();
                }

                if (onStderr != null)
                {
                    process.ErrorDataReceived += (s, e) =>
                    {
                        if (e.Data == null) return;
                        try { onStderr(e.Data); } catch { }
                        errorBuilder.AppendLine(e.Data);
                    };
                    process.BeginErrorReadLine();
                }
                else
                {
                    process.ErrorDataReceived += (s, e) =>
                    {
                        if (e.Data != null) errorBuilder.AppendLine(e.Data);
                    };
                    process.BeginErrorReadLine();
                }
                
                // Wait for process to complete without timeout (per request)
                LogMessage("Waiting for Python process to complete (no timeout)...");
                process.WaitForExit();
                LogMessage("Process completed: True");
                try { LogMessage($"Process exit code: {process.ExitCode}"); } catch { }
                
                // Ensure async readers flush remaining data
                LogMessage("Reading process output and error streams...");
                try { if (!process.HasExited) process.WaitForExit(); } catch { }
                try { process.CancelOutputRead(); } catch { }
                try { process.CancelErrorRead(); } catch { }
                // Small delay to allow event handlers to finish appending
                try { Thread.Sleep(50); } catch { }
                var output = outputBuilder.ToString();
                var error = errorBuilder.ToString();
                
                LogMessage($"Process output length: {output.Length} characters");
                LogMessage($"Process error length: {error.Length} characters");

                // Removed persisting stdout/stderr files per request
                
                if (!string.IsNullOrEmpty(output))
                {
                    LogMessage("=== PYTHON STDOUT ===");
                    LogMessage(output.Length > 2000 ? output.Substring(0, 2000) + "\n... (truncated)" : output);
                    LogMessage("=== END PYTHON STDOUT ===");
                    try { DebugLogService.ProcessPythonOutput(output); } catch { }
                }
                
                if (!string.IsNullOrEmpty(error))
                {
                    LogMessage("=== PYTHON STDERR ===");
                    LogMessage(error.Length > 2000 ? error.Substring(0, 2000) + "\n... (truncated)" : error);
                    LogMessage("=== END PYTHON STDERR ===");
                }
                
                LogMessage($"Python execution complete. Returning result with exit code: {process.ExitCode}");
                
                var result = new PythonExecutionResult
                {
                    ExitCode = process.ExitCode,
                    Output = output ?? string.Empty,
                    Error = error ?? string.Empty
                };
                
                // Clean up process reference
                try { process.Dispose(); } catch { }
                _currentProcess = null;
                
                return result;
            }
            catch (Exception ex)
            {
                LogMessage($"CRITICAL ERROR during Python execution: {ex.Message}");
                LogMessage($"Exception type: {ex.GetType().Name}");
                
                // Clean up process reference in case of exception
                try { _currentProcess?.Dispose(); } catch { }
                _currentProcess = null;
                LogMessage($"Stack trace: {ex.StackTrace}");
                
                return new PythonExecutionResult
                {
                    ExitCode = -999,
                    Output = "",
                    Error = $"Failed to execute Python script: {ex.Message}"
                };
            }
            finally
            {
                try
                {
                    File.Delete(tempScriptPath);
                }
                catch
                {
                    // Ignore cleanup errors
                }
            }
        }
        
        public string PythonExecutablePath => _pythonExecutablePath ?? throw new InvalidOperationException("Python environment not initialized");
        public string DdquintModulePath => _ddquintModulePath ?? throw new InvalidOperationException("Python environment not initialized");
        public bool IsInitialized => _isInitialized;
        
        private static void LogMessage(string message)
        {
            // Unified debug log (AppData/ddQuint/logs/debug.log)
            try { DebugLogService.LogMessage(message); } catch { }

            // Console echo for live visibility
            var timestamp = DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss.fff");
            var logEntry = $"[{timestamp}] PYTHON: {message}";
            Console.WriteLine(logEntry);

            // Keep the original temp file for quick tracing
            try
            {
                var logPath = Path.Combine(Path.GetTempPath(), "ddquint_startup.log");
                File.AppendAllText(logPath, logEntry + Environment.NewLine);
            }
            catch { }
        }
    }
    
    public class PythonExecutionResult
    {
        public int ExitCode { get; set; }
        public string Output { get; set; } = "";
        public string Error { get; set; } = "";
    }
}
