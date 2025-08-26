import Cocoa


class InteractiveMainWindowController: NSWindowController, NSWindowDelegate {
    
    // UI Elements
    private var wellListScrollView: NSScrollView!
    var wellListView: NSTableView!
    private var filterButton: NSButton!
    private var legendButton: NSButton!
    private var overviewButton: NSButton!
    private var filterPopover: NSPopover?
    private var hideBufferZoneButton: NSButton!
    private var hideWarningButton: NSButton!
    private var plotImageView: HighQualityImageView!
    private var plotClickView: NSView!
    private var progressIndicator: NSProgressIndicator!
    var editWellButton: NSButton!
    private var globalParamsButton: NSButton!
    private var exportButton: NSButton!
    private var statusLabel: NSTextField!
    
    // Data
    private var selectedFolderURL: URL?
    private var analysisResults: [[String: Any]] = []
    var wellData: [WellData] = []
    var filteredWellData: [WellData] = []
    var selectedWellIndex: Int = -1
    
    // Filter state
    private var hideBufferZones = false
    private var hideWarnings = false
    
    // Analysis state
    private var isAnalysisComplete = false
    
    // Editor references
    private var currentGlobalWindow: NSWindow?
    private var currentWellWindow: NSWindow?
    private var currentParamTabView: NSTabView?
    private var processingIndicatorWindow: NSWindow?
    private var templateFileURL: URL?
    private var templateDescriptionCount: Int = 4
    private let userDefaultsDescCountKey = "DDQ.SampleDescriptionCount"
    private var templateDesigner: TemplateCreatorWindowController?
    
    // Parameter storage - well parameters stored per well ID, reset on app close
    var wellParametersMap: [String: [String: Any]] = [:]
    private var activelyAdjustedParameters: [String: Set<String>] = [:] // Tracks which parameters per well were actively changed
    
    // Cache for processed results
    private var cachedResults: [[String: Any]] = []
    private var cacheKey: String?
    private var cacheTimestamp: Date?
    
    // Composite overview
    private var compositeImagePath: String?
    
    convenience init() {
        let window = NSWindow(
            contentRect: NSRect(x: 0, y: 0, width: 1000, height: 600),
            styleMask: [.titled, .closable, .miniaturizable, .resizable],
            backing: .buffered,
            defer: false
        )
        
        self.init(window: window)
        setupWindow()
    }
    
    private func setupWindow() {
        window?.title = "ddQuint"
        window?.center()
        window?.minSize = NSSize(width: 800, height: 600)
        window?.delegate = self

        // Load persisted template description count (1-4)
        let savedCount = UserDefaults.standard.integer(forKey: userDefaultsDescCountKey)
        if (1...4).contains(savedCount) {
            templateDescriptionCount = savedCount
            writeDebugLog("🧩 Loaded persisted Sample Description Fields: \(savedCount)")
        } else {
            writeDebugLog("🧩 No persisted Sample Description Fields found; using default: \(templateDescriptionCount)")
        }
        
        guard let contentView = window?.contentView else { return }
        
        setupUI(in: contentView)
        setupConstraints(in: contentView)
        
        // Clear all cache files on app launch for fresh analysis
        clearAllCacheFiles()
        
        // Show initial prompt to select folder
        showFolderSelectionPrompt()
        
        // Set up drag and drop after UI is created
        setupDragAndDrop()
    }
    
    private func setupDragAndDrop() {
        guard window?.contentView != nil else { return }
        
        // Create a custom drag and drop view that covers only the plot area
        let dragDropView = DragDropView()
        dragDropView.dragDropDelegate = self
        dragDropView.translatesAutoresizingMaskIntoConstraints = false
        
        // DragDropView doesn't need visible background
        
        // Insert the drag drop view as the top layer over the plot area
        plotClickView.addSubview(dragDropView)
        
        // Ensure it's on top of all other subviews
        dragDropView.layer?.zPosition = 1000
        
        // Set up click handling on the drag drop view (since it covers the plot area)
        dragDropView.clickTarget = self
        dragDropView.clickAction = #selector(plotAreaClicked)
        
        // Make it cover the entire plot area
        NSLayoutConstraint.activate([
            dragDropView.topAnchor.constraint(equalTo: plotClickView.topAnchor),
            dragDropView.leadingAnchor.constraint(equalTo: plotClickView.leadingAnchor),
            dragDropView.trailingAnchor.constraint(equalTo: plotClickView.trailingAnchor),
            dragDropView.bottomAnchor.constraint(equalTo: plotClickView.bottomAnchor)
        ])
        
        // Drag drop view now covers the entire plot area
    }
    
