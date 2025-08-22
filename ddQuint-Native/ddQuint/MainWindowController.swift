import Cocoa

class MainWindowController: NSWindowController {
    
    @IBOutlet weak var folderPathField: NSTextField!
    @IBOutlet weak var browseButton: NSButton!
    @IBOutlet weak var fileCountLabel: NSTextField!
    @IBOutlet weak var startButton: NSButton!
    @IBOutlet weak var progressIndicator: NSProgressIndicator!
    @IBOutlet weak var progressLabel: NSTextField!
    @IBOutlet weak var exportButton: NSButton!
    @IBOutlet weak var resultsTableView: NSTableView!
    
    private var selectedFolderURL: URL?
    private var analysisProcess: Process?
    private var csvFiles: [URL] = []
    private var analysisResults: [[String: Any]] = []
    
    override init(window: NSWindow?) {
        super.init(window: window)
        setupWindow()
    }
    
    required init?(coder: NSCoder) {
        super.init(coder: coder)
        setupWindow()
    }
    
    convenience init() {
        // Create window programmatically
        let window = NSWindow(
            contentRect: NSRect(x: 0, y: 0, width: 800, height: 600),
            styleMask: [.titled, .closable, .miniaturizable, .resizable],
            backing: .buffered,
            defer: false
        )
        
        self.init(window: window)
    }
    
    private func setupWindow() {
        window?.title = "ddQuint - Digital Droplet PCR Analysis"
        window?.center()
        
        // Create the main content view
        setupContentView()
        
        // Set initial state
        updateUIState(stage: .initial)
    }
    
    private func setupContentView() {
        guard let window = window else { return }
        
        let contentView = NSView(frame: window.contentRect(forFrameRect: window.frame))
        window.contentView = contentView
        
        // Create UI elements programmatically
        setupFolderSelectionArea(in: contentView)
        setupProgressArea(in: contentView)
        setupResultsArea(in: contentView)
        setupExportArea(in: contentView)
        
        // Setup constraints
        setupConstraints(in: contentView)
    }
    
