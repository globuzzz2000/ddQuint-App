import Cocoa

class SimpleMainWindowController: NSWindowController {
    
    private var folderPathField: NSTextField!
    private var browseButton: NSButton!
    private var fileCountLabel: NSTextField!
    private var startButton: NSButton!
    private var progressIndicator: NSProgressIndicator!
    private var progressLabel: NSTextField!
    
    private var selectedFolderURL: URL?
    private var csvFiles: [URL] = []
    
    convenience init() {
        let window = NSWindow(
            contentRect: NSRect(x: 0, y: 0, width: 600, height: 400),
            styleMask: [.titled, .closable, .miniaturizable, .resizable],
            backing: .buffered,
            defer: false
        )
        
        self.init(window: window)
        setupWindow()
    }
    
    private func setupWindow() {
        window?.title = "ddQuint - Digital Droplet PCR Analysis"
        window?.center()
        
        guard let contentView = window?.contentView else { return }
        
        // Create UI elements
        setupUI(in: contentView)
        setupConstraints(in: contentView)
        updateUIState()
    }
    
    private func setupUI(in contentView: NSView) {
        // Folder path field
        folderPathField = NSTextField()
        folderPathField.placeholderString = "Select a folder containing CSV files..."
        folderPathField.isEditable = false
        folderPathField.translatesAutoresizingMaskIntoConstraints = false
        contentView.addSubview(folderPathField)
        
        // Browse button
        browseButton = NSButton(title: "Browse...", target: self, action: #selector(browseClicked))
        browseButton.bezelStyle = .rounded
        browseButton.translatesAutoresizingMaskIntoConstraints = false
        contentView.addSubview(browseButton)
        
        // File count label
        fileCountLabel = NSTextField(labelWithString: "")
        fileCountLabel.textColor = .secondaryLabelColor
        fileCountLabel.translatesAutoresizingMaskIntoConstraints = false
        contentView.addSubview(fileCountLabel)
        
        // Start button
        startButton = NSButton(title: "Start Analysis", target: self, action: #selector(startClicked))
        startButton.bezelStyle = .rounded
        startButton.isEnabled = false
        startButton.translatesAutoresizingMaskIntoConstraints = false
        contentView.addSubview(startButton)
        
        // Progress indicator
        progressIndicator = NSProgressIndicator()
        progressIndicator.style = .bar
        progressIndicator.isIndeterminate = true
        progressIndicator.isHidden = true
        progressIndicator.translatesAutoresizingMaskIntoConstraints = false
        contentView.addSubview(progressIndicator)
        
        // Progress label
        progressLabel = NSTextField(labelWithString: "")
        progressLabel.textColor = .secondaryLabelColor
        progressLabel.isHidden = true
        progressLabel.translatesAutoresizingMaskIntoConstraints = false
        contentView.addSubview(progressLabel)
    }
    
    private func setupConstraints(in contentView: NSView) {
        NSLayoutConstraint.activate([
            // Folder path field - fixed width to prevent window resizing
            folderPathField.topAnchor.constraint(equalTo: contentView.topAnchor, constant: 50),
            folderPathField.leadingAnchor.constraint(equalTo: contentView.leadingAnchor, constant: 30),
            folderPathField.widthAnchor.constraint(equalToConstant: 400),
            
            // Browse button
            browseButton.topAnchor.constraint(equalTo: folderPathField.topAnchor),
            browseButton.trailingAnchor.constraint(equalTo: contentView.trailingAnchor, constant: -30),
            browseButton.widthAnchor.constraint(equalToConstant: 100),
            
            // File count label
            fileCountLabel.topAnchor.constraint(equalTo: folderPathField.bottomAnchor, constant: 10),
            fileCountLabel.leadingAnchor.constraint(equalTo: contentView.leadingAnchor, constant: 30),
            fileCountLabel.trailingAnchor.constraint(equalTo: contentView.trailingAnchor, constant: -30),
            
            // Start button
            startButton.topAnchor.constraint(equalTo: fileCountLabel.bottomAnchor, constant: 30),
            startButton.centerXAnchor.constraint(equalTo: contentView.centerXAnchor),
            startButton.widthAnchor.constraint(equalToConstant: 120),
            
            // Progress indicator
            progressIndicator.topAnchor.constraint(equalTo: startButton.bottomAnchor, constant: 30),
            progressIndicator.leadingAnchor.constraint(equalTo: contentView.leadingAnchor, constant: 30),
            progressIndicator.trailingAnchor.constraint(equalTo: contentView.trailingAnchor, constant: -30),
            
            // Progress label
            progressLabel.topAnchor.constraint(equalTo: progressIndicator.bottomAnchor, constant: 10),
            progressLabel.leadingAnchor.constraint(equalTo: contentView.leadingAnchor, constant: 30),
            progressLabel.trailingAnchor.constraint(equalTo: contentView.trailingAnchor, constant: -30),
        ])
    }
    
    @objc private func browseClicked() {
        print("Browse button clicked!") // Debug output
        
        let openPanel = NSOpenPanel()
        openPanel.canChooseFiles = false
        openPanel.canChooseDirectories = true
        openPanel.allowsMultipleSelection = false
        openPanel.prompt = "Select Folder"
        openPanel.message = "Choose a folder containing ddPCR CSV files"
        
        // Try synchronous version first for debugging
        let response = openPanel.runModal()
        
        if response == .OK, let url = openPanel.url {
            print("Selected folder: \(url.path)")
            folderSelected(url: url)
        } else {
            print("Dialog cancelled or no selection")
        }
    }
    
    private func folderSelected(url: URL) {
        print("folderSelected called with: \(url.path)")
        selectedFolderURL = url
        folderPathField.stringValue = url.path
        
        // Find CSV files
        csvFiles = findCSVFiles(in: url)
        print("Found \(csvFiles.count) CSV files")
        
        if csvFiles.isEmpty {
            fileCountLabel.stringValue = "⚠️ No CSV files found"
            fileCountLabel.textColor = .systemOrange
            startButton.isEnabled = false
        } else {
            fileCountLabel.stringValue = "✅ Found \(csvFiles.count) CSV files"
            fileCountLabel.textColor = .systemGreen
            startButton.isEnabled = true
        }
    }
    
    private func findCSVFiles(in directory: URL) -> [URL] {
        do {
            let contents = try FileManager.default.contentsOfDirectory(
                at: directory,
                includingPropertiesForKeys: nil,
                options: .skipsHiddenFiles
            )
            return contents.filter { $0.pathExtension.lowercased() == "csv" }
        } catch {
            return []
        }
    }
    
    @objc private func startClicked() {
        guard let folderURL = selectedFolderURL else { return }
        
        updateUIState(analyzing: true)
        runAnalysis(folderURL: folderURL)
    }
    
    private func runAnalysis(folderURL: URL) {
        progressLabel.stringValue = "Running ddQuint analysis..."
        
        // Find Python and ddQuint
        guard let pythonPath = findPython(),
              let ddquintPath = findDDQuint() else {
            let error = "Python: \(findPython() ?? "not found"), ddQuint: \(findDDQuint() ?? "not found")"
            showError("Python or ddQuint not found.\n\(error)")
            updateUIState(analyzing: false)
            return
        }
        
        print("Using Python: \(pythonPath)")
        print("Using ddQuint: \(ddquintPath)")
        print("Processing folder: \(folderURL.path)")
        
        // Run analysis
        DispatchQueue.global().async { [weak self] in
            let process = Process()
            process.executableURL = URL(fileURLWithPath: pythonPath)
            // Escape the path to handle quotes and special characters
            let escapedFolderPath = folderURL.path.replacingOccurrences(of: "'", with: "\\'")
            let escapedDDQuintPath = ddquintPath.replacingOccurrences(of: "'", with: "\\'")
            
            process.arguments = [
                "-c",
                """
                import sys
                import traceback
                
                try:
                    sys.path.insert(0, '\(escapedDDQuintPath)')
                    from ddquint.core import process_directory
                    from ddquint.utils import get_sample_names
                    
                    print('Starting ddQuint analysis...')
                    
                    # Run analysis
                    sample_names = get_sample_names('\(escapedFolderPath)')
                    print(f'Found {len(sample_names)} sample names')
                    
                    results = process_directory('\(escapedFolderPath)', '\(escapedFolderPath)', sample_names, verbose=True)
                    print(f'Analysis complete! Processed {len(results)} files.')
                    
                except Exception as e:
                    print(f'PYTHON ERROR: {e}')
                    traceback.print_exc()
                    sys.exit(1)
                """
            ]
            
            // Capture output for debugging
            let outputPipe = Pipe()
            let errorPipe = Pipe()
            process.standardOutput = outputPipe
            process.standardError = errorPipe
            
            do {
                try process.run()
                process.waitUntilExit()
                
                // Read output
                let outputData = outputPipe.fileHandleForReading.readDataToEndOfFile()
                let errorData = errorPipe.fileHandleForReading.readDataToEndOfFile()
                
                let output = String(data: outputData, encoding: .utf8) ?? ""
                let errorOutput = String(data: errorData, encoding: .utf8) ?? ""
                
                print("Python stdout: \(output)")
                print("Python stderr: \(errorOutput)")
                print("Exit code: \(process.terminationStatus)")
                
                DispatchQueue.main.async {
                    self?.analysisComplete(success: process.terminationStatus == 0, output: output, error: errorOutput)
                }
            } catch {
                print("Process launch error: \(error)")
                DispatchQueue.main.async {
                    self?.showError("Failed to run analysis: \(error)")
                    self?.updateUIState(analyzing: false)
                }
            }
        }
    }
    
    private func analysisComplete(success: Bool, output: String = "", error: String = "") {
        if success {
            progressLabel.stringValue = "✅ Analysis complete! Check the output folder for results."
            
            // Show results folder in Finder
            if let folderURL = selectedFolderURL {
                NSWorkspace.shared.activateFileViewerSelecting([folderURL])
            }
        } else {
            progressLabel.stringValue = "❌ Analysis failed. Check console for details."
            
            // Show detailed error in an alert
            if !error.isEmpty || !output.isEmpty {
                let alert = NSAlert()
                alert.messageText = "Analysis Failed"
                alert.informativeText = "Error: \(error)\n\nOutput: \(output)"
                alert.alertStyle = .warning
                alert.runModal()
            }
        }
        
        DispatchQueue.main.asyncAfter(deadline: .now() + 3) { [weak self] in
            self?.updateUIState(analyzing: false)
        }
    }
    
    private func updateUIState(analyzing: Bool = false) {
        if analyzing {
            progressIndicator.isHidden = false
            progressLabel.isHidden = false
            progressIndicator.startAnimation(nil)
            startButton.isEnabled = false
            browseButton.isEnabled = false
        } else {
            progressIndicator.isHidden = true
            progressLabel.isHidden = true
            progressIndicator.stopAnimation(nil)
            startButton.isEnabled = !csvFiles.isEmpty
            browseButton.isEnabled = true
        }
    }
    
    private func findPython() -> String? {
        let paths = [
            "/opt/miniconda3/envs/ddpcr/bin/python",
            "/usr/local/bin/python3",
            "/usr/bin/python3"
        ]
        
        for path in paths {
            if FileManager.default.isExecutableFile(atPath: path) {
                return path
            }
        }
        return nil
    }
    
    private func findDDQuint() -> String? {
        let paths = [
            "/Users/jakob/Applications/Git/ddQuint",
            NSHomeDirectory() + "/ddQuint"
        ]
        
        for path in paths {
            let modulePath = path + "/ddquint"
            if FileManager.default.fileExists(atPath: modulePath) {
                return path
            }
        }
        return nil
    }
    
    private func showError(_ message: String) {
        let alert = NSAlert()
        alert.messageText = "Error"
        alert.informativeText = message
        alert.alertStyle = .warning
        alert.runModal()
    }
}