    private func setupUI(in contentView: NSView) {
        // Well list (left panel)
        wellListScrollView = NSScrollView()
        wellListScrollView.hasVerticalScroller = true
        wellListScrollView.hasHorizontalScroller = false
        wellListScrollView.autohidesScrollers = false
        wellListScrollView.borderType = .bezelBorder
        wellListScrollView.translatesAutoresizingMaskIntoConstraints = false
        
        wellListView = NSTableView()
        wellListView.usesAlternatingRowBackgroundColors = true
        wellListView.gridStyleMask = [.solidHorizontalGridLineMask]
        wellListView.headerView = nil // No header
        wellListView.allowsMultipleSelection = true // Enable multi-selection
        
        // Create single column for well list
        let wellColumn = NSTableColumn(identifier: NSUserInterfaceItemIdentifier("well"))
        wellColumn.title = "Wells"
        wellColumn.width = 200
        wellListView.addTableColumn(wellColumn)
        
        wellListScrollView.documentView = wellListView
        wellListView.dataSource = self
        wellListView.delegate = self
        
        // Filter + help controls (icons)
        if #available(macOS 11.0, *) {
            // Use a larger SF Symbol for better visibility
            var img = NSImage(systemSymbolName: "line.3.horizontal.decrease.circle", accessibilityDescription: "Filter") ?? NSImage()
            if let configured = img.withSymbolConfiguration(NSImage.SymbolConfiguration(pointSize: 22, weight: .regular)) {
                img = configured
            }
            filterButton = NSButton(image: img, target: self, action: #selector(showFilterPopover))
        } else {
            filterButton = NSButton(title: "Filter", target: self, action: #selector(showFilterPopover))
        }
        legendButton = NSButton()
        legendButton.bezelStyle = .helpButton
        legendButton.title = ""
        legendButton.target = self
        legendButton.action = #selector(showLegend)

        overviewButton = NSButton(title: "Overview", target: self, action: #selector(showOverview))
        overviewButton.bezelStyle = .rounded
        overviewButton.isEnabled = false

        filterButton.translatesAutoresizingMaskIntoConstraints = false
        legendButton.translatesAutoresizingMaskIntoConstraints = false
        overviewButton.translatesAutoresizingMaskIntoConstraints = false
        
        contentView.addSubview(wellListScrollView)
        contentView.addSubview(filterButton)
        contentView.addSubview(legendButton)
        contentView.addSubview(overviewButton)
        
        // Plot display (right panel)
        plotClickView = NSView()
        plotClickView.wantsLayer = true
        plotClickView.layer?.backgroundColor = NSColor.controlBackgroundColor.cgColor
        plotClickView.translatesAutoresizingMaskIntoConstraints = false
        contentView.addSubview(plotClickView)
        
        // Add custom high-quality image view directly to plot area
        plotImageView = HighQualityImageView()
        plotImageView.translatesAutoresizingMaskIntoConstraints = false
        plotClickView.addSubview(plotImageView)
        
        // Make image view fill the entire plot area
        NSLayoutConstraint.activate([
            plotImageView.topAnchor.constraint(equalTo: plotClickView.topAnchor),
            plotImageView.leadingAnchor.constraint(equalTo: plotClickView.leadingAnchor),
            plotImageView.trailingAnchor.constraint(equalTo: plotClickView.trailingAnchor),
            plotImageView.bottomAnchor.constraint(equalTo: plotClickView.bottomAnchor)
        ])
        
        // Progress indicator (initially hidden) - add to main content view
        progressIndicator = NSProgressIndicator()
        progressIndicator.style = .spinning
        progressIndicator.isHidden = true
        progressIndicator.translatesAutoresizingMaskIntoConstraints = false
        contentView.addSubview(progressIndicator)
        
        // Status label
        statusLabel = NSTextField(labelWithString: "Loading...")
        statusLabel.textColor = .secondaryLabelColor
        statusLabel.translatesAutoresizingMaskIntoConstraints = false
        contentView.addSubview(statusLabel)
        
        // Parameter editing buttons
        editWellButton = NSButton(title: "Edit This Well", target: self, action: #selector(editWellParameters))
        editWellButton.bezelStyle = .rounded
        editWellButton.isEnabled = false
        editWellButton.translatesAutoresizingMaskIntoConstraints = false
        contentView.addSubview(editWellButton)
        
        globalParamsButton = NSButton(title: "Global Parameters", target: self, action: #selector(editGlobalParameters))
        globalParamsButton.bezelStyle = .rounded
        globalParamsButton.isEnabled = false
        globalParamsButton.translatesAutoresizingMaskIntoConstraints = false
        contentView.addSubview(globalParamsButton)
        
        // Export button (comprehensive export)
        exportButton = NSButton(title: "Export", target: self, action: #selector(exportAll))
        exportButton.bezelStyle = .rounded
        exportButton.isEnabled = false
        exportButton.translatesAutoresizingMaskIntoConstraints = false
        contentView.addSubview(exportButton)
        
        // Initial state - don't show placeholder yet
    }
    
    

    // MARK: - Helpers: Parameter value formatting and last-used directories

    private func formatParamValue(_ value: Any) -> String {
        if let d = value as? Double {
            // Round to 6 decimals then trim trailing zeros and dot
            let s = String(format: "%.6f", d)
            var trimmed = s
            while trimmed.contains(".") && (trimmed.hasSuffix("0") || trimmed.hasSuffix(".")) {
                trimmed.removeLast()
            }
            return trimmed
        }
        return String(describing: value)
    }

    private func lastURL(for key: String) -> URL? {
        if let path = UserDefaults.standard.string(forKey: key), !path.isEmpty { return URL(fileURLWithPath: path) }
        return nil
    }

    private func setLastURL(_ url: URL, for key: String) {
        UserDefaults.standard.set(url.path, forKey: key)
    }
private func setupConstraints(in contentView: NSView) {
        NSLayoutConstraint.activate([
            // Filter/help controls (above well list)
            filterButton.topAnchor.constraint(equalTo: contentView.topAnchor, constant: 20),
            filterButton.leadingAnchor.constraint(equalTo: contentView.leadingAnchor, constant: 20),
            filterButton.widthAnchor.constraint(equalToConstant: 28),
            filterButton.heightAnchor.constraint(equalToConstant: 28),

            legendButton.centerYAnchor.constraint(equalTo: filterButton.centerYAnchor),
            legendButton.leadingAnchor.constraint(equalTo: filterButton.trailingAnchor, constant: 8),
            legendButton.widthAnchor.constraint(equalToConstant: 20),
            legendButton.heightAnchor.constraint(equalToConstant: 20),

            overviewButton.centerYAnchor.constraint(equalTo: filterButton.centerYAnchor),
            overviewButton.trailingAnchor.constraint(equalTo: wellListScrollView.trailingAnchor),
            overviewButton.heightAnchor.constraint(equalToConstant: 28),
            
            // Well list (left side, below filter/help controls)
            wellListScrollView.topAnchor.constraint(equalTo: filterButton.bottomAnchor, constant: 8),
            wellListScrollView.leadingAnchor.constraint(equalTo: contentView.leadingAnchor, constant: 20),
            wellListScrollView.widthAnchor.constraint(equalToConstant: 220),
            wellListScrollView.bottomAnchor.constraint(equalTo: statusLabel.topAnchor, constant: -20),
            
            // Plot display (right side)
            plotClickView.topAnchor.constraint(equalTo: contentView.topAnchor, constant: 20),
            plotClickView.leadingAnchor.constraint(equalTo: wellListScrollView.trailingAnchor, constant: 20),
            plotClickView.trailingAnchor.constraint(equalTo: contentView.trailingAnchor, constant: -20),
            plotClickView.bottomAnchor.constraint(equalTo: editWellButton.topAnchor, constant: -20),
            
            // Plot image view constraints are now handled by the scroll view
            
            // Progress indicator - position in the space to the left of status text
            progressIndicator.leadingAnchor.constraint(equalTo: contentView.leadingAnchor, constant: 20),
            progressIndicator.centerYAnchor.constraint(equalTo: statusLabel.centerYAnchor),
            progressIndicator.widthAnchor.constraint(equalToConstant: 16),
            progressIndicator.heightAnchor.constraint(equalToConstant: 16),
            
            // Status label - shifted right to make space for progress indicator
            statusLabel.leadingAnchor.constraint(equalTo: contentView.leadingAnchor, constant: 45),
            statusLabel.bottomAnchor.constraint(equalTo: contentView.bottomAnchor, constant: -20),
            
            // Parameter buttons
            editWellButton.leadingAnchor.constraint(equalTo: plotClickView.leadingAnchor),
            editWellButton.bottomAnchor.constraint(equalTo: contentView.bottomAnchor, constant: -20),
            editWellButton.widthAnchor.constraint(equalToConstant: 120),
            
            globalParamsButton.leadingAnchor.constraint(equalTo: editWellButton.trailingAnchor, constant: 10),
            globalParamsButton.bottomAnchor.constraint(equalTo: editWellButton.bottomAnchor),
            globalParamsButton.widthAnchor.constraint(equalToConstant: 130),
            
            // Export button
            exportButton.trailingAnchor.constraint(equalTo: contentView.trailingAnchor, constant: -20),
            exportButton.bottomAnchor.constraint(equalTo: contentView.bottomAnchor, constant: -20),
            exportButton.widthAnchor.constraint(equalToConstant: 100),
        ])
    }
    
    private func showPlaceholderImage() {
        // Delay to ensure Auto Layout has settled and we have the correct plot view size
        DispatchQueue.main.async {
            self.createPlaceholderImage()
        }
    }
    
    private func createPlaceholderImage() {
        // Create placeholder image that fills the plot area
        let plotSize = plotClickView.frame.size
        let imageWidth = max(plotSize.width, 400)  // Ensure minimum size
        let imageHeight = max(plotSize.height, 300)
        
        let image = NSImage(size: NSSize(width: imageWidth, height: imageHeight))
        image.lockFocus()
        
        NSColor.controlBackgroundColor.setFill()
        NSRect(x: 0, y: 0, width: imageWidth, height: imageHeight).fill()
        
        let text = "Select a well to view plot"
        let attrs: [NSAttributedString.Key: Any] = [
            .font: NSFont.systemFont(ofSize: 16),
            .foregroundColor: NSColor.secondaryLabelColor
        ]
        
        let textSize = text.size(withAttributes: attrs)
        let textRect = NSRect(
            x: (imageWidth - textSize.width) / 2,
            y: (imageHeight - textSize.height) / 2,
            width: textSize.width,
            height: textSize.height
        )
        
        text.draw(in: textRect, withAttributes: attrs)
        image.unlockFocus()
        
        plotImageView.image = image
        ensurePlotFillsArea()
    }
    
    private func showFolderSelectionPrompt() {
        // Delay to ensure Auto Layout has settled and we have the correct plot view size
        DispatchQueue.main.async {
            self.createFolderSelectionImage()
        }
    }
    
    private func createFolderSelectionImage() {
        // Create clickable prompt to select folder - use the full plot view size
        let plotSize = plotClickView.frame.size
        let imageWidth = max(plotSize.width, 400)  // Ensure minimum size
        let imageHeight = max(plotSize.height, 300)
        
        let image = NSImage(size: NSSize(width: imageWidth, height: imageHeight))
        image.lockFocus()
        
        NSColor.controlBackgroundColor.setFill()
        NSRect(x: 0, y: 0, width: imageWidth, height: imageHeight).fill()
        
        // Add border with margin from edges
        let margin: CGFloat = 20
        NSColor.separatorColor.setStroke()
        let borderPath = NSBezierPath(rect: NSRect(x: margin, y: margin, width: imageWidth - 2*margin, height: imageHeight - 2*margin))
        borderPath.setLineDash([5, 5], count: 2, phase: 0)
        borderPath.lineWidth = 2
        borderPath.stroke()
        
        let text = "Click here to select folder\ncontaining ddPCR CSV files"
        let attrs: [NSAttributedString.Key: Any] = [
            .font: NSFont.systemFont(ofSize: 18),
            .foregroundColor: NSColor.controlTextColor,
            .paragraphStyle: {
                let style = NSMutableParagraphStyle()
                style.alignment = .center
                style.lineSpacing = 4
                return style
            }()
        ]
        
        let textSize = text.size(withAttributes: attrs)
        let textRect = NSRect(
            x: (imageWidth - textSize.width) / 2,
            y: (imageHeight - textSize.height) / 2,
            width: textSize.width,
            height: textSize.height
        )
        
        text.draw(in: textRect, withAttributes: attrs)
        image.unlockFocus()
        
        plotImageView.image = image
        ensurePlotFillsArea()
        statusLabel.stringValue = "Ready to analyze ddPCR data"
        
        // Click handling is now done by the DragDropView that covers the plot area
    }
    
    @objc private func plotAreaClicked() {
        if selectedFolderURL == nil {
            selectFolderAndAnalyze()
        }
    }
    
    // MARK: - Analysis
    
    private func selectFolderAndAnalyze() {
        let openPanel = NSOpenPanel()
        openPanel.canChooseFiles = false
        openPanel.canChooseDirectories = true
        openPanel.allowsMultipleSelection = false
        openPanel.prompt = "Select Folder"
        openPanel.message = "Choose a folder containing ddPCR CSV files"
        if let last = lastURL(for: "LastDir.InputFolder") { openPanel.directoryURL = last }
        
        let response = openPanel.runModal()
        
        if response == .OK, let url = openPanel.url {
            // Save the parent directory of the selected folder
            setLastURL(url.deletingLastPathComponent(), for: "LastDir.InputFolder")
            selectedFolderURL = url
            
            // Check for existing parameters.json and offer to apply it
            checkForParametersFile(in: url)
            
            showAnalysisProgress()
            startAnalysis(folderURL: url)
        }
    }
    
    private func checkForParametersFile(in folderURL: URL) {
        let parametersURL = folderURL.appendingPathComponent("ddQuint_Parameters.json")
        
        // Check if ddQuint_Parameters.json exists in the selected folder
        guard FileManager.default.fileExists(atPath: parametersURL.path) else {
            return // No parameters file found, continue normally
        }
        
        // Show alert asking user if they want to apply the parameters
        let alert = NSAlert()
        alert.messageText = "Parameters file found"
        alert.informativeText = "The selected folder contains a 'ddQuint_Parameters.json' file. Would you like to apply these parameters before analysis?"
        alert.addButton(withTitle: "Apply Parameters")
        alert.addButton(withTitle: "Skip")
        alert.alertStyle = .informational
        
        let response = alert.runModal()
        
        if response == .alertFirstButtonReturn {
            // User chose to apply parameters
            applyParametersFromFile(parametersURL)
        }
    }
    
    private func applyParametersFromFile(_ url: URL) {
        do {
            let data = try Data(contentsOf: url)
            guard let obj = try JSONSerialization.jsonObject(with: data) as? [String: Any] else {
                showError("Invalid parameters file format in selected folder")
                return
            }
            
            print("📂 Applying parameters from folder: \(url.lastPathComponent)")
            
            // Load global parameters (if present)
            if let globals = obj["global_parameters"] as? [String: Any] {
                saveParametersToFile(globals)
                print("✅ Applied \(globals.count) global parameters")
            }
            
            // Load well-specific parameters
            if let wells = obj["well_parameters"] as? [String: Any] {
                var map: [String: [String: Any]] = [:]
                for (well, value) in wells {
                    if let params = value as? [String: Any] {
                        map[well] = params
                    }
                }
                wellParametersMap = map
                print("✅ Applied parameters for \(map.count) wells")
            }
            
        } catch {
            showError("Failed to load parameters from folder: \(error.localizedDescription)")
        }
    }
    
    private func showAnalysisProgress() {
        statusLabel.stringValue = "Analyzing files..."
        progressIndicator.isHidden = false
        progressIndicator.startAnimation(nil)
        
        // Clear existing data for progressive loading
        wellData.removeAll()
        filteredWellData.removeAll()
        wellListView.reloadData()
        
        // Disable buttons until wells start completing
        editWellButton.isEnabled = false
        globalParamsButton.isEnabled = false
        exportButton.isEnabled = false
        overviewButton.isEnabled = false
        
        // Clear the plot area and show progress
        plotImageView.image = nil
        showPlaceholderImage()
    }
    
    private func startAnalysis(folderURL: URL) {
        // Start corner spinner
        showCornerSpinner()
        
        // Always run fresh analysis - clear any existing cache for this folder
        let cacheFile = getCacheFilePath(folderURL: folderURL)
        try? FileManager.default.removeItem(at: cacheFile)
        print("🗑️ Cleared cache file for fresh analysis: \(cacheFile.lastPathComponent)")
        
        guard let pythonPath = findPython(),
              let ddquintPath = findDDQuint() else {
            showError("Python or ddQuint not found")
            return
        }
        
        DispatchQueue.global().async { [weak self] in
            let process = Process()
            process.executableURL = URL(fileURLWithPath: pythonPath)
            
            // Hide matplotlib windows from dock and pass template settings
            var env = (process.environment ?? ProcessInfo.processInfo.environment).merging([
                "MPLBACKEND": "Agg",
                "PYTHONDONTWRITEBYTECODE": "1",
                "PYTHONUNBUFFERED": "1",  // Enable real-time output
                "TQDM_DISABLE": "1"  // Disable tqdm progress bars for GUI
            ]) { _, new in new }
            // Inject template parser settings
            env["DDQ_TEMPLATE_DESC_COUNT"] = String(self?.templateDescriptionCount ?? 4)
            if let tpl = self?.templateFileURL?.path { env["DDQ_TEMPLATE_PATH"] = tpl }
            process.environment = env
            
            // Set up pipes for output monitoring (revert to original approach)
            let outputPipe = Pipe()
            let errorPipe = Pipe()
            process.standardOutput = outputPipe
            process.standardError = errorPipe
            
            let escapedFolderPath = folderURL.path.replacingOccurrences(of: "'", with: "\\'")
            let escapedDDQuintPath = ddquintPath.replacingOccurrences(of: "'", with: "\\'")
            let templateCount = self?.templateDescriptionCount ?? 4
            let escapedTemplatePath = self?.templateFileURL?.path.replacingOccurrences(of: "'", with: "\\'") ?? ""

            // Serialize well-specific parameters for batch application
            let wellParamsJSON: String = {
                do {
                    let data = try JSONSerialization.data(withJSONObject: self?.wellParametersMap ?? [:], options: [])
                    return String(data: data, encoding: .utf8) ?? "{}"
                } catch {
                    return "{}"
                }
            }()
            
            process.arguments = [
                "-c",
                """
                import sys
                import json
                import traceback
                import logging
                
                try:
                    sys.path.insert(0, '\(escapedDDQuintPath)')
                    
                    # Initialize logging to capture debug output
                    from ddquint.config.logging_config import setup_logging
                    log_file = setup_logging(debug=True)
                    print(f'Logging initialized: {log_file}')
                    
                    # Also add a handler that prints to stdout so we see logs in debug.log
                    stdout_handler = logging.StreamHandler(sys.stdout)
                    stdout_handler.setLevel(logging.DEBUG)
                    stdout_handler.setFormatter(logging.Formatter('DDQUINT_LOG: %(name)s - %(levelname)s - %(message)s'))
                    logging.getLogger().addHandler(stdout_handler)
                    
                    # Initialize config properly (like main.py does)
                    from ddquint.config import Config
                    from ddquint.utils.parameter_editor import load_parameters_if_exist
                    
                    # Load user parameters if they exist
                    config = Config.get_instance()
                    load_parameters_if_exist(Config)
                    config.finalize_colors()
                    
                    # Import analysis modules
                    from ddquint.core import process_directory
                    from ddquint.utils.template_parser import get_sample_names as _gs
                    from ddquint.utils.template_parser import parse_template_file as _ptf
                    from ddquint.utils.template_parser import find_template_file as _ftf
                    import os
                    
                    # Debug: show template env settings
                    import os
                    print('DEBUG:TEMPLATE_ENV', os.environ.get('DDQ_TEMPLATE_DESC_COUNT'), os.environ.get('DDQ_TEMPLATE_PATH'))
                    
                    # Get sample names with explicit options first (template path + description count)
                    # Fallback to search logic if no explicit template path is provided
                    config.TEMPLATE_SEARCH_PARENT_LEVELS = 5  # Go up 5 levels to find common parent
                    sample_names = {}
                    template_path = '\(escapedTemplatePath)'
                    if template_path:
                        try:
                            sample_names = _ptf(template_path, description_count=\(templateCount))
                        except Exception as e:
                            print(f'DEBUG:TEMPLATE_PARSE_ERROR {e}')
                            sample_names = {}
                    if not sample_names:
                        try:
                            # Search for a template file then parse with desired description count
                            found = _ftf('\(escapedFolderPath)')
                            if found:
                                sample_names = _ptf(found, description_count=\(templateCount))
                            else:
                                sample_names = {}
                        except Exception as e:
                            print(f'DEBUG:TEMPLATE_FALLBACK_ERROR {e}')
                            sample_names = {}
                    print(f'Sample names found: {len(sample_names) if sample_names else 0} entries')
                    print(f'Sample names found: {len(sample_names) if sample_names else 0} entries')
                    if sample_names:
                        sample_entries = list(sample_names.items())[:3]
                        print(f'Sample examples: {sample_entries}')
                    else:
                        # Also try without 'Kopie' suffix if directory name contains it
                        import os
                        dir_name = os.path.basename('\(escapedFolderPath)')
                        if 'Kopie' in dir_name:
                            alt_dir_name = dir_name.replace(' Kopie', '').replace('Kopie', '')
                            print(f'Trying alternative template name: {alt_dir_name}.csv')
                            # Try manual template search with alternative name
                            from ddquint.utils.template_parser import find_template_file
                            import tempfile
                            temp_dir = tempfile.mkdtemp()
                            alt_temp_path = os.path.join(temp_dir, alt_dir_name)
                            os.makedirs(alt_temp_path, exist_ok=True)
                            try:
                                alt_template = find_template_file(alt_temp_path)
                                if alt_template:
                                    from ddquint.utils.template_parser import parse_template_file
                                    sample_names = parse_template_file(alt_template)
                                    print(f'Found alternative template: {alt_template}')
                                    print(f'Alternative sample names found: {len(sample_names)} entries')
                            except Exception as e:
                                print(f'Alternative template search failed: {e}')
                            finally:
                                import shutil
                                shutil.rmtree(temp_dir, ignore_errors=True)
                    
                    # Process files progressively with proper pipeline setup
                    import glob
                    import os
                    from ddquint.core.file_processor import process_csv_file
                    from ddquint.core import process_directory  # For final composite generation
                    
                    csv_files = glob.glob(os.path.join('\(escapedFolderPath)', '*.csv'))
                    
                    # Sort files by well ID in column-first order (A01, B01, C01, A02, B02, ...)
                    # Robust parser with clear separators to avoid false positives (e.g., 'HeLa2').
                    def parse_well_id_from_filename(filename):
                        import re, os
                        basename = os.path.basename(filename)
                        name_no_ext = os.path.splitext(basename)[0]
                        # Accept A1/A01..A12 for rows A-H (case-insensitive), with non-alnum or boundary separators
                        pattern = re.compile(r'(?<![A-Za-z0-9])([A-Ha-h])0?([1-9]|1[0-2])(?![A-Za-z0-9])')
                        matches = list(pattern.finditer(name_no_ext))
                        if not matches:
                            return (999, 999)
                        # Use the last (right-most) well token in the filename
                        m = matches[-1]
                        row_letter = m.group(1).upper()
                        col_number = int(m.group(2))
                        row_number = ord(row_letter) - ord('A') + 1
                        return (col_number, row_number)
                    
                    csv_files.sort(key=parse_well_id_from_filename)
                    print(f'TOTAL_FILES:{len(csv_files)}')
                    try:
                        import json
                        debug_preview = [{'name': os.path.basename(f), 'key': parse_well_id_from_filename(f)} for f in csv_files[:16]]
                        print('DEBUG:SORT_PREVIEW:' + json.dumps(debug_preview))
                    except Exception as _e:
                        print('DEBUG:SORT_PREVIEW_FAILED')
                    
                    results = []
                    processed_count = 0
                    # Parse well-specific overrides (if any)
                    WELL_PARAMS = json.loads('''\(wellParamsJSON)''') if '''\(wellParamsJSON)''' else {}
                    PARAM_KEYS = [
                        'HDBSCAN_MIN_CLUSTER_SIZE','HDBSCAN_MIN_SAMPLES','HDBSCAN_EPSILON','HDBSCAN_METRIC','HDBSCAN_CLUSTER_SELECTION_METHOD','MIN_POINTS_FOR_CLUSTERING',
                        'INDIVIDUAL_PLOT_DPI','PLACEHOLDER_PLOT_DPI',
                        'X_AXIS_MIN','X_AXIS_MAX','Y_AXIS_MIN','Y_AXIS_MAX','X_GRID_INTERVAL','Y_GRID_INTERVAL',
                        'BASE_TARGET_TOLERANCE','EXPECTED_CENTROIDS','EXPECTED_COPY_NUMBERS','EXPECTED_STANDARD_DEVIATION','ANEUPLOIDY_TARGETS','CNV_LOSS_RATIO','CNV_GAIN_RATIO','LOWER_DEVIATION_TARGET','UPPER_DEVIATION_TARGET','TOLERANCE_MULTIPLIER','COPY_NUMBER_MULTIPLIER','CHROMOSOME_COUNT','ENABLE_COPY_NUMBER_ANALYSIS','CLASSIFY_CNV_DEVIATIONS','TARGET_NAMES'
                    ]
                    
                    for csv_file in csv_files:
                        filename = os.path.basename(csv_file)
                        print(f'PROCESSING_FILE:{filename}')
                        
                        try:
                            # Use temporary directory for plots (don't save to input folder)
                            import tempfile
                            temp_base = tempfile.gettempdir()
                            graphs_dir = os.path.join(temp_base, 'ddquint_analysis_plots')
                            os.makedirs(graphs_dir, exist_ok=True)
                            
                            # Apply per-well overrides using new Config context API
                            try:
                                # Compute well_id from filename
                                import re
                                name_no_ext = os.path.splitext(filename)[0]
                                pattern = re.compile(r'(?<![A-Za-z0-9])([A-Ha-h])0?([1-9]|1[0-2])(?![A-Za-z0-9])')
                                m = list(pattern.finditer(name_no_ext))
                                well_id = None
                                if m:
                                    row_letter = m[-1].group(1).upper()
                                    col_number = int(m[-1].group(2))
                                    well_id = f"{row_letter}{col_number:02d}"
                                
                                # Set well context with parameters (if any)
                                if well_id and well_id in WELL_PARAMS:
                                    overrides = WELL_PARAMS.get(well_id, {})
                                    config.set_well_context(well_id, overrides)
                                    print(f"Set well context for {well_id} with {len(overrides)} parameter overrides")
                                else:
                                    # Clear context for wells without custom parameters
                                    config.clear_well_context()
                                    if well_id:
                                        print(f"No custom parameters for {well_id}, using defaults")
                            except Exception as _e:
                                print(f"Well context error: {_e}")
                                # Ensure context is cleared on error
                                config.clear_well_context()

                            # Process individual file with proper error handling
                            result = process_csv_file(csv_file, graphs_dir, sample_names, verbose=False)
                            
                            if result and isinstance(result, dict):
                                results.append(result)
                                processed_count += 1
                                
                                # Extract well data for progressive display
                                well_id = result.get('well', '')
                                sample_name = result.get('sample_name', '')
                                
                                # Get droplet count from various possible sources
                                total_droplets = 0
                                if 'total_droplets' in result:
                                    total_droplets = result['total_droplets']
                                elif 'df_filtered' in result and result['df_filtered'] is not None:
                                    try:
                                        total_droplets = len(result['df_filtered'])
                                    except:
                                        total_droplets = 0
                                
                                # Determine if well has meaningful data
                                has_data = False
                                if 'df_filtered' in result and result['df_filtered'] is not None:
                                    try:
                                        has_data = len(result['df_filtered']) > 0
                                    except:
                                        has_data = False
                                elif total_droplets > 0:
                                    has_data = True
                                
                                well_info = {
                                    'well': well_id,
                                    'sample_name': sample_name,
                                    'droplet_count': total_droplets,
                                    'has_data': has_data,
                                    'has_buffer_zone': bool(result.get('has_buffer_zone', False)),
                                    'has_aneuploidy': bool(result.get('has_aneuploidy', False)),
                                    'error': result.get('error')
                                }
                                
                                print(f'WELL_COMPLETED:{json.dumps(well_info)}')
                                print(f'PROGRESS:{processed_count}/{len(csv_files)}')
                                
                                # Also output complete result for Excel export caching (like regeneration does)
                                serializable_result = {'well': well_id, 'sample_name': sample_name}
                                if isinstance(result, dict):
                                    for key, value in result.items():
                                        if key in ['df_filtered', 'df_original']:
                                            continue  # Skip DataFrames
                                        elif isinstance(value, (str, int, float, bool, list)):
                                            serializable_result[key] = value
                                        elif isinstance(value, dict):
                                            # Handle dictionary values (like copy_numbers, counts)
                                            try:
                                                serializable_dict = {}
                                                for k, v in value.items():
                                                    if isinstance(v, (str, int, float, bool)):
                                                        serializable_dict[k] = v
                                                    else:
                                                        serializable_dict[k] = str(v)
                                                serializable_result[key] = serializable_dict
                                            except Exception:
                                                pass  # Skip if serialization fails
                                print(f'UPDATED_RESULT:{json.dumps(serializable_result)}')
                                
                            else:
                                print(f'No valid result for {filename}')
                                
                        except Exception as e:
                            print(f'Error processing {csv_file}: {str(e)}')
                            import traceback
                            print(f'Traceback: {traceback.format_exc()}')
                            continue
                    
                    print(f'ANALYSIS_COMPLETE: Processed {len(results)} files successfully')
                    
                    
                    # Extract well data for GUI
                    wells_data = []
                    for result in results:
                        df_filtered = result.get('df_filtered')
                        total_droplets = result.get('total_droplets', 0)
                        has_data = df_filtered is not None and len(df_filtered) > 0 if df_filtered is not None else total_droplets > 0
                        
                        well_info = {
                            'well': result.get('well', ''),
                            'sample_name': result.get('sample_name', ''),
                            'droplet_count': total_droplets,
                            'has_data': has_data
                        }
                        wells_data.append(well_info)
                    
                    # Output basic data for GUI (legacy)
                    print('WELLS_DATA:' + json.dumps(wells_data))
                    
                    # Prepare complete results for Excel export (remove non-serializable data)
                    complete_results = []
                    for result in results:
                        # Create a copy without DataFrame objects
                        cached_result = {}
                        for key, value in result.items():
                            if key not in ['df_filtered', 'df_original']:  # Skip DataFrames
                                try:
                                    # Test if value is JSON serializable
                                    json.dumps(value)
                                    cached_result[key] = value
                                except (TypeError, ValueError):
                                    # Skip non-serializable values
                                    continue
                        complete_results.append(cached_result)
                    
                    # Output complete results for Excel export
                    print(f'DEBUG: About to output {len(complete_results)} complete results')
                    print('COMPLETE_RESULTS:' + json.dumps(complete_results))
                    print('DEBUG: Complete results output completed')
                    
                except Exception as e:
                    print(f'PYTHON_ERROR: {e}')
                    traceback.print_exc()
                    # Still try to output whatever results we have
                    if 'results' in locals():
                        try:
                            simple_results = [{'well': r.get('well', 'unknown'), 'sample_name': r.get('sample_name', 'unknown')} for r in results]
                            print('COMPLETE_RESULTS:' + json.dumps(simple_results))
                        except:
                            print('COMPLETE_RESULTS:[]')
                    sys.exit(1)
                """
            ]
            
            do {
                try process.run()
                
                // Set up real-time output monitoring for progressive updates
                let outputHandle = outputPipe.fileHandleForReading
                let errorHandle = errorPipe.fileHandleForReading
                
                var outputBuffer = ""
                var errorBuffer = ""
                
                // Monitor output in real-time
                outputHandle.readabilityHandler = { handle in
                    let data = handle.availableData
                    if data.isEmpty {
                        handle.readabilityHandler = nil
                        return
                    }
                    
                    if let string = String(data: data, encoding: .utf8) {
                        outputBuffer += string
                        
                        // Process line by line for progressive updates
                        let lines = outputBuffer.components(separatedBy: .newlines)
                        outputBuffer = lines.last ?? "" // Keep incomplete line
                        
                        for line in lines.dropLast() {
                            DispatchQueue.main.async {
                                self?.handleProgressiveLine(line: line, folderURL: folderURL)
                            }
                        }
                    }
                }
                
                errorHandle.readabilityHandler = { handle in
                    let data = handle.availableData
                    if data.isEmpty {
                        handle.readabilityHandler = nil
                        return
                    }
                    
                    if let string = String(data: data, encoding: .utf8) {
                        errorBuffer += string
                    }
                }
                
                // Wait for process completion
                DispatchQueue.global().async {
                    process.waitUntilExit()
                    
                    // Clean up handlers
                    outputHandle.readabilityHandler = nil
                    errorHandle.readabilityHandler = nil
                    
                    DispatchQueue.main.async {
                        let debugMsg = """
                        =====DDQUINT ANALYSIS DEBUG=====
                        Python process completed:
                        Exit code: \(process.terminationStatus)
                        Output: \(outputBuffer)
                        Error output: \(errorBuffer)
                        ================================
                        """
                        print(debugMsg)
                        
                        // Write to debug file
                        self?.writeDebugLog(debugMsg)
                        
                        self?.processAnalysisResults(output: outputBuffer, error: errorBuffer, exitCode: process.terminationStatus)
                    }
                }
            } catch {
                DispatchQueue.main.async {
                    self?.showError("Failed to run analysis: \(error)")
                }
            }
        }
    }
    
    private func handleProgressiveLine(line: String, folderURL: URL) {
        let trimmedLine = line.trimmingCharacters(in: .whitespacesAndNewlines)
        
        if trimmedLine.hasPrefix("TOTAL_FILES:") {
            let totalFiles = String(trimmedLine.dropFirst("TOTAL_FILES:".count))
            statusLabel.stringValue = "Found \(totalFiles) files to process"
        }
        else if trimmedLine.hasPrefix("PROCESSING_FILE:") {
            statusLabel.stringValue = "Processing files..."
        }
        else if trimmedLine.hasPrefix("WELL_COMPLETED:") {
            let jsonString = String(trimmedLine.dropFirst("WELL_COMPLETED:".count))
            do {
                if let data = jsonString.data(using: .utf8),
                   let wellInfo = try JSONSerialization.jsonObject(with: data) as? [String: Any] {
                    // Reuse common handler to append, sort, and preserve selection
                    self.addWellProgressively(wellInfo: wellInfo)
                    print("📊 Total wells loaded: \(self.wellData.count)")
                }
            } catch {
                print("Error parsing well data JSON: \(error)")
                print("JSON string was: \(jsonString)")
            }
        }
        else if trimmedLine.hasPrefix("PROGRESS:") {
            let progressInfo = String(trimmedLine.dropFirst("PROGRESS:".count))
            statusLabel.stringValue = "Progress: \(progressInfo) files processed"
        }
        else if trimmedLine.hasPrefix("ANALYSIS_COMPLETE:") {
            statusLabel.stringValue = "Analysis complete"
        }
        else if trimmedLine.hasPrefix("COMPLETE_RESULTS:") {
            let resultsJson = String(trimmedLine.dropFirst("COMPLETE_RESULTS:".count)).trimmingCharacters(in: .whitespacesAndNewlines)
            print("🎯 FOUND COMPLETE_RESULTS in output parser: \(resultsJson.prefix(100))...")
            cacheCompleteResults(resultsJson)
        }
        else if trimmedLine.hasPrefix("UPDATED_RESULT:") {
            let resultJson = String(trimmedLine.dropFirst("UPDATED_RESULT:".count)).trimmingCharacters(in: .whitespacesAndNewlines)
            if let resultData = resultJson.data(using: .utf8),
               let result = try? JSONSerialization.jsonObject(with: resultData) as? [String: Any],
               let wellName = result["well"] as? String {
                print("🎯 FOUND UPDATED_RESULT in output parser for well: \(wellName)")
                updateCachedResultForWell(wellName: wellName, resultJson: resultJson)
                // Update the indicator immediately
                if let idx = wellData.firstIndex(where: { $0.well == wellName }) {
                    let newStatus = determineWellStatus(from: result, wellName: wellName)
                    let edited = isWellEdited(wellName)
                    let current = wellData[idx]
                    wellData[idx] = WellData(well: current.well,
                                              sampleName: current.sampleName,
                                              dropletCount: current.dropletCount,
                                              hasData: current.hasData,
                                              status: newStatus,
                                              isEdited: edited)
                    applyFilters()
                    if let filteredIdx = filteredWellData.firstIndex(where: { $0.well == wellName }) {
                        let tableRow = (compositeImagePath != nil) ? filteredIdx + 1 : filteredIdx
                        wellListView.reloadData(forRowIndexes: IndexSet(integer: tableRow), columnIndexes: IndexSet(integer: 0))
                    }
                }
            }
        }
        else if trimmedLine.hasPrefix("DEBUG:") {
            // Log debug messages from Python
            print("🐍 Python: \(trimmedLine)")
            writeDebugLog("🐍 \(trimmedLine)")
        }
    }
    
    private func processAnalysisResults(output: String, error: String, exitCode: Int32) {
        // Hide processing indicators when analysis completes
        hideProcessingIndicator()
        hideCornerSpinner()
        
        if exitCode != 0 {
            showError("Analysis failed: \(error)")
            return
        }
        
        print("🏁 Processing analysis completion...")
        
        // Check for complete results for Excel export
        if let resultsStart = output.range(of: "COMPLETE_RESULTS:")?.upperBound {
            let resultsLine = output[resultsStart...].components(separatedBy: .newlines)[0]
            let resultsJson = String(resultsLine).trimmingCharacters(in: .whitespacesAndNewlines)
            cacheCompleteResults(resultsJson)
        }
        
        
        // Analysis complete - finalize UI
        progressIndicator.isHidden = true
        progressIndicator.stopAnimation(nil)
        
        // Enable buttons now that analysis is complete
        globalParamsButton.isEnabled = true
        exportButton.isEnabled = true
        overviewButton.isEnabled = true
        
        statusLabel.stringValue = "Analysis complete"
        print("🏁 Analysis complete with \(wellData.count) wells")
        
        // Note: Complete results are cached by cacheCompleteResults() method when COMPLETE_RESULTS is received
        print("🏁 Analysis complete, complete results should be cached for Excel export")
    }
    
    private func generateCacheKey(folderURL: URL) -> String {
        // Simplified cache key - just use folder path for now to avoid template issues
        let folderName = folderURL.lastPathComponent
        let cacheKey = "ddquint_\(folderName)_\(folderURL.path.hash)"
        print("🔑 Generated cache key: \(cacheKey)")
        print("   folder: \(folderURL.path)")
        print("   folderName: \(folderName)")
        return cacheKey
    }
    
    private func cacheCompleteResults(_ resultsJson: String) {
        do {
            let data = resultsJson.data(using: .utf8) ?? Data()
            if let completeResults = try JSONSerialization.jsonObject(with: data, options: []) as? [[String: Any]] {
                // Update cache with complete results for Excel export
                if let folderURL = selectedFolderURL {
                    cacheKey = generateCacheKey(folderURL: folderURL)
                    cachedResults = completeResults
                    cacheTimestamp = Date()
                    print("✅ Cached \(cachedResults.count) complete analysis results for Excel export")
                    // Also update indicators for all wells from final results
                    var updated = false
                    for (i, w) in wellData.enumerated() {
                        if let r = cachedResults.first(where: { ($0["well"] as? String) == w.well }) {
                            let st = determineWellStatus(from: r, wellName: w.well)
                            let ed = isWellEdited(w.well)
                            wellData[i] = WellData(well: w.well,
                                                   sampleName: w.sampleName,
                                                   dropletCount: w.dropletCount,
                                                   hasData: w.hasData,
                                                   status: st,
                                                   isEdited: ed)
                            updated = true
                        }
                    }
                    if updated { applyFilters() }
                    
                    // Persist cache to disk
                    persistCacheToFile(folderURL: folderURL)
                }
            } else {
                print("⚠️ Could not parse complete results as array")
            }
        } catch {
            print("⚠️ Failed to parse complete results JSON: \(error)")
        }
    }
    
    
    
    private func addWellProgressively(wellInfo: [String: Any]) {
        guard let well = wellInfo["well"] as? String,
              let dropletCount = wellInfo["droplet_count"] as? Int,
              let hasData = wellInfo["has_data"] as? Bool else { return }
        
        let sampleName = wellInfo["sample_name"] as? String ?? ""
        
        // Determine status from WELL_COMPLETED payload if available; fall back to cache
        var status: WellStatus = .euploid
        var isEdited = isWellEdited(well)
        if let err = wellInfo["error"] as? String, !err.isEmpty {
            status = .warning
        } else if let hb = wellInfo["has_buffer_zone"] as? Bool, hb {
            status = .buffer
        } else if let ha = wellInfo["has_aneuploidy"] as? Bool, ha {
            status = .aneuploid
        } else if let cachedResult = cachedResults.first(where: { ($0["well"] as? String) == well }) {
            status = determineWellStatus(from: cachedResult, wellName: well)
        }
        
        // Avoid duplicate entries if both progressive handlers emit the same well
        if wellData.contains(where: { $0.well == well }) {
            // Update sample name/droplet count/hasData if changed, then refresh list preserving selection
            if let idx = wellData.firstIndex(where: { $0.well == well }) {
                wellData[idx] = WellData(well: well,
                                         sampleName: sampleName,
                                         dropletCount: dropletCount,
                                         hasData: hasData,
                                         status: status,
                                         isEdited: isEdited)
                reloadWellListPreservingSelection()
            }
            return
        }

        let wellEntry = WellData(
            well: well,
            sampleName: sampleName,
            dropletCount: dropletCount,
            hasData: hasData,
            status: status,
            isEdited: isEdited
        )
        
        // Add to well data, keep column-first ordering, and preserve selection
        wellData.append(wellEntry)
        applyFilters() // This will reload the table with filtered data
        
        // Don't enable buttons here - wait until analysis is completely finished
        
        statusLabel.stringValue = "Processed \(wellData.count) wells..."
    }

    // Reload table while preserving current selection and column-first order
    private func reloadWellListPreservingSelection() {
        // Capture current selection
        let selectedRow = wellListView.selectedRow
        var selectedWellId: String? = nil
        var selectedIsOverview = false
        if selectedRow >= 0 {
            if compositeImagePath != nil && selectedRow == 0 {
                selectedIsOverview = true
            } else {
                var dataIndex = selectedRow
                if compositeImagePath != nil { dataIndex -= 1 }
                if dataIndex >= 0 && dataIndex < wellData.count {
                    selectedWellId = wellData[dataIndex].well
                }
            }
        }
        
        // Sort wells by column-first
        wellData.sort { a, b in
            let (c1, r1) = parseWellIdColumnFirst(a.well)
            let (c2, r2) = parseWellIdColumnFirst(b.well)
            return c1 < c2 || (c1 == c2 && r1 < r2)
        }
        
        // Reload table
        wellListView.reloadData()
        
        // Restore selection
        if selectedIsOverview, compositeImagePath != nil {
            wellListView.selectRowIndexes(IndexSet(integer: 0), byExtendingSelection: false)
        } else if let id = selectedWellId, let idx = wellData.firstIndex(where: { $0.well == id }) {
            let tableRow = (compositeImagePath != nil) ? idx + 1 : idx
            wellListView.selectRowIndexes(IndexSet(integer: tableRow), byExtendingSelection: false)
        }
    }
    
    private func updateProgress(current: Int, total: Int) {
        statusLabel.stringValue = "Processing \(current)/\(total) wells..."
        
        // Update progress indicator if it supports progress values
        if current == total {
            statusLabel.stringValue = "Analysis complete - \(total) wells processed"
        }
    }
    
    
    
    
    
    private func updateUIAfterAnalysis() {
        print("DEBUG: updateUIAfterAnalysis() called with \(wellData.count) wells")
        isAnalysisComplete = true
        
        // Hide progress indicator
        progressIndicator.stopAnimation(nil)
        progressIndicator.isHidden = true
        
        // Sort wells by well ID in column-first order (A01, B01, C01, A02, B02, ...)
        writeDebugLog("DEBUG WELL SORTING: Before sort - wells: \(wellData.map { $0.well })")
        wellData.sort { well1, well2 in
            let (col1, row1) = parseWellIdColumnFirst(well1.well)
            let (col2, row2) = parseWellIdColumnFirst(well2.well)
            let result = col1 < col2 || (col1 == col2 && row1 < row2)
            writeDebugLog("DEBUG WELL SORTING: \(well1.well) (\(col1),\(row1)) vs \(well2.well) (\(col2),\(row2)) = \(result)")
            return result
        }
        writeDebugLog("DEBUG WELL SORTING: After sort - wells: \(wellData.map { $0.well })")
        
        statusLabel.stringValue = "Analysis complete"
        
        // Enable buttons
        globalParamsButton.isEnabled = true
        exportButton.isEnabled = true
        overviewButton.isEnabled = true
        
        // Reload table
        wellListView.reloadData()
        
        // Select first well if available
        if !wellData.isEmpty {
            wellListView.selectRowIndexes(IndexSet(integer: 0), byExtendingSelection: false)
            selectedWellIndex = 0
            loadPlotForSelectedWell()
        } else {
            showPlaceholderImage()
        }
    }
    
    // MARK: - Plot Scaling
    
    private func ensurePlotFillsArea() {
        // Force the image view to update its layout and ensure it fills the container
        plotClickView.needsLayout = true
        plotImageView.needsLayout = true
        
        // Force layout update
        plotClickView.layoutSubtreeIfNeeded()
        
        print("🖼️ Plot area size: \(plotClickView.bounds.size)")
        print("🖼️ Image view size: \(plotImageView.bounds.size)")
        if let image = plotImageView.image {
            print("🖼️ Image size: \(image.size)")
        }
    }
    
    // MARK: - Plot Loading
    
    func loadPlotForSelectedWell() {
        guard selectedWellIndex >= 0 && selectedWellIndex < wellData.count else {
            print("Invalid well selection: \(selectedWellIndex) of \(wellData.count)")
            return
        }
        
        let well = wellData[selectedWellIndex]
        print("Loading plot for well: \(well.well), hasData: \(well.hasData)")
        editWellButton.isEnabled = well.hasData
        
        if !well.hasData {
            print("Well has no data, showing placeholder")
            showPlaceholderImage()
            return
        }
        
        // Generate plot for this well
        print("Generating plot for well: \(well.well)")
        generatePlotForWell(well: well.well)
    }
    
    private func generatePlotForWell(well: String) {
        guard let pythonPath = findPython(),
              let _ = findDDQuint(),
              let folderURL = selectedFolderURL else {
            return
        }
        
        statusLabel.stringValue = "Generating plot for \(well)..."
        
        DispatchQueue.global().async { [weak self] in
            let process = Process()
            process.executableURL = URL(fileURLWithPath: pythonPath)
            
            // Hide matplotlib windows from dock
            var env = (process.environment ?? ProcessInfo.processInfo.environment).merging([
                "MPLBACKEND": "Agg",
                "PYTHONDONTWRITEBYTECODE": "1"
            ]) { _, new in new }
            // Pass template settings to Python
            env["DDQ_TEMPLATE_DESC_COUNT"] = String(self?.templateDescriptionCount ?? 4)
            if let tpl = self?.templateFileURL?.path { env["DDQ_TEMPLATE_PATH"] = tpl }
            process.environment = env
            
            let escapedFolderPath = folderURL.path.replacingOccurrences(of: "'", with: "\\'")
            let tempPlotPath = "/tmp/ddquint_plot_\(well).png"
            
            process.arguments = [
                "-c",
                """
                import sys
                import traceback
                
                try:
                    import os
                    import glob
                    print('DEBUG:TEMPLATE_ENV', os.environ.get('DDQ_TEMPLATE_DESC_COUNT'), os.environ.get('DDQ_TEMPLATE_PATH'))
                    import shutil
                    
                    # Look for existing plot file from the main analysis
                    # The main analysis creates plots in temporary directory
                    import tempfile
                    temp_base = tempfile.gettempdir()
                    possible_graphs_dirs = [
                        os.path.join(temp_base, 'ddquint_analysis_plots')
                    ]
                    
                    existing_plot = None
                    for graphs_dir in possible_graphs_dirs:
                        if os.path.exists(graphs_dir):
                            plot_path = os.path.join(graphs_dir, f'\(well).png')
                            if os.path.exists(plot_path):
                                existing_plot = plot_path
                                break
                    
                    if existing_plot:
                        # Use the existing plot file created by main analysis
                        print(f'Found existing plot: {existing_plot}')
                        shutil.copy2(existing_plot, '\(tempPlotPath)')
                        print('PLOT_CREATED:' + '\(tempPlotPath)')
                    else:
                        # Fallback: Try to regenerate plot using Python CLI
                        # Call the same process that worked in main analysis
                        print('No existing plot found, attempting to generate...')
                        
                        # Check if we can find a plot pattern
                        all_plots = []
                        for graphs_dir in possible_graphs_dirs:
                            if os.path.exists(graphs_dir):
                                pattern = os.path.join(graphs_dir, '*.png')
                                all_plots.extend(glob.glob(pattern))
                        
                        if all_plots:
                            print(f'Available plots: {[os.path.basename(p) for p in all_plots[:5]]}...')
                        
                        print('PLOT_NOT_FOUND')
                        
                except Exception as e:
                    print(f'PLOT_ERROR: {e}')
                    traceback.print_exc()
                    sys.exit(1)
                """
            ]
            
            let outputPipe = Pipe()
            process.standardOutput = outputPipe
            
            do {
                try process.run()
                process.waitUntilExit()
                
                let outputData = outputPipe.fileHandleForReading.readDataToEndOfFile()
                let output = String(data: outputData, encoding: .utf8) ?? ""
                
                DispatchQueue.main.async {
                    let debugMsg = """
                    =====DDQUINT PLOT DEBUG=====
                    Plot generation completed for \(well):
                    Exit code: \(process.terminationStatus)
                    Output: \(output)
                    ============================
                    """
                    print(debugMsg)
                    
                    // Write to debug file
                    self?.writeDebugLog(debugMsg)
                    
                    self?.handlePlotGeneration(output: output, well: well)
                }
            } catch {
                DispatchQueue.main.async {
                    self?.statusLabel.stringValue = "Failed to generate plot"
                }
            }
        }
    }
    
    private func handlePlotGeneration(output: String, well: String) {
        if let plotStart = output.range(of: "PLOT_CREATED:")?.upperBound {
            let plotPath = String(output[plotStart...]).trimmingCharacters(in: .whitespacesAndNewlines)
            
            if let image = NSImage(contentsOfFile: plotPath) {
                plotImageView.image = image
                ensurePlotFillsArea()
                statusLabel.stringValue = "Showing plot for \(well)"
            } else {
                showPlaceholderImage()
                statusLabel.stringValue = "Failed to load plot for \(well)"
            }
        } else if output.contains("NO_DATA_FOR_WELL") {
            showPlaceholderImage()
            statusLabel.stringValue = "No data available for \(well)"
        } else {
            // Fallback: try to regenerate this well's plot from CSV if available
            if let folder = selectedFolderURL {
                let csvFiles = findCSVFiles(in: folder)
                if let csv = csvFiles.first(where: { $0.lastPathComponent.contains(well) }) {
                    statusLabel.stringValue = "Generating plot for \(well)"
                    applyParametersAndRegeneratePlot(wellName: well, parameters: wellParametersMap[well] ?? [:])
                    return
                }
            }
            showPlaceholderImage()
            statusLabel.stringValue = "Could not generate plot for \(well)"
        }
    }
    
    // MARK: - Parameter Window Management
    
    private func openParameterWindow(isGlobal: Bool, title: String) {
        // Close existing window if open to prevent multiple instances
        if isGlobal {
            currentGlobalWindow?.close()
            currentGlobalWindow = nil
        } else {
            currentWellWindow?.close()
            currentWellWindow = nil
        }
        
        // Load parameters FIRST, before creating UI
        var savedParams: [String: Any]
        if isGlobal {
            savedParams = loadGlobalParameters()
        } else {
            // Load parameters for well editing (single or multi-well)
            print("🔍 Loading well parameters:")
            print("   selectedWellIndex: \(selectedWellIndex)")
            print("   wellData.count: \(wellData.count)")
            print("   currentMultiEditWells: \(currentMultiEditWells)")
            
            if selectedWellIndex >= 0 && selectedWellIndex < wellData.count {
                // Always start with global parameters as base
                savedParams = loadGlobalParameters()
                print("📄 Loaded \(savedParams.count) global parameters as base: \(savedParams.keys.sorted())")
                
                if !currentMultiEditWells.isEmpty {
                    // Multi-well editing: find parameters common to ALL selected wells
                    print("🔧 Multi-well editing mode: finding common parameters across \(currentMultiEditWells.count) wells")
                    
                    var commonParameters: [String: Any] = [:]
                    
                    // Get parameters for each selected well
                    for (index, wellName) in currentMultiEditWells.enumerated() {
                        if let wellParams = wellParametersMap[wellName] {
                            print("   Well \(wellName) has \(wellParams.count) custom parameters: \(wellParams.keys.sorted())")
                            
                            if index == 0 {
                                // First well - start with its parameters
                                commonParameters = wellParams
                            } else {
                                // Subsequent wells - keep only parameters that match
                                var paramsToRemove: [String] = []
                                for (key, value) in commonParameters {
                                    if let otherValue = wellParams[key] {
                                        // Parameter exists in this well, check if values match
                                        if !areParameterValuesEqual(value, otherValue) {
                                            print("     Parameter \(key) differs: \(value) vs \(otherValue) - removing from common set")
                                            paramsToRemove.append(key)
                                        }
                                    } else {
                                        // Parameter doesn't exist in this well - remove from common set
                                        print("     Parameter \(key) missing in well \(wellName) - removing from common set")
                                        paramsToRemove.append(key)
                                    }
                                }
                                
                                for key in paramsToRemove {
                                    commonParameters.removeValue(forKey: key)
                                }
                            }
                        } else {
                            print("   Well \(wellName) has no custom parameters")
                            if index == 0 {
                                commonParameters = [:] // First well has no params, so no common params
                            } else {
                                // If any well has no custom parameters, only global parameters are common
                                commonParameters = [:]
                            }
                        }
                    }
                    
                    // Apply common parameters
                    for (key, value) in commonParameters {
                        savedParams[key] = value
                    }
                    
                    print("✅ Applied \(commonParameters.count) common parameters across all wells: \(commonParameters.keys.sorted())")
                    
                } else {
                    // Single-well editing: use existing logic
                    let wellId = wellData[selectedWellIndex].well
                    print("   Single well editing: wellId: \(wellId)")
                    print("   wellParametersMap has \(wellParametersMap.count) entries: \(Array(wellParametersMap.keys).sorted())")
                    
                    // Overlay well-specific modifications if they exist
                    if let savedWellParams = wellParametersMap[wellId], !savedWellParams.isEmpty {
                        for (key, value) in savedWellParams {
                            savedParams[key] = value
                        }
                        print("✅ Applied \(savedWellParams.count) well-specific parameter overrides for well \(wellId): \(savedWellParams.keys.sorted())")
                    } else {
                        print("📄 No well-specific parameter overrides for well \(wellId)")
                    }
                }
            } else {
                savedParams = [:]
                print("❌ NO FALLBACK: Invalid selectedWellIndex: \(selectedWellIndex) (valid range: 0..<\(wellData.count))!")
            }
        }
        
        print("📋 Using \(savedParams.count) parameters for UI creation: \(savedParams.keys.sorted())")
        
        statusLabel.stringValue = "Opening \(isGlobal ? "Global" : "Well") Parameters window..."
        
        // Create parameter window with proper styling
        let paramWindow = NSWindow(
            contentRect: NSRect(x: 100, y: 100, width: 800, height: 650),
            styleMask: [.titled, .closable, .resizable],
            backing: .buffered,
            defer: false
        )
        
        paramWindow.title = title
        paramWindow.center()
        paramWindow.delegate = self
        paramWindow.isReleasedWhenClosed = false
        
        // Create content view with Auto Layout
        let contentView = NSView()
        paramWindow.contentView = contentView
        
        // Create tab view
        let tabView = NSTabView()
        tabView.translatesAutoresizingMaskIntoConstraints = false
        tabView.tabViewType = .topTabsBezelBorder
        contentView.addSubview(tabView)
        // Keep a reference so we can extract values from all tabs, not just the visible one
        currentParamTabView = tabView
        
        // Tab 1: HDBSCAN Settings
        let hdbscanTab = NSTabViewItem(identifier: "hdbscan")
        hdbscanTab.label = "HDBSCAN Settings"
        let hdbscanView = createHDBSCANParametersView(isGlobal: isGlobal, parameters: savedParams)
        hdbscanTab.view = hdbscanView
        tabView.addTabViewItem(hdbscanTab)
        
        // Detect current chromosome count for auto-layout
        let currentChromCount = savedParams["CHROMOSOME_COUNT"] as? Int ?? 5
        
        // Tab 2: Expected Centroids (for both global and well-specific)
        let centroidsTab = NSTabViewItem(identifier: "centroids")
        centroidsTab.label = "Expected Centroids"
        let centroidsView = createCentroidsParametersView(isGlobal: isGlobal, parameters: savedParams)
        centroidsTab.view = centroidsView
        tabView.addTabViewItem(centroidsTab)
        
        // Auto-apply two-column layout if chromosome count > 5
        if currentChromCount > 5 {
            if let scrollView = centroidsView as? NSScrollView,
               let documentView = scrollView.documentView {
                updateCentroidsViewForTargetCount(documentView, targetCount: currentChromCount, parameters: savedParams)
            }
        }
        
        // Tab 3: Copy Number Settings (for both global and well-specific)
        let copyNumberTab = NSTabViewItem(identifier: "copynumber")
        copyNumberTab.label = "Copy Number"
        let copyNumberView = createCopyNumberParametersView(parameters: savedParams)
        copyNumberTab.view = copyNumberView
        tabView.addTabViewItem(copyNumberTab)
        
        // Auto-apply two-column layout if chromosome count > 5
        // Detect current chromosome count for auto-layout (declared above)
        if currentChromCount > 5 {
            if let scrollView = copyNumberView as? NSScrollView,
               let documentView = scrollView.documentView {
                updateCopyNumberViewForTargetCount(documentView, targetCount: currentChromCount, parameters: savedParams)
            }
        }
        
        // Tab 4: Visualization Settings (for both global and well-specific)
        let visualizationTab = NSTabViewItem(identifier: "visualization")
        visualizationTab.label = "Visualization"
        let visualizationView = createVisualizationParametersView(parameters: savedParams)
        visualizationTab.view = visualizationView
        tabView.addTabViewItem(visualizationTab)
        
        // Tab 5: General Settings
        let generalTab = NSTabViewItem(identifier: "general")
        generalTab.label = "General"
        let generalView = createGeneralSettingsView(parameters: savedParams)
        generalTab.view = generalView
        tabView.addTabViewItem(generalTab)

        // Ensure scroll views start at the top for better UX
        DispatchQueue.main.async { [weak self] in
            if let scroll = copyNumberView as? NSScrollView { self?.scrollToTop(scroll) }
            if let scroll = visualizationView as? NSScrollView { self?.scrollToTop(scroll) }
            if let scroll = hdbscanView as? NSScrollView { self?.scrollToTop(scroll) }
            if let scroll = centroidsView as? NSScrollView { self?.scrollToTop(scroll) }
            if let scroll = generalView as? NSScrollView { self?.scrollToTop(scroll) }
        }
        
        // Create button container
        let buttonContainer = NSView()
        buttonContainer.translatesAutoresizingMaskIntoConstraints = false
        contentView.addSubview(buttonContainer)
        
        // Create buttons with proper sizing
        let restoreButton = NSButton(title: "Restore Defaults", target: self, action: isGlobal ? #selector(restoreGlobalDefaults) : #selector(restoreWellDefaults))
        restoreButton.translatesAutoresizingMaskIntoConstraints = false
        restoreButton.bezelStyle = .rounded
        
        var resetButton: NSButton?
        if !isGlobal {
            resetButton = NSButton(title: "Reset Parameters", target: self, action: #selector(resetWellParameters))
            resetButton!.translatesAutoresizingMaskIntoConstraints = false
            resetButton!.bezelStyle = .rounded
        }
        
        let cancelButton = NSButton(title: "Cancel", target: self, action: isGlobal ? #selector(closeGlobalParameterWindow) : #selector(closeWellParameterWindow))
        cancelButton.translatesAutoresizingMaskIntoConstraints = false
        cancelButton.bezelStyle = .rounded
        
        let saveButton = NSButton(title: "Save & Apply", target: self, action: isGlobal ? #selector(saveGlobalParameters) : #selector(saveWellParameters))
        saveButton.translatesAutoresizingMaskIntoConstraints = false
        saveButton.bezelStyle = .rounded
        saveButton.keyEquivalent = "\r"
        
        buttonContainer.addSubview(restoreButton)
        if let resetButton = resetButton {
            buttonContainer.addSubview(resetButton)
        }
        buttonContainer.addSubview(cancelButton)
        buttonContainer.addSubview(saveButton)
        
        // Set up Auto Layout constraints
        NSLayoutConstraint.activate([
            // Tab view constraints
            tabView.topAnchor.constraint(equalTo: contentView.topAnchor, constant: 20),
            tabView.leadingAnchor.constraint(equalTo: contentView.leadingAnchor, constant: 20),
            tabView.trailingAnchor.constraint(equalTo: contentView.trailingAnchor, constant: -20),
            tabView.bottomAnchor.constraint(equalTo: buttonContainer.topAnchor, constant: -10),
            
            // Button container constraints
            buttonContainer.leadingAnchor.constraint(equalTo: contentView.leadingAnchor, constant: 20),
            buttonContainer.trailingAnchor.constraint(equalTo: contentView.trailingAnchor, constant: -20),
            buttonContainer.bottomAnchor.constraint(equalTo: contentView.bottomAnchor, constant: -10),
            buttonContainer.heightAnchor.constraint(equalToConstant: 32),
            
            // Button constraints
            restoreButton.leadingAnchor.constraint(equalTo: buttonContainer.leadingAnchor),
            restoreButton.centerYAnchor.constraint(equalTo: buttonContainer.centerYAnchor),
            restoreButton.widthAnchor.constraint(equalToConstant: 130),
            restoreButton.heightAnchor.constraint(equalToConstant: 32),
            
            cancelButton.trailingAnchor.constraint(equalTo: saveButton.leadingAnchor, constant: -10),
            cancelButton.centerYAnchor.constraint(equalTo: buttonContainer.centerYAnchor),
            cancelButton.widthAnchor.constraint(equalToConstant: 100),
            cancelButton.heightAnchor.constraint(equalToConstant: 32),
            
            saveButton.trailingAnchor.constraint(equalTo: buttonContainer.trailingAnchor),
            saveButton.centerYAnchor.constraint(equalTo: buttonContainer.centerYAnchor),
            saveButton.widthAnchor.constraint(equalToConstant: 120),
            saveButton.heightAnchor.constraint(equalToConstant: 32)
        ])
        
        // Add reset button constraints if it exists
        if let resetButton = resetButton {
            NSLayoutConstraint.activate([
                resetButton.leadingAnchor.constraint(equalTo: restoreButton.trailingAnchor, constant: 10),
                resetButton.centerYAnchor.constraint(equalTo: buttonContainer.centerYAnchor),
                resetButton.widthAnchor.constraint(equalToConstant: 130),
                resetButton.heightAnchor.constraint(equalToConstant: 32)
            ])
        }
        
        // Store window reference before showing
        if isGlobal {
            currentGlobalWindow = paramWindow
        } else {
            currentWellWindow = paramWindow
        }
        
        // Show window
        paramWindow.makeKeyAndOrderFront(nil)
        print("🪟 Window created and shown: \(paramWindow.title ?? "No Title")")
        
        // Parameters were already loaded and applied during UI creation above
        
        statusLabel.stringValue = "\(isGlobal ? "Global" : "Well") Parameters window opened"
    }

    private func scrollToTop(_ scrollView: NSScrollView) {
        guard let doc = scrollView.documentView else { return }
        let clip = scrollView.contentView
        // Compute the top-left point in non-flipped coordinates
        let maxY = max(0, doc.bounds.size.height - clip.bounds.size.height)
        let topPoint = NSPoint(x: 0, y: maxY)
        clip.scroll(to: topPoint)
        scrollView.reflectScrolledClipView(clip)
    }
    
    private func createHDBSCANParametersView(isGlobal: Bool, parameters: [String: Any]) -> NSView {
        let scrollView = NSScrollView()
        let view = NSView()
        
        var yPos: CGFloat = 500
        let fieldHeight: CGFloat = 24
        let spacing: CGFloat = 30
        
        // Title
        let titleLabel = NSTextField(labelWithString: "HDBSCAN Clustering Parameters")
        titleLabel.font = NSFont.boldSystemFont(ofSize: 16)
        titleLabel.frame = NSRect(x: 20, y: yPos, width: 400, height: 20)
        view.addSubview(titleLabel)
        yPos -= 50
        
        // Instructions
        let instructionLabel = NSTextField(labelWithString: "Configure clustering parameters for droplet classification.")
        instructionLabel.font = NSFont.systemFont(ofSize: 12)
        instructionLabel.textColor = .secondaryLabelColor
        instructionLabel.frame = NSRect(x: 40, y: yPos, width: 500, height: 16)
        view.addSubview(instructionLabel)
        yPos -= 40
        
        // Core HDBSCAN Parameters
        let coreParams = [
            ("HDBSCAN_MIN_CLUSTER_SIZE", "Min Cluster Size:", "", "Minimum number of droplets required to form a cluster"),
            ("HDBSCAN_MIN_SAMPLES", "Min Samples:", "", "Minimum number of samples in a neighborhood for core points"),
            ("HDBSCAN_EPSILON", "Epsilon:", "", "Maximum distance between samples in the same neighborhood"),
            ("MIN_POINTS_FOR_CLUSTERING", "Min Points for Clustering:", "", "Minimum droplets needed before clustering is performed")
        ]
        
        for (identifier, label, _, tooltip) in coreParams {
            let paramLabel = NSTextField(labelWithString: label)
            paramLabel.frame = NSRect(x: 40, y: yPos, width: 200, height: fieldHeight)
            paramLabel.wantsLayer = true
            paramLabel.layer?.zPosition = 10000  // Ensure label is clickable
            addParameterTooltip(to: paramLabel, identifier: identifier)
            
            let paramField = NSTextField()
            paramField.identifier = NSUserInterfaceItemIdentifier(identifier)
            addParameterTooltip(to: paramField, identifier: identifier)
            // Use parameter value if available, otherwise leave empty (no hardcoded defaults)
            if let paramValue = parameters[identifier] {
                paramField.stringValue = formatParamValue(paramValue)
                print("🎯 Set field \(identifier) = \(paramValue)")
            } else {
                paramField.stringValue = ""
                print("⚪ Field \(identifier) has no parameter value, leaving empty")
            }
            paramField.frame = NSRect(x: 250, y: yPos, width: 100, height: fieldHeight)
            paramField.toolTip = tooltip
            paramField.isEditable = true
            paramField.isSelectable = true
            paramField.isBordered = true
            paramField.bezelStyle = .roundedBezel
            paramField.wantsLayer = true
            paramField.layer?.zPosition = 10000  // Ensure field is above other UI elements
            
            view.addSubview(paramLabel)
            view.addSubview(paramField)
            yPos -= spacing
        }
        
        // Advanced Parameters (shown for both global and well-specific to match layout)
        do {
            yPos -= 20
            let advancedLabel = NSTextField(labelWithString: "Advanced Settings")
            advancedLabel.font = NSFont.boldSystemFont(ofSize: 14)
            advancedLabel.frame = NSRect(x: 20, y: yPos, width: 200, height: 20)
            view.addSubview(advancedLabel)
            yPos -= 40
            
            // Distance Metric dropdown
            let metricLabel = NSTextField(labelWithString: "Distance Metric:")
            metricLabel.frame = NSRect(x: 40, y: yPos, width: 200, height: fieldHeight)
            addParameterTooltip(to: metricLabel, identifier: "HDBSCAN_METRIC")
            
            let metricPopup = NSPopUpButton()
            metricPopup.identifier = NSUserInterfaceItemIdentifier("HDBSCAN_METRIC")
            addParameterTooltip(to: metricPopup, identifier: "HDBSCAN_METRIC")
            metricPopup.addItems(withTitles: ["euclidean", "manhattan", "chebyshev", "minkowski"])
            if let value = parameters["HDBSCAN_METRIC"] as? String {
                metricPopup.selectItem(withTitle: value)
            } else {
                metricPopup.selectItem(withTitle: "euclidean")
            }
            metricPopup.frame = NSRect(x: 250, y: yPos, width: 120, height: fieldHeight)
            metricPopup.toolTip = "Distance metric used for clustering calculations"
            
            view.addSubview(metricLabel)
            view.addSubview(metricPopup)
            yPos -= spacing
            
            // Cluster Selection Method dropdown
            let selectionLabel = NSTextField(labelWithString: "Cluster Selection Method:")
            selectionLabel.frame = NSRect(x: 40, y: yPos, width: 200, height: fieldHeight)
            addParameterTooltip(to: selectionLabel, identifier: "HDBSCAN_CLUSTER_SELECTION_METHOD")
            
            let selectionPopup = NSPopUpButton()
            selectionPopup.identifier = NSUserInterfaceItemIdentifier("HDBSCAN_CLUSTER_SELECTION_METHOD")
            addParameterTooltip(to: selectionPopup, identifier: "HDBSCAN_CLUSTER_SELECTION_METHOD")
            selectionPopup.addItems(withTitles: ["eom", "leaf"])
            if let value = parameters["HDBSCAN_CLUSTER_SELECTION_METHOD"] as? String {
                selectionPopup.selectItem(withTitle: value)
            } else {
                selectionPopup.selectItem(withTitle: "eom")
            }
            selectionPopup.frame = NSRect(x: 250, y: yPos, width: 120, height: fieldHeight)
            selectionPopup.toolTip = "Method for selecting clusters from the hierarchy tree"
            
            view.addSubview(selectionLabel)
            view.addSubview(selectionPopup)
            yPos -= spacing
        }
        
        // Set proper view size with padding
        let finalHeight = max(500 - yPos + 80, 500)  // Ensure adequate height
        view.frame = NSRect(x: 0, y: 0, width: 620, height: finalHeight)
        
        // Setup scroll view properly
        // Remove explicit frame - let Auto Layout handle it
        scrollView.documentView = view
        scrollView.hasVerticalScroller = true
        scrollView.hasHorizontalScroller = false
        scrollView.autohidesScrollers = true
        scrollView.borderType = .noBorder
        
        // Ensure proper scrolling behavior
        scrollView.verticalScrollElasticity = .allowed
        scrollView.horizontalScrollElasticity = .none
        
        return scrollView
    }
    
    private func createCentroidsParametersView(isGlobal: Bool, parameters: [String: Any]) -> NSView {
        let scrollView = NSScrollView()
        let view = NSView()
        
        var yPos: CGFloat = 500  // Fixed title position
        let fieldHeight: CGFloat = 24
        let spacing: CGFloat = 30
        
        // Title
        let titleLabel = NSTextField(labelWithString: "Expected Centroids Configuration")
        titleLabel.font = NSFont.boldSystemFont(ofSize: 16)
        titleLabel.frame = NSRect(x: 20, y: yPos, width: 400, height: 20)
        view.addSubview(titleLabel)
        yPos -= 40
        
        // Instructions
        let instructionLabel = NSTextField(labelWithString: "Define expected centroid positions for targets. Format: HEX, FAM")
        instructionLabel.font = NSFont.systemFont(ofSize: 12)
        instructionLabel.textColor = .secondaryLabelColor
        instructionLabel.frame = NSRect(x: 40, y: yPos, width: 500, height: 16)
        view.addSubview(instructionLabel)
        yPos -= 40
        
        // Target count selection
        let chromCountLabel = NSTextField(labelWithString: "Number of Targets:")
        chromCountLabel.frame = NSRect(x: 40, y: yPos, width: 200, height: fieldHeight)
        addParameterTooltip(to: chromCountLabel, identifier: "CHROMOSOME_COUNT")
        
        let chromCountPopup = NSPopUpButton()
        chromCountPopup.identifier = NSUserInterfaceItemIdentifier("CHROMOSOME_COUNT")
        addParameterTooltip(to: chromCountPopup, identifier: "CHROMOSOME_COUNT")
        chromCountPopup.addItems(withTitles: ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10"])
        
        // Determine current chromosome count from existing data - check CHROMOSOME_COUNT parameter first
        var currentChromCount = 5 // Default
        if let chromCount = parameters["CHROMOSOME_COUNT"] as? Int {
            currentChromCount = chromCount
            print("🎯 Using CHROMOSOME_COUNT parameter: \(chromCount)")
        } else if let centroids = parameters["EXPECTED_CENTROIDS"] as? [String: [Double]] {
            let chromKeys = centroids.keys.filter { $0.starts(with: "Chrom") }
            if !chromKeys.isEmpty {
                currentChromCount = chromKeys.count
                print("🎯 Inferred chromosome count from centroids: \(chromKeys.count)")
            }
        } else if let copyNumbers = parameters["EXPECTED_COPY_NUMBERS"] as? [String: Double] {
            let chromKeys = copyNumbers.keys.filter { $0.starts(with: "Chrom") }
            if !chromKeys.isEmpty {
                currentChromCount = chromKeys.count
                print("🎯 Inferred chromosome count from copy numbers: \(chromKeys.count)")
            }
        }
        
        // Set the popup to current count
        if currentChromCount >= 1 && currentChromCount <= 10 {
            chromCountPopup.selectItem(at: currentChromCount - 1)
        }
        
        chromCountPopup.frame = NSRect(x: 250, y: yPos, width: 80, height: fieldHeight)
        // Ensure popup is above other elements
        chromCountPopup.wantsLayer = true
        chromCountPopup.layer?.zPosition = 100
        chromCountPopup.target = self
        chromCountPopup.action = #selector(chromosomeCountChanged(_:))
        
        view.addSubview(chromCountLabel)
        view.addSubview(chromCountPopup)
        yPos -= 50
        
        // Centroid entries - dynamically create based on chromosome count
        var targets = ["Negative"]
        for i in 1...currentChromCount {
            targets.append("Chrom\(i)")
        }
        
        for (index, target) in targets.enumerated() {
            let displayLabel = target == "Negative" ? "Negative:" : "Target \(index):"
            let targetLabel = NSTextField(labelWithString: displayLabel)
            targetLabel.frame = NSRect(x: 40, y: yPos, width: 120, height: fieldHeight)
            targetLabel.wantsLayer = true
            targetLabel.layer?.zPosition = 10000  // Ensure label is clickable
            addParameterTooltip(to: targetLabel, identifier: "EXPECTED_CENTROIDS_\(target)")
            
            let targetField = NSTextField()
            targetField.identifier = NSUserInterfaceItemIdentifier("EXPECTED_CENTROIDS_\(target)")
            addParameterTooltip(to: targetField, identifier: "EXPECTED_CENTROIDS_\(target)")
            
            // Load value from parameters instead of hardcoded defaults
            if let centroids = parameters["EXPECTED_CENTROIDS"] as? [String: [Double]],
               let coords = centroids[target], coords.count >= 2 {
                targetField.stringValue = "\(Int(coords[0])), \(Int(coords[1]))"
            } else {
                targetField.stringValue = ""
            }
            targetField.frame = NSRect(x: 170, y: yPos, width: 150, height: fieldHeight)
            targetField.toolTip = "Expected centroid coordinates (HEX, FAM) for \(target)"
            targetField.isEditable = true
            targetField.isSelectable = true
            targetField.isBordered = true
            targetField.bezelStyle = .roundedBezel
            targetField.backgroundColor = NSColor.textBackgroundColor
            targetField.wantsLayer = true
            targetField.layer?.zPosition = 10000  // Ensure field is above other UI elements
            
            view.addSubview(targetLabel)
            view.addSubview(targetField)
            yPos -= spacing
        }
        
        // Centroid Matching Parameters (shown for both global and well-specific to match layout)
        do {
            yPos -= 20
            let matchingLabel = NSTextField(labelWithString: "Centroid Matching Parameters")
            matchingLabel.font = NSFont.boldSystemFont(ofSize: 14)
            matchingLabel.frame = NSRect(x: 20, y: yPos, width: 300, height: 20)
            view.addSubview(matchingLabel)
            yPos -= 40
            
            let matchingParams = [
                ("BASE_TARGET_TOLERANCE", "Target Tolerance:", "", "Base tolerance distance for matching detected clusters")
            ]
            
            for (identifier, label, _, tooltip) in matchingParams {
                let paramLabel = NSTextField(labelWithString: label)
                paramLabel.frame = NSRect(x: 40, y: yPos, width: 200, height: fieldHeight)
                addParameterTooltip(to: paramLabel, identifier: identifier)
                
                let paramField = NSTextField()
                paramField.identifier = NSUserInterfaceItemIdentifier(identifier)
                addParameterTooltip(to: paramField, identifier: identifier)
                // Use parameter value if available, otherwise leave empty
                if let paramValue = parameters[identifier] {
                    paramField.stringValue = formatParamValue(paramValue)
                    print("🎯 Set field \(identifier) = \(paramValue)")
                } else {
                    paramField.stringValue = ""
                    print("⚪ Field \(identifier) has no parameter value, leaving empty")
                }
                paramField.frame = NSRect(x: 250, y: yPos, width: 100, height: fieldHeight)
                paramField.toolTip = tooltip
                paramField.isEditable = true
                paramField.isSelectable = true
                paramField.isBordered = true
                paramField.bezelStyle = .roundedBezel
                
                view.addSubview(paramLabel)
                view.addSubview(paramField)
                yPos -= spacing
            }
        }
        
        // Set proper view size with padding
        let finalHeight = max(500 - yPos + 80, 400)  // Calculate from actual content height
        view.frame = NSRect(x: 0, y: 0, width: 620, height: finalHeight)
        
        // Setup scroll view properly
        // Remove explicit frame - let Auto Layout handle it
        scrollView.documentView = view
        scrollView.hasVerticalScroller = true
        scrollView.hasHorizontalScroller = false
        scrollView.autohidesScrollers = true
        scrollView.borderType = .noBorder
        
        // Ensure proper scrolling behavior
        scrollView.verticalScrollElasticity = .allowed
        scrollView.horizontalScrollElasticity = .none
        
        return scrollView
    }
    
    private func createCopyNumberParametersView(parameters: [String: Any]) -> NSView {
        let scrollView = NSScrollView()
        let view = NSView()
        
        var yPos: CGFloat = 500
        let fieldHeight: CGFloat = 24
        let spacing: CGFloat = 30
        
        // Title
        let titleLabel = NSTextField(labelWithString: "Copy Number Analysis Settings")
        titleLabel.font = NSFont.boldSystemFont(ofSize: 16)
        titleLabel.frame = NSRect(x: 20, y: yPos, width: 400, height: 20)
        view.addSubview(titleLabel)
        yPos -= 40
        
        // Instructions
        let instructionLabel = NSTextField(labelWithString: "Configure copy number analysis and classification parameters.")
        instructionLabel.font = NSFont.systemFont(ofSize: 12)
        instructionLabel.textColor = .secondaryLabelColor
        instructionLabel.frame = NSRect(x: 40, y: yPos, width: 500, height: 16)
        view.addSubview(instructionLabel)
        yPos -= 40
        
        // General Parameters
        let generalParams = [
            ("MIN_USABLE_DROPLETS", "Min Usable Droplets:", "", "Minimum total droplets required for reliable analysis"),
            ("COPY_NUMBER_MEDIAN_DEVIATION_THRESHOLD", "Median Deviation Threshold:", "", "Maximum deviation from median for baseline selection"),
            ("COPY_NUMBER_MULTIPLIER", "Copy Number Multiplier:", "", "Multiplier applied for displaying relative copy number results")
        ]
        
        for (identifier, label, paramType, tooltip) in generalParams {
            let paramLabel = NSTextField(labelWithString: label)
            paramLabel.frame = NSRect(x: 40, y: yPos, width: 220, height: fieldHeight)
            addParameterTooltip(to: paramLabel, identifier: identifier)
            
            view.addSubview(paramLabel)
            
            // Handle dropdown parameters differently
            if paramType == "yes/no" {
                let dropdown = NSPopUpButton()
                dropdown.identifier = NSUserInterfaceItemIdentifier(identifier)
                dropdown.addItems(withTitles: ["Yes", "No"])
                
                // Set current value
                if let paramValue = parameters[identifier] as? Bool {
                    dropdown.selectItem(at: paramValue ? 0 : 1)
                } else if let paramValue = parameters[identifier] as? String {
                    dropdown.selectItem(at: paramValue.lowercased() == "yes" ? 0 : 1)
                } else {
                    dropdown.selectItem(at: 0) // Default to Yes
                }
                
                dropdown.frame = NSRect(x: 270, y: yPos, width: 80, height: fieldHeight)
                addParameterTooltip(to: dropdown, identifier: identifier)
                view.addSubview(dropdown)
            } else {
                let paramField = NSTextField()
                paramField.identifier = NSUserInterfaceItemIdentifier(identifier)
                addParameterTooltip(to: paramField, identifier: identifier)
                // Use parameter value if available, otherwise leave empty
                if let paramValue = parameters[identifier] {
                    paramField.stringValue = formatParamValue(paramValue)
                    print("🎯 Set field \(identifier) = \(paramValue)")
                } else {
                    paramField.stringValue = ""
                    print("⚪ Field \(identifier) has no parameter value, leaving empty")
                }
                paramField.frame = NSRect(x: 270, y: yPos, width: 100, height: fieldHeight)
                paramField.toolTip = tooltip
                paramField.isEditable = true
                paramField.isSelectable = true
                paramField.isBordered = true
                paramField.bezelStyle = .roundedBezel
                
                view.addSubview(paramField)
            }
            
            yPos -= spacing
        }
        
        // Expected Copy Number
        yPos -= 20
        let aneuploidyLabel = NSTextField(labelWithString: "Expected Copy Number")
        aneuploidyLabel.font = NSFont.boldSystemFont(ofSize: 14)
        aneuploidyLabel.frame = NSRect(x: 20, y: yPos, width: 200, height: 20)
        view.addSubview(aneuploidyLabel)
        yPos -= 40
        
        let aneuploidyParams = [
            ("TOLERANCE_MULTIPLIER", "Tolerance Multiplier:", "", "Multiplier for target-specific standard deviation in classification"),
            ("LOWER_DEVIATION_TARGET", "Lower deviation target:", "", "Expected ratio for lower copy number deviation"),
            ("UPPER_DEVIATION_TARGET", "Upper deviation target:", "", "Expected ratio for upper copy number deviation")
        ]
        
        for (identifier, label, paramType, tooltip) in aneuploidyParams {
            let paramLabel = NSTextField(labelWithString: label)
            paramLabel.frame = NSRect(x: 40, y: yPos, width: 220, height: fieldHeight)
            addParameterTooltip(to: paramLabel, identifier: identifier)
            
            let paramField = NSTextField()
            paramField.identifier = NSUserInterfaceItemIdentifier(identifier)
            addParameterTooltip(to: paramField, identifier: identifier)
            // Special handling for dropdown and ratio parameters
            if identifier == "ENABLE_COPY_NUMBER_ANALYSIS" || identifier == "CLASSIFY_CNV_DEVIATIONS" {
                // Create dropdown for yes/no parameters
                paramField.removeFromSuperview()
                let dropdown = NSPopUpButton()
                dropdown.identifier = NSUserInterfaceItemIdentifier(identifier)
                dropdown.addItems(withTitles: ["Yes", "No"])
                
                // Set current value
                if let paramValue = parameters[identifier] as? Bool {
                    dropdown.selectItem(at: paramValue ? 0 : 1)
                } else if let paramValue = parameters[identifier] as? String {
                    dropdown.selectItem(at: paramValue.lowercased() == "yes" ? 0 : 1)
                } else {
                    dropdown.selectItem(at: 0) // Default to Yes
                }
                
                dropdown.frame = NSRect(x: 270, y: yPos, width: 80, height: fieldHeight)
                addParameterTooltip(to: dropdown, identifier: identifier)
                view.addSubview(dropdown)
                continue
            } else if identifier == "TOLERANCE_MULTIPLIER" {
                if let paramValue = parameters[identifier] {
                    paramField.stringValue = formatParamValue(paramValue)
                    print("🎯 Set field \(identifier) = \(paramValue)")
                } else {
                    paramField.stringValue = ""
                    print("⚪ Field \(identifier) has no parameter value, leaving empty")
                }
            } else if identifier == "LOWER_DEVIATION_TARGET" {
                // Check both new and old parameter names for backward compatibility
                if let targets = parameters["ANEUPLOIDY_TARGETS"] as? [String: Double],
                   let value = targets["low"] {
                    paramField.stringValue = String(value)
                    print("🎯 Set deviation field \(identifier) = \(value)")
                } else if let value = parameters["CNV_LOSS_RATIO"] {
                    paramField.stringValue = formatParamValue(value)
                    print("🎯 Set deviation field \(identifier) = \(value)")
                } else if let value = parameters["LOWER_DEVIATION_TARGET"] {
                    paramField.stringValue = formatParamValue(value)
                    print("🎯 Set deviation field \(identifier) = \(value)")
                } else {
                    paramField.stringValue = ""
                    print("⚪ Deviation field \(identifier) has no parameter value, leaving empty")
                }
            } else if identifier == "UPPER_DEVIATION_TARGET" {
                // Check both new and old parameter names for backward compatibility
                if let targets = parameters["ANEUPLOIDY_TARGETS"] as? [String: Double],
                   let value = targets["high"] {
                    paramField.stringValue = String(value)
                    print("🎯 Set deviation field \(identifier) = \(value)")
                } else if let value = parameters["CNV_GAIN_RATIO"] {
                    paramField.stringValue = formatParamValue(value)
                    print("🎯 Set deviation field \(identifier) = \(value)")
                } else if let value = parameters["UPPER_DEVIATION_TARGET"] {
                    paramField.stringValue = formatParamValue(value)
                    print("🎯 Set deviation field \(identifier) = \(value)")
                } else {
                    paramField.stringValue = ""
                    print("⚪ Deviation field \(identifier) has no parameter value, leaving empty")
                }
            } else if identifier == "CNV_LOSS_RATIO" {
                // Check both new and old parameter names for backward compatibility
                if let targets = parameters["ANEUPLOIDY_TARGETS"] as? [String: Double],
                   let value = targets["low"] {
                    paramField.stringValue = String(value)
                    print("🎯 Set CNV field \(identifier) = \(value)")
                } else if let value = parameters["CNV_LOSS_RATIO"] {
                    paramField.stringValue = formatParamValue(value)
                    print("🎯 Set CNV field \(identifier) = \(value)")
                } else {
                    paramField.stringValue = ""
                    print("⚪ CNV field \(identifier) has no parameter value, leaving empty")
                }
            } else if identifier == "CNV_GAIN_RATIO" {
                // Check both new and old parameter names for backward compatibility
                if let targets = parameters["ANEUPLOIDY_TARGETS"] as? [String: Double],
                   let value = targets["high"] {
                    paramField.stringValue = String(value)
                    print("🎯 Set CNV field \(identifier) = \(value)")
                } else if let value = parameters["CNV_GAIN_RATIO"] {
                    paramField.stringValue = formatParamValue(value)
                    print("🎯 Set CNV field \(identifier) = \(value)")
                } else {
                    paramField.stringValue = ""
                    print("⚪ CNV field \(identifier) has no parameter value, leaving empty")
                }
            } else if let paramValue = parameters[identifier] {
                paramField.stringValue = formatParamValue(paramValue)
                print("🎯 Set field \(identifier) = \(paramValue)")
            } else {
                paramField.stringValue = ""
                print("⚪ Field \(identifier) has no parameter value, leaving empty")
            }
            paramField.frame = NSRect(x: 270, y: yPos, width: 100, height: fieldHeight)
            paramField.toolTip = tooltip
            paramField.isEditable = true
            paramField.isSelectable = true
            paramField.isBordered = true
            paramField.bezelStyle = .roundedBezel
            
            view.addSubview(paramLabel)
            view.addSubview(paramField)
            yPos -= spacing
        }
        
        // Expected Copy Numbers Grid
        yPos -= 20
        let copyNumLabel = NSTextField(labelWithString: "Expected Copy Numbers by Chromosome")
        copyNumLabel.font = NSFont.boldSystemFont(ofSize: 14)
        copyNumLabel.frame = NSRect(x: 20, y: yPos, width: 300, height: 20)
        addParameterTooltip(to: copyNumLabel, identifier: "EXPECTED_COPY_NUMBERS")
        view.addSubview(copyNumLabel)
        yPos -= 40
        
        // Determine current chromosome count from existing data - check CHROMOSOME_COUNT parameter first
        var currentChromCount = 5 // Default
        if let chromCount = parameters["CHROMOSOME_COUNT"] as? Int {
            currentChromCount = chromCount
            print("🎯 Copy numbers view using CHROMOSOME_COUNT parameter: \(chromCount)")
        } else if let copyNumbers = parameters["EXPECTED_COPY_NUMBERS"] as? [String: Double] {
            let chromKeys = copyNumbers.keys.filter { $0.starts(with: "Chrom") }
            if !chromKeys.isEmpty {
                currentChromCount = chromKeys.count
                print("🎯 Copy numbers view inferred from copy numbers: \(chromKeys.count)")
            }
        } else if let centroids = parameters["EXPECTED_CENTROIDS"] as? [String: [Double]] {
            let chromKeys = centroids.keys.filter { $0.starts(with: "Chrom") }
            if !chromKeys.isEmpty {
                currentChromCount = chromKeys.count
                print("🎯 Copy numbers view inferred from centroids: \(chromKeys.count)")
            }
        }
        
        // Generate chromosome list dynamically
        var chromosomes: [String] = []
        for i in 1...currentChromCount {
            chromosomes.append("Chrom\(i)")
        }
        
        for (index, chrom) in chromosomes.enumerated() {
            let chromLabel = NSTextField(labelWithString: "Target \(index + 1):")
            chromLabel.frame = NSRect(x: 40, y: yPos, width: 80, height: fieldHeight)
            
            let copyNumField = NSTextField()
            copyNumField.identifier = NSUserInterfaceItemIdentifier("EXPECTED_COPY_NUMBERS_\(chrom)")
            addParameterTooltip(to: copyNumField, identifier: "EXPECTED_COPY_NUMBERS_\(chrom)")
            // Use parameter value if available, otherwise leave empty
            if let copyNumbers = parameters["EXPECTED_COPY_NUMBERS"] as? [String: Double],
               let value = copyNumbers[chrom] {
                copyNumField.stringValue = String(value)
                print("🎯 Set copy number field \(chrom) = \(value)")
            } else {
                copyNumField.stringValue = ""
                print("⚪ Copy number field \(chrom) has no parameter value, leaving empty")
            }
            copyNumField.frame = NSRect(x: 130, y: yPos, width: 80, height: fieldHeight)
            copyNumField.toolTip = "Expected copy number value for \(chrom)"
            copyNumField.isEditable = true
            copyNumField.isSelectable = true
            copyNumField.isBordered = true
            copyNumField.bezelStyle = .roundedBezel
            
            let stdDevLabel = NSTextField(labelWithString: "SD \(index + 1):")
            stdDevLabel.frame = NSRect(x: 430, y: yPos, width: 55, height: fieldHeight)  // Match update method spacing (490-60=430)
            stdDevLabel.alignment = .left  // Match update method alignment
            
            let stdDevField = NSTextField()
            stdDevField.identifier = NSUserInterfaceItemIdentifier("EXPECTED_STANDARD_DEVIATION_\(chrom)")
            addParameterTooltip(to: stdDevField, identifier: "EXPECTED_STANDARD_DEVIATION_\(chrom)")
            // Use parameter value if available, otherwise leave empty
            if let stdDevs = parameters["EXPECTED_STANDARD_DEVIATION"] as? [String: Double],
               let value = stdDevs[chrom] {
                stdDevField.stringValue = String(value)
                print("🎯 Set std dev field \(chrom) = \(value)")
            } else {
                stdDevField.stringValue = ""
                print("⚪ Std dev field \(chrom) has no parameter value, leaving empty")
            }
            stdDevField.frame = NSRect(x: 490, y: yPos, width: 80, height: fieldHeight)  // Match update method position
            stdDevField.toolTip = "Expected standard deviation for \(chrom)"
            stdDevField.isEditable = true
            stdDevField.isSelectable = true
            stdDevField.isBordered = true
            stdDevField.bezelStyle = .roundedBezel
            
            view.addSubview(chromLabel)
            view.addSubview(copyNumField)
            view.addSubview(stdDevLabel)
            view.addSubview(stdDevField)
            yPos -= spacing
        }
        
        // Ensure all elements are visible by adjusting if yPos went below safe margin
        // Automatic offset logic removed - use manual positioning like other parameter screens
        
        // Set proper view size with padding - ensure all content is visible
        let contentHeight = 480 - yPos + 40  // Total content height from top to bottom element
        let finalHeight = max(contentHeight, 500)  // Ensure sufficient minimum height
        print("📏 Copy Number view: final yPos = \(yPos), contentHeight = \(contentHeight), finalHeight = \(finalHeight)")
        view.frame = NSRect(x: 0, y: 0, width: 620, height: finalHeight)

        // Content alignment disabled - maintain manual positioning
        print("📐 Copy Number view: keeping manual title positioning (auto-alignment disabled)")
        
        // Setup scroll view properly
        // Remove explicit frame - let Auto Layout handle it
        scrollView.documentView = view
        scrollView.hasVerticalScroller = true
        scrollView.hasHorizontalScroller = false
        scrollView.autohidesScrollers = true
        scrollView.borderType = .noBorder
        
        // Ensure proper scrolling behavior
        scrollView.verticalScrollElasticity = .allowed
        scrollView.horizontalScrollElasticity = .none
        
        return scrollView
    }
    
    private func createVisualizationParametersView(parameters: [String: Any]) -> NSView {
        let scrollView = NSScrollView()
        let view = NSView()
        
        var yPos: CGFloat = 500
        let fieldHeight: CGFloat = 24
        let spacing: CGFloat = 30
        
        // Title
        let titleLabel = NSTextField(labelWithString: "Visualization Settings")
        titleLabel.font = NSFont.boldSystemFont(ofSize: 16)
        titleLabel.frame = NSRect(x: 20, y: yPos, width: 400, height: 20)
        view.addSubview(titleLabel)
        yPos -= 40
        
        // Instructions
        let instructionLabel = NSTextField(labelWithString: "Configure plot axis limits, grid settings, and output resolution.")
        instructionLabel.font = NSFont.systemFont(ofSize: 12)
        instructionLabel.textColor = .secondaryLabelColor
        instructionLabel.frame = NSRect(x: 40, y: yPos, width: 500, height: 16)
        view.addSubview(instructionLabel)
        yPos -= 40
        
        // Axis Settings
        let axisLabel = NSTextField(labelWithString: "Plot Axis Limits")
        axisLabel.font = NSFont.boldSystemFont(ofSize: 14)
        axisLabel.frame = NSRect(x: 20, y: yPos, width: 200, height: 20)
        view.addSubview(axisLabel)
        yPos -= 40
        
        let axisParams = [
            ("X_AXIS_MIN", "X-Axis Min:", "", "Minimum value for X-axis (HEX fluorescence)"),
            ("X_AXIS_MAX", "X-Axis Max:", "", "Maximum value for X-axis (HEX fluorescence)"),
            ("Y_AXIS_MIN", "Y-Axis Min:", "", "Minimum value for Y-axis (FAM fluorescence)"),
            ("Y_AXIS_MAX", "Y-Axis Max:", "", "Maximum value for Y-axis (FAM fluorescence)"),
            ("X_GRID_INTERVAL", "X-Grid Interval:", "", "Spacing between vertical grid lines"),
            ("Y_GRID_INTERVAL", "Y-Grid Interval:", "", "Spacing between horizontal grid lines")
        ]
        
        for (identifier, label, _, tooltip) in axisParams {
            let paramLabel = NSTextField(labelWithString: label)
            paramLabel.frame = NSRect(x: 40, y: yPos, width: 150, height: fieldHeight)
            addParameterTooltip(to: paramLabel, identifier: identifier)
            
            let paramField = NSTextField()
            paramField.identifier = NSUserInterfaceItemIdentifier(identifier)
            addParameterTooltip(to: paramField, identifier: identifier)
            // Use parameter value if available, otherwise leave empty
            if let paramValue = parameters[identifier] {
                paramField.stringValue = formatParamValue(paramValue)
                print("🎯 Set field \(identifier) = \(paramValue)")
            } else {
                paramField.stringValue = ""
                print("⚪ Field \(identifier) has no parameter value, leaving empty")
            }
            paramField.frame = NSRect(x: 200, y: yPos, width: 100, height: fieldHeight)
            paramField.toolTip = tooltip
            paramField.isEditable = true
            paramField.isSelectable = true
            paramField.isBordered = true
            paramField.bezelStyle = .roundedBezel
            
            view.addSubview(paramLabel)
            view.addSubview(paramField)
            yPos -= spacing
        }
        
        // DPI Settings
        yPos -= 20
        let dpiLabel = NSTextField(labelWithString: "Resolution")
        dpiLabel.font = NSFont.boldSystemFont(ofSize: 14)
        dpiLabel.frame = NSRect(x: 20, y: yPos, width: 200, height: 20)
        view.addSubview(dpiLabel)
        yPos -= 40
        
        let dpiParams = [
            ("INDIVIDUAL_PLOT_DPI", "Plot DPI:", "", "Resolution for individual well plots")
        ]
        
        for (identifier, label, _, tooltip) in dpiParams {
            let paramLabel = NSTextField(labelWithString: label)
            paramLabel.frame = NSRect(x: 40, y: yPos, width: 150, height: fieldHeight)
            addParameterTooltip(to: paramLabel, identifier: identifier)
            
            let paramField = NSTextField()
            paramField.identifier = NSUserInterfaceItemIdentifier(identifier)
            addParameterTooltip(to: paramField, identifier: identifier)
            // Use parameter value if available, otherwise leave empty
            if let paramValue = parameters[identifier] {
                paramField.stringValue = formatParamValue(paramValue)
                print("🎯 Set field \(identifier) = \(paramValue)")
            } else {
                paramField.stringValue = ""
                print("⚪ Field \(identifier) has no parameter value, leaving empty")
            }
            paramField.frame = NSRect(x: 200, y: yPos, width: 100, height: fieldHeight)
            paramField.toolTip = tooltip
            paramField.isEditable = true
            paramField.isSelectable = true
            paramField.isBordered = true
            paramField.bezelStyle = .roundedBezel
            
            view.addSubview(paramLabel)
            view.addSubview(paramField)
            yPos -= spacing
        }
        
        // Set proper view size with padding and top-align content to avoid empty space at top
        let contentHeight = 350 - yPos + 40
        let finalHeight = max(contentHeight, 400)  // Reduced minimum height to fit in window
        view.frame = NSRect(x: 0, y: 0, width: 620, height: finalHeight)

        let topMargin: CGFloat = 20
        var maxSubviewY: CGFloat = 0
        for subview in view.subviews { maxSubviewY = max(maxSubviewY, subview.frame.maxY) }
        if maxSubviewY < finalHeight - topMargin {
            let shift = (finalHeight - topMargin) - maxSubviewY
            for subview in view.subviews {
                var f = subview.frame
                f.origin.y += shift
                subview.frame = f
            }
            print("📐 Visualization view: shifted content up by \(shift)")
        }
        
        // Setup scroll view properly
        // Remove explicit frame - let Auto Layout handle it
        scrollView.documentView = view
        scrollView.hasVerticalScroller = true
        scrollView.hasHorizontalScroller = false
        scrollView.autohidesScrollers = true
        scrollView.borderType = .noBorder
        
        // Ensure proper scrolling behavior
        scrollView.verticalScrollElasticity = .allowed
        scrollView.horizontalScrollElasticity = .none
        
        return scrollView
    }
    
    private func createGeneralSettingsView(parameters: [String: Any]) -> NSView {
        let scrollView = NSScrollView()
        let view = NSView()
        
        var yPos: CGFloat = 500
        let fieldHeight: CGFloat = 24
        let spacing: CGFloat = 30
        
        // Title
        let titleLabel = NSTextField(labelWithString: "General Settings")
        titleLabel.font = NSFont.boldSystemFont(ofSize: 16)
        titleLabel.frame = NSRect(x: 20, y: yPos, width: 400, height: 20)
        view.addSubview(titleLabel)
        yPos -= 40
        
        // Instructions
        let instructionLabel = NSTextField(labelWithString: "Configure general application settings and analysis behavior.")
        instructionLabel.font = NSFont.systemFont(ofSize: 12)
        instructionLabel.textColor = .secondaryLabelColor
        instructionLabel.frame = NSRect(x: 40, y: yPos, width: 500, height: 16)
        view.addSubview(instructionLabel)
        yPos -= 40
        
        // Analysis Settings
        let analysisLabel = NSTextField(labelWithString: "Analysis Settings")
        analysisLabel.font = NSFont.boldSystemFont(ofSize: 14)
        analysisLabel.frame = NSRect(x: 20, y: yPos, width: 200, height: 20)
        view.addSubview(analysisLabel)
        yPos -= 40
        
        let analysisParams = [
            ("ENABLE_COPY_NUMBER_ANALYSIS", "Do copy number analysis?", "yes/no", "Enable or disable copy number analysis and buffer zone detection"),
            ("CLASSIFY_CNV_DEVIATIONS", "Classify copy number deviations?", "yes/no", "Enable or disable copy number deviation classification")
        ]
        
        for (identifier, label, paramType, tooltip) in analysisParams {
            let paramLabel = NSTextField(labelWithString: label)
            paramLabel.frame = NSRect(x: 40, y: yPos, width: 250, height: fieldHeight)
            addParameterTooltip(to: paramLabel, identifier: identifier)
            
            view.addSubview(paramLabel)
            
            // Create dropdown for yes/no parameters
            let dropdown = NSPopUpButton()
            dropdown.identifier = NSUserInterfaceItemIdentifier(identifier)
            dropdown.addItems(withTitles: ["Yes", "No"])
            
            // Set current value
            if let paramValue = parameters[identifier] as? Bool {
                dropdown.selectItem(at: paramValue ? 0 : 1)
            } else if let paramValue = parameters[identifier] as? String {
                dropdown.selectItem(at: paramValue.lowercased() == "yes" ? 0 : 1)
            } else {
                dropdown.selectItem(at: 0) // Default to Yes
            }
            
            dropdown.frame = NSRect(x: 300, y: yPos, width: 80, height: fieldHeight)
            addParameterTooltip(to: dropdown, identifier: identifier)
            view.addSubview(dropdown)
            
            yPos -= spacing
        }
        
        // Target Name Customization
        yPos -= 20
        let targetNamesLabel = NSTextField(labelWithString: "Target Names")
        targetNamesLabel.font = NSFont.boldSystemFont(ofSize: 14)
        targetNamesLabel.frame = NSRect(x: 20, y: yPos, width: 200, height: 20)
        view.addSubview(targetNamesLabel)
        yPos -= 40
        
        // Get current chromosome count to determine how many target name fields to show
        var currentChromCount = 5 // Default
        if let chromCount = parameters["CHROMOSOME_COUNT"] as? Int {
            currentChromCount = chromCount
        }
        
        // Create target name fields dynamically based on chromosome count
        for i in 1...currentChromCount {
            let targetLabel = NSTextField(labelWithString: "Target \(i):")
            targetLabel.frame = NSRect(x: 40, y: yPos, width: 120, height: fieldHeight)
            
            let targetField = NSTextField()
            targetField.identifier = NSUserInterfaceItemIdentifier("TARGET_NAME_\(i)")
            
            // Set current value or default
            if let targetNames = parameters["TARGET_NAMES"] as? [String: String],
               let name = targetNames["Target\(i)"] {
                targetField.stringValue = name
            } else {
                targetField.stringValue = "Target\(i)" // Default name
            }
            
            targetField.frame = NSRect(x: 170, y: yPos, width: 150, height: fieldHeight)
            targetField.toolTip = "Custom name for Target \(i) (leave empty for default)"
            targetField.isEditable = true
            targetField.isSelectable = true
            targetField.isBordered = true
            targetField.bezelStyle = .roundedBezel
            
            view.addSubview(targetLabel)
            view.addSubview(targetField)
            yPos -= spacing
        }
        
        // Set proper view size
        let contentHeight = 500 - yPos + 60
        let finalHeight = max(contentHeight, 400)
        view.frame = NSRect(x: 0, y: 0, width: 620, height: finalHeight)
        
        // Setup scroll view
        scrollView.documentView = view
        scrollView.hasVerticalScroller = true
        scrollView.hasHorizontalScroller = false
        scrollView.autohidesScrollers = true
        scrollView.borderType = .noBorder
        scrollView.verticalScrollElasticity = .allowed
        scrollView.horizontalScrollElasticity = .none
        
        return scrollView
    }
    
    // MARK: - Parameter Window Actions
    
    @objc private func closeWellParameterWindow() {
        currentWellWindow?.close()
        currentWellWindow = nil
        statusLabel.stringValue = "Well parameter editing cancelled"
    }
    
    @objc private func closeGlobalParameterWindow() {
        currentGlobalWindow?.close()
        currentGlobalWindow = nil
        statusLabel.stringValue = "Global parameter editing cancelled"
    }
    
    @objc private func restoreGlobalDefaults() {
        guard let window = currentGlobalWindow else { 
            print("❌ No current global window")
            return 
        }
        
        print("🔄 Starting global defaults restoration...")
        writeDebugLog("🔄 Starting global defaults restoration...")
        
        // Get default parameters
        let defaultParams = getDefaultParameters()
        let logMessage = "📋 Got \(defaultParams.count) default parameters: \(Array(defaultParams.keys.prefix(10)))"
        print(logMessage)
        writeDebugLog(logMessage)
        
        if defaultParams.isEmpty {
            let errorMsg = "❌ No default parameters loaded!"
            print(errorMsg)
            writeDebugLog(errorMsg)
            statusLabel.stringValue = "Failed to load default parameters"
            return
        }
        
        // Update all UI fields with default values
        restoreDefaultsInWindow(window, parameters: defaultParams)
        
        statusLabel.stringValue = "Global parameters restored to defaults"
        let successMsg = "✅ Global defaults restoration completed"
        print(successMsg)
        writeDebugLog(successMsg)
    }
    
    @objc private func restoreWellDefaults() {
        guard let window = currentWellWindow else { 
            print("❌ No current well window")
            return 
        }
        
        print("🔄 Starting well defaults restoration...")
        
        // Get default parameters
        let defaultParams = getDefaultParameters()
        print("📋 Got \(defaultParams.count) default parameters: \(Array(defaultParams.keys.prefix(10)))")
        
        if defaultParams.isEmpty {
            print("❌ No default parameters loaded!")
            statusLabel.stringValue = "Failed to load default parameters"
            return
        }
        
        // Update all UI fields with default values
        restoreDefaultsInWindow(window, parameters: defaultParams)
        
        statusLabel.stringValue = "Well parameters restored to defaults - Got \(defaultParams.count) params"
        print("✅ Well defaults restoration completed with \(defaultParams.count) parameters")
    }
    
    @objc private func resetWellParameters() {
        guard selectedWellIndex >= 0 && selectedWellIndex < wellData.count else { 
            print("❌ No valid well selected")
            return 
        }
        
        let well = wellData[selectedWellIndex]
        print("🔄 Resetting parameters for well \(well.well)")
        
        // Remove well-specific parameters so it falls back to global defaults
        if wellParametersMap[well.well] != nil {
            wellParametersMap.removeValue(forKey: well.well)
            print("✅ Removed well-specific parameters for \(well.well)")
            
            // Close the parameter window
            if let window = currentWellWindow {
                window.close()
                currentWellWindow = nil
            }
            
            statusLabel.stringValue = "Well \(well.well) reset to global parameters"
            
            // Regenerate the plot with global parameters
            if let folder = selectedFolderURL {
                let csvFiles = findCSVFiles(in: folder)
                if csvFiles.first(where: { $0.lastPathComponent.contains(well.well) }) != nil {
                    statusLabel.stringValue = "Regenerating plot for \(well.well) with global parameters..."
                    applyParametersAndRegeneratePlot(wellName: well.well, parameters: [:])
                }
            }
        } else {
            print("ℹ️ Well \(well.well) already using global parameters")
            statusLabel.stringValue = "Well \(well.well) already using global parameters"
        }
    }
    
    @objc private func saveWellParameters() {
        guard let window = currentWellWindow else { return }
        
        statusLabel.stringValue = "Saving well parameters and re-processing..."
        
        // Extract ALL parameters from the UI fields 
        let allParametersFromWindow = extractParametersFromWindow(window, isGlobal: false)
        
        // Get global parameters for comparison
        let globalParameters = loadGlobalParameters()
        
        // Only store parameters that are different from global defaults
        var changedParameters: [String: Any] = [:]
        
        // For single well editing, start with existing well-specific parameters to preserve previous changes not shown in current window
        // For multi-well editing, start fresh to avoid inheriting parameters from the first selected well
        if currentMultiEditWells.isEmpty && selectedWellIndex >= 0 && selectedWellIndex < wellData.count {
            let well = wellData[selectedWellIndex]
            if let existing = wellParametersMap[well.well] {
                changedParameters = existing
            }
        }
        
        // Compare window values with global defaults and only keep differences
        for (key, windowValue) in allParametersFromWindow {
            if let globalValue = globalParameters[key] {
                // Check if values are different (handle different types properly)
                let valuesAreDifferent = !areParameterValuesEqual(windowValue, globalValue)
                if valuesAreDifferent {
                    changedParameters[key] = windowValue
                    print("📝 Parameter \(key) differs from global: window=\(windowValue), global=\(globalValue)")
                } else {
                    // Value matches global default, remove from well-specific overrides if it exists
                    changedParameters.removeValue(forKey: key)
                    print("🔄 Parameter \(key) matches global default, removing override")
                }
            } else {
                // Parameter not in global defaults, keep it
                changedParameters[key] = windowValue
                print("➕ Parameter \(key) not in global defaults, keeping: \(windowValue)")
            }
        }
        
        // Validate the changed parameters
        if !changedParameters.isEmpty && !validateParameters(changedParameters) {
            statusLabel.stringValue = "Invalid parameter values detected"
            return
        }
        
        // Close window first
        closeWellParameterWindow()
        
        // Apply changed parameters to selected wells (handles both single and multi-well editing)
        let wellsToUpdate = currentMultiEditWells.isEmpty ? 
            (selectedWellIndex >= 0 && selectedWellIndex < wellData.count ? [wellData[selectedWellIndex].well] : []) : 
            currentMultiEditWells
        
        print("📝 Applying parameters to \(wellsToUpdate.count) wells: \(wellsToUpdate)")
        
        for wellName in wellsToUpdate {
            // Find the well index for this well name
            guard let wellIndex = wellData.firstIndex(where: { $0.well == wellName }) else {
                print("⚠️ Could not find well index for \(wellName)")
                continue
            }
            
            if changedParameters.isEmpty {
                // No parameters differ from global defaults, remove well from map
                wellParametersMap.removeValue(forKey: wellName)
                print("✅ No parameter differences found, removed well \(wellName) from custom parameters")
                
                // Mark as not edited since it now uses global parameters
                let current = wellData[wellIndex]
                wellData[wellIndex] = WellData(well: current.well,
                                             sampleName: current.sampleName,
                                             dropletCount: current.dropletCount,
                                             hasData: current.hasData,
                                             status: current.status,
                                             isEdited: false)
            } else {
                // Merge changed parameters with existing well-specific parameters
                var wellSpecificParams = wellParametersMap[wellName] ?? [:]
                
                // Apply the changes from this edit session
                for (key, value) in changedParameters {
                    wellSpecificParams[key] = value
                }
                
                // Remove any parameters that now match global defaults (cleanup)
                let globalParameters = loadGlobalParameters()
                var paramsToRemove: [String] = []
                for (key, value) in wellSpecificParams {
                    if let globalValue = globalParameters[key] {
                        if areParameterValuesEqual(value, globalValue) {
                            paramsToRemove.append(key)
                            print("🔄 Parameter \(key) now matches global default, removing from well \(wellName)")
                        }
                    }
                }
                
                for key in paramsToRemove {
                    wellSpecificParams.removeValue(forKey: key)
                }
                
                // Store the merged parameters and mark well accordingly
                let current = wellData[wellIndex]
                if wellSpecificParams.isEmpty {
                    wellParametersMap.removeValue(forKey: wellName)
                    print("✅ All parameters match global defaults, removed well \(wellName) from custom parameters")
                    
                    // Mark as not edited since it now uses only global parameters
                    wellData[wellIndex] = WellData(well: current.well,
                                                 sampleName: current.sampleName,
                                                 dropletCount: current.dropletCount,
                                                 hasData: current.hasData,
                                                 status: current.status,
                                                 isEdited: false)
                } else {
                    wellParametersMap[wellName] = wellSpecificParams
                    print("✅ Merged \(changedParameters.count) changed parameters with existing parameters for well \(wellName). Total: \(wellSpecificParams.count) custom parameters: \(wellSpecificParams.keys.sorted())")
                    
                    // Mark as edited since it has custom parameters
                    wellData[wellIndex] = WellData(well: current.well,
                                                 sampleName: current.sampleName,
                                                 dropletCount: current.dropletCount,
                                                 hasData: current.hasData,
                                                 status: current.status,
                                                 isEdited: true)
                }
            }
        }
        
        print("   wellParametersMap now has \(wellParametersMap.count) entries: \(Array(wellParametersMap.keys).sorted())")
        applyFilters()
        
        // Apply parameters and re-process all updated wells
        // For processing, we need to merge changed parameters with global defaults
        var parametersForProcessing = globalParameters
        for (key, value) in changedParameters {
            parametersForProcessing[key] = value
        }
        
        for wellName in wellsToUpdate {
            applyParametersAndRegeneratePlot(wellName: wellName, parameters: parametersForProcessing)
        }
        
        // Clear the multi-edit array after saving
        currentMultiEditWells.removeAll()
    }
    
    @objc private func saveGlobalParameters() {
        guard let window = currentGlobalWindow else { return }
        
        // Extract parameters from the UI fields
        let parameters = extractParametersFromWindow(window, isGlobal: true)
        
        if parameters.isEmpty {
            statusLabel.stringValue = "Failed to extract parameters"
            return
        }
        
        // Validate parameters BEFORE showing processing indicator
        print("🔍 Validating extracted global parameters...")
        guard validateParameters(parameters) else {
            print("❌ Global parameter validation failed")
            statusLabel.stringValue = "Invalid parameter values detected"
            return
        }
        print("✅ Global parameter validation passed")
        
        // Only show processing indicator after validation passes
        showProcessingIndicator("Saving global parameters and re-processing all wells...")
        
        // Save parameters to file for persistence
        saveParametersToFile(parameters)
        
        // Close window first
        closeGlobalParameterWindow()
        
        // Apply parameters and re-process all wells
        if selectedFolderURL != nil {
            applyGlobalParametersAndReanalyze(parameters: parameters)
        }
    }
    
    // Helper function to compare parameter values of different types
    private func areParameterValuesEqual(_ value1: Any, _ value2: Any) -> Bool {
        // Handle different types of parameter values
        if let dict1 = value1 as? [String: Any], let dict2 = value2 as? [String: Any] {
            // Compare dictionaries (like EXPECTED_CENTROIDS, EXPECTED_COPY_NUMBERS)
            if dict1.count != dict2.count { return false }
            for (key, val1) in dict1 {
                guard let val2 = dict2[key] else { return false }
                if !areParameterValuesEqual(val1, val2) { return false }
            }
            return true
        } else if let arr1 = value1 as? [Double], let arr2 = value2 as? [Double] {
            // Compare arrays of doubles
            return arr1.count == arr2.count && zip(arr1, arr2).allSatisfy { abs($0 - $1) < 1e-10 }
        } else if let num1 = value1 as? NSNumber, let num2 = value2 as? NSNumber {
            // Compare numbers (Int, Double, etc.)
            return num1.isEqual(to: num2)
        } else if let int1 = value1 as? Int, let int2 = value2 as? Int {
            return int1 == int2
        } else if let double1 = value1 as? Double, let double2 = value2 as? Double {
            return abs(double1 - double2) < 1e-10
        } else if let str1 = value1 as? String, let str2 = value2 as? String {
            return str1 == str2
        } else {
            // Fallback: convert to string and compare
            return "\(value1)" == "\(value2)"
        }
    }
    
    private func extractParametersFromWindow(_ window: NSWindow, isGlobal: Bool) -> [String: Any] {
        var parameters: [String: Any] = [:]
        print("🔍 Extracting \(isGlobal ? "global" : "well") parameters from window...")
        
        // Find all text fields and popups with identifiers
        var foundFields = 0
        func extractFromView(_ view: NSView) {
            for subview in view.subviews {
                if let textField = subview as? NSTextField,
                   let identifier = textField.identifier?.rawValue,
                   !identifier.isEmpty {
                    foundFields += 1
                    print("   Found field: \(identifier) = '\(textField.stringValue)'")
                    
                    // Handle different parameter types
                    if identifier.hasPrefix("EXPECTED_CENTROIDS_") {
                        let target = String(identifier.dropFirst("EXPECTED_CENTROIDS_".count))
                        let trimmedValue = textField.stringValue.trimmingCharacters(in: .whitespacesAndNewlines)
                        if trimmedValue.isEmpty {
                            // Store as empty string to detect missing required fields
                            parameters[identifier] = ""
                        } else {
                            let coordinates = textField.stringValue.components(separatedBy: ",").compactMap { Double($0.trimmingCharacters(in: .whitespaces)) }
                            if coordinates.count == 2 {
                                if parameters["EXPECTED_CENTROIDS"] == nil {
                                    parameters["EXPECTED_CENTROIDS"] = [String: [Double]]()
                                }
                                var centroids = parameters["EXPECTED_CENTROIDS"] as! [String: [Double]]
                                centroids[target] = coordinates
                                parameters["EXPECTED_CENTROIDS"] = centroids
                            } else {
                                // Store as invalid string for validation
                                parameters[identifier] = trimmedValue
                            }
                        }
                    } else if identifier.hasPrefix("EXPECTED_COPY_NUMBERS_") {
                        let chrom = String(identifier.dropFirst("EXPECTED_COPY_NUMBERS_".count))
                        let trimmedValue = textField.stringValue.trimmingCharacters(in: .whitespacesAndNewlines)
                        if trimmedValue.isEmpty {
                            // Store as empty string to detect missing required fields
                            parameters[identifier] = ""
                        } else if let value = Double(trimmedValue) {
                            if parameters["EXPECTED_COPY_NUMBERS"] == nil {
                                parameters["EXPECTED_COPY_NUMBERS"] = [String: Double]()
                            }
                            var copyNumbers = parameters["EXPECTED_COPY_NUMBERS"] as! [String: Double]
                            copyNumbers[chrom] = value
                            parameters["EXPECTED_COPY_NUMBERS"] = copyNumbers
                            // Also store individual parameter for consistency
                            parameters[identifier] = value
                        } else {
                            // Store as invalid string for validation
                            parameters[identifier] = trimmedValue
                        }
                    } else if identifier.hasPrefix("EXPECTED_STANDARD_DEVIATION_") {
                        let chrom = String(identifier.dropFirst("EXPECTED_STANDARD_DEVIATION_".count))
                        let trimmedValue = textField.stringValue.trimmingCharacters(in: .whitespacesAndNewlines)
                        if trimmedValue.isEmpty {
                            // Store as empty string to detect missing required fields
                            parameters[identifier] = ""
                        } else if let value = Double(trimmedValue) {
                            if parameters["EXPECTED_STANDARD_DEVIATION"] == nil {
                                parameters["EXPECTED_STANDARD_DEVIATION"] = [String: Double]()
                            }
                            var stdDevs = parameters["EXPECTED_STANDARD_DEVIATION"] as! [String: Double]
                            stdDevs[chrom] = value
                            parameters["EXPECTED_STANDARD_DEVIATION"] = stdDevs
                            // Also store individual parameter for consistency
                            parameters[identifier] = value
                        } else {
                            // Store as invalid string for validation
                            parameters[identifier] = trimmedValue
                        }
                    } else if identifier.hasPrefix("TARGET_NAME_") {
                        // Extract target name
                        let targetIndex = String(identifier.dropFirst("TARGET_NAME_".count))
                        let targetKey = "Target\(targetIndex)"
                        
                        // Initialize TARGET_NAMES dictionary if needed
                        if parameters["TARGET_NAMES"] == nil {
                            parameters["TARGET_NAMES"] = [String: String]()
                        }
                        var targetNames = parameters["TARGET_NAMES"] as! [String: String]
                        
                        let trimmedValue = textField.stringValue.trimmingCharacters(in: .whitespacesAndNewlines)
                        // Store empty string if field is empty (Python will handle default)
                        targetNames[targetKey] = trimmedValue
                        parameters["TARGET_NAMES"] = targetNames
                        print("🔍 TARGET_NAMES set in parameters: \(targetNames)")
                    } else if identifier == "LOWER_DEVIATION_TARGET" || identifier == "UPPER_DEVIATION_TARGET" || identifier == "COPY_NUMBER_MULTIPLIER" {
                        if let value = Double(textField.stringValue) {
                            // Store in new format
                            parameters[identifier] = value
                            
                            // Also maintain old formats for backward compatibility
                            parameters[identifier == "LOWER_DEVIATION_TARGET" ? "CNV_LOSS_RATIO" : "CNV_GAIN_RATIO"] = value
                            
                            if parameters["ANEUPLOIDY_TARGETS"] == nil {
                                parameters["ANEUPLOIDY_TARGETS"] = [String: Double]()
                            }
                            var targets = parameters["ANEUPLOIDY_TARGETS"] as! [String: Double]
                            let key = identifier == "LOWER_DEVIATION_TARGET" ? "low" : "high"
                            targets[key] = value
                            parameters["ANEUPLOIDY_TARGETS"] = targets
                        }
                    } else if identifier == "CNV_LOSS_RATIO" || identifier == "CNV_GAIN_RATIO" {
                        if let value = Double(textField.stringValue) {
                            // Store both in new format and maintain backward compatibility
                            parameters[identifier] = value
                            
                            // Also maintain old ANEUPLOIDY_TARGETS format for backward compatibility
                            if parameters["ANEUPLOIDY_TARGETS"] == nil {
                                parameters["ANEUPLOIDY_TARGETS"] = [String: Double]()
                            }
                            var targets = parameters["ANEUPLOIDY_TARGETS"] as! [String: Double]
                            let key = identifier == "CNV_LOSS_RATIO" ? "low" : "high"
                            targets[key] = value
                            parameters["ANEUPLOIDY_TARGETS"] = targets
                        }
                    } else {
                        // Handle other numeric parameters - check for empty values
                        let trimmedValue = textField.stringValue.trimmingCharacters(in: .whitespacesAndNewlines)
                        if trimmedValue.isEmpty {
                            parameters[identifier] = ""
                            print("⚠️ Extracted empty \(identifier)")
                        } else if let intValue = Int(trimmedValue) {
                            parameters[identifier] = intValue
                            print("✅ Extracted \(identifier) = \(intValue) (Int)")
                        } else if let doubleValue = Double(trimmedValue) {
                            parameters[identifier] = doubleValue
                            print("✅ Extracted \(identifier) = \(doubleValue) (Double)")
                        } else {
                            parameters[identifier] = trimmedValue
                            print("✅ Extracted \(identifier) = \(trimmedValue) (String)")
                        }
                    }
                } else if let popup = subview as? NSPopUpButton,
                          let identifier = popup.identifier?.rawValue,
                          !identifier.isEmpty {
                    if identifier == "CHROMOSOME_COUNT" {
                        // Convert chromosome count to integer
                        if let title = popup.titleOfSelectedItem, let count = Int(title) {
                            parameters[identifier] = count
                        }
                    } else if identifier == "ENABLE_COPY_NUMBER_ANALYSIS" || identifier == "CLASSIFY_CNV_DEVIATIONS" {
                        // Handle yes/no dropdown values as boolean
                        let selectedTitle = popup.titleOfSelectedItem ?? "Yes"
                        parameters[identifier] = selectedTitle.lowercased() == "yes"
                        print("✅ Extracted dropdown \(identifier) = \(selectedTitle) -> \(selectedTitle.lowercased() == "yes")")
                    } else {
                        parameters[identifier] = popup.titleOfSelectedItem ?? ""
                    }
                }
                
                // Recursively search subviews
                extractFromView(subview)
            }
        }
        
        // Extract from the currently visible hierarchy first
        if let content = window.contentView { extractFromView(content) }
        // Also extract from all tab views to include fields from non-visible tabs
        if let tabView = currentParamTabView {
            for item in tabView.tabViewItems {
                if let v = item.view { extractFromView(v) }
            }
        }
        
        // Ensure all chromosome dictionaries are properly formed if any individual fields exist
        let hasCopyNumberFields = parameters.keys.contains { $0.hasPrefix("EXPECTED_COPY_NUMBERS_") }
        let hasStdDevFields = parameters.keys.contains { $0.hasPrefix("EXPECTED_STANDARD_DEVIATION_") }
        
        if hasCopyNumberFields && parameters["EXPECTED_COPY_NUMBERS"] == nil {
            parameters["EXPECTED_COPY_NUMBERS"] = [String: Double]()
        }
        if hasStdDevFields && parameters["EXPECTED_STANDARD_DEVIATION"] == nil {
            parameters["EXPECTED_STANDARD_DEVIATION"] = [String: Double]()
        }
        
        // Ensure TARGET_NAMES is always present, even if empty
        if parameters["TARGET_NAMES"] == nil {
            parameters["TARGET_NAMES"] = [String: String]()
            print("🔍 Initialized empty TARGET_NAMES dictionary")
        }
        
        print("   Found \(foundFields) UI fields total")
        print("   Extracted \(parameters.count) parameters: \(parameters.keys.sorted())")
        if let targetNames = parameters["TARGET_NAMES"] {
            print("🔍 Final TARGET_NAMES in extracted parameters: \(targetNames)")
        } else {
            print("🔍 TARGET_NAMES not found in extracted parameters")
        }
        return parameters
    }
    
    private func validateParameters(_ parameters: [String: Any]) -> Bool {
        // Validate only the parameters that are present, not all required parameters
        // This allows partial parameter sets from different tabs
        
        // Check for empty required string parameters
        let stringParams = ["HDBSCAN_METRIC", "HDBSCAN_CLUSTER_SELECTION_METHOD"]
        for param in stringParams {
            if let value = parameters[param] as? String, value.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
                showError("\(param.replacingOccurrences(of: "_", with: " ").capitalized) cannot be empty")
                return false
            }
        }
        
        // Check for empty numeric parameters (converted from empty strings)
        let requiredNumericFields = [
            "HDBSCAN_MIN_CLUSTER_SIZE", "HDBSCAN_MIN_SAMPLES", "HDBSCAN_EPSILON", 
            "MIN_POINTS_FOR_CLUSTERING", "BASE_TARGET_TOLERANCE", 
            "TOLERANCE_MULTIPLIER"
        ]
        
        for field in requiredNumericFields {
            if parameters[field] != nil {
                // Parameter is present, check if it's valid
                if let strValue = parameters[field] as? String, strValue.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
                    showError("\(field.replacingOccurrences(of: "_", with: " ").capitalized) cannot be empty")
                    return false
                }
                // Also check if numeric conversion failed (resulting in nil)
                if parameters[field] == nil || 
                   (parameters[field] as? Int == nil && parameters[field] as? Double == nil && parameters[field] as? String != nil) {
                    showError("\(field.replacingOccurrences(of: "_", with: " ").capitalized) must be a valid number")
                    return false
                }
            }
        }
        
        // Check for empty dynamic centroid fields and ensure complete chromosome configurations
        var configuredChroms = Set<String>()
        var chromsWithCentroids = Set<String>()
        var chromsWithCopyNumbers = Set<String>()
        var chromsWithStdDevs = Set<String>()
        
        // First pass: identify all configured chromosomes and check for empty fields
        for (key, value) in parameters {
            if key.hasPrefix("EXPECTED_CENTROIDS_") {
                let targetName = String(key.dropFirst("EXPECTED_CENTROIDS_".count))
                if targetName.starts(with: "Chrom") {
                    configuredChroms.insert(targetName)
                    if let stringValue = value as? String, stringValue.isEmpty {
                        let displayName = targetName.replacingOccurrences(of: "Chrom", with: "Target ")
                        showError("Expected centroids for \(displayName) cannot be empty")
                        return false
                    } else {
                        chromsWithCentroids.insert(targetName)
                    }
                }
            }
            if key.hasPrefix("EXPECTED_COPY_NUMBERS_") {
                let chromName = String(key.dropFirst("EXPECTED_COPY_NUMBERS_".count))
                configuredChroms.insert(chromName)
                if let stringValue = value as? String, stringValue.isEmpty {
                    let displayName = chromName.replacingOccurrences(of: "Chrom", with: "Target ")
                    showError("Expected copy number for \(displayName) cannot be empty")
                    return false
                } else {
                    chromsWithCopyNumbers.insert(chromName)
                }
            }
            if key.hasPrefix("EXPECTED_STANDARD_DEVIATION_") {
                let chromName = String(key.dropFirst("EXPECTED_STANDARD_DEVIATION_".count))
                configuredChroms.insert(chromName)
                if let stringValue = value as? String, stringValue.isEmpty {
                    let displayName = chromName.replacingOccurrences(of: "Chrom", with: "Target ")
                    showError("Standard deviation for \(displayName) cannot be empty")
                    return false
                } else {
                    chromsWithStdDevs.insert(chromName)
                }
            }
        }
        
        // Also check chromosomes in the combined dictionaries
        if let centroids = parameters["EXPECTED_CENTROIDS"] as? [String: [Double]] {
            for target in centroids.keys {
                if target.starts(with: "Chrom") {
                    configuredChroms.insert(target)
                    chromsWithCentroids.insert(target)
                }
            }
        }
        if let copyNumbers = parameters["EXPECTED_COPY_NUMBERS"] as? [String: Double] {
            for chrom in copyNumbers.keys {
                configuredChroms.insert(chrom)
                chromsWithCopyNumbers.insert(chrom)
            }
        }
        if let stdDevs = parameters["EXPECTED_STANDARD_DEVIATION"] as? [String: Double] {
            for chrom in stdDevs.keys {
                configuredChroms.insert(chrom)
                chromsWithStdDevs.insert(chrom)
            }
        }
        
        // Second pass: ensure all configured chromosomes have complete configuration
        // (either from well-specific parameters or global defaults)
        let globalDefaults = loadGlobalParameters()
        
        for chrom in configuredChroms {
            let displayName = chrom.replacingOccurrences(of: "Chrom", with: "Target ")
            
            // Check if centroids are available (well-specific OR global default)
            let hasWellCentroids = chromsWithCentroids.contains(chrom)
            let hasGlobalCentroids = (globalDefaults["EXPECTED_CENTROIDS"] as? [String: [Double]])?[chrom] != nil
            if !hasWellCentroids && !hasGlobalCentroids {
                showError("Missing centroids for \(displayName) - no well-specific or global default available")
                return false
            }
            
            // Check if copy numbers are available (well-specific OR global default)
            let hasWellCopyNumbers = chromsWithCopyNumbers.contains(chrom)
            let hasGlobalCopyNumbers = (globalDefaults["EXPECTED_COPY_NUMBERS"] as? [String: Double])?[chrom] != nil
            if !hasWellCopyNumbers && !hasGlobalCopyNumbers {
                showError("Missing copy number for \(displayName) - no well-specific or global default available")
                return false
            }
            
            // Check if standard deviations are available (well-specific OR global default)
            let hasWellStdDevs = chromsWithStdDevs.contains(chrom)
            let hasGlobalStdDevs = (globalDefaults["EXPECTED_STANDARD_DEVIATION"] as? [String: Double])?[chrom] != nil
            if !hasWellStdDevs && !hasGlobalStdDevs {
                showError("Missing standard deviation for \(displayName) - no well-specific or global default available")
                return false
            }
        }
        
        // Validate copy number and centroid data for completeness
        if let centroids = parameters["EXPECTED_CENTROIDS"] as? [String: [Double]] {
            for (target, coords) in centroids {
                if coords.count < 2 {
                    showError("Expected centroids for \(target) must have both HEX and FAM coordinates")
                    return false
                }
            }
        }
        
        if let copyNumbers = parameters["EXPECTED_COPY_NUMBERS"] as? [String: Double] {
            for (target, value) in copyNumbers {
                if value <= 0 {
                    showError("Expected copy number for \(target) must be greater than 0")
                    return false
                }
            }
        }
        
        // Validate HDBSCAN parameters if present
        if let minClusterSize = parameters["HDBSCAN_MIN_CLUSTER_SIZE"] as? Int {
            if minClusterSize < 1 {
                showError("Min Cluster Size must be at least 1")
                return false
            }
        }
        
        if let minSamples = parameters["HDBSCAN_MIN_SAMPLES"] as? Int {
            if minSamples < 1 {
                showError("Min Samples must be at least 1")
                return false
            }
        }
        
        if let epsilon = parameters["HDBSCAN_EPSILON"] as? Double {
            if epsilon <= 0 {
                showError("Epsilon must be greater than 0")
                return false
            }
        }
        
        if let minPoints = parameters["MIN_POINTS_FOR_CLUSTERING"] as? Int {
            if minPoints < 1 {
                showError("Min Points for Clustering must be at least 1")
                return false
            }
        }
        
        // Validate tolerance parameters if present
        if let tolerance = parameters["BASE_TARGET_TOLERANCE"] as? Int {
            if tolerance < 1 {
                showError("Target Tolerance must be at least 1")
                return false
            }
        }
        
        
        // Validate deviation targets if present
        if let lowerTarget = parameters["LOWER_DEVIATION_TARGET"] as? Double {
            if lowerTarget < 0.1 || lowerTarget > 1.0 {
                showError("Lower deviation target must be between 0.1 and 1.0")
                return false
            }
        }
        if let upperTarget = parameters["UPPER_DEVIATION_TARGET"] as? Double {
            if upperTarget < 1.0 || upperTarget > 2.0 {
                showError("Upper deviation target must be between 1.0 and 2.0")
                return false
            }
        }
        
        // Also validate CNV ratios for backward compatibility
        if let cnvLoss = parameters["CNV_LOSS_RATIO"] as? Double {
            if cnvLoss < 0.1 || cnvLoss > 1.0 {
                showError("Lower deviation target must be between 0.1 and 1.0")
                return false
            }
        }
        if let cnvGain = parameters["CNV_GAIN_RATIO"] as? Double {
            if cnvGain < 1.0 || cnvGain > 2.0 {
                showError("Upper deviation target must be between 1.0 and 2.0")
                return false
            }
        }
        
        // Also validate old aneuploidy targets format for backward compatibility
        if let aneuploidyTargets = parameters["ANEUPLOIDY_TARGETS"] as? [String: Double] {
            if let low = aneuploidyTargets["low"], (low < 0.1 || low > 1.0) {
                showError("CNV Loss Ratio must be between 0.1 and 1.0")
                return false
            }
            if let high = aneuploidyTargets["high"], (high < 1.0 || high > 2.0) {
                showError("CNV Gain Ratio must be between 1.0 and 2.0")
                return false
            }
        }
        
        return true
    }
    
    private func saveParametersToFile(_ parameters: [String: Any]) {
        let homeDir = FileManager.default.homeDirectoryForCurrentUser
        let ddquintDir = homeDir.appendingPathComponent(".ddQuint")
        let parametersFile = ddquintDir.appendingPathComponent("parameters.json")
        
        print("💾 Saving global parameters:")
        print("   New/changed parameters: \(parameters.count) - \(parameters.keys.sorted())")
        print("   Target dir: \(ddquintDir.path)")
        print("   Target file: \(parametersFile.path)")
        
        do {
            // Create directory if it doesn't exist
            let dirExists = FileManager.default.fileExists(atPath: ddquintDir.path)
            print("   Directory exists: \(dirExists)")
            
            if !dirExists {
                try FileManager.default.createDirectory(at: ddquintDir, withIntermediateDirectories: true)
                print("   ✅ Created directory: \(ddquintDir.path)")
            }
            
            // Load existing parameters first
            var mergedParameters: [String: Any] = [:]
            if FileManager.default.fileExists(atPath: parametersFile.path) {
                let existingData = try Data(contentsOf: parametersFile)
                if let existing = try JSONSerialization.jsonObject(with: existingData) as? [String: Any] {
                    mergedParameters = existing
                    print("   📂 Loaded \(existing.count) existing parameters")
                } else {
                    print("   ⚠️ Could not parse existing parameters, starting fresh")
                }
            } else {
                print("   📝 No existing parameters file, creating new one")
            }
            
            // Merge new parameters with existing ones
            for (key, value) in parameters {
                mergedParameters[key] = value
                print("   🔄 Updated parameter: \(key)")
            }
            
            print("   💾 Final parameter count: \(mergedParameters.count)")
            
            // Save merged parameters as JSON
            let jsonData = try JSONSerialization.data(withJSONObject: mergedParameters, options: .prettyPrinted)
            print("   JSON data size: \(jsonData.count) bytes")
            
            try jsonData.write(to: parametersFile)
            
            // Verify the file was written
            let fileExists = FileManager.default.fileExists(atPath: parametersFile.path)
            print("   ✅ File written successfully, exists: \(fileExists)")
            
        } catch {
            print("❌ Failed to save parameters: \(error)")
            showError("Failed to save parameters: \(error.localizedDescription)")
        }
    }
    
    
    
    private func getDefaultParameters() -> [String: Any] {
        print("📋 Loading default parameters from config.py")
        
        // Use Python to extract default values from config.py
        let task = Process()
        task.launchPath = "/usr/bin/python3"
        task.arguments = ["-c", """
import sys
import os
import json
import re

# Hardcoded default values from config.py to avoid import issues
# These values are directly extracted from the Config class definition
defaults = {
    'BASE_TARGET_TOLERANCE': 750,
    'HDBSCAN_MIN_CLUSTER_SIZE': 4,
    'HDBSCAN_MIN_SAMPLES': 70,
    'HDBSCAN_EPSILON': 0.06,
    'HDBSCAN_METRIC': 'euclidean',
    'HDBSCAN_CLUSTER_SELECTION_METHOD': 'eom',
    'MIN_POINTS_FOR_CLUSTERING': 50,
    'MIN_USABLE_DROPLETS': 3000,
    'COPY_NUMBER_MEDIAN_DEVIATION_THRESHOLD': 0.15,
    'TOLERANCE_MULTIPLIER': 3,
    'CHROMOSOME_COUNT': 5,
    'EXPECTED_CENTROIDS': {
        'Negative': [1000, 900],
        'Chrom1': [1000, 2300],
        'Chrom2': [1800, 2200],
        'Chrom3': [2400, 1750],
        'Chrom4': [3100, 1300],
        'Chrom5': [3500, 900]
    },
    'EXPECTED_COPY_NUMBERS': {
        'Chrom1': 0.9716,
        'Chrom2': 1.0052,
        'Chrom3': 1.0278,
        'Chrom4': 0.9912,
        'Chrom5': 1.0035
    },
    'EXPECTED_STANDARD_DEVIATION': {
        'Chrom1': 0.0312,
        'Chrom2': 0.0241,
        'Chrom3': 0.0290,
        'Chrom4': 0.0242,
        'Chrom5': 0.0230
    },
    'ENABLE_COPY_NUMBER_ANALYSIS': True,
    'CLASSIFY_CNV_DEVIATIONS': True,
    'USE_PLOIDY_TERMINOLOGY': False,
    'LOWER_DEVIATION_TARGET': 0.75,
    'UPPER_DEVIATION_TARGET': 1.25,
    'CNV_LOSS_RATIO': 0.75,
    'CNV_GAIN_RATIO': 1.25,
    'ANEUPLOIDY_TARGETS': {
        'low': 0.75,
        'high': 1.25
    },
    'X_AXIS_MIN': 0,
    'X_AXIS_MAX': 3000,
    'Y_AXIS_MIN': 0,
    'Y_AXIS_MAX': 5000,
    'X_GRID_INTERVAL': 500,
    'Y_GRID_INTERVAL': 1000,
    'INDIVIDUAL_PLOT_DPI': 300,
    'PLACEHOLDER_PLOT_DPI': 150,
    'COMPOSITE_FIGURE_SIZE': [16, 11],
    'INDIVIDUAL_FIGURE_SIZE': [6, 5],
    'COMPOSITE_PLOT_SIZE': [5, 5]
}

print(json.dumps(defaults))
"""]
        
        let pipe = Pipe()
        let errorPipe = Pipe()
        task.standardOutput = pipe
        task.standardError = errorPipe
        
        do {
            try task.run()
            task.waitUntilExit()
            
            let data = pipe.fileHandleForReading.readDataToEndOfFile()
            let errorData = errorPipe.fileHandleForReading.readDataToEndOfFile()
            print("📋 Python script executed, got \(data.count) bytes of output, \(errorData.count) bytes of error")
            
            // Check for errors first
            if errorData.count > 0, let errorOutput = String(data: errorData, encoding: .utf8) {
                print("❌ Python errors: \(errorOutput)")
            }
            
            if let output = String(data: data, encoding: .utf8) {
                print("📋 Python output: \(output.prefix(200))...")
                
                if let jsonData = output.data(using: .utf8),
                   let parameters = try JSONSerialization.jsonObject(with: jsonData) as? [String: Any] {
                    print("📋 Successfully loaded \(parameters.count) default parameters from config.py")
                    print("📋 Sample keys: \(Array(parameters.keys.prefix(5)))")
                    return parameters
                } else {
                    print("❌ Failed to parse JSON from Python output")
                }
            } else {
                print("❌ Failed to decode Python output as UTF-8")
            }
        } catch {
            print("❌ Failed to load defaults from config.py: \(error)")
        }
        
        print("⚠️ Fallback: Using empty defaults - all values should come from parameters.json")
        return [:]
    }
    
    private func restoreDefaultsInWindow(_ window: NSWindow, parameters: [String: Any]) {
        print("🔧 Restoring parameters to window with \(parameters.count) parameters: \(parameters.keys.sorted())")
        
        var restoredFields = 0
        var totalFields = 0
        let defaultChromCount = 5 // Default chromosome count
        
        // Get default chromosome count from parameters (fallback to 5)
        let targetChromCount = parameters["CHROMOSOME_COUNT"] as? Int ?? defaultChromCount
        
        print("🔧 Restoring to chromosome count: \(targetChromCount)")
        
        // Simple approach: Just restore values to all fields that exist, and trigger a chromosome count change
        func restoreAllFields(_ view: NSView) {
            for subview in view.subviews {
                if let textField = subview as? NSTextField,
                   let identifier = textField.identifier?.rawValue,
                   !identifier.isEmpty {
                    totalFields += 1
                    
                    // Handle different parameter types
                    if identifier.hasPrefix("EXPECTED_CENTROIDS_") {
                        let target = String(identifier.dropFirst("EXPECTED_CENTROIDS_".count))
                        if let centroids = parameters["EXPECTED_CENTROIDS"] as? [String: [Double]],
                           let coords = centroids[target], coords.count >= 2 {
                            textField.stringValue = "\(Int(coords[0])), \(Int(coords[1]))"
                            restoredFields += 1
                            print("✅ Restored centroid \(target): \(textField.stringValue)")
                        }
                    } else if identifier.hasPrefix("EXPECTED_COPY_NUMBERS_") {
                        let chrom = String(identifier.dropFirst("EXPECTED_COPY_NUMBERS_".count))
                        if let copyNumbers = parameters["EXPECTED_COPY_NUMBERS"] as? [String: Double],
                           let value = copyNumbers[chrom] {
                            textField.stringValue = String(value)
                            restoredFields += 1
                            print("✅ Restored copy number \(chrom): \(textField.stringValue)")
                        }
                    } else if identifier.hasPrefix("EXPECTED_STANDARD_DEVIATION_") {
                        let chrom = String(identifier.dropFirst("EXPECTED_STANDARD_DEVIATION_".count))
                        if let stdDevs = parameters["EXPECTED_STANDARD_DEVIATION"] as? [String: Double],
                           let value = stdDevs[chrom] {
                            textField.stringValue = String(value)
                            restoredFields += 1
                            print("✅ Restored standard deviation \(chrom): \(textField.stringValue)")
                        }
                    } else if identifier == "LOWER_DEVIATION_TARGET" {
                        // Check new format first, then fall back to old formats
                        if let value = parameters["LOWER_DEVIATION_TARGET"] {
                            textField.stringValue = String(describing: value)
                            restoredFields += 1
                        } else if let value = parameters["CNV_LOSS_RATIO"] {
                            textField.stringValue = String(describing: value)
                            restoredFields += 1
                        } else if let targets = parameters["ANEUPLOIDY_TARGETS"] as? [String: Double],
                           let value = targets["low"] {
                            textField.stringValue = String(value)
                            restoredFields += 1
                        }
                    } else if identifier == "UPPER_DEVIATION_TARGET" {
                        // Check new format first, then fall back to old formats
                        if let value = parameters["UPPER_DEVIATION_TARGET"] {
                            textField.stringValue = String(describing: value)
                            restoredFields += 1
                        } else if let value = parameters["CNV_GAIN_RATIO"] {
                            textField.stringValue = String(describing: value)
                            restoredFields += 1
                        } else if let targets = parameters["ANEUPLOIDY_TARGETS"] as? [String: Double],
                           let value = targets["high"] {
                            textField.stringValue = String(value)
                            restoredFields += 1
                        }
                    } else if identifier == "ENABLE_COPY_NUMBER_ANALYSIS" || identifier == "CLASSIFY_CNV_DEVIATIONS" {
                        // Handle dropdown restoration
                        if let popup = view.subviews.first(where: { $0.identifier?.rawValue == identifier }) as? NSPopUpButton {
                            if let value = parameters[identifier] as? Bool {
                                popup.selectItem(at: value ? 0 : 1)
                                restoredFields += 1
                            } else if let value = parameters[identifier] as? String {
                                popup.selectItem(at: value.lowercased() == "yes" ? 0 : 1)
                                restoredFields += 1
                            }
                        }
                    } else if identifier == "CNV_LOSS_RATIO" {
                        // Check new format first, then fall back to old format
                        if let value = parameters["CNV_LOSS_RATIO"] {
                            textField.stringValue = String(describing: value)
                            restoredFields += 1
                        } else if let targets = parameters["ANEUPLOIDY_TARGETS"] as? [String: Double],
                           let value = targets["low"] {
                            textField.stringValue = String(value)
                            restoredFields += 1
                        }
                    } else if identifier == "CNV_GAIN_RATIO" {
                        // Check new format first, then fall back to old format
                        if let value = parameters["CNV_GAIN_RATIO"] {
                            textField.stringValue = String(describing: value)
                            restoredFields += 1
                        } else if let targets = parameters["ANEUPLOIDY_TARGETS"] as? [String: Double],
                           let value = targets["high"] {
                            textField.stringValue = String(value)
                            restoredFields += 1
                        }
                    } else if let value = parameters[identifier] {
                        let oldValue = textField.stringValue
                        textField.stringValue = String(describing: value)
                        restoredFields += 1
                        print("✅ Restored \(identifier): \(oldValue) → \(value)")
                    }
                } else if let popup = subview as? NSPopUpButton,
                          let identifier = popup.identifier?.rawValue {
                    if identifier == "CHROMOSOME_COUNT" {
                        // Set chromosome count and trigger the change event
                        let currentSelection = popup.titleOfSelectedItem
                        popup.selectItem(withTitle: String(targetChromCount))
                        restoredFields += 1
                        print("✅ Set chromosome count to \(targetChromCount) (was: \(currentSelection ?? "nil"))")
                        
                        // Only trigger the change event if the value actually changed
                        if currentSelection != String(targetChromCount) {
                            print("🔄 Triggering chromosome count change event...")
                            chromosomeCountChanged(popup)
                        }
                    } else if let value = parameters[identifier] as? String {
                        popup.selectItem(withTitle: value)
                        restoredFields += 1
                    }
                }
                
                // Recursively restore in subviews
                restoreAllFields(subview)
            }
        }
        
        restoreAllFields(window.contentView!)
        
        print("🔧 Restoration complete: restored \(restoredFields)/\(totalFields) fields with chromosome count \(targetChromCount)")
    }
    
    private func loadGlobalParameters() -> [String: Any] {
        let homeDir = FileManager.default.homeDirectoryForCurrentUser
        let ddquintDir = homeDir.appendingPathComponent(".ddQuint")
        let parametersFile = ddquintDir.appendingPathComponent("parameters.json")
        
        print("🔍 Loading global parameters:")
        print("   Home dir: \(homeDir.path)")
        print("   ddQuint dir: \(ddquintDir.path)")
        print("   Parameters file: \(parametersFile.path)")
        print("   File exists: \(FileManager.default.fileExists(atPath: parametersFile.path))")
        
        guard FileManager.default.fileExists(atPath: parametersFile.path) else {
            print("❌ NO FALLBACK: Global parameters file not found!")
            return [:]  // Return empty instead of defaults
        }
        
        do {
            let data = try Data(contentsOf: parametersFile)
            print("   File size: \(data.count) bytes")
            
            let parameters = try JSONSerialization.jsonObject(with: data) as? [String: Any] ?? [:]
            print("   Parsed \(parameters.count) parameters: \(parameters.keys.sorted())")
            
            if parameters.isEmpty {
                print("❌ NO FALLBACK: Parameters file is empty!")
                return [:]  // Return empty instead of defaults
            } else {
                print("✅ Successfully loaded global parameters from file")
                // Show some specific parameter values for debugging
                if let xAxisMax = parameters["X_AXIS_MAX"] {
                    print("   Sample parameter: X_AXIS_MAX = \(xAxisMax) (\(type(of: xAxisMax)))")
                }
                return parameters
            }
        } catch {
            print("❌ NO FALLBACK: Failed to load/parse parameters file: \(error)")
            return [:]  // Return empty instead of defaults
        }
    }
    
    private func saveWellParametersToTempFile(_ parameters: [String: Any], wellName: String) -> String? {
        guard !parameters.isEmpty else { return nil }
        
        let tempDir = NSTemporaryDirectory()
        let tempFile = "\(tempDir)/ddquint_well_params_\(wellName).json"
        
        do {
            let jsonData = try JSONSerialization.data(withJSONObject: parameters, options: .prettyPrinted)
            try jsonData.write(to: URL(fileURLWithPath: tempFile))
            print("✅ Saved well parameters to: \(tempFile)")
            return tempFile
        } catch {
            print("❌ Failed to save well parameters: \(error)")
            return nil
        }
    }
    
    
    
    // MARK: - Processing Indicator
    
    private func showProcessingIndicator(_ message: String) {
        // Close existing processing indicator if open
        hideProcessingIndicator()
        
        // Create a persistent processing message that doesn't get overwritten
        let processingWindow = NSWindow(
            contentRect: NSRect(x: 0, y: 0, width: 450, height: 120),
            styleMask: [.titled, .closable],
            backing: .buffered,
            defer: false
        )
        
        processingWindow.title = "Processing"
        processingWindow.center()
        processingWindow.level = .floating
        processingWindow.isReleasedWhenClosed = false
        
        // Create content view with Auto Layout
        let contentView = NSView()
        processingWindow.contentView = contentView
        
        let stackView = NSStackView()
        stackView.orientation = .vertical
        stackView.spacing = 10
        stackView.translatesAutoresizingMaskIntoConstraints = false
        contentView.addSubview(stackView)
        
        let label = NSTextField(labelWithString: message)
        label.isEditable = false
        label.isBordered = false
        label.backgroundColor = .clear
        label.alignment = .center
        label.font = NSFont.systemFont(ofSize: 13)
        
        let spinner = NSProgressIndicator()
        spinner.style = .spinning
        spinner.controlSize = .regular
        spinner.startAnimation(nil)
        
        stackView.addArrangedSubview(label)
        stackView.addArrangedSubview(spinner)
        
        // Set up Auto Layout constraints
        NSLayoutConstraint.activate([
            stackView.centerXAnchor.constraint(equalTo: contentView.centerXAnchor),
            stackView.centerYAnchor.constraint(equalTo: contentView.centerYAnchor),
            stackView.leadingAnchor.constraint(greaterThanOrEqualTo: contentView.leadingAnchor, constant: 20),
            stackView.trailingAnchor.constraint(lessThanOrEqualTo: contentView.trailingAnchor, constant: -20),
            spinner.widthAnchor.constraint(equalToConstant: 32),
            spinner.heightAnchor.constraint(equalToConstant: 32)
        ])
        
        // Store reference and show window
        processingIndicatorWindow = processingWindow
        processingWindow.makeKeyAndOrderFront(nil)
        
        print("⚡ Processing indicator shown: \(message)")
    }
    
    private func hideProcessingIndicator() {
        if let window = processingIndicatorWindow {
            window.close()
            processingIndicatorWindow = nil
            print("✅ Processing indicator hidden")
        }
    }
    
    // MARK: - Corner Spinner Methods
    
    private func showCornerSpinner() {
        DispatchQueue.main.async { [weak self] in
            self?.progressIndicator.isHidden = false
            self?.progressIndicator.startAnimation(nil)
            print("⚡ Corner spinner started")
        }
    }
    
    private func hideCornerSpinner() {
        DispatchQueue.main.async { [weak self] in
            self?.progressIndicator.stopAnimation(nil)
            self?.progressIndicator.isHidden = true
            print("✅ Corner spinner stopped")
        }
    }
    
    

    // MARK: - Actions

    // Exposed for menu action: open a new input folder and start analysis
    @objc func openInputFolder() {
        selectFolderAndAnalyze()
    }

    @objc private func editWellParameters() {
        let selectedRows = wellListView.selectedRowIndexes
        guard !selectedRows.isEmpty else { return }
        
        if selectedRows.count == 1 {
            // Single well selection - existing behavior
            guard selectedWellIndex >= 0 && selectedWellIndex < wellData.count else { return }
            let well = wellData[selectedWellIndex]
            openParameterWindow(isGlobal: false, title: "Edit Parameters - \(well.well)")
        } else {
            // Multiple well selection - batch edit
            let selectedWells = selectedRows.compactMap { row -> String? in
                guard row >= 0 && row < filteredWellData.count else { return nil }
                return filteredWellData[row].well
            }
            
            if !selectedWells.isEmpty {
                let title = "Edit Parameters - \(selectedWells.count) Wells (\(selectedWells.sorted().joined(separator: ", ")))"
                openMultiWellParameterWindow(wells: selectedWells, title: title)
            }
        }
    }
    
    @objc private func editGlobalParameters() {
        openParameterWindow(isGlobal: true, title: "Global Parameters")
    }
    
    private func openMultiWellParameterWindow(wells: [String], title: String) {
        print("🔧 Opening multi-well parameter window for \(wells.count) wells: \(wells.sorted().joined(separator: ", "))")
        
        // Store the wells to be edited
        currentMultiEditWells = wells
        
        // Use the first well as the base for parameters, but mark as multi-edit mode
        if let firstWell = wells.first,
           let originalIndex = wellData.firstIndex(where: { $0.well == firstWell }) {
            selectedWellIndex = originalIndex
            openParameterWindow(isGlobal: false, title: title)
        }
    }
    
    // Track multi-well editing state
    private var currentMultiEditWells: [String] = []
    
    @objc private func exportAll() {
        print("🚀 exportAll() called!")
        guard let sourceFolder = selectedFolderURL else { 
            print("❌ No source folder selected")
            return 
        }
        
        print("📂 Source folder: \(sourceFolder.path)")
        
        let openPanel = NSOpenPanel()
        openPanel.canChooseFiles = false
        openPanel.canChooseDirectories = true
        openPanel.allowsMultipleSelection = false
        if let last = lastURL(for: "LastDir.ExportAll") { openPanel.directoryURL = last }
        openPanel.prompt = "Select Export Folder"
        openPanel.message = "Choose a folder to export Excel file, parameters, and plots"
        
        print("📁 Showing export folder selection dialog...")
        let response = openPanel.runModal()
        if response == .OK, let exportFolder = openPanel.url {
            print("✅ User selected export folder: \(exportFolder.path)")
            setLastURL(exportFolder, for: "LastDir.ExportAll")
            performComprehensiveExport(to: exportFolder, sourceFolder: sourceFolder)
        } else {
            print("❌ User cancelled export folder selection")
        }
    }
    
    @objc private func exportExcel() {
        guard let folderURL = selectedFolderURL else { return }
        
        let savePanel = NSSavePanel()
        savePanel.allowedContentTypes = [.spreadsheet]
        savePanel.nameFieldStringValue = "ddQuint_Results.xlsx"
        if let last = lastURL(for: "LastDir.ExcelExport") { savePanel.directoryURL = last }
        
        let response = savePanel.runModal()
        if response == .OK, let saveURL = savePanel.url {
            setLastURL(saveURL.deletingLastPathComponent(), for: "LastDir.ExcelExport")
            exportExcelFile(to: saveURL, sourceFolder: folderURL)
        }
    }
    
    @objc private func chromosomeCountChanged(_ sender: NSPopUpButton) {
        // Get the new chromosome count
        guard let selectedTitle = sender.titleOfSelectedItem,
              let newCount = Int(selectedTitle) else { return }
        
        print("🔄 Chromosome count changed to: \(newCount)")
        
        // Find the current tab view and update the centroids view dynamically
        if let tabView = currentParamTabView {
            // Find the centroids tab
            for item in tabView.tabViewItems {
                if item.identifier as? String == "centroids" {
                    if let scrollView = item.view as? NSScrollView,
                       let documentView = scrollView.documentView {
                        updateCentroidsViewForTargetCount(documentView, targetCount: newCount, parameters: { if let window = currentWellWindow ?? currentGlobalWindow { return extractParametersFromWindow(window, isGlobal: currentWellWindow == nil) } else { return loadGlobalParameters() } }())
                    }
                    break
                }
            }
        }
        
        // Also update copy number tab if it exists
        if let tabView = currentParamTabView {
            for item in tabView.tabViewItems {
                if item.identifier as? String == "copynumber" {
                    if let scrollView = item.view as? NSScrollView,
                       let documentView = scrollView.documentView {
                        updateCopyNumberViewForTargetCount(documentView, targetCount: newCount, parameters: { if let window = currentWellWindow ?? currentGlobalWindow { return extractParametersFromWindow(window, isGlobal: currentWellWindow == nil) } else { return loadGlobalParameters() } }())
                    }
                    break
                }
            }
        }
        
        // Also update general settings tab for target names
        if let tabView = currentParamTabView {
            for item in tabView.tabViewItems {
                if item.identifier as? String == "general" {
                    if let scrollView = item.view as? NSScrollView,
                       let documentView = scrollView.documentView {
                        updateGeneralSettingsViewForTargetCount(documentView, targetCount: newCount, parameters: { if let window = currentWellWindow ?? currentGlobalWindow { return extractParametersFromWindow(window, isGlobal: currentWellWindow == nil) } else { return loadGlobalParameters() } }())
                    }
                    break
                }
            }
        }
    }
    
    // Update General Settings view target names when chromosome count changes
    private func updateGeneralSettingsViewForTargetCount(_ view: NSView, targetCount: Int, parameters: [String: Any] = [:]) {
        let fieldHeight: CGFloat = 24
        let spacing: CGFloat = 30
        
        // Find the base position from existing target name field
        var baseY: CGFloat?
        var baseX: CGFloat = 40  // Default X position
        
        // Look for existing target name fields to find base position
        for subview in view.subviews {
            if let textField = subview as? NSTextField,
               textField.identifier?.rawValue == "TARGET_NAME_1" {
                baseY = textField.frame.minY
                baseX = textField.frame.minX - 130  // Account for label width
                break
            }
        }
        
        // If no existing target fields found, try to find the target customization label
        if baseY == nil {
            for subview in view.subviews {
                if let textField = subview as? NSTextField,
                   textField.stringValue == "Target Name Customization" {
                    baseY = textField.frame.minY - 40  // Position below the section header
                    break
                }
            }
        }
        
        guard let startY = baseY else {
            print("Warning: Could not find base position for target name fields")
            return
        }
        
        // Remove existing target name fields and labels
        var toRemove: [NSView] = []
        for subview in view.subviews {
            if let textField = subview as? NSTextField {
                if let identifier = textField.identifier?.rawValue,
                   identifier.hasPrefix("TARGET_NAME_") {
                    toRemove.append(textField)
                } else if textField.stringValue.hasPrefix("Target ") && 
                         textField.stringValue.hasSuffix(":") &&
                         textField.stringValue != "Target Name Customization" {
                    // Remove target labels like "Target 1:", "Target 2:", etc.
                    toRemove.append(textField)
                }
            }
        }
        
        for view in toRemove {
            view.removeFromSuperview()
        }
        
        // Add new target name fields based on target count
        var currentY = startY
        for i in 1...targetCount {
            let targetLabel = NSTextField(labelWithString: "Target \(i):")
            targetLabel.frame = NSRect(x: baseX, y: currentY, width: 120, height: fieldHeight)
            
            let targetField = NSTextField()
            targetField.identifier = NSUserInterfaceItemIdentifier("TARGET_NAME_\(i)")
            
            // Set current value from parameters or default
            if let targetNames = parameters["TARGET_NAMES"] as? [String: String],
               let name = targetNames["Target\(i)"], !name.isEmpty {
                targetField.stringValue = name
            } else {
                targetField.stringValue = "" // Empty by default, falls back to "Target X"
            }
            
            targetField.frame = NSRect(x: baseX + 130, y: currentY, width: 150, height: fieldHeight)
            targetField.toolTip = "Custom name for Target \(i) (leave empty for default 'Target \(i)')"
            targetField.isEditable = true
            targetField.isSelectable = true
            targetField.isBordered = true
            targetField.bezelStyle = .roundedBezel
            
            view.addSubview(targetLabel)
            view.addSubview(targetField)
            currentY -= spacing
        }
        
        print("✅ Updated General Settings target names for \(targetCount) targets")
    }
    
    // MARK: - Comprehensive Export
    
    private func performComprehensiveExport(to exportFolder: URL, sourceFolder: URL) {
        statusLabel.stringValue = "Starting comprehensive export..."
        print("🚀 Starting comprehensive export to: \(exportFolder.path)")
        print("🚀 Source folder: \(sourceFolder.path)")
        
        DispatchQueue.global().async { [weak self] in
            guard let self = self else { 
                print("❌ Self is nil in comprehensive export")
                return 
            }
            
            // Create export structure
            let excelURL = exportFolder.appendingPathComponent("ddQuint_Results.xlsx")
            let parametersURL = exportFolder.appendingPathComponent("ddQuint_Parameters.json")
            let graphsFolder = exportFolder.appendingPathComponent("Graphs")
            
            var exportSuccess = true
            var exportSteps = 0
            let totalSteps = 3
            
            print("📂 Export paths:")
            print("   Excel: \(excelURL.path)")
            print("   Parameters: \(parametersURL.path)")
            print("   Graphs: \(graphsFolder.path)")
            
            // Step 1: Export Excel file
            DispatchQueue.main.async {
                self.statusLabel.stringValue = "Exporting Excel file... (1/3)"
            }
            
            print("📊 Starting Excel export...")
            if self.exportExcelToURL(excelURL, sourceFolder: sourceFolder) {
                exportSteps += 1
                print("✅ Excel export completed")
            } else {
                exportSuccess = false
                print("❌ Excel export failed")
            }
            
            // Step 2: Export parameters
            if exportSuccess {
                DispatchQueue.main.async {
                    self.statusLabel.stringValue = "Exporting parameters... (2/3)"
                }
                
                print("⚙️ Starting parameters export...")
                if self.exportParametersToURL(parametersURL) {
                    exportSteps += 1
                    print("✅ Parameters export completed")
                } else {
                    exportSuccess = false
                    print("❌ Parameters export failed")
                }
            }
            
            // Step 3: Export plots
            if exportSuccess {
                DispatchQueue.main.async {
                    self.statusLabel.stringValue = "Exporting plots... (3/3)"
                }
                
                print("📈 Starting plots export...")
                if self.exportPlotsToFolder(graphsFolder, sourceFolder: sourceFolder) {
                    exportSteps += 1
                    print("✅ Plots export completed")
                } else {
                    exportSuccess = false
                    print("❌ Plots export failed")
                }
            }
            
            // Final status
            DispatchQueue.main.async {
                if exportSuccess {
                    self.statusLabel.stringValue = "Comprehensive export completed successfully"
                } else {
                    self.statusLabel.stringValue = "Export failed"
                    self.showError("Export failed. Check the debug log for details.")
                }
            }
        }
    }
    
    private func exportExcelToURL(_ url: URL, sourceFolder: URL) -> Bool {
        // Try loading from cache file if not in memory
        print("🔍 EXCEL_DEBUG: Checking cache before comprehensive export")
        print("   cachedResults.isEmpty: \(cachedResults.isEmpty)")
        print("   current cacheKey: \(cacheKey ?? "nil")")
        
        if cachedResults.isEmpty || cacheKey != generateCacheKey(folderURL: sourceFolder) {
            print("🔍 EXCEL_DEBUG: Attempting to load cache from file for comprehensive export")
            let loaded = loadCacheFromFile(folderURL: sourceFolder)
            print("   cache load result: \(loaded)")
        } else {
            print("🔍 EXCEL_DEBUG: Using existing in-memory cache for comprehensive export")
        }
        
        let currentCacheKey = generateCacheKey(folderURL: sourceFolder)
        
        if let existingKey = cacheKey, existingKey == currentCacheKey, !cachedResults.isEmpty {
            return exportExcelFromCachedResultsSync(to: url, sourceFolder: sourceFolder)
        }
        
        print("❌ No cached results available for Excel export")
        return false
    }
    
    private func exportParametersToURL(_ url: URL) -> Bool {
        // Export current global parameters
        let globalParams = loadGlobalParameters()
        
        let bundle: [String: Any] = [
            "global_parameters": globalParams,
            "well_parameters": wellParametersMap,
            "export_date": ISO8601DateFormatter().string(from: Date()),
            "source": "ddQuint macOS App"
        ]
        
        do {
            let data = try JSONSerialization.data(withJSONObject: bundle, options: .prettyPrinted)
            try data.write(to: url)
            return true
        } catch {
            print("❌ Failed to export parameters: \(error)")
            return false
        }
    }
    
    private func exportPlotsToFolder(_ folder: URL, sourceFolder: URL) -> Bool {
        do {
            // Create graphs folder
            try FileManager.default.createDirectory(at: folder, withIntermediateDirectories: true)
            
            // Find the temp analysis plots folder (it's created during analysis)
            let tempBase = NSTemporaryDirectory()
            let tempPlotsFolder = URL(fileURLWithPath: tempBase).appendingPathComponent("ddquint_analysis_plots")
            
            print("🔍 Looking for plots in: \(tempPlotsFolder.path)")
            
            if FileManager.default.fileExists(atPath: tempPlotsFolder.path) {
                let plotFiles = try FileManager.default.contentsOfDirectory(at: tempPlotsFolder, includingPropertiesForKeys: nil)
                let pngFiles = plotFiles.filter({ $0.pathExtension == "png" })
                
                print("🔍 Found \(pngFiles.count) PNG files to export")
                
                for plotFile in pngFiles {
                    let destination = folder.appendingPathComponent(plotFile.lastPathComponent)
                    try FileManager.default.copyItem(at: plotFile, to: destination)
                    print("📋 Copied plot: \(plotFile.lastPathComponent)")
                }
                
                return true
            } else {
                print("❌ No plots folder found at: \(tempPlotsFolder.path)")
                return false
            }
        } catch {
            print("❌ Failed to export plots: \(error)")
            return false
        }
    }
    
    private func getMaxTargetCount() -> Int {
        // Calculate maximum chromosome count across all wells
        
        // Start with global parameter default
        let globalParams = loadGlobalParameters()
        var maxTargetCount = globalParams["CHROMOSOME_COUNT"] as? Int ?? 5
        print("📊 Global CHROMOSOME_COUNT: \(maxTargetCount)")
        
        // Check well-specific parameter overrides
        for (wellId, params) in wellParametersMap {
            if let chromCount = params["CHROMOSOME_COUNT"] as? Int {
                maxTargetCount = max(maxTargetCount, chromCount)
                print("📊 Well \(wellId) has \(chromCount) targets, max so far: \(maxTargetCount)")
            }
        }
        
        // Also check cached results for actual chromosome data (in case processing created more targets than configured)
        for result in cachedResults {
            if let copyNumbers = result["copy_numbers"] as? [String: Any] {
                let chromCount = copyNumbers.keys.filter { $0.hasPrefix("Chrom") }.count
                if chromCount > 0 {
                    maxTargetCount = max(maxTargetCount, chromCount)
                    print("📊 Cached result has \(chromCount) targets, max so far: \(maxTargetCount)")
                }
            }
            // Also check centroids data
            if let centroids = result["centroids"] as? [String: Any] {
                let chromCount = centroids.keys.filter { $0.hasPrefix("Chrom") }.count
                if chromCount > 0 {
                    maxTargetCount = max(maxTargetCount, chromCount)
                    print("📊 Cached centroids has \(chromCount) targets, max so far: \(maxTargetCount)")
                }
            }
        }
        
        print("✅ Maximum target count across all wells: \(maxTargetCount)")
        return maxTargetCount
    }
    
    private func exportExcelFromCachedResultsSync(to saveURL: URL, sourceFolder: URL) -> Bool {
        guard let pythonPath = findPython(),
              let ddquintPath = findDDQuint() else {
            print("❌ Python or ddQuint not found")
            return false
        }
        
        // Calculate maximum target count for proper Excel columns
        let maxTargetCount = getMaxTargetCount()
        
        // Save cachedResults to temporary JSON file
        let tempFile = URL(fileURLWithPath: NSTemporaryDirectory()).appendingPathComponent("ddquint_cached_results.json")
        
        do {
            let jsonData = try JSONSerialization.data(withJSONObject: cachedResults, options: .prettyPrinted)
            try jsonData.write(to: tempFile)
        } catch {
            print("❌ Failed to create temporary cache file: \(error)")
            return false
        }
        
        // Execute Python script synchronously with max target count
        let process = Process()
        process.executableURL = URL(fileURLWithPath: pythonPath)
        
        let escapedSavePath = saveURL.path.replacingOccurrences(of: "'", with: "\\'")
        let escapedDDQuintPath = ddquintPath.replacingOccurrences(of: "'", with: "\\'")
        let escapedTempJsonPath = tempFile.path.replacingOccurrences(of: "'", with: "\\'")
        
        process.arguments = [
            "-c",
            """
            import sys
            import json
            import traceback
            import os
            
            try:
                sys.path.insert(0, '\(escapedDDQuintPath)')
                
                # Initialize config
                from ddquint.config import Config
                from ddquint.utils.parameter_editor import load_parameters_if_exist
                
                config = Config.get_instance()
                load_parameters_if_exist(Config)
                config.finalize_colors()
                
                # Import create_list_report
                from ddquint.core import create_list_report
                
                # Load cached results from temp file
                with open('\(escapedTempJsonPath)', 'r') as f:
                    results = json.load(f)
                
                print(f'DEBUG: Loaded {len(results)} cached results for Excel export (sync)')
                
                # Export to Excel using cached results with max target count
                create_list_report(results, '\(escapedSavePath)', \(maxTargetCount))
                print('EXCEL_EXPORT_SUCCESS_CACHED_SYNC')
                
            except Exception as e:
                print(f'EXPORT_ERROR: {e}')
                traceback.print_exc()
                sys.exit(1)
            """
        ]
        
        // Set environment
        var env = ProcessInfo.processInfo.environment
        if let pythonPath = env["PATH"] {
            env["PATH"] = "\(ddquintPath):\(pythonPath)"
        } else {
            env["PATH"] = ddquintPath
        }
        env["PYTHONPATH"] = ddquintPath
        process.environment = env
        
        do {
            try process.run()
            process.waitUntilExit()
            
            // Clean up temp file
            try? FileManager.default.removeItem(at: tempFile)
            
            return process.terminationStatus == 0
        } catch {
            print("❌ Failed to run Excel export process: \(error)")
            return false
        }
    }
    
private func updateCentroidsViewForTargetCount(_ view: NSView, targetCount: Int, parameters: [String: Any] = [:]) {
    // Column-based layout: first 5 chromosomes go in column 1, next 5 in column 2, etc.
    
    let fieldHeight: CGFloat = 24
    let rowSpacing: CGFloat = 30
    let columnWidth: CGFloat = 200
    let columnSpacing: CGFloat = 120  // Move second column further right
    let chromsPerColumn = 5
    
    // Find the first chromosome field to establish the base layout
    var firstChromY: CGFloat?
    var firstChromX: CGFloat?
    for s in view.subviews {
        if let tf = s as? NSTextField,
           tf.identifier?.rawValue == "EXPECTED_CENTROIDS_Chrom1" {
            firstChromY = tf.frame.minY
            firstChromX = tf.frame.minX
            break
        }
    }
    
    // Fallback: use Negative field position and estimate first chrom position
    if firstChromY == nil {
        for s in view.subviews {
            if let tf = s as? NSTextField,
               tf.identifier?.rawValue == "EXPECTED_CENTROIDS_Negative" {
                firstChromY = tf.frame.minY - rowSpacing
                firstChromX = tf.frame.minX
                break
            }
        }
    }
    
    guard let baseY = firstChromY, let baseX = firstChromX else {
        print("Warning: Could not establish base position")
        return
    }
    
    // Remove existing Chrom* fields AND labels we created for additional columns only
    var toRemove: [NSView] = []
    for s in view.subviews {
        guard let tf = s as? NSTextField else { continue }
        if let id = tf.identifier?.rawValue {
            if id.hasPrefix("EXPECTED_CENTROIDS_Chrom") {
                toRemove.append(tf)
            }
        } else {
            // Only remove labels for Target 6 and above (additional columns)
            if tf.stringValue.hasPrefix("Target ") && tf.stringValue.hasSuffix(":") {
                // Extract target number from "Target X:"
                let targetStr = tf.stringValue.dropFirst(7).dropLast(1)  // Remove "Target " and ":"
                if let targetNum = Int(targetStr), targetNum > 5 {
                    toRemove.append(tf)
                }
            }
        }
    }
    toRemove.forEach { $0.removeFromSuperview() }
    
    // Load saved values - use passed parameters if available, otherwise extract from current window
    let currentParameters = !parameters.isEmpty ? parameters : { if let window = currentWellWindow ?? currentGlobalWindow { return extractParametersFromWindow(window, isGlobal: currentWellWindow == nil) } else { return loadGlobalParameters() } }()
    let savedCentroids = (currentParameters["EXPECTED_CENTROIDS"] as? [String: [Double]]) ?? [:]
    
    // Add chromosome fields in column layout
    for idx in 1...max(0, targetCount) {
        let chromName = "Chrom\(idx)"
        
        // Calculate which column and position within that column
        let columnIndex = (idx - 1) / chromsPerColumn
        let positionInColumn = (idx - 1) % chromsPerColumn
        
        let columnX = baseX + CGFloat(columnIndex) * (columnWidth + columnSpacing)
        let fieldY = baseY - CGFloat(positionInColumn) * rowSpacing
        
        // Create the field
        let field = NSTextField()
        field.identifier = NSUserInterfaceItemIdentifier("EXPECTED_CENTROIDS_\(chromName)")
        if let coords = savedCentroids[chromName], coords.count >= 2 {
            field.stringValue = "\(Int(coords[0])), \(Int(coords[1]))"
        } else {
            field.stringValue = ""
        }
        field.frame = NSRect(x: columnX, y: fieldY, width: 150, height: fieldHeight)
        field.toolTip = "Expected centroid coordinates (HEX, FAM) for \(chromName)"
        field.isEditable = true
        field.isSelectable = true
        field.isBordered = true
        field.bezelStyle = .roundedBezel
        field.backgroundColor = NSColor.textBackgroundColor
        field.wantsLayer = true
        field.layer?.zPosition = 10000
        view.addSubview(field)
        
        // Only add label for chromosomes in additional columns (first column uses existing labels)
        if columnIndex > 0 {
            let labelX = columnX - 130  // Consistent spacing with first column
            let label = NSTextField(labelWithString: "Target \(idx):")
            label.frame = NSRect(x: labelX, y: fieldY, width: 120, height: fieldHeight)
            // Match the font and style of original labels
            if let existingLabel = view.subviews.first(where: { 
                ($0 as? NSTextField)?.stringValue == "Negative:" 
            }) as? NSTextField {
                label.font = existingLabel.font
                label.textColor = existingLabel.textColor
            }
            label.wantsLayer = true
            label.layer?.zPosition = 10000
            view.addSubview(label)
        }
    }
    
    // Expand document width if we added additional columns
    let numberOfColumns = (targetCount + chromsPerColumn - 1) / chromsPerColumn
    if numberOfColumns > 1 {
        let requiredWidth = baseX + CGFloat(numberOfColumns - 1) * (columnWidth + columnSpacing) + 200
        if view.frame.width < requiredWidth {
            var f = view.frame
            f.size.width = requiredWidth
            view.frame = f
        }
    }
    
    view.needsDisplay = true
}
    
private func updateCopyNumberViewForTargetCount(_ view: NSView, targetCount: Int, parameters: [String: Any] = [:]) {
    // Column grouping: CN1 - CN2 (if needed) - SD1 - SD2 (if needed)
    // 5 chromosomes per column, tighter spacing since we already have 2 default columns
    
    let fieldHeight: CGFloat = 24
    let rowSpacing: CGFloat = 30
    let columnSpacing: CGFloat = 30  // Tighter spacing
    let chromsPerColumn = 5
    
    // Find existing first chromosome fields to establish base positions
    var baseCnY: CGFloat?
    var baseCnX: CGFloat?
    var baseSdX: CGFloat?
    
    for s in view.subviews {
        if let tf = s as? NSTextField,
           let id = tf.identifier?.rawValue {
            if id == "EXPECTED_COPY_NUMBERS_Chrom1" {
                baseCnY = tf.frame.minY
                baseCnX = tf.frame.minX
            } else if id == "EXPECTED_STANDARD_DEVIATION_Chrom1" {
                baseSdX = tf.frame.minX
            }
        }
    }
    
    guard let baseY = baseCnY, let baseCnXPos = baseCnX, let baseSdXPos = baseSdX else {
        print("Warning: Could not find base copy number field positions")
        return
    }
    
    // Remove existing Chrom* fields AND all SD-related labels (both old and new)
    var toRemove: [NSView] = []
    for s in view.subviews {
        guard let tf = s as? NSTextField else { continue }
        if let id = tf.identifier?.rawValue {
            if id.hasPrefix("EXPECTED_COPY_NUMBERS_Chrom") || id.hasPrefix("EXPECTED_STANDARD_DEVIATION_Chrom") {
                toRemove.append(tf)
            }
        } else {
            // Remove Target labels for additional columns (6+) and ALL SD labels
            if tf.stringValue.hasPrefix("Target ") && tf.stringValue.hasSuffix(":") {
                // Extract target number from "Target X:"
                let targetStr = tf.stringValue.dropFirst(7).dropLast(1)  // Remove "Target " and ":"
                if let targetNum = Int(targetStr), targetNum > 5 {
                    toRemove.append(tf)
                }
            } else if tf.stringValue.hasPrefix("SD ") || tf.stringValue == "SD:" || tf.stringValue == "SD" {
                // Remove ALL SD-related labels (old "SD:", "SD", and new "SD X:" labels)
                toRemove.append(tf)
            }
        }
    }
    toRemove.forEach { $0.removeFromSuperview() }
    
    // Load saved values - use passed parameters if available, otherwise extract from current window
    let currentParameters = !parameters.isEmpty ? parameters : { if let window = currentWellWindow ?? currentGlobalWindow { return extractParametersFromWindow(window, isGlobal: currentWellWindow == nil) } else { return loadGlobalParameters() } }()
    let savedCNs = (currentParameters["EXPECTED_COPY_NUMBERS"] as? [String: Double]) ?? [:]
    let savedSDs = (currentParameters["EXPECTED_STANDARD_DEVIATION"] as? [String: Double]) ?? [:]
    
    // Calculate total columns needed and positions
    let totalCnColumns = (targetCount + chromsPerColumn - 1) / chromsPerColumn
    let totalSdColumns = totalCnColumns
    
    // Column positions: CN1, CN2, SD1, SD2 with proper separation
    let cn1X = baseCnXPos
    let cn2X = baseCnXPos + (totalCnColumns > 1 ? 180 : 0)  // Shift 20px left from previous 200px
    // SD1 should always stay at current position - never shift further
    let sd1X = baseSdXPos  // Use current SD position as-is, no more shifting
    let sd2X = sd1X + (totalSdColumns > 1 ? 150 : 0)  // Second SD column 150px right of SD1 (was 130px)
    
    // Add chromosome fields with new grouping
    for idx in 1...max(0, targetCount) {
        let chrom = "Chrom\(idx)"
        
        // Calculate which column and position within that column
        let cnColumnIndex = (idx - 1) / chromsPerColumn  // 0 for first column, 1 for second
        let positionInColumn = (idx - 1) % chromsPerColumn
        
        let fieldY = baseY - CGFloat(positionInColumn) * rowSpacing
        
        // Copy Number field - goes in CN1 or CN2 column
        let cnFieldX = cnColumnIndex == 0 ? cn1X : cn2X
        let cnField = NSTextField()
        cnField.identifier = NSUserInterfaceItemIdentifier("EXPECTED_COPY_NUMBERS_\(chrom)")
        if let v = savedCNs[chrom] { cnField.stringValue = String(v) } else { cnField.stringValue = "" }
        cnField.isEditable = true
        cnField.isBordered = true
        cnField.bezelStyle = .roundedBezel
        cnField.frame = NSRect(x: cnFieldX, y: fieldY, width: 70, height: fieldHeight)
        cnField.toolTip = "Expected copy number for \(chrom)"
        view.addSubview(cnField)
        
        // Standard Deviation field - goes in SD1 or SD2 column
        let sdFieldX = cnColumnIndex == 0 ? sd1X : sd2X
        let sdField = NSTextField()
        sdField.identifier = NSUserInterfaceItemIdentifier("EXPECTED_STANDARD_DEVIATION_\(chrom)")
        if let v = savedSDs[chrom] { sdField.stringValue = String(v) } else { sdField.stringValue = "" }
        sdField.isEditable = true
        sdField.isBordered = true
        sdField.bezelStyle = .roundedBezel
        sdField.frame = NSRect(x: sdFieldX, y: fieldY, width: 70, height: fieldHeight)
        sdField.toolTip = "Expected standard deviation for \(chrom)"
        view.addSubview(sdField)
        
        // Add "SD X:" label for first column SD fields too (replace the generic "SD:" labels)
        if cnColumnIndex == 0 {
            let sdLabelX = sdFieldX - 60  // 50px gap between label and textbox
            let sdLabel = NSTextField(labelWithString: "SD \(idx):")
            sdLabel.frame = NSRect(x: sdLabelX, y: fieldY, width: 55, height: fieldHeight)
            sdLabel.alignment = .left  // Change to left alignment to see if gap changes
            // Match the font and style of existing Target labels
            if let existingLabel = view.subviews.first(where: { 
                ($0 as? NSTextField)?.stringValue.hasPrefix("Target ") ?? false 
            }) as? NSTextField {
                sdLabel.font = existingLabel.font
                sdLabel.textColor = existingLabel.textColor
            }
            view.addSubview(sdLabel)
        }
        
        // Add row labels for second column chromosomes using "Target X" format
        if cnColumnIndex > 0 {
            let labelX = cnFieldX - 85  // Consistent spacing with first column
            let label = NSTextField(labelWithString: "Target \(idx):")
            label.frame = NSRect(x: labelX, y: fieldY, width: 75, height: fieldHeight)
            // Match the font and style of existing Target labels
            if let existingLabel = view.subviews.first(where: { 
                ($0 as? NSTextField)?.stringValue.hasPrefix("Target ") ?? false 
            }) as? NSTextField {
                label.font = existingLabel.font
                label.textColor = existingLabel.textColor
            }
            view.addSubview(label)
            
            // Add "SD X:" label for each SD field in second column (proper row labels, not headers)
            let sdLabelX = sdFieldX - 60  // 50px gap between label and textbox
            let sdLabel = NSTextField(labelWithString: "SD \(idx):")
            sdLabel.frame = NSRect(x: sdLabelX, y: fieldY, width: 55, height: fieldHeight)
            sdLabel.alignment = .left  // Change to left alignment to see if gap changes
            // Match the font and style of existing Target labels
            if let existingLabel = view.subviews.first(where: { 
                ($0 as? NSTextField)?.stringValue.hasPrefix("Target ") ?? false 
            }) as? NSTextField {
                sdLabel.font = existingLabel.font
                sdLabel.textColor = existingLabel.textColor
            }
            view.addSubview(sdLabel)
        }
    }
    
    // Expand document width if needed
    if totalCnColumns > 1 {
        let requiredWidth = max(cn2X + 70, sd2X + 70) + 50
        if view.frame.width < requiredWidth {
            var f = view.frame
            f.size.width = requiredWidth
            view.frame = f
        }
    }
    
    view.needsDisplay = true
}
    
    @objc private func exportPlots() {
        guard let folderURL = selectedFolderURL else { return }
        
        let openPanel = NSOpenPanel()
        openPanel.canChooseFiles = false
        openPanel.canChooseDirectories = true
        openPanel.allowsMultipleSelection = false
        if let last = lastURL(for: "LastDir.PlotsExport") { openPanel.directoryURL = last }
        openPanel.prompt = "Select Export Folder"
        openPanel.message = "Choose a folder to export all plots"
        
        let response = openPanel.runModal()
        if response == .OK, let exportURL = openPanel.url {
            setLastURL(exportURL, for: "LastDir.PlotsExport")
            exportAllPlots(to: exportURL, sourceFolder: folderURL)
        }
    }
    
    private func monitorProgressiveOutput(process: Process, outputPipe: Pipe, errorPipe: Pipe) {
        var outputBuffer = ""
        var errorBuffer = ""
        
        let outputHandle = outputPipe.fileHandleForReading
        let errorHandle = errorPipe.fileHandleForReading
        
        outputHandle.readabilityHandler = { handle in
            let data = handle.availableData
            if data.count > 0 {
                if let string = String(data: data, encoding: .utf8) {
                    outputBuffer += string
                    self.processPartialOutput(outputBuffer)
                }
            }
        }
        
        errorHandle.readabilityHandler = { handle in
            let data = handle.availableData
            if data.count > 0 {
                if let string = String(data: data, encoding: .utf8) {
                    errorBuffer += string
                }
            }
        }
        
        // Wait for process to complete
        process.waitUntilExit()
        
        // Clean up handlers
        outputHandle.readabilityHandler = nil
        errorHandle.readabilityHandler = nil
        
        // Final processing
        DispatchQueue.main.async { [weak self] in
            let debugMsg = """
            =====DDQUINT ANALYSIS DEBUG=====
            Python process completed:
            Exit code: \(process.terminationStatus)
            Output: \(outputBuffer)
            Error output: \(errorBuffer)
            ================================
            """
            print(debugMsg)
            
            // Write to debug file
            self?.writeDebugLog(debugMsg)
            
            self?.processAnalysisResults(output: outputBuffer, error: errorBuffer, exitCode: process.terminationStatus)
        }
    }
    
    private func processPartialOutput(_ output: String) {
        let lines = output.components(separatedBy: .newlines)
        
        for line in lines {
            if line.hasPrefix("WELL_COMPLETED:") {
                let jsonString = String(line.dropFirst("WELL_COMPLETED:".count))
                self.handleWellCompleted(jsonString: jsonString)
            } else if line.hasPrefix("ANALYSIS_STARTED:") {
                let totalWells = String(line.dropFirst("ANALYSIS_STARTED:".count))
                if let count = Int(totalWells) {
                    DispatchQueue.main.async { [weak self] in
                        self?.statusLabel.stringValue = "Processing \(count) wells..."
                    }
                }
            } else if line.hasPrefix("COMPLETE_RESULTS:") {
                let resultsJson = String(line.dropFirst("COMPLETE_RESULTS:".count)).trimmingCharacters(in: .whitespacesAndNewlines)
                print("🎯 FOUND COMPLETE_RESULTS in progressive output: \(resultsJson.prefix(100))...")
                DispatchQueue.main.async { [weak self] in
                    self?.cacheCompleteResults(resultsJson)
                }
            } else if line.hasPrefix("UPDATED_RESULT:") {
                let resultJson = String(line.dropFirst("UPDATED_RESULT:".count)).trimmingCharacters(in: .whitespacesAndNewlines)
                if let resultData = resultJson.data(using: .utf8),
                   let result = try? JSONSerialization.jsonObject(with: resultData) as? [String: Any],
                   let wellName = result["well"] as? String {
                    print("🎯 FOUND UPDATED_RESULT in partial output for well: \(wellName)")
                    DispatchQueue.main.async { [weak self] in
                        self?.updateCachedResultForWell(wellName: wellName, resultJson: resultJson)
                    }
                }
            } else if line.hasPrefix("DEBUG:") {
                // Log debug messages from Python
                print("🐍 Python: \(line)")
                writeDebugLog("🐍 \(line)")
            }
        }
    }
    
    private func handleWellCompleted(jsonString: String) {
        guard let data = jsonString.data(using: .utf8),
              let wellInfo = try? JSONSerialization.jsonObject(with: data, options: []) as? [String: Any] else {
            return
        }
        
        DispatchQueue.main.async { [weak self] in
            self?.addWellProgressively(wellInfo: wellInfo)
        }
    }
    
    // MARK: - Cache Management
    
    private func getCacheFilePath(folderURL: URL) -> URL {
        let ddquintDir = folderURL.appendingPathComponent(".ddQuint")
        
        // Ensure .ddQuint directory exists
        do {
            try FileManager.default.createDirectory(at: ddquintDir, withIntermediateDirectories: true, attributes: nil)
        } catch {
            print("Warning: Could not create .ddQuint directory: \(error)")
        }
        
        return ddquintDir.appendingPathComponent("results_cache.json")
    }
    
    private func persistCacheToFile(folderURL: URL) {
        guard !cachedResults.isEmpty else { return }
        
        let cacheFile = getCacheFilePath(folderURL: folderURL)
        
        let cacheData: [String: Any] = [
            "results": cachedResults,
            "cacheKey": cacheKey ?? "",
            "timestamp": cacheTimestamp?.timeIntervalSince1970 ?? 0,
            "version": "1.0"
        ]
        
        do {
            let jsonData = try JSONSerialization.data(withJSONObject: cacheData, options: [.prettyPrinted])
            try jsonData.write(to: cacheFile)
            print("💾 Persisted cache to: \(cacheFile.path)")
        } catch {
            print("⚠️ Failed to persist cache: \(error)")
        }
    }
    
    private func loadCacheFromFile(folderURL: URL) -> Bool {
        let cacheFile = getCacheFilePath(folderURL: folderURL)
        
        guard FileManager.default.fileExists(atPath: cacheFile.path) else {
            print("📂 No cache file found at: \(cacheFile.path)")
            return false
        }
        
        do {
            let jsonData = try Data(contentsOf: cacheFile)
            let cacheData = try JSONSerialization.jsonObject(with: jsonData) as? [String: Any]
            
            guard let cacheData = cacheData,
                  let results = cacheData["results"] as? [[String: Any]],
                  let storedCacheKey = cacheData["cacheKey"] as? String,
                  let timestamp = cacheData["timestamp"] as? TimeInterval else {
                print("⚠️ Invalid cache file format")
                return false
            }
            
            // Check if cache is still valid (less than 24 hours old)
            let cacheAge = Date().timeIntervalSince1970 - timestamp
            let maxCacheAge: TimeInterval = 24 * 60 * 60 // 24 hours
            
            if cacheAge > maxCacheAge {
                print("⏰ Cache is too old (\(Int(cacheAge/3600)) hours), ignoring")
                return false
            }
            
            // Validate cache key matches current context
            let currentCacheKey = generateCacheKey(folderURL: folderURL)
            if storedCacheKey != currentCacheKey {
                print("🔑 Cache key mismatch, ignoring cache")
                return false
            }
            
            // Load cache
            cachedResults = results
            cacheKey = storedCacheKey
            cacheTimestamp = Date(timeIntervalSince1970: timestamp)
            
            print("✅ Loaded \(cachedResults.count) results from cache (age: \(Int(cacheAge/60)) minutes)")
            return true
            
        } catch {
            print("⚠️ Failed to load cache: \(error)")
            return false
        }
    }
    
    private func invalidateCache() {
        cacheKey = nil
        cachedResults.removeAll()
        cacheTimestamp = nil
        
        // Clean up cache file if it exists for selected folder
        if let folderURL = selectedFolderURL {
            let cacheFile = getCacheFilePath(folderURL: folderURL)
            try? FileManager.default.removeItem(at: cacheFile)
            print("🗑️ Invalidated and removed cache file for selected folder")
        }
    }
    
    private func clearAllCacheFiles() {
        // Clear in-memory cache
        cacheKey = nil
        cachedResults.removeAll()
        cacheTimestamp = nil
        
        print("🗑️ Cache cleared on app launch (in-memory)")
        
        // Note: We don't need to scan file system for cache files since they're created 
        // per-folder and will be handled when folders are selected
    }

    // MARK: - Helper Methods
    
    private func parseWellIdColumnFirst(_ wellId: String) -> (Int, Int) {
        // Parse well ID to support column-first sorting (A01, B01, C01, A02, B02, ...)
        // Returns (column_number, row_number) tuple - EXACTLY like list_report.py
        
        if wellId.isEmpty {
            return (999, 999)  // Put empty well IDs at the end
        }
        
        // Extract letter(s) for row and number(s) for column
        var rowPart = ""
        var colPart = ""
        
        for char in wellId {
            if char.isLetter {
                rowPart += String(char)
            } else if char.isNumber {
                colPart += String(char)
            }
        }
        
        // Convert row letters to number (A=1, B=2, etc.) - EXACTLY like Python
        var rowNumber: Int
        if !rowPart.isEmpty {
            rowNumber = 0
            for (i, char) in rowPart.uppercased().reversed().enumerated() {
                rowNumber += (Int(char.asciiValue! - Character("A").asciiValue!) + 1) * Int(pow(26.0, Double(i)))
            }
        } else {
            rowNumber = 999  // Put malformed wells at the end
        }
        
        // Convert column to integer
        let colNumber: Int
        if !colPart.isEmpty, let parsed = Int(colPart) {
            colNumber = parsed
        } else {
            colNumber = colPart.isEmpty ? 0 : 999
        }
        
        // Return (column, row) for column-first sorting - EXACTLY like Python
        let result = (colNumber, rowNumber)
        print("DEBUG PARSE: '\(wellId)' -> row_part:'\(rowPart)' col_part:'\(colPart)' -> (\(colNumber), \(rowNumber))")
        return result
    }
    
    private func findPython() -> String? {
        let fm = FileManager.default
        
        // 1) First priority: Use bundled Python in the .app
        if let resPath = Bundle.main.resourcePath {
            let bundledPython = resPath + "/Python/python_launcher"
            if fm.isExecutableFile(atPath: bundledPython) {
                print("✅ Using bundled Python: \(bundledPython)")
                return bundledPython
            }
        }
        
        // 2) Fallback to system Python installations
        let systemPaths = [
            "/opt/miniconda3/envs/ddpcr/bin/python",
            "/usr/local/bin/python3",
            "/usr/bin/python3"
        ]
        
        for path in systemPaths {
            if fm.isExecutableFile(atPath: path) {
                print("⚠️ Using system Python: \(path)")
                return path
            }
        }
        
        print("❌ No Python installation found!")
        return nil
    }
    
    private func findDDQuint() -> String? {
        let fm = FileManager.default
        // 1) Prefer bundled Python resources in the .app
        if let resPath = Bundle.main.resourcePath {
            let pyPath = resPath + "/Python"
            if fm.fileExists(atPath: pyPath + "/ddquint") {
                return pyPath
            }
        }
        // 2) Prefer local project-relative 'ddquint' (dev/debug)
        let cwd = fm.currentDirectoryPath
        let localPath = (cwd as NSString).appendingPathComponent("ddquint")
        if fm.fileExists(atPath: localPath) {
            return cwd
        }
        // 3) Fallback to user paths
        let fallbacks = [
            "/Users/jakob/Applications/Git/ddQuint",
            NSHomeDirectory() + "/ddQuint"
        ]
        return fallbacks.first { fm.fileExists(atPath: $0 + "/ddquint") }
    }
    
    private func showError(_ message: String) {
        let alert = NSAlert()
        alert.messageText = "Error"
        alert.informativeText = message
        alert.alertStyle = .warning
        alert.runModal()
    }
    
    func writeDebugLog(_ message: String) {
        let formatter = DateFormatter()
        formatter.dateFormat = "yyyy-MM-dd HH:mm:ss"
        let timestamp = formatter.string(from: Date())
        let logMessage = "[\(timestamp)] \(message)\n"
        
        let logPath = "/Users/jakob/Applications/Git/ddQuint-App/debug.log"
        let logURL = URL(fileURLWithPath: logPath)
        
        if let data = logMessage.data(using: .utf8) {
            if FileManager.default.fileExists(atPath: logPath) {
                if let fileHandle = try? FileHandle(forWritingTo: logURL) {
                    fileHandle.seekToEndOfFile()
                    fileHandle.write(data)
                    fileHandle.closeFile()
                }
            } else {
                try? data.write(to: logURL)
            }
        }
    }
    
    private func applyParametersAndRegeneratePlot(wellName: String, parameters: [String: Any]) {
        // Show progress
        showCornerSpinner()
        statusLabel.stringValue = "Applying parameters and regenerating plot for \(wellName)..."
        
        guard let folderURL = selectedFolderURL else {
            hideCornerSpinner()
            statusLabel.stringValue = "No folder selected"
            return
        }
        
        // Invalidate cache for this specific well so it gets regenerated with new parameters
        if let wellIndex = wellData.firstIndex(where: { $0.well == wellName }) {
            // Mark this well as needing regeneration by removing it from cache
            // The parameters are already stored in wellParametersMap[wellName]
            
            // Update the well data to reflect that it has custom parameters
            let currentWell = wellData[wellIndex]
            let status = cachedResults.first(where: { ($0["well"] as? String) == currentWell.well }).map { determineWellStatus(from: $0, wellName: currentWell.well) } ?? WellStatus.euploid
            wellData[wellIndex] = WellData(
                well: currentWell.well,
                sampleName: currentWell.sampleName,
                dropletCount: currentWell.dropletCount,
                hasData: currentWell.hasData,
                status: status,
                isEdited: true // This well now has custom parameters
            )
        }
        
        // Find the specific CSV file for this well
        let csvFiles = findCSVFiles(in: folderURL)
        let wellCSVFile = csvFiles.first { $0.lastPathComponent.contains(wellName) }
        
        guard let csvFile = wellCSVFile else {
            hideCornerSpinner()
            statusLabel.stringValue = "Could not find CSV file for \(wellName)"
            return
        }
        
        // Regenerate plot for this specific well with custom parameters
        regeneratePlotForWell(csvFile: csvFile, wellName: wellName)
    }
    
    private func applyGlobalParametersAndReanalyze(parameters: [String: Any]) {
        // Re-run full analysis with new global parameters
        statusLabel.stringValue = "Applying global parameters and reanalyzing..."
        showCornerSpinner()
        
        guard let folderURL = selectedFolderURL else { 
            hideCornerSpinner()
            return 
        }
        
        // Save parameters first
        saveParametersToFile(parameters)
        
        // Clear ALL caches to force complete re-analysis
        // NOTE: We keep wellParametersMap intact to preserve well-specific parameter customizations
        invalidateCache()
        compositeImagePath = nil
        
        // Clear existing data and restart analysis
        wellData.removeAll()
        filteredWellData.removeAll()
        wellListView.reloadData()
        showPlaceholderImage()
        
        // Restart analysis from scratch
        startAnalysis(folderURL: folderURL)
    }
    
    private func findCSVFiles(in folderURL: URL) -> [URL] {
        do {
            let contents = try FileManager.default.contentsOfDirectory(at: folderURL, includingPropertiesForKeys: nil)
            return contents.filter { $0.pathExtension.lowercased() == "csv" }
        } catch {
            print("Error finding CSV files: \(error)")
            return []
        }
    }
    
    private func regeneratePlotForWell(csvFile: URL, wellName: String) {
        writeDebugLog("🔧 REGEN_START: Starting regeneration for well \(wellName)")
        writeDebugLog("🔧 REGEN_START: CSV file: \(csvFile.path)")
        
        // Clear the existing plot image to prevent file locking issues
        plotImageView.image = nil
        writeDebugLog("🔧 REGEN_START: Cleared existing plot image")
        
        guard let pythonPath = findPython(),
              let ddquintPath = findDDQuint() else {
            writeDebugLog("❌ REGEN_ERROR: Python or ddQuint not found")
            hideCornerSpinner()
            showError("Python or ddQuint not found")
            return
        }
        
        writeDebugLog("🔧 REGEN_START: Python path: \(pythonPath)")
        writeDebugLog("🔧 REGEN_START: ddQuint path: \(ddquintPath)")
        
        // Save well-specific parameters to a temporary file for Python to use
        let wellParams = wellParametersMap[wellName] ?? [:]
        writeDebugLog("🔧 REGEN_PARAMS: Well \(wellName) has \(wellParams.count) custom parameters")
        writeDebugLog("🔧 REGEN_PARAMS: Parameter keys: \(Array(wellParams.keys).sorted())")
        for (key, value) in wellParams {
            writeDebugLog("🔧 REGEN_PARAMS: \(key) = \(value)")
        }
        let tempParamsFile = saveWellParametersToTempFile(wellParams, wellName: wellName)
        writeDebugLog("🔧 REGEN_PARAMS: Temp params file: \(tempParamsFile ?? "none")")
        
        DispatchQueue.global().async { [weak self] in
            let process = Process()
            process.executableURL = URL(fileURLWithPath: pythonPath)
            
            // Set environment for matplotlib and template settings
            var env = (process.environment ?? ProcessInfo.processInfo.environment).merging([
                "MPLBACKEND": "Agg",
                "PYTHONDONTWRITEBYTECODE": "1",
                "PYTHONUNBUFFERED": "1"  // Enable real-time output to prevent pipe buffer deadlock
            ]) { _, new in new }
            env["DDQ_TEMPLATE_DESC_COUNT"] = String(self?.templateDescriptionCount ?? 4)
            if let tpl = self?.templateFileURL?.path { env["DDQ_TEMPLATE_PATH"] = tpl }
            process.environment = env
            
            let escapedCSVPath = csvFile.path.replacingOccurrences(of: "'", with: "\\'")
            let escapedDDQuintPath = ddquintPath.replacingOccurrences(of: "'", with: "\\'")
            let escapedParamFile = tempParamsFile?.replacingOccurrences(of: "'", with: "\\'") ?? ""
            let escapedTemplatePath = self?.templateFileURL?.path.replacingOccurrences(of: "'", with: "\\'") ?? ""
            let templateCount = self?.templateDescriptionCount ?? 4
            
            // Use inline Python approach (like main analysis and plot generation)
            process.arguments = [
                "-c",
                """
                import sys, os, tempfile, json, logging
                sys.path.insert(0, '\(escapedDDQuintPath)')
                
                # Force regeneration by removing existing plot file FIRST
                temp_base = tempfile.gettempdir()
                graphs_dir = os.path.join(temp_base, 'ddquint_analysis_plots')
                os.makedirs(graphs_dir, exist_ok=True)
                existing_plot = os.path.join(graphs_dir, '\(wellName).png')
                if os.path.exists(existing_plot):
                    os.remove(existing_plot)
                    print(f'EARLY_REMOVAL: Removed existing plot file to force regeneration: {existing_plot}')
                
                try:
                    # Initialize logging to capture debug output
                    from ddquint.config.logging_config import setup_logging
                    log_file = setup_logging(debug=True)
                    print(f'Logging initialized: {log_file}')
                    
                    # Also add a handler that prints to stdout so we see logs in debug.log
                    import logging
                    stdout_handler = logging.StreamHandler(sys.stdout)
                    stdout_handler.setLevel(logging.DEBUG)
                    stdout_handler.setFormatter(logging.Formatter('DDQUINT_LOG: %(name)s - %(levelname)s - %(message)s'))
                    logging.getLogger().addHandler(stdout_handler)
                    
                    from ddquint.config import Config
                    from ddquint.utils.parameter_editor import load_parameters_if_exist
                    from ddquint.core.file_processor import process_csv_file
                    from ddquint.utils.template_parser import parse_template_file as _ptf
                    
                    # Initialize config
                    config = Config.get_instance()
                    load_parameters_if_exist(Config)
                    
                    # Load well-specific parameters if available
                    print(f'Parameter file path: {repr("\(escapedParamFile)")}')
                    print(f'Parameter file exists: {os.path.exists("\(escapedParamFile)") if "\(escapedParamFile)" else False}')
                    
                    if '\(escapedParamFile)' and os.path.exists('\(escapedParamFile)'):
                        with open('\(escapedParamFile)', 'r') as f:
                            custom_params = json.load(f)
                        
                        print(f'Loaded {len(custom_params)} custom parameters: {list(custom_params.keys())}')
                        
                        # Apply custom parameters using new Config context API
                        print(f'Config instance id: {id(config)}')
                        
                        # Extract well ID from the current processing context
                        well_id = '\(wellName)'
                        config.set_well_context(well_id, custom_params)
                        print(f'Set well context for {well_id} with {len(custom_params)} parameter overrides')
                        
                        # Debug verification
                        print(f'Current well context: {config.get_current_well_context()}')
                        print(f'get_expected_centroids(): {config.get_expected_centroids()}')
                    else:
                        print('No custom parameters file found or file does not exist')
                    
                    config.finalize_colors()
                    
                    # Get sample names using explicit template path if available
                    folder_path = os.path.dirname('\(escapedCSVPath)')
                    template_path = '\(escapedTemplatePath)'
                    sample_names = {}
                    if template_path:
                        try:
                            sample_names = _ptf(template_path, description_count=\(templateCount))
                        except Exception as e:
                            print(f'DEBUG:TEMPLATE_PARSE_ERROR {e}')
                            sample_names = {}
                    if not sample_names:
                        try:
                            # Search for a template file then parse with desired description count  
                            found = _ftf(folder_path)
                            if found:
                                sample_names = _ptf(found, description_count=\(templateCount))
                            else:
                                sample_names = {}
                        except Exception as e:
                            print(f'DEBUG:TEMPLATE_FALLBACK_ERROR {e}')
                            sample_names = {}
                    
                    # Process the CSV file (this will regenerate the plot)
                    print('DEBUG: About to call process_csv_file for well \(wellName)')
                    print(f'DEBUG: CSV path: \(escapedCSVPath)')  
                    print(f'DEBUG: graphs_dir: {graphs_dir}')
                    print(f'DEBUG: sample_names: {sample_names}')
                    try:
                        print('DEBUG: Calling process_csv_file now...')
                        result = process_csv_file('\(escapedCSVPath)', graphs_dir, sample_names, verbose=True)
                        print('DEBUG: process_csv_file call completed successfully')
                        print(f'DEBUG: process_csv_file returned result type: {type(result)}')
                        print(f'DEBUG: result is None: {result is None}')
                        print(f'DEBUG: result bool value: {bool(result)}')
                        if result is None:
                            print('DEBUG: ERROR - process_csv_file returned None!')
                        elif isinstance(result, dict):
                            print(f'DEBUG: result keys: {list(result.keys())}')
                            print(f'DEBUG: has_buffer_zone: {result.get("has_buffer_zone", "MISSING")}')
                            print(f'DEBUG: has_aneuploidy: {result.get("has_aneuploidy", "MISSING")}')
                            print(f'DEBUG: error: {result.get("error", "MISSING")}')
                        else:
                            print(f'DEBUG: result is not dict: {str(result)[:200]}')
                    except Exception as e:
                        print(f'DEBUG: EXCEPTION in process_csv_file: {str(e)}')
                        result = None
                    
                    # Check if plot was created
                    plot_path = os.path.join(graphs_dir, '\(wellName).png')
                    print(f'Looking for plot at: {plot_path}')
                    print(f'Plot exists: {os.path.exists(plot_path)}')
                    if os.path.exists(plot_path):
                        # Copy to /tmp/ location like working plot generation does
                        import shutil
                        temp_plot_path = '/tmp/ddquint_plot_\(wellName).png'
                        
                        # Remove existing temp file if it exists
                        if os.path.exists(temp_plot_path):
                            os.remove(temp_plot_path)
                            print(f'Removed existing temp file: {temp_plot_path}')
                        
                        shutil.copy2(plot_path, temp_plot_path)
                        print(f'Copied plot to: {temp_plot_path}')
                        print(f'Temp file exists: {os.path.exists(temp_plot_path)}')
                        print(f'Temp file size: {os.path.getsize(temp_plot_path) if os.path.exists(temp_plot_path) else "N/A"}')
                        print(f'PLOT_CREATED:{temp_plot_path}')
                        
                        # Output complete analysis results for cache update
                        if result and isinstance(result, dict):
                            # Create serializable result
                            serializable_result = {
                                'well': '\(wellName)',
                                'status': 'regenerated',
                                'plot_path': plot_path
                            }
                            
                            # Add all analysis data
                            for key, value in result.items():
                                if key in ['df_filtered', 'df_original']:
                                    continue  # Skip DataFrames
                                try:
                                    json.dumps(value)  # Test serialization
                                    serializable_result[key] = value
                                except (TypeError, ValueError):
                                    if isinstance(value, (tuple, set)):
                                        serializable_result[key] = list(value)
                                    # Skip other non-serializable values
                            
                            # Ensure sample name exists
                            if 'sample_name' not in serializable_result:
                                if '\(wellName)' in sample_names:
                                    serializable_result['sample_name'] = sample_names['\(wellName)']
                                else:
                                    serializable_result['sample_name'] = '\(wellName)'
                            
                            # Explicitly include status flags for proper classification (critical for UI updates)
                            serializable_result['has_buffer_zone'] = bool(result.get('has_buffer_zone', False))
                            serializable_result['has_aneuploidy'] = bool(result.get('has_aneuploidy', False))
                            if result.get('error'):
                                serializable_result['error'] = str(result.get('error'))
                            
                            print(f'UPDATED_RESULT:{json.dumps(serializable_result)}')
                        else:
                            # Fallback result with proper status flags
                            fallback_result = {
                                'well': '\(wellName)',
                                'status': 'regenerated',
                                'plot_path': plot_path,
                                'has_buffer_zone': False,
                                'has_aneuploidy': False
                            }
                            print(f'UPDATED_RESULT:{json.dumps(fallback_result)}')
                    else:
                        print('Plot not found for \(wellName)')
                        print('REGENERATION_FAILED')
                        
                except Exception as e:
                    print(f'ERROR: {str(e)}')
                    import traceback
                    traceback.print_exc()
                """
            ]
            
            self?.writeDebugLog("🔧 REGEN: Using inline Python approach")
            
            let outputPipe = Pipe()
            let errorPipe = Pipe()
            process.standardOutput = outputPipe
            process.standardError = errorPipe
            
            do {
                self?.writeDebugLog("🔧 REGEN: Starting process...")
                try process.run()
                self?.writeDebugLog("🔧 REGEN: Process started, waiting for completion...")
                
                // Set up continuous pipe draining to prevent deadlock
                var outputBuffer = ""
                var errorBuffer = ""
                let outputHandle = outputPipe.fileHandleForReading
                let errorHandle = errorPipe.fileHandleForReading
                
                outputHandle.readabilityHandler = { handle in
                    let data = handle.availableData
                    if data.count > 0, let string = String(data: data, encoding: .utf8) {
                        outputBuffer += string
                    }
                }
                
                errorHandle.readabilityHandler = { handle in
                    let data = handle.availableData
                    if data.count > 0, let string = String(data: data, encoding: .utf8) {
                        errorBuffer += string
                    }
                }
                
                // Add timeout handling
                DispatchQueue.global(qos: .userInitiated).async {
                    process.waitUntilExit()
                    
                    // Clean up handlers and read any remaining data
                    DispatchQueue.main.async {
                        outputHandle.readabilityHandler = nil
                        errorHandle.readabilityHandler = nil
                        
                        // Read any final data
                        let finalOutputData = outputHandle.readDataToEndOfFile()
                        let finalErrorData = errorHandle.readDataToEndOfFile()
                        
                        if let finalOutput = String(data: finalOutputData, encoding: .utf8) {
                            outputBuffer += finalOutput
                        }
                        if let finalError = String(data: finalErrorData, encoding: .utf8) {
                            errorBuffer += finalError
                        }
                        
                        // Use the buffered output instead of reading from pipe again
                        let output = outputBuffer
                        let errorOutput = errorBuffer
                        
                        DispatchQueue.main.async { [weak self] in
                        self?.hideCornerSpinner()
                        self?.writeDebugLog("🔧 REGEN: Process completed with exit code: \(process.terminationStatus)")
                        self?.writeDebugLog("🔧 REGEN_OUTPUT: Raw output length: \(output.count) characters")
                        self?.writeDebugLog("🔧 REGEN_OUTPUT: First 500 chars: \(String(output.prefix(500)))")
                        
                        if !errorOutput.isEmpty {
                            self?.writeDebugLog("🔧 REGEN_ERROR: Error output length: \(errorOutput.count) characters")
                            self?.writeDebugLog("🔧 REGEN_ERROR: \(String(errorOutput.prefix(500)))")
                        }
                        
                        self?.writeDebugLog("🔧 REGEN_OUTPUT: Contains EARLY_REMOVAL: \(output.contains("EARLY_REMOVAL"))")
                        self?.writeDebugLog("🔧 REGEN_OUTPUT: Contains PLOT_CREATED: \(output.contains("PLOT_CREATED"))")
                        self?.writeDebugLog("🔧 REGEN_OUTPUT: Contains UPDATED_RESULT: \(output.contains("UPDATED_RESULT"))")
                        self?.writeDebugLog("🔧 REGEN_OUTPUT: Contains ERROR: \(output.contains("ERROR") || !errorOutput.isEmpty)")
                        
                        // Check for exit code errors
                        if process.terminationStatus != 0 {
                            self?.writeDebugLog("🔧 REGEN_ERROR: Process failed with exit code \(process.terminationStatus)")
                            self?.showError("Plot regeneration failed with exit code \(process.terminationStatus)")
                        }
                        
                        // Process the output
                        self?.handleWellRegenerationResult(output: output, wellName: wellName)
                        }
                    }
                }
                
                // Add timeout mechanism - increased from 30 to 60 seconds
                DispatchQueue.main.asyncAfter(deadline: .now() + 60) { [weak self] in
                    if process.isRunning {
                        self?.writeDebugLog("🔧 REGEN_TIMEOUT: Process timed out after 60 seconds, terminating...")
                        process.terminate()
                        self?.hideCornerSpinner()
                        self?.showError("Plot regeneration timed out after 60 seconds")
                    }
                }
                
            } catch {
                DispatchQueue.main.async { [weak self] in
                    self?.hideCornerSpinner()
                    self?.writeDebugLog("🔧 REGEN_ERROR: Failed to start process: \(error)")
                    self?.showError("Failed to regenerate plot: \(error.localizedDescription)")
                }
            }
        }
    }
    
    private func handleWellRegenerationResult(output: String, wellName: String) {
        print("Regeneration output for \(wellName): \(output)")
        writeDebugLog("=====WELL REGENERATION DEBUG=====")
        writeDebugLog("Well: \(wellName)")
        writeDebugLog("Output: \(output)")
        writeDebugLog("Output contains UPDATED_RESULT: \(output.contains("UPDATED_RESULT"))")
        writeDebugLog("Output contains ERROR: \(output.contains("ERROR"))")
        writeDebugLog("Output contains DEBUG: \(output.contains("DEBUG"))")
        writeDebugLog("==================================")
        
        // Update cached results if we got updated analysis data
        if let resultStart = output.range(of: "UPDATED_RESULT:")?.upperBound {
            let remainingOutput = String(output[resultStart...])
            // Extract JSON until end of line or end of output
            let resultJson = remainingOutput.components(separatedBy: .newlines).first?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
            if !resultJson.isEmpty {
                updateCachedResultForWell(wellName: wellName, resultJson: resultJson)
                // Update wellData status based on new result
                if let data = resultJson.data(using: .utf8),
                   let resultObj = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
                   let idx = wellData.firstIndex(where: { $0.well == wellName }) {
                    let newStatus = determineWellStatus(from: resultObj, wellName: wellName)
                    let edited = isWellEdited(wellName)
                    let current = wellData[idx]
                    wellData[idx] = WellData(well: current.well,
                                              sampleName: current.sampleName,
                                              dropletCount: current.dropletCount,
                                              hasData: current.hasData,
                                              status: newStatus,
                                              isEdited: edited)
                    applyFilters()
                    // Reload specific row if still visible
                    if let filteredIdx = filteredWellData.firstIndex(where: { $0.well == wellName }) {
                        let tableRow = (compositeImagePath != nil) ? filteredIdx + 1 : filteredIdx
                        wellListView.reloadData(forRowIndexes: IndexSet(integer: tableRow), columnIndexes: IndexSet(integer: 0))
                    }
                }
            } else {
                print("⚠️ Empty result JSON for well \(wellName)")
            }
        }
        
        if let plotStart = output.range(of: "PLOT_CREATED:")?.upperBound {
            let rawPlotPath = String(output[plotStart...])
            let plotPath = rawPlotPath.trimmingCharacters(in: .whitespacesAndNewlines)
            
            writeDebugLog("Raw plot path from output: '\(rawPlotPath)'")
            writeDebugLog("Trimmed plot path: '\(plotPath)'")
            writeDebugLog("Plot path length: \(plotPath.count)")
            writeDebugLog("Plot path contains newline: \(plotPath.contains("\\n"))")
            
            // Extract just the first line in case there are multiple lines
            let firstLineOnly = plotPath.components(separatedBy: .newlines).first ?? plotPath
            writeDebugLog("First line only: '\(firstLineOnly)'")
            
            writeDebugLog("Attempting to load plot from: \(firstLineOnly)")
            writeDebugLog("File exists: \(FileManager.default.fileExists(atPath: firstLineOnly))")
            
            if FileManager.default.fileExists(atPath: firstLineOnly) {
                if let image = NSImage(contentsOfFile: firstLineOnly) {
                    writeDebugLog("Successfully loaded image from: \(firstLineOnly)")
                    plotImageView.image = image
                    ensurePlotFillsArea()
                    statusLabel.stringValue = "Plot regenerated for \(wellName) with new parameters"
                    
                    // Refresh the well list to show any visual changes from regeneration
                    if let wellIndex = wellData.firstIndex(where: { $0.well == wellName }) {
                        wellListView.reloadData(forRowIndexes: IndexSet(integer: wellIndex), columnIndexes: IndexSet(integer: 0))
                    }
                } else {
                    writeDebugLog("Failed to create NSImage from existing file: \(firstLineOnly)")
                    statusLabel.stringValue = "Failed to load regenerated plot for \(wellName) - image creation failed"
                }
            } else {
                writeDebugLog("Plot file does not exist at: \(firstLineOnly)")
                statusLabel.stringValue = "Failed to load regenerated plot for \(wellName) - file not found"
            }
        } else if output.contains("NO_PLOT_GENERATED") {
            statusLabel.stringValue = "No plot could be generated for \(wellName)"
        } else if output.contains("PROCESSING_FAILED") {
            statusLabel.stringValue = "Processing failed for \(wellName)"
        } else if output.contains("ERROR:") {
            statusLabel.stringValue = "Error regenerating plot for \(wellName)"
        } else {
            statusLabel.stringValue = "Unknown result for \(wellName) regeneration"
        }
    }
    
    private func updateCachedResultForWell(wellName: String, resultJson: String) {
        writeDebugLog("🔄 updateCachedResultForWell called for well: \(wellName)")
        writeDebugLog("🔄 JSON length: \(resultJson.count) characters")
        writeDebugLog("🔄 JSON preview: \(String(resultJson.prefix(200)))")
        
        do {
            let data = resultJson.data(using: .utf8) ?? Data()
            if let updatedResult = try JSONSerialization.jsonObject(with: data, options: []) as? [String: Any] {
                writeDebugLog("🔄 Successfully parsed JSON result")
                writeDebugLog("🔄 Result keys: \(updatedResult.keys.sorted())")
                writeDebugLog("🔄 has_buffer_zone: \(updatedResult["has_buffer_zone"] ?? "MISSING")")
                writeDebugLog("🔄 has_aneuploidy: \(updatedResult["has_aneuploidy"] ?? "MISSING")")
                writeDebugLog("🔄 error: \(updatedResult["error"] ?? "MISSING")")
                
                // Find and update the corresponding entry in cachedResults
                if let index = cachedResults.firstIndex(where: { ($0["well"] as? String) == wellName }) {
                    cachedResults[index] = updatedResult
                    print("✅ Updated cached results for well \(wellName)")
                    writeDebugLog("✅ Updated cached results for well \(wellName)")
                } else {
                    // If not found, append it
                    cachedResults.append(updatedResult)
                    print("✅ Added new cached result for well \(wellName)")
                    writeDebugLog("✅ Added new cached result for well \(wellName)")
                }
                
                // Persist updated cache to file
                if let folderURL = selectedFolderURL {
                    cacheTimestamp = Date()
                    persistCacheToFile(folderURL: folderURL)
                }
            }
        } catch {
            print("⚠️ Failed to parse updated result for well \(wellName): \(error)")
        }
    }
    
    // MARK: - Export Methods
    
    private func exportExcelFile(to saveURL: URL, sourceFolder: URL) {
        statusLabel.stringValue = "Exporting Excel file..."
        
        // Try loading from cache file if not in memory
        print("🔍 EXCEL_DEBUG: Checking cache before export")
        print("   cachedResults.isEmpty: \(cachedResults.isEmpty)")
        print("   current cacheKey: \(cacheKey ?? "nil")")
        
        if cachedResults.isEmpty || cacheKey != generateCacheKey(folderURL: sourceFolder) {
            print("🔍 EXCEL_DEBUG: Attempting to load cache from file")
            let loaded = loadCacheFromFile(folderURL: sourceFolder)
            print("   cache load result: \(loaded)")
        } else {
            print("🔍 EXCEL_DEBUG: Using existing in-memory cache")
        }
        
        let currentCacheKey = generateCacheKey(folderURL: sourceFolder)
        
        writeDebugLog("🔍 EXCEL_DEBUG: currentCacheKey = \(currentCacheKey)")
        writeDebugLog("🔍 EXCEL_DEBUG: existing cacheKey = \(cacheKey ?? "nil")")
        writeDebugLog("🔍 EXCEL_DEBUG: cachedResults.count = \(cachedResults.count)")
        writeDebugLog("🔍 EXCEL_DEBUG: cachedResults sample = \(cachedResults.first?.keys.sorted() ?? [])")
        
        // Always use cached results for Excel export - no fallback to full analysis
        if let existingKey = cacheKey, existingKey == currentCacheKey, !cachedResults.isEmpty {
            writeDebugLog("✅ EXCEL_DEBUG: Using cached results for Excel export")
            statusLabel.stringValue = "Exporting Excel file from cached results..."
            exportExcelFromCachedResults(to: saveURL, sourceFolder: sourceFolder)
            return
        }
        
        // If no cache is available, prompt user to run analysis first
        showError("No analysis results found. Please run analysis on this folder first before exporting.")
        statusLabel.stringValue = "Excel export cancelled - no cached results available"
    }
    
    private func exportExcelFromCachedResults(to saveURL: URL, sourceFolder: URL) {
        guard let pythonPath = findPython(),
              let ddquintPath = findDDQuint() else {
            showError("Python or ddQuint not found")
            return
        }
        
        // Calculate maximum target count for proper Excel columns
        let maxTargetCount = getMaxTargetCount()
        
        DispatchQueue.global().async { [weak self] in
            guard let self = self else { return }
            
            // Save cachedResults to temporary JSON file
            do {
                let jsonData = try JSONSerialization.data(withJSONObject: self.cachedResults, options: [.prettyPrinted])
                let tempDir = FileManager.default.temporaryDirectory
                let tempJsonFile = tempDir.appendingPathComponent("ddquint_cached_results_\(UUID().uuidString).json")
                
                try jsonData.write(to: tempJsonFile)
                print("💾 Saved cached results to temp file: \(tempJsonFile.path)")
                
                self.executeExcelExportWithTempFile(tempJsonFile: tempJsonFile, saveURL: saveURL, ddquintPath: ddquintPath, pythonPath: pythonPath, maxTargetCount: maxTargetCount)
                
            } catch {
                DispatchQueue.main.async {
                    self.showError("Failed to serialize cached results: \(error)")
                }
                return
            }
        }
    }
    
    private func executeExcelExportWithTempFile(tempJsonFile: URL, saveURL: URL, ddquintPath: String, pythonPath: String, maxTargetCount: Int) {
        let process = Process()
        process.executableURL = URL(fileURLWithPath: pythonPath)
        
        process.environment = (process.environment ?? ProcessInfo.processInfo.environment).merging([
            "MPLBACKEND": "Agg",
            "PYTHONDONTWRITEBYTECODE": "1"
        ]) { _, new in new }
        
        let escapedSavePath = saveURL.path.replacingOccurrences(of: "'", with: "\\'")
        let escapedDDQuintPath = ddquintPath.replacingOccurrences(of: "'", with: "\\'")
        let escapedTempJsonPath = tempJsonFile.path.replacingOccurrences(of: "'", with: "\\'")
        
        process.arguments = [
            "-c",
            """
            import sys
            import json
            import traceback
            import os
            
            try:
                sys.path.insert(0, '\(escapedDDQuintPath)')
                
                # Initialize config
                from ddquint.config import Config
                from ddquint.utils.parameter_editor import load_parameters_if_exist
                
                config = Config.get_instance()
                load_parameters_if_exist(Config)
                config.finalize_colors()
                
                # Import create_list_report
                from ddquint.core import create_list_report
                
                # Load cached results from temp file
                with open('\(escapedTempJsonPath)', 'r') as f:
                    results = json.load(f)
                
                print(f'DEBUG: Loaded {len(results)} cached results for Excel export')
                
                # Export to Excel using cached results with max target count
                create_list_report(results, '\(escapedSavePath)', \(maxTargetCount))
                print('EXCEL_EXPORT_SUCCESS_CACHED')
                
                # Clean up temp file
                os.remove('\(escapedTempJsonPath)')
                
            except Exception as e:
                print(f'EXPORT_ERROR: {e}')
                traceback.print_exc()
                sys.exit(1)
            """
        ]
        
        let outputPipe = Pipe()
        let errorPipe = Pipe()
        process.standardOutput = outputPipe
        process.standardError = errorPipe
        
        do {
            try process.run()
            process.waitUntilExit()
            
            let outputData = outputPipe.fileHandleForReading.readDataToEndOfFile()
            let output = String(data: outputData, encoding: .utf8) ?? ""
            
            let errorData = errorPipe.fileHandleForReading.readDataToEndOfFile()
            let errorOutput = String(data: errorData, encoding: .utf8) ?? ""
            
            DispatchQueue.main.async { [weak self] in
                self?.writeDebugLog("🔍 EXCEL_CACHED_OUTPUT: \(output)")
                self?.writeDebugLog("🔍 EXCEL_CACHED_ERROR: \(errorOutput)")
                self?.writeDebugLog("🔍 EXCEL_CACHED_EXIT_CODE: \(process.terminationStatus)")
                
                if output.contains("EXCEL_EXPORT_SUCCESS") || output.contains("EXCEL_EXPORT_SUCCESS_CACHED") {
                    self?.statusLabel.stringValue = "Excel export completed successfully"
                    NSWorkspace.shared.activateFileViewerSelecting([saveURL])
                } else {
                    self?.statusLabel.stringValue = "Excel export failed"
                    self?.showError("Failed to export Excel file from cached results")
                }
            }
        } catch {
            DispatchQueue.main.async { [weak self] in
                self?.statusLabel.stringValue = "Excel export failed"
                self?.showError("Failed to run Excel export: \(error)")
            }
        }
    }
    
    private func exportExcelFromResultsFile(resultsPath: URL, to saveURL: URL, sourceFolder: URL) {
        guard let pythonPath = findPython(),
              let ddquintPath = findDDQuint() else {
            showError("Python or ddQuint not found")
            return
        }
        
        // Calculate maximum target count for proper Excel columns
        let maxTargetCount = getMaxTargetCount()
        
        DispatchQueue.global().async { [weak self] in
            let process = Process()
            process.executableURL = URL(fileURLWithPath: pythonPath)
            
            process.environment = (process.environment ?? ProcessInfo.processInfo.environment).merging([
                "MPLBACKEND": "Agg",
                "PYTHONDONTWRITEBYTECODE": "1"
            ]) { _, new in new }
            
            let escapedResultsPath = resultsPath.path.replacingOccurrences(of: "'", with: "\\'")
            let escapedSavePath = saveURL.path.replacingOccurrences(of: "'", with: "\\'")
            let escapedDDQuintPath = ddquintPath.replacingOccurrences(of: "'", with: "\\'")
            
            process.arguments = [
                "-c",
                """
                import sys
                import json
                import traceback
                
                try:
                    sys.path.insert(0, '\(escapedDDQuintPath)')
                    
                    # Initialize config
                    from ddquint.config import Config
                    from ddquint.utils.parameter_editor import load_parameters_if_exist
                    
                    config = Config.get_instance()
                    load_parameters_if_exist(Config)
                    config.finalize_colors()
                    
                    # Import create_list_report
                    from ddquint.core import create_list_report
                    
                    # Load results from existing file
                    with open('\(escapedResultsPath)', 'r') as f:
                        results = json.load(f)
                    
                    # Export to Excel using existing results with max target count
                    create_list_report(results, '\(escapedSavePath)', \(maxTargetCount))
                    print('EXCEL_EXPORT_SUCCESS_FROM_FILE')
                    
                except Exception as e:
                    print(f'EXPORT_ERROR: {e}')
                    traceback.print_exc()
                    sys.exit(1)
                """
            ]
            
            let outputPipe = Pipe()
            process.standardOutput = outputPipe
            
            do {
                try process.run()
                process.waitUntilExit()
                
                let outputData = outputPipe.fileHandleForReading.readDataToEndOfFile()
                let output = String(data: outputData, encoding: .utf8) ?? ""
                
                DispatchQueue.main.async {
                    if output.contains("EXCEL_EXPORT_SUCCESS_FROM_FILE") {
                        self?.statusLabel.stringValue = "Excel export completed successfully"
                        NSWorkspace.shared.activateFileViewerSelecting([saveURL])
                    } else {
                        self?.statusLabel.stringValue = "Excel export failed"
                        self?.showError("Failed to export Excel file from results file")
                    }
                }
            } catch {
                DispatchQueue.main.async {
                    self?.statusLabel.stringValue = "Excel export failed"
                    self?.showError("Failed to run Excel export: \(error)")
                }
            }
        }
    }
    
    private func exportAllPlots(to exportURL: URL, sourceFolder: URL) {
        statusLabel.stringValue = "Exporting all plots..."
        
        guard let pythonPath = findPython(),
              let ddquintPath = findDDQuint() else {
            showError("Python or ddQuint not found")
            return
        }
        
        DispatchQueue.global().async { [weak self] in
            let process = Process()
            process.executableURL = URL(fileURLWithPath: pythonPath)
            
            // Hide matplotlib windows from dock and pass template settings
            var env = (process.environment ?? ProcessInfo.processInfo.environment).merging([
                "MPLBACKEND": "Agg",
                "PYTHONDONTWRITEBYTECODE": "1"
            ]) { _, new in new }
            // Template settings for Python template_parser
            env["DDQ_TEMPLATE_DESC_COUNT"] = String(self?.templateDescriptionCount ?? 4)
            if let tpl = self?.templateFileURL?.path { env["DDQ_TEMPLATE_PATH"] = tpl }
            process.environment = env
            
            let escapedSourcePath = sourceFolder.path.replacingOccurrences(of: "'", with: "\\'")
            let escapedExportPath = exportURL.path.replacingOccurrences(of: "'", with: "\\'")
            let escapedDDQuintPath = ddquintPath.replacingOccurrences(of: "'", with: "\\'")
            
            process.arguments = [
                "-c",
                """
                import sys
                import traceback
                
                try:
                    sys.path.insert(0, '\(escapedDDQuintPath)')
                    
                    # Initialize config properly
                    from ddquint.config import Config
                    from ddquint.utils.parameter_editor import load_parameters_if_exist
                    
                    config = Config.get_instance()
                    load_parameters_if_exist(Config)
                    config.finalize_colors()
                    
                    # Import modules
                    from ddquint.core import process_directory
                    from ddquint.utils import get_sample_names
                    from ddquint.visualization import create_well_plot, create_composite_image
                    import os
                    
                    # Simply copy existing plots from temp directory (no need to regenerate)
                    import os
                    import shutil
                    import glob
                    import tempfile
                    
                    # Look for existing plots in the temp directory
                    temp_base = tempfile.gettempdir()
                    graphs_dir = os.path.join(temp_base, 'ddquint_analysis_plots')
                    
                    if not os.path.exists(graphs_dir):
                        print('No plots found in temp directory. Please run analysis first.')
                        sys.exit(1)
                    
                    # Find all PNG files in the Graphs directory
                    plot_files = glob.glob(os.path.join(graphs_dir, '*.png'))
                    
                    if not plot_files:
                        print('No plot files found in Graphs directory.')
                        sys.exit(1)
                    
                    # Copy each plot to the export directory
                    plot_count = 0
                    for plot_path in plot_files:
                        filename = os.path.basename(plot_path)
                        well_id = os.path.splitext(filename)[0]
                        export_plot_path = os.path.join('\(escapedExportPath)', f'{well_id}_plot.png')
                        
                        try:
                            shutil.copy2(plot_path, export_plot_path)
                            plot_count += 1
                        except Exception as e:
                            print(f'Error copying {filename}: {e}')
                    
                    print(f'PLOTS_EXPORT_SUCCESS: {plot_count} individual well plots exported')
                    
                except Exception as e:
                    print(f'EXPORT_ERROR: {e}')
                    traceback.print_exc()
                    sys.exit(1)
                """
            ]
            
            let outputPipe = Pipe()
            process.standardOutput = outputPipe
            
            do {
                try process.run()
                process.waitUntilExit()
                
                let outputData = outputPipe.fileHandleForReading.readDataToEndOfFile()
                let output = String(data: outputData, encoding: .utf8) ?? ""
                
                DispatchQueue.main.async {
                    if output.contains("PLOTS_EXPORT_SUCCESS") {
                        self?.statusLabel.stringValue = "Plot export completed successfully"
                        NSWorkspace.shared.activateFileViewerSelecting([exportURL])
                    } else {
                        self?.statusLabel.stringValue = "Plot export failed"
                        self?.showError("Failed to export plots")
                    }
                }
            } catch {
                DispatchQueue.main.async {
                    self?.statusLabel.stringValue = "Plot export failed"
                    self?.showError("Failed to run plot export: \(error)")
                }
            }
        }
    }
    
    // MARK: - Template File Support
    
    func setTemplateFile(_ url: URL) {
        templateFileURL = url
        statusLabel.stringValue = "Template file selected: \(url.lastPathComponent)"
    }

    func getTemplateDescriptionCount() -> Int { templateDescriptionCount }

    func setTemplateDescriptionCount(_ count: Int) {
        guard (1...4).contains(count) else { return }
        templateDescriptionCount = count
        statusLabel.stringValue = "Using \(count) sample description field(s)"
        UserDefaults.standard.set(count, forKey: userDefaultsDescCountKey)
        writeDebugLog("🧩 Persisted Sample Description Fields: \(count)")
    }

    func applyTemplateChangeAndReanalyze() {
        // If a folder is selected, re-run analysis so names and plots update
        guard let folderURL = selectedFolderURL else { return }
        // Clear caches and restart
        invalidateCache()
        wellData.removeAll()
        filteredWellData.removeAll()
        wellListView.reloadData()
        showPlaceholderImage()
        startAnalysis(folderURL: folderURL)
    }
    
    // MARK: - Export/Import Parameters Bundle
    
    func exportParametersBundle() {
        // Gather current parameters
        let globalParams = loadGlobalParameters()
        let bundle: [String: Any] = [
            "global_parameters": globalParams,
            "well_parameters": wellParametersMap,
            "template_description_count": templateDescriptionCount,
            "template_file": templateFileURL?.path ?? NSNull()
        ]
        
        // Show save panel
        let savePanel = NSSavePanel()
        savePanel.title = "Export Parameters"
        savePanel.prompt = "Export"
        savePanel.allowedContentTypes = [.json]
        savePanel.nameFieldStringValue = "ddQuint_parameters.json"
        if let last = lastURL(for: "LastDir.ParametersExport") { savePanel.directoryURL = last }
        
        let response = savePanel.runModal()
        if response == .OK, let url = savePanel.url {
            setLastURL(url.deletingLastPathComponent(), for: "LastDir.ParametersExport")
            do {
                let data = try JSONSerialization.data(withJSONObject: bundle, options: .prettyPrinted)
                try data.write(to: url)
                statusLabel.stringValue = "Parameters exported to \(url.lastPathComponent)"
            } catch {
                showError("Failed to export parameters: \(error.localizedDescription)")
            }
        }
    }
    
    func importParametersBundle() {
        // Open panel
        let openPanel = NSOpenPanel()
        openPanel.canChooseFiles = true
        openPanel.canChooseDirectories = false
        openPanel.allowsMultipleSelection = false
        openPanel.allowedContentTypes = [.json]
        if let last = lastURL(for: "LastDir.ParametersImport") { openPanel.directoryURL = last }
        openPanel.prompt = "Load"
        openPanel.message = "Choose a ddQuint parameters JSON file"
        
        let response = openPanel.runModal()
        guard response == .OK, let url = openPanel.url else { return }
        setLastURL(url.deletingLastPathComponent(), for: "LastDir.ParametersImport")
        
        do {
            let data = try Data(contentsOf: url)
            guard let obj = try JSONSerialization.jsonObject(with: data) as? [String: Any] else {
                showError("Invalid parameters file format")
                return
            }
            
            // Load global parameters (if present)
            if let globals = obj["global_parameters"] as? [String: Any] {
                saveParametersToFile(globals)
            }
            
            // Load well-specific parameters
            if let wells = obj["well_parameters"] as? [String: Any] {
                var map: [String: [String: Any]] = [:]
                for (well, value) in wells {
                    if let dict = value as? [String: Any] {
                        map[well] = dict
                    }
                }
                wellParametersMap = map
            }
            
            // Apply template settings if present
            if let count = obj["template_description_count"] as? Int, (1...4).contains(count) {
                templateDescriptionCount = count
                UserDefaults.standard.set(count, forKey: userDefaultsDescCountKey)
            }
            if let tpl = obj["template_file"] as? String, !tpl.isEmpty {
                templateFileURL = URL(fileURLWithPath: tpl)
            }
            
            statusLabel.stringValue = "Parameters loaded. Re-running analysis..."
            applyTemplateChangeAndReanalyze()
        } catch {
            showError("Failed to load parameters: \(error.localizedDescription)")
        }
    }

    // MARK: - Template Creator
    
    func openTemplateDesigner() {
        // Single instance
        if templateDesigner == nil {
            templateDesigner = TemplateCreatorWindowController(findPython: { [weak self] in self?.findPython() },
                                                               findDDQuint: { [weak self] in self?.findDDQuint() })
        }
        templateDesigner?.showWindow(nil)
        templateDesigner?.window?.makeKeyAndOrderFront(nil)
    }
    
    
}

extension InteractiveMainWindowController {
    // Filter well data based on current filter settings
    func applyFilters() {
        // Preserve current selection by well ID
        var selectedWellId: String? = nil
        if selectedWellIndex >= 0 && selectedWellIndex < wellData.count {
            selectedWellId = wellData[selectedWellIndex].well
        }
        
        // Recompute filtered list from current wellData
        filteredWellData = wellData.filter { well in
            if hideBufferZones && well.status == .buffer { return false }
            if hideWarnings && well.status == .warning { return false }
            return true
        }
        
        // Reload table
        wellListView.reloadData()
        
        // Restore selection if the previously selected well is still present
        if let id = selectedWellId,
           let filteredIdx = filteredWellData.firstIndex(where: { $0.well == id }) {
            let tableRow = (compositeImagePath != nil) ? filteredIdx + 1 : filteredIdx
            wellListView.selectRowIndexes(IndexSet(integer: tableRow), byExtendingSelection: false)
        } else {
            // If selection no longer valid, clear selection and placeholder
            selectedWellIndex = -1
            showPlaceholderImage()
        }
    }
    
    @objc func filterChanged() {
        hideBufferZones = hideBufferZoneButton.state == .on
        hideWarnings = hideWarningButton.state == .on
        applyFilters()
    }

    @objc func showFilterPopover() {
        if filterPopover == nil {
            let pop = NSPopover()
            pop.behavior = .transient
            let vc = NSViewController()
            let container = NSView()
            container.translatesAutoresizingMaskIntoConstraints = false
            
            hideBufferZoneButton = NSButton(checkboxWithTitle: "Hide Buffer Zone Samples", target: self, action: #selector(filterChanged))
            hideWarningButton = NSButton(checkboxWithTitle: "Hide Warning Samples", target: self, action: #selector(filterChanged))
            hideBufferZoneButton.setButtonType(.switch)
            hideWarningButton.setButtonType(.switch)
            hideBufferZoneButton.state = hideBufferZones ? .on : .off
            hideWarningButton.state = hideWarnings ? .on : .off
            hideBufferZoneButton.translatesAutoresizingMaskIntoConstraints = false
            hideWarningButton.translatesAutoresizingMaskIntoConstraints = false
            container.addSubview(hideBufferZoneButton)
            container.addSubview(hideWarningButton)
            
            NSLayoutConstraint.activate([
                hideBufferZoneButton.topAnchor.constraint(equalTo: container.topAnchor, constant: 10),
                hideBufferZoneButton.leadingAnchor.constraint(equalTo: container.leadingAnchor, constant: 10),
                hideBufferZoneButton.trailingAnchor.constraint(equalTo: container.trailingAnchor, constant: -10),
                
                hideWarningButton.topAnchor.constraint(equalTo: hideBufferZoneButton.bottomAnchor, constant: 8),
                hideWarningButton.leadingAnchor.constraint(equalTo: container.leadingAnchor, constant: 10),
                hideWarningButton.trailingAnchor.constraint(equalTo: container.trailingAnchor, constant: -10),
                hideWarningButton.bottomAnchor.constraint(equalTo: container.bottomAnchor, constant: -10),
                container.widthAnchor.constraint(equalToConstant: 220)
            ])
            vc.view = container
            pop.contentViewController = vc
            filterPopover = pop
        }
        if let button = filterButton {
            filterPopover?.show(relativeTo: button.bounds, of: button, preferredEdge: .maxY)
        }
    }
    
    @objc func showOverview() {
        // TODO: Wire up overview functionality
        print("Overview button clicked - functionality to be implemented")
    }
    
    @objc func showLegend() {
        let pop = NSPopover()
        pop.behavior = .transient
        let vc = NSViewController()
        
        let title = NSTextField(labelWithString: "ddQuint Overview")
        title.font = NSFont.boldSystemFont(ofSize: 14)
        
        let overviewText = """
        Use the well list to navigate. Select a well to view its plot. Adjust parameters via 'Edit This Well'.

        Indicators next to each well:
        • White circle: Euploid
        • Grey circle: Buffer Zone
        • Purple circle: Aneuploid
        • Red circle: Warning
        • Square shape: Edited well (custom parameters)

        Use the filter icon to hide buffer zone samples or warning samples.
        """
        let overview = NSTextField(labelWithString: overviewText)
        overview.lineBreakMode = .byWordWrapping
        if let cell = overview.cell as? NSTextFieldCell { cell.wraps = true; cell.usesSingleLineMode = false }
        
        let stack = NSStackView()
        stack.orientation = .vertical
        stack.alignment = .leading
        stack.spacing = 8
        stack.translatesAutoresizingMaskIntoConstraints = false
        stack.addArrangedSubview(title)
        stack.addArrangedSubview(overview)
        
        let container = NSView()
        container.translatesAutoresizingMaskIntoConstraints = false
        container.addSubview(stack)
        
        NSLayoutConstraint.activate([
            stack.leadingAnchor.constraint(equalTo: container.leadingAnchor, constant: 12),
            stack.trailingAnchor.constraint(equalTo: container.trailingAnchor, constant: -12),
            stack.topAnchor.constraint(equalTo: container.topAnchor, constant: 10),
            stack.bottomAnchor.constraint(equalTo: container.bottomAnchor, constant: -10),
            container.widthAnchor.constraint(equalToConstant: 420)
        ])
        
        vc.view = container
        pop.contentViewController = vc
        guard let button = legendButton else { return }
        pop.show(relativeTo: button.bounds, of: button, preferredEdge: .maxY)
    }
}


// MARK: - Window Delegate
extension InteractiveMainWindowController {
    func windowShouldClose(_ sender: NSWindow) -> Bool {
        // Only terminate if this is the main window
        if sender === window {
            NSApplication.shared.terminate(nil)
            return true
        }
        return true
    }
    
    func windowWillClose(_ notification: Notification) {
        guard let window = notification.object as? NSWindow else { return }
        
        // Clean up window references when windows are closed
        if window === currentGlobalWindow {
            currentGlobalWindow = nil
            statusLabel.stringValue = "Global parameter window closed"
        } else if window === currentWellWindow {
            currentWellWindow = nil
            statusLabel.stringValue = "Well parameter window closed"
        } else if window === processingIndicatorWindow {
            processingIndicatorWindow = nil
            print("✅ Processing indicator window closed")
        }
    }
    
    // MARK: - Menu Export Methods
    
    func exportExcelFromMenu() {
        exportExcel()
    }
    
    func exportPlotsFromMenu() {
        exportPlots()
    }
}

extension InteractiveMainWindowController: DragDropDelegate {
    func didReceiveDroppedFolder(url: URL) {
        selectedFolderURL = url
        showAnalysisProgress()
        startAnalysis(folderURL: url)
    }
}

 