    private func setupFolderSelectionArea(in contentView: NSView) {
        // Folder selection label
        let folderLabel = NSTextField(labelWithString: "Select folder with ddPCR CSV files:")
        folderLabel.font = NSFont.systemFont(ofSize: 14, weight: .medium)
        folderLabel.translatesAutoresizingMaskIntoConstraints = false
        contentView.addSubview(folderLabel)
        
        // Folder path field
        folderPathField = NSTextField()
        folderPathField.placeholderString = "Choose a folder containing CSV files..."
        folderPathField.isEditable = false
        folderPathField.translatesAutoresizingMaskIntoConstraints = false
        contentView.addSubview(folderPathField)
        
        // Browse button
        browseButton = NSButton(title: "Browse...", target: self, action: #selector(browseButtonClicked))
        browseButton.bezelStyle = .rounded
        browseButton.translatesAutoresizingMaskIntoConstraints = false
        contentView.addSubview(browseButton)
        
        // File count label
        fileCountLabel = NSTextField(labelWithString: "")
        fileCountLabel.font = NSFont.systemFont(ofSize: 12)
        fileCountLabel.textColor = .secondaryLabelColor
        fileCountLabel.translatesAutoresizingMaskIntoConstraints = false
        contentView.addSubview(fileCountLabel)
        
        // Start button
        startButton = NSButton(title: "Start Analysis", target: self, action: #selector(startAnalysis))
        startButton.bezelStyle = .rounded
        startButton.keyEquivalent = "\\r" // Return key
        startButton.isEnabled = false
        startButton.translatesAutoresizingMaskIntoConstraints = false
        contentView.addSubview(startButton)
        
        // Store references for constraints
        contentView.setValue(folderLabel, forKey: "folderLabel")
        contentView.setValue(folderPathField, forKey: "folderPathField")
        contentView.setValue(browseButton, forKey: "browseButton")
        contentView.setValue(fileCountLabel, forKey: "fileCountLabel")
        contentView.setValue(startButton, forKey: "startButton")
    }
    
    private func setupProgressArea(in contentView: NSView) {
        // Progress indicator
        progressIndicator = NSProgressIndicator()
        progressIndicator.style = .bar
        progressIndicator.isIndeterminate = false
        progressIndicator.minValue = 0
        progressIndicator.maxValue = 100
        progressIndicator.isHidden = true
        progressIndicator.translatesAutoresizingMaskIntoConstraints = false
        contentView.addSubview(progressIndicator)
        
        // Progress label
        progressLabel = NSTextField(labelWithString: "")
        progressLabel.font = NSFont.systemFont(ofSize: 12)
        progressLabel.textColor = .secondaryLabelColor
        progressLabel.isHidden = true
        progressLabel.translatesAutoresizingMaskIntoConstraints = false
        contentView.addSubview(progressLabel)
        
        contentView.setValue(progressIndicator, forKey: "progressIndicator")
        contentView.setValue(progressLabel, forKey: "progressLabel")
    }
    
    private func setupResultsArea(in contentView: NSView) {
        // Results table view with scroll view
        let scrollView = NSScrollView()
        scrollView.hasVerticalScroller = true
        scrollView.hasHorizontalScroller = true
        scrollView.autohidesScrollers = false
        scrollView.borderType = .bezelBorder
        scrollView.translatesAutoresizingMaskIntoConstraints = false
        
        resultsTableView = NSTableView()
        resultsTableView.usesAlternatingRowBackgroundColors = true
        resultsTableView.gridStyleMask = [.solidHorizontalGridLineMask]
        
        // Create table columns
        let wellColumn = NSTableColumn(identifier: NSUserInterfaceItemIdentifier("well"))
        wellColumn.title = "Well"
        wellColumn.width = 60
        resultsTableView.addTableColumn(wellColumn)
        
        let sampleColumn = NSTableColumn(identifier: NSUserInterfaceItemIdentifier("sample"))
        sampleColumn.title = "Sample"
        sampleColumn.width = 150
        resultsTableView.addTableColumn(sampleColumn)
        
        let statusColumn = NSTableColumn(identifier: NSUserInterfaceItemIdentifier("status"))
        statusColumn.title = "Status"
        statusColumn.width = 100
        resultsTableView.addTableColumn(statusColumn)
        
        let dropletsColumn = NSTableColumn(identifier: NSUserInterfaceItemIdentifier("droplets"))
        dropletsColumn.title = "Droplets"
        dropletsColumn.width = 80
        resultsTableView.addTableColumn(dropletsColumn)
        
        scrollView.documentView = resultsTableView
        resultsTableView.dataSource = self
        resultsTableView.delegate = self
        
        scrollView.isHidden = true
        contentView.addSubview(scrollView)
        contentView.setValue(scrollView, forKey: "resultsScrollView")
    }
    
    private func setupExportArea(in contentView: NSView) {
        exportButton = NSButton(title: "Export Results", target: self, action: #selector(exportResults))
        exportButton.bezelStyle = .rounded
        exportButton.isEnabled = false
        exportButton.isHidden = true
        exportButton.translatesAutoresizingMaskIntoConstraints = false
        contentView.addSubview(exportButton)
        
        contentView.setValue(exportButton, forKey: "exportButton")
    }
    
    private func setupConstraints(in contentView: NSView) {
        let views = [
            "folderLabel": contentView.value(forKey: "folderLabel"),
            "folderPathField": contentView.value(forKey: "folderPathField"),
            "browseButton": contentView.value(forKey: "browseButton"),
            "fileCountLabel": contentView.value(forKey: "fileCountLabel"),
            "startButton": contentView.value(forKey: "startButton"),
            "progressIndicator": contentView.value(forKey: "progressIndicator"),
            "progressLabel": contentView.value(forKey: "progressLabel"),
            "resultsScrollView": contentView.value(forKey: "resultsScrollView"),
            "exportButton": contentView.value(forKey: "exportButton")
        ] as [String: Any]
        
        // Vertical layout
        let vConstraints = NSLayoutConstraint.constraints(
            withVisualFormat: "V:|-30-[folderLabel]-10-[folderPathField]-5-[fileCountLabel]-20-[startButton]-20-[progressIndicator]-5-[progressLabel]-20-[resultsScrollView]-20-[exportButton]-20-|",
            options: [],
            metrics: nil,
            views: views
        )
        contentView.addConstraints(vConstraints)
        
        // Horizontal layout
        let folderFieldConstraints = NSLayoutConstraint.constraints(
            withVisualFormat: "H:|-30-[folderLabel]-30-|",
            options: [],
            metrics: nil,
            views: views
        )
        contentView.addConstraints(folderFieldConstraints)
        
        let pathFieldConstraints = NSLayoutConstraint.constraints(
            withVisualFormat: "H:|-30-[folderPathField]-10-[browseButton(80)]-30-|",
            options: [],
            metrics: nil,
            views: views
        )
        contentView.addConstraints(pathFieldConstraints)
        
        let countLabelConstraints = NSLayoutConstraint.constraints(
            withVisualFormat: "H:|-30-[fileCountLabel]-30-|",
            options: [],
            metrics: nil,
            views: views
        )
        contentView.addConstraints(countLabelConstraints)
        
        // Center start button
        startButton.centerXAnchor.constraint(equalTo: contentView.centerXAnchor).isActive = true
        startButton.widthAnchor.constraint(equalToConstant: 120).isActive = true
        
        // Progress elements
        let progressConstraints = NSLayoutConstraint.constraints(
            withVisualFormat: "H:|-30-[progressIndicator]-30-|",
            options: [],
            metrics: nil,
            views: views
        )
        contentView.addConstraints(progressConstraints)
        
        let progressLabelConstraints = NSLayoutConstraint.constraints(
            withVisualFormat: "H:|-30-[progressLabel]-30-|",
            options: [],
            metrics: nil,
            views: views
        )
        contentView.addConstraints(progressLabelConstraints)
        
        // Results table
        let resultsConstraints = NSLayoutConstraint.constraints(
            withVisualFormat: "H:|-30-[resultsScrollView]-30-|",
            options: [],
            metrics: nil,
            views: views
        )
        contentView.addConstraints(resultsConstraints)
        
        // Export button
        exportButton.centerXAnchor.constraint(equalTo: contentView.centerXAnchor).isActive = true
        exportButton.widthAnchor.constraint(equalToConstant: 120).isActive = true
    }
    
    // MARK: - Actions
    
    @objc private func browseButtonClicked() {
        let openPanel = NSOpenPanel()
        openPanel.canChooseFiles = false
        openPanel.canChooseDirectories = true
        openPanel.allowsMultipleSelection = false
        openPanel.prompt = "Select Folder"
        openPanel.message = "Choose a folder containing ddPCR CSV files"
        
        openPanel.begin { [weak self] response in
            if response == .OK, let url = openPanel.url {
                self?.selectedFolderURL = url
                self?.updateFolderSelection(url: url)
            }
        }
    }
    
    private func updateFolderSelection(url: URL) {
        folderPathField.stringValue = url.path
        
        // Count CSV files
        csvFiles = findCSVFiles(in: url)
        
        if csvFiles.isEmpty {
            fileCountLabel.stringValue = "⚠️ No CSV files found in this folder"
            fileCountLabel.textColor = .systemOrange
            startButton.isEnabled = false
        } else {
            fileCountLabel.stringValue = "✅ Found \\(csvFiles.count) CSV files"
            fileCountLabel.textColor = .systemGreen
            startButton.isEnabled = true
        }
    }
    
    private func findCSVFiles(in directory: URL) -> [URL] {
        do {
            let contents = try FileManager.default.contentsOfDirectory(
                at: directory,
                includingPropertiesForKeys: [.isRegularFileKey],
                options: .skipsHiddenFiles
            )
            
            return contents.filter { url in
                url.pathExtension.lowercased() == "csv"
            }
        } catch {
            print("Error reading directory: \\(error)")
            return []
        }
    }
    
    @objc private func startAnalysis() {
        guard let folderURL = selectedFolderURL else { return }
        
        updateUIState(stage: .analyzing)
        runDDQuintAnalysis(on: folderURL)
    }
    
    @objc private func exportResults() {
        let savePanel = NSSavePanel()
        savePanel.allowedContentTypes = [.init(filenameExtension: "xlsx")!]
        savePanel.nameFieldStringValue = "ddQuint_Results.xlsx"
        savePanel.prompt = "Export"
        savePanel.message = "Save analysis results as Excel file"
        
        savePanel.begin { [weak self] response in
            if response == .OK, let url = savePanel.url {
                self?.exportToExcel(url: url)
            }
        }
    }
    
    // MARK: - Analysis
    
    private func runDDQuintAnalysis(on folderURL: URL) {
        guard let pythonPath = findPythonPath(),
              let ddquintPath = findDDQuintPath() else {
            showError("Python or ddQuint not found. Please ensure ddQuint is properly installed.")
            updateUIState(stage: .initial)
            return
        }
        
        progressLabel.stringValue = "Starting analysis..."
        progressIndicator.doubleValue = 10
        
        // Create analysis process
        analysisProcess = Process()
        analysisProcess?.executableURL = URL(fileURLWithPath: pythonPath)
        analysisProcess?.arguments = [
            "-c",
            """
            import sys
            sys.path.insert(0, '\\(ddquintPath)')
            from ddquint.core import process_directory
            from ddquint.utils import get_sample_names
            import json
            
            # Get sample names
            sample_names = get_sample_names('\\(folderURL.path)')
            
            # Process directory
            results = process_directory('\\(folderURL.path)', '\\(folderURL.path)', sample_names, verbose=True)
            
            # Output results as JSON
            output = []
            for result in results:
                output.append({
                    'well': result.get('well', ''),
                    'sample_name': result.get('sample_name', ''),
                    'droplet_count': len(result.get('dataframe', [])) if result.get('dataframe') is not None else 0,
                    'status': 'Completed'
                })
            
            print('RESULTS_JSON:' + json.dumps(output))
            """
        ]
        
        let pipe = Pipe()
        analysisProcess?.standardOutput = pipe
        analysisProcess?.standardError = pipe
        
        // Monitor output
        pipe.fileHandleForReading.readabilityHandler = { [weak self] handle in
            let data = handle.availableData
            if !data.isEmpty {
                let output = String(data: data, encoding: .utf8) ?? ""
                DispatchQueue.main.async {
                    self?.processAnalysisOutput(output)
                }
            }
        }
        
        analysisProcess?.terminationHandler = { [weak self] process in
            DispatchQueue.main.async {
                self?.analysisDidComplete()
            }
        }
        
        do {
            try analysisProcess?.run()
        } catch {
            showError("Failed to start analysis: \\(error)")
            updateUIState(stage: .initial)
        }
    }
    
    private func processAnalysisOutput(_ output: String) {
        // Update progress based on output
        if output.contains("Processing files:") {
            // Try to extract percentage from tqdm output
            let lines = output.components(separatedBy: .newlines)
            for line in lines {
                if line.contains("%") {
                    progressLabel.stringValue = "Processing CSV files..."
                    // Extract percentage if possible
                    if let percentMatch = line.range(of: "\\d+%", options: .regularExpression) {
                        let percentStr = String(line[percentMatch]).dropLast()
                        if let percent = Double(percentStr) {
                            progressIndicator.doubleValue = percent
                        }
                    }
                }
            }
        } else if output.contains("RESULTS_JSON:") {
            // Parse results JSON
            let jsonStart = output.range(of: "RESULTS_JSON:")?.upperBound
            if let jsonStart = jsonStart {
                let jsonString = String(output[jsonStart...])
                parseAnalysisResults(jsonString)
            }
        }
    }
    
    private func parseAnalysisResults(_ jsonString: String) {
        do {
            let data = jsonString.data(using: .utf8) ?? Data()
            if let results = try JSONSerialization.jsonObject(with: data, options: []) as? [[String: Any]] {
                analysisResults = results
            }
        } catch {
            print("Error parsing results JSON: \\(error)")
        }
    }
    
    private func analysisDidComplete() {
        progressIndicator.doubleValue = 100
        progressLabel.stringValue = "Analysis complete!"
        
        DispatchQueue.main.asyncAfter(deadline: .now() + 1.0) { [weak self] in
            self?.updateUIState(stage: .results)
            self?.resultsTableView.reloadData()
        }
    }
    
    // MARK: - Helper Methods
    
    private func findPythonPath() -> String? {
        // Try to find Python executable
        let possiblePaths = [
            "/opt/miniconda3/envs/ddpcr/bin/python",
            "/usr/local/bin/python3",
            "/usr/bin/python3",
            "/opt/homebrew/bin/python3"
        ]
        
        for path in possiblePaths {
            if FileManager.default.isExecutableFile(atPath: path) {
                return path
            }
        }
        
        // Try using 'which python3'
        let task = Process()
        task.executableURL = URL(fileURLWithPath: "/usr/bin/which")
        task.arguments = ["python3"]
        
        let pipe = Pipe()
        task.standardOutput = pipe
        
        do {
            try task.run()
            task.waitUntilExit()
            
            let data = pipe.fileHandleForReading.readDataToEndOfFile()
            let path = String(data: data, encoding: .utf8)?.trimmingCharacters(in: .whitespacesAndNewlines)
            return path?.isEmpty == false ? path : nil
        } catch {
            return nil
        }
    }
    
    private func findDDQuintPath() -> String? {
        // Assume ddQuint is in the parent directory of this app
        let currentPath = Bundle.main.bundlePath
        let ddquintPath = (currentPath as NSString).deletingLastPathComponent
        
        // Check if ddQuint exists there
        let ddquintModulePath = (ddquintPath as NSString).appendingPathComponent("ddquint")
        if FileManager.default.fileExists(atPath: ddquintModulePath) {
            return ddquintPath
        }
        
        // Try common locations
        let possiblePaths = [
            "/Users/jakob/Applications/Git/ddQuint",
            NSHomeDirectory() + "/ddQuint",
            "/opt/ddQuint"
        ]
        
        for path in possiblePaths {
            let modulePath = (path as NSString).appendingPathComponent("ddquint")
            if FileManager.default.fileExists(atPath: modulePath) {
                return path
            }
        }
        
        return nil
    }
    
    private func updateUIState(stage: AnalysisStage) {
        switch stage {
        case .initial:
            progressIndicator.isHidden = true
            progressLabel.isHidden = true
            resultsTableView.superview?.isHidden = true
            exportButton.isHidden = true
            startButton.isEnabled = !csvFiles.isEmpty
            
        case .analyzing:
            progressIndicator.isHidden = false
            progressIndicator.startAnimation(nil)
            progressLabel.isHidden = false
            resultsTableView.superview?.isHidden = true
            exportButton.isHidden = true
            startButton.isEnabled = false
            
        case .results:
            progressIndicator.isHidden = true
            progressLabel.isHidden = true
            resultsTableView.superview?.isHidden = false
            exportButton.isHidden = false
            exportButton.isEnabled = true
            startButton.isEnabled = true
            startButton.title = "New Analysis"
        }
    }
    
    private func showError(_ message: String) {
        let alert = NSAlert()
        alert.messageText = "Error"
        alert.informativeText = message
        alert.alertStyle = .warning
        alert.addButton(withTitle: "OK")
        alert.runModal()
    }
    
    private func exportToExcel(url: URL) {
        // Create a simple CSV export for now
        // In a real implementation, you'd call the ddQuint export function
        var csvContent = "Well,Sample,Droplets,Status\\n"
        
        for result in analysisResults {
            let well = result["well"] as? String ?? ""
            let sample = result["sample_name"] as? String ?? ""
            let droplets = result["droplet_count"] as? Int ?? 0
            let status = result["status"] as? String ?? ""
            csvContent += "\\(well),\\(sample),\\(droplets),\\(status)\\n"
        }
        
        do {
            try csvContent.write(to: url, atomically: true, encoding: .utf8)
            let alert = NSAlert()
            alert.messageText = "Export Complete"
            alert.informativeText = "Results exported successfully"
            alert.alertStyle = .informational
            alert.addButton(withTitle: "OK")
            alert.runModal()
        } catch {
            showError("Failed to export results: \\(error)")
        }
    }
}

// MARK: - Table View Data Source & Delegate

extension MainWindowController: NSTableViewDataSource, NSTableViewDelegate {
    func numberOfRows(in tableView: NSTableView) -> Int {
        return analysisResults.count
    }
    
    func tableView(_ tableView: NSTableView, viewFor tableColumn: NSTableColumn?, row: Int) -> NSView? {
        guard row < analysisResults.count else { return nil }
        
        let result = analysisResults[row]
        let identifier = tableColumn?.identifier.rawValue ?? ""
        
        let cellView = NSTableCellView()
        let textField = NSTextField()
        textField.isBordered = false
        textField.isEditable = false
        textField.backgroundColor = .clear
        
        switch identifier {
        case "well":
            textField.stringValue = result["well"] as? String ?? ""
        case "sample":
            textField.stringValue = result["sample_name"] as? String ?? ""
        case "status":
            textField.stringValue = result["status"] as? String ?? ""
        case "droplets":
            textField.stringValue = "\\(result["droplet_count"] as? Int ?? 0)"
        default:
            textField.stringValue = ""
        }
        
        cellView.addSubview(textField)
        textField.translatesAutoresizingMaskIntoConstraints = false
        NSLayoutConstraint.activate([
            textField.leadingAnchor.constraint(equalTo: cellView.leadingAnchor, constant: 4),
            textField.trailingAnchor.constraint(equalTo: cellView.trailingAnchor, constant: -4),
            textField.centerYAnchor.constraint(equalTo: cellView.centerYAnchor)
        ])
        
        return cellView
    }
}

enum AnalysisStage {
    case initial
    case analyzing
    case results
}