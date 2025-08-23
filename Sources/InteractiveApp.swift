import Cocoa

// MARK: - High Quality Image View

class HighQualityImageView: NSView {
    var image: NSImage? {
        didSet {
            needsDisplay = true
        }
    }
    
    override func draw(_ dirtyRect: NSRect) {
        super.draw(dirtyRect)
        
        guard let image = self.image,
              let context = NSGraphicsContext.current?.cgContext else { return }
        
        // Set high-quality interpolation
        context.interpolationQuality = .high
        context.setShouldAntialias(true)
        context.setAllowsAntialiasing(true)
        
        // Calculate scaling to fit bounds while maintaining aspect ratio
        let imageSize = image.size
        let viewSize = bounds.size
        
        let scaleX = viewSize.width / imageSize.width
        let scaleY = viewSize.height / imageSize.height
        let scale = min(scaleX, scaleY)
        
        let scaledWidth = imageSize.width * scale
        let scaledHeight = imageSize.height * scale
        
        // Center the image
        let x = (viewSize.width - scaledWidth) / 2
        let y = (viewSize.height - scaledHeight) / 2
        
        let drawRect = NSRect(x: x, y: y, width: scaledWidth, height: scaledHeight)
        
        // Draw with high quality scaling
        if let cgImage = image.cgImage(forProposedRect: nil, context: nil, hints: [
            .interpolation: NSNumber(value: NSImageInterpolation.high.rawValue)
        ]) {
            context.draw(cgImage, in: drawRect)
        }
    }
}

class InteractiveMainWindowController: NSWindowController, NSWindowDelegate {
    
    // UI Elements
    private var wellListScrollView: NSScrollView!
    private var wellListView: NSTableView!
    private var filterButton: NSButton!
    private var legendButton: NSButton!
    private var overviewButton: NSButton!
    private var filterPopover: NSPopover?
    private var hideBufferZoneButton: NSButton!
    private var hideWarningButton: NSButton!
    private var plotImageView: HighQualityImageView!
    private var plotClickView: NSView!
    private var progressIndicator: NSProgressIndicator!
    private var editWellButton: NSButton!
    private var globalParamsButton: NSButton!
    private var exportExcelButton: NSButton!
    private var exportPlotsButton: NSButton!
    private var statusLabel: NSTextField!
    
    // Data
    private var selectedFolderURL: URL?
    private var analysisResults: [[String: Any]] = []
    private var wellData: [WellData] = []
    private var filteredWellData: [WellData] = []
    private var selectedWellIndex: Int = -1
    
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
    private var wellParametersMap: [String: [String: Any]] = [:]
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
        
        // Export buttons
        exportExcelButton = NSButton(title: "Export Excel", target: self, action: #selector(exportExcel))
        exportExcelButton.bezelStyle = .rounded
        exportExcelButton.isEnabled = false
        exportExcelButton.translatesAutoresizingMaskIntoConstraints = false
        contentView.addSubview(exportExcelButton)
        
        exportPlotsButton = NSButton(title: "Export Plots", target: self, action: #selector(exportPlots))
        exportPlotsButton.bezelStyle = .rounded
        exportPlotsButton.isEnabled = false
        exportPlotsButton.translatesAutoresizingMaskIntoConstraints = false
        contentView.addSubview(exportPlotsButton)
        
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
            
            // Export buttons
            exportExcelButton.trailingAnchor.constraint(equalTo: contentView.trailingAnchor, constant: -20),
            exportExcelButton.bottomAnchor.constraint(equalTo: contentView.bottomAnchor, constant: -20),
            exportExcelButton.widthAnchor.constraint(equalToConstant: 100),
            
            exportPlotsButton.trailingAnchor.constraint(equalTo: exportExcelButton.leadingAnchor, constant: -10),
            exportPlotsButton.bottomAnchor.constraint(equalTo: exportExcelButton.bottomAnchor),
            exportPlotsButton.widthAnchor.constraint(equalToConstant: 100),
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
            showAnalysisProgress()
            startAnalysis(folderURL: url)
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
        exportExcelButton.isEnabled = false
        exportPlotsButton.isEnabled = false
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
                        'BASE_TARGET_TOLERANCE','SCALE_FACTOR_MIN','SCALE_FACTOR_MAX','EXPECTED_CENTROIDS','EXPECTED_COPY_NUMBERS','EXPECTED_STANDARD_DEVIATION','ANEUPLOIDY_TARGETS','TOLERANCE_MULTIPLIER'
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
                            
                            # Apply per-well overrides if present (reset instance overrides first)
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
                                # Reset any instance-set overrides to fallback to class/global defaults
                                for k in PARAM_KEYS:
                                    if hasattr(config, k) and k in getattr(config, '__dict__', {}):
                                        delattr(config, k)
                                # Apply overrides for this well
                                if well_id and well_id in WELL_PARAMS:
                                    overrides = WELL_PARAMS.get(well_id, {})
                                    applied = 0
                                    for k, v in overrides.items():
                                        try:
                                            setattr(config, k, v)
                                            applied += 1
                                        except Exception:
                                            pass
                                    print(f"Applied {applied} per-well overrides for {well_id}")
                            except Exception as _e:
                                print(f"Per-well override error: {_e}")

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
        exportExcelButton.isEnabled = true
        exportPlotsButton.isEnabled = true
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
        exportExcelButton.isEnabled = true
        exportPlotsButton.isEnabled = true
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
    
    private func loadPlotForSelectedWell() {
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
            // Load parameters for the current well
            print("🔍 Loading well parameters:")
            print("   selectedWellIndex: \(selectedWellIndex)")
            print("   wellData.count: \(wellData.count)")
            
            if selectedWellIndex >= 0 && selectedWellIndex < wellData.count {
                let wellId = wellData[selectedWellIndex].well
                print("   wellId: \(wellId)")
                print("   wellParametersMap has \(wellParametersMap.count) entries: \(Array(wellParametersMap.keys).sorted())")
                
                // Always start with global parameters as base
                savedParams = loadGlobalParameters()
                print("📄 Loaded \(savedParams.count) global parameters as base: \(savedParams.keys.sorted())")
                
                // Overlay well-specific modifications if they exist
                if let savedWellParams = wellParametersMap[wellId], !savedWellParams.isEmpty {
                    for (key, value) in savedWellParams {
                        savedParams[key] = value
                    }
                    print("✅ Applied \(savedWellParams.count) well-specific parameter overrides for well \(wellId): \(savedWellParams.keys.sorted())")
                } else {
                    print("📄 No well-specific parameter overrides for well \(wellId)")
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
        
        // Tab 2: Expected Centroids (for both global and well-specific)
        let centroidsTab = NSTabViewItem(identifier: "centroids")
        centroidsTab.label = "Expected Centroids"
        let centroidsView = createCentroidsParametersView(isGlobal: isGlobal, parameters: savedParams)
        centroidsTab.view = centroidsView
        tabView.addTabViewItem(centroidsTab)
        
        // Tab 3: Copy Number Settings (for both global and well-specific)
        let copyNumberTab = NSTabViewItem(identifier: "copynumber")
        copyNumberTab.label = "Copy Number"
        let copyNumberView = createCopyNumberParametersView(parameters: savedParams)
        copyNumberTab.view = copyNumberView
        tabView.addTabViewItem(copyNumberTab)
        
        // Tab 4: Visualization Settings (for both global and well-specific)
        let visualizationTab = NSTabViewItem(identifier: "visualization")
        visualizationTab.label = "Visualization"
        let visualizationView = createVisualizationParametersView(parameters: savedParams)
        visualizationTab.view = visualizationView
        tabView.addTabViewItem(visualizationTab)

        // Ensure scroll views start at the top for better UX
        DispatchQueue.main.async { [weak self] in
            if let scroll = copyNumberView as? NSScrollView { self?.scrollToTop(scroll) }
            if let scroll = visualizationView as? NSScrollView { self?.scrollToTop(scroll) }
            if let scroll = hdbscanView as? NSScrollView { self?.scrollToTop(scroll) }
            if let scroll = centroidsView as? NSScrollView { self?.scrollToTop(scroll) }
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
            
            let paramField = NSTextField()
            paramField.identifier = NSUserInterfaceItemIdentifier(identifier)
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
            
            let metricPopup = NSPopUpButton()
            metricPopup.identifier = NSUserInterfaceItemIdentifier("HDBSCAN_METRIC")
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
            
            let selectionPopup = NSPopUpButton()
            selectionPopup.identifier = NSUserInterfaceItemIdentifier("HDBSCAN_CLUSTER_SELECTION_METHOD")
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
        let finalHeight = max(450 - yPos + 40, 400)  // Ensure minimum height
        view.frame = NSRect(x: 0, y: 0, width: 620, height: finalHeight)
        
        // Setup scroll view properly
        scrollView.documentView = view
        scrollView.hasVerticalScroller = true
        scrollView.hasHorizontalScroller = false
        scrollView.autohidesScrollers = true
        scrollView.borderType = .noBorder
        
        return scrollView
    }
    
    private func createCentroidsParametersView(isGlobal: Bool, parameters: [String: Any]) -> NSView {
        let scrollView = NSScrollView()
        let view = NSView()
        
        var yPos: CGFloat = 500
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
        
        // Centroid entries
        let targets = ["Negative", "Chrom1", "Chrom2", "Chrom3", "Chrom4", "Chrom5"]
        
        for (_, target) in targets.enumerated() {
            let targetLabel = NSTextField(labelWithString: "\(target):")
            targetLabel.frame = NSRect(x: 40, y: yPos, width: 120, height: fieldHeight)
            
            let targetField = NSTextField()
            targetField.identifier = NSUserInterfaceItemIdentifier("EXPECTED_CENTROIDS_\(target)")
            
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
                ("BASE_TARGET_TOLERANCE", "Base Target Tolerance:", "", "Base tolerance distance for matching detected clusters"),
                ("SCALE_FACTOR_MIN", "Scale Factor Min:", "", "Minimum scale factor for adaptive tolerance adjustment"),
                ("SCALE_FACTOR_MAX", "Scale Factor Max:", "", "Maximum scale factor for adaptive tolerance adjustment")
            ]
            
            for (identifier, label, _, tooltip) in matchingParams {
                let paramLabel = NSTextField(labelWithString: label)
                paramLabel.frame = NSRect(x: 40, y: yPos, width: 200, height: fieldHeight)
                
                let paramField = NSTextField()
                paramField.identifier = NSUserInterfaceItemIdentifier(identifier)
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
        let finalHeight = max(480 - yPos + 40, 400)  // Ensure minimum height
        view.frame = NSRect(x: 0, y: 0, width: 620, height: finalHeight)
        
        // Setup scroll view properly
        scrollView.documentView = view
        scrollView.hasVerticalScroller = true
        scrollView.hasHorizontalScroller = false
        scrollView.autohidesScrollers = true
        scrollView.borderType = .noBorder
        
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
            ("COPY_NUMBER_BASELINE_MIN_CHROMS", "Baseline Min Chromosomes:", "", "Minimum chromosomes needed for normalization baseline"),
            ("TOLERANCE_MULTIPLIER", "Tolerance Multiplier:", "", "Multiplier for chromosome standard deviation in classification")
        ]
        
        for (identifier, label, _, tooltip) in generalParams {
            let paramLabel = NSTextField(labelWithString: label)
            paramLabel.frame = NSRect(x: 40, y: yPos, width: 220, height: fieldHeight)
            
            let paramField = NSTextField()
            paramField.identifier = NSUserInterfaceItemIdentifier(identifier)
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
            
            view.addSubview(paramLabel)
            view.addSubview(paramField)
            yPos -= spacing
        }
        
        // Aneuploidy Targets
        yPos -= 20
        let aneuploidyLabel = NSTextField(labelWithString: "Aneuploidy Target Ratios")
        aneuploidyLabel.font = NSFont.boldSystemFont(ofSize: 14)
        aneuploidyLabel.frame = NSRect(x: 20, y: yPos, width: 200, height: 20)
        view.addSubview(aneuploidyLabel)
        yPos -= 40
        
        let aneuploidyParams = [
            ("ANEUPLOIDY_TARGETS_LOW", "Chromosomal loss:", "", "Target copy number ratio for chromosome deletions"),
            ("ANEUPLOIDY_TARGETS_HIGH", "Chromosomal gain:", "", "Target copy number ratio for chromosome duplications")
        ]
        
        for (identifier, label, _, tooltip) in aneuploidyParams {
            let paramLabel = NSTextField(labelWithString: label)
            paramLabel.frame = NSRect(x: 40, y: yPos, width: 220, height: fieldHeight)
            
            let paramField = NSTextField()
            paramField.identifier = NSUserInterfaceItemIdentifier(identifier)
            // Special handling for aneuploidy targets
            if identifier == "ANEUPLOIDY_TARGETS_LOW" {
                if let targets = parameters["ANEUPLOIDY_TARGETS"] as? [String: Double],
                   let value = targets["low"] {
                    paramField.stringValue = String(value)
                    print("🎯 Set aneuploidy field \(identifier) = \(value)")
                } else {
                    paramField.stringValue = ""
                    print("⚪ Aneuploidy field \(identifier) has no parameter value, leaving empty")
                }
            } else if identifier == "ANEUPLOIDY_TARGETS_HIGH" {
                if let targets = parameters["ANEUPLOIDY_TARGETS"] as? [String: Double],
                   let value = targets["high"] {
                    paramField.stringValue = String(value)
                    print("🎯 Set aneuploidy field \(identifier) = \(value)")
                } else {
                    paramField.stringValue = ""
                    print("⚪ Aneuploidy field \(identifier) has no parameter value, leaving empty")
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
        view.addSubview(copyNumLabel)
        yPos -= 40
        
        let chromosomes = ["Chrom1", "Chrom2", "Chrom3", "Chrom4", "Chrom5"]
        
        for chrom in chromosomes {
            let chromLabel = NSTextField(labelWithString: "\(chrom):")
            chromLabel.frame = NSRect(x: 40, y: yPos, width: 80, height: fieldHeight)
            
            let copyNumField = NSTextField()
            copyNumField.identifier = NSUserInterfaceItemIdentifier("EXPECTED_COPY_NUMBERS_\(chrom)")
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
            
            let stdDevLabel = NSTextField(labelWithString: "Std Dev:")
            stdDevLabel.frame = NSRect(x: 220, y: yPos, width: 60, height: fieldHeight)
            
            let stdDevField = NSTextField()
            stdDevField.identifier = NSUserInterfaceItemIdentifier("EXPECTED_STANDARD_DEVIATION_\(chrom)")
            // Use parameter value if available, otherwise leave empty
            if let stdDevs = parameters["EXPECTED_STANDARD_DEVIATION"] as? [String: Double],
               let value = stdDevs[chrom] {
                stdDevField.stringValue = String(value)
                print("🎯 Set std dev field \(chrom) = \(value)")
            } else {
                stdDevField.stringValue = ""
                print("⚪ Std dev field \(chrom) has no parameter value, leaving empty")
            }
            stdDevField.frame = NSRect(x: 290, y: yPos, width: 80, height: fieldHeight)
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
        let bottomMargin: CGFloat = 20
        if yPos < bottomMargin {
            let offsetNeeded = bottomMargin - yPos
            print("📏 Copy Number view: yPos = \(yPos), offsetting all elements up by \(offsetNeeded)")
            
            // Move all subviews up by the offset
            for subview in view.subviews {
                var frame = subview.frame
                frame.origin.y += offsetNeeded
                subview.frame = frame
            }
            yPos += offsetNeeded
        }
        
        // Set proper view size with padding - ensure all content is visible
        let contentHeight = 480 - yPos + 40  // Total content height from top to bottom element
        let finalHeight = max(contentHeight, 600)  // Ensure sufficient minimum height
        print("📏 Copy Number view: final yPos = \(yPos), contentHeight = \(contentHeight), finalHeight = \(finalHeight)")
        view.frame = NSRect(x: 0, y: 0, width: 620, height: finalHeight)

        // Align content towards the top to avoid large empty space above
        let topMargin: CGFloat = 20
        var maxSubviewY: CGFloat = 0
        for subview in view.subviews {
            maxSubviewY = max(maxSubviewY, subview.frame.maxY)
        }
        if maxSubviewY < finalHeight - topMargin {
            let shift = (finalHeight - topMargin) - maxSubviewY
            for subview in view.subviews {
                var f = subview.frame
                f.origin.y += shift
                subview.frame = f
            }
            // Recompute max Y after shift (for debugging)
            var newMaxY: CGFloat = 0
            for subview in view.subviews { newMaxY = max(newMaxY, subview.frame.maxY) }
            print("📐 Copy Number view: shifted content up by \(shift), newMaxY=\(newMaxY)")
        }
        
        // Setup scroll view properly
        scrollView.documentView = view
        scrollView.hasVerticalScroller = true
        scrollView.hasHorizontalScroller = false
        scrollView.autohidesScrollers = true
        scrollView.borderType = .noBorder
        
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
            
            let paramField = NSTextField()
            paramField.identifier = NSUserInterfaceItemIdentifier(identifier)
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
            
            let paramField = NSTextField()
            paramField.identifier = NSUserInterfaceItemIdentifier(identifier)
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
        scrollView.documentView = view
        scrollView.hasVerticalScroller = true
        scrollView.hasHorizontalScroller = false
        scrollView.autohidesScrollers = true
        scrollView.borderType = .noBorder
        
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
        
        // Extract parameters from the UI fields (all tabs)
        var parameters = extractParametersFromWindow(window, isGlobal: false)
        // Merge with any existing well-specific parameters to avoid losing untouched overrides
        if selectedWellIndex >= 0 && selectedWellIndex < wellData.count {
            let well = wellData[selectedWellIndex]
            if let existing = wellParametersMap[well.well] {
                // Keep existing values for keys not present in the current extraction
                for (k, v) in existing where parameters[k] == nil {
                    parameters[k] = v
                }
            }
        }
        
        if parameters.isEmpty {
            statusLabel.stringValue = "Failed to extract parameters"
            return
        }
        
        // Validate parameters
        guard validateParameters(parameters) else {
            statusLabel.stringValue = "Invalid parameter values detected"
            return
        }
        
        // Close window first
        closeWellParameterWindow()
        
        // Store parameters for this specific well
        if selectedWellIndex >= 0 && selectedWellIndex < wellData.count {
            let well = wellData[selectedWellIndex]
            wellParametersMap[well.well] = parameters
            print("✅ Saved \(parameters.count) parameters for well \(well.well): \(parameters.keys.sorted())")
            print("   wellParametersMap now has \(wellParametersMap.count) entries: \(Array(wellParametersMap.keys).sorted())")
            // Mark as edited in our table model and refresh row
            let current = wellData[selectedWellIndex]
            wellData[selectedWellIndex] = WellData(well: current.well,
                                                   sampleName: current.sampleName,
                                                   dropletCount: current.dropletCount,
                                                   hasData: current.hasData,
                                                   status: current.status,
                                                   isEdited: true)
            applyFilters()
            
            // Apply parameters and re-process the specific well
            applyParametersAndRegeneratePlot(wellName: well.well, parameters: parameters)
        }
    }
    
    @objc private func saveGlobalParameters() {
        guard let window = currentGlobalWindow else { return }
        
        showProcessingIndicator("Saving global parameters and re-processing all wells...")
        
        // Extract parameters from the UI fields
        let parameters = extractParametersFromWindow(window, isGlobal: true)
        
        if parameters.isEmpty {
            statusLabel.stringValue = "Failed to extract parameters"
            return
        }
        
        // Validate parameters
        print("🔍 Validating extracted global parameters...")
        guard validateParameters(parameters) else {
            print("❌ Global parameter validation failed")
            statusLabel.stringValue = "Invalid parameter values detected"
            return
        }
        print("✅ Global parameter validation passed")
        
        // Save parameters to file for persistence
        saveParametersToFile(parameters)
        
        // Close window first
        closeGlobalParameterWindow()
        
        // Apply parameters and re-process all wells
        if selectedFolderURL != nil {
            applyGlobalParametersAndReanalyze(parameters: parameters)
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
                        let coordinates = textField.stringValue.components(separatedBy: ",").compactMap { Double($0.trimmingCharacters(in: .whitespaces)) }
                        if coordinates.count == 2 {
                            if parameters["EXPECTED_CENTROIDS"] == nil {
                                parameters["EXPECTED_CENTROIDS"] = [String: [Double]]()
                            }
                            var centroids = parameters["EXPECTED_CENTROIDS"] as! [String: [Double]]
                            centroids[target] = coordinates
                            parameters["EXPECTED_CENTROIDS"] = centroids
                        }
                    } else if identifier.hasPrefix("EXPECTED_COPY_NUMBERS_") {
                        let chrom = String(identifier.dropFirst("EXPECTED_COPY_NUMBERS_".count))
                        if let value = Double(textField.stringValue) {
                            if parameters["EXPECTED_COPY_NUMBERS"] == nil {
                                parameters["EXPECTED_COPY_NUMBERS"] = [String: Double]()
                            }
                            var copyNumbers = parameters["EXPECTED_COPY_NUMBERS"] as! [String: Double]
                            copyNumbers[chrom] = value
                            parameters["EXPECTED_COPY_NUMBERS"] = copyNumbers
                        }
                    } else if identifier.hasPrefix("EXPECTED_STANDARD_DEVIATION_") {
                        let chrom = String(identifier.dropFirst("EXPECTED_STANDARD_DEVIATION_".count))
                        if let value = Double(textField.stringValue) {
                            if parameters["EXPECTED_STANDARD_DEVIATION"] == nil {
                                parameters["EXPECTED_STANDARD_DEVIATION"] = [String: Double]()
                            }
                            var stdDevs = parameters["EXPECTED_STANDARD_DEVIATION"] as! [String: Double]
                            stdDevs[chrom] = value
                            parameters["EXPECTED_STANDARD_DEVIATION"] = stdDevs
                        }
                    } else if identifier == "ANEUPLOIDY_TARGETS_LOW" || identifier == "ANEUPLOIDY_TARGETS_HIGH" {
                        if let value = Double(textField.stringValue) {
                            if parameters["ANEUPLOIDY_TARGETS"] == nil {
                                parameters["ANEUPLOIDY_TARGETS"] = [String: Double]()
                            }
                            var targets = parameters["ANEUPLOIDY_TARGETS"] as! [String: Double]
                            let key = identifier == "ANEUPLOIDY_TARGETS_LOW" ? "low" : "high"
                            targets[key] = value
                            parameters["ANEUPLOIDY_TARGETS"] = targets
                        }
                    } else {
                        // Handle other numeric parameters
                        if let intValue = Int(textField.stringValue) {
                            parameters[identifier] = intValue
                            print("✅ Extracted \(identifier) = \(intValue) (Int)")
                        } else if let doubleValue = Double(textField.stringValue) {
                            parameters[identifier] = doubleValue
                            print("✅ Extracted \(identifier) = \(doubleValue) (Double)")
                        } else {
                            parameters[identifier] = textField.stringValue
                            print("✅ Extracted \(identifier) = \(textField.stringValue) (String)")
                        }
                    }
                } else if let popup = subview as? NSPopUpButton,
                          let identifier = popup.identifier?.rawValue,
                          !identifier.isEmpty {
                    parameters[identifier] = popup.titleOfSelectedItem ?? ""
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
        print("   Found \(foundFields) UI fields total")
        print("   Extracted \(parameters.count) parameters: \(parameters.keys.sorted())")
        return parameters
    }
    
    private func validateParameters(_ parameters: [String: Any]) -> Bool {
        // Validate only the parameters that are present, not all required parameters
        // This allows partial parameter sets from different tabs
        
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
                showError("Base Target Tolerance must be at least 1")
                return false
            }
        }
        
        // Validate scale factors if present
        if let scaleMin = parameters["SCALE_FACTOR_MIN"] as? Double {
            if scaleMin < 0.1 || scaleMin > 1.0 {
                showError("Scale Factor Min must be between 0.1 and 1.0")
                return false
            }
        }
        
        if let scaleMax = parameters["SCALE_FACTOR_MAX"] as? Double {
            if scaleMax < 1.0 || scaleMax > 2.0 {
                showError("Scale Factor Max must be between 1.0 and 2.0")
                return false
            }
        }
        
        // Validate aneuploidy targets if present
        if let aneuploidyTargets = parameters["ANEUPLOIDY_TARGETS"] as? [String: Double] {
            if let low = aneuploidyTargets["low"], (low < 0.1 || low > 1.0) {
                showError("Aneuploidy deletion target must be between 0.1 and 1.0")
                return false
            }
            if let high = aneuploidyTargets["high"], (high < 1.0 || high > 2.0) {
                showError("Aneuploidy duplication target must be between 1.0 and 2.0")
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
    'SCALE_FACTOR_MIN': 0.5,
    'SCALE_FACTOR_MAX': 1.0,
    'HDBSCAN_MIN_CLUSTER_SIZE': 4,
    'HDBSCAN_MIN_SAMPLES': 70,
    'HDBSCAN_EPSILON': 0.06,
    'HDBSCAN_METRIC': 'euclidean',
    'HDBSCAN_CLUSTER_SELECTION_METHOD': 'eom',
    'MIN_POINTS_FOR_CLUSTERING': 50,
    'MIN_USABLE_DROPLETS': 3000,
    'COPY_NUMBER_MEDIAN_DEVIATION_THRESHOLD': 0.15,
    'COPY_NUMBER_BASELINE_MIN_CHROMS': 3,
    'TOLERANCE_MULTIPLIER': 3,
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
        
        func restoreInView(_ view: NSView) {
            for subview in view.subviews {
                if let textField = subview as? NSTextField,
                   let identifier = textField.identifier?.rawValue,
                   !identifier.isEmpty {
                    totalFields += 1
                    print("🔍 Found text field with identifier: \(identifier)")
                    
                    // Handle different parameter types
                    if identifier.hasPrefix("EXPECTED_CENTROIDS_") {
                        let target = String(identifier.dropFirst("EXPECTED_CENTROIDS_".count))
                        if let centroids = parameters["EXPECTED_CENTROIDS"] as? [String: [Double]],
                           let coords = centroids[target] {
                            textField.stringValue = "\(Int(coords[0])), \(Int(coords[1]))"
                        }
                    } else if identifier.hasPrefix("EXPECTED_COPY_NUMBERS_") {
                        let chrom = String(identifier.dropFirst("EXPECTED_COPY_NUMBERS_".count))
                        if let copyNumbers = parameters["EXPECTED_COPY_NUMBERS"] as? [String: Double],
                           let value = copyNumbers[chrom] {
                            textField.stringValue = String(value)
                        }
                    } else if identifier.hasPrefix("EXPECTED_STANDARD_DEVIATION_") {
                        let chrom = String(identifier.dropFirst("EXPECTED_STANDARD_DEVIATION_".count))
                        if let stdDevs = parameters["EXPECTED_STANDARD_DEVIATION"] as? [String: Double],
                           let value = stdDevs[chrom] {
                            textField.stringValue = String(value)
                        }
                    } else if identifier == "ANEUPLOIDY_TARGETS_LOW" {
                        if let targets = parameters["ANEUPLOIDY_TARGETS"] as? [String: Double],
                           let value = targets["low"] {
                            textField.stringValue = String(value)
                        }
                    } else if identifier == "ANEUPLOIDY_TARGETS_HIGH" {
                        if let targets = parameters["ANEUPLOIDY_TARGETS"] as? [String: Double],
                           let value = targets["high"] {
                            textField.stringValue = String(value)
                        }
                    } else if let value = parameters[identifier] {
                        let oldValue = textField.stringValue
                        textField.stringValue = String(describing: value)
                        restoredFields += 1
                        print("✅ Restored \(identifier): \(oldValue) → \(value)")
                    } else {
                        print("⚠️ No parameter found for identifier: \(identifier) (current value: \(textField.stringValue))")
                    }
                } else if let popup = subview as? NSPopUpButton,
                          let identifier = popup.identifier?.rawValue,
                          let value = parameters[identifier] as? String {
                    popup.selectItem(withTitle: value)
                }
                
                // Recursively restore in subviews
                restoreInView(subview)
            }
        }
        
        restoreInView(window.contentView!)
        print("🔧 Restoration complete: restored \(restoredFields)/\(totalFields) fields")
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
        guard selectedWellIndex >= 0 && selectedWellIndex < wellData.count else { return }
        let well = wellData[selectedWellIndex]
        openParameterWindow(isGlobal: false, title: "Edit Parameters - \(well.well)")
    }
    
    @objc private func editGlobalParameters() {
        openParameterWindow(isGlobal: true, title: "Global Parameters")
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
        let paths = [
            "/opt/miniconda3/envs/ddpcr/bin/python",
            "/usr/local/bin/python3",
            "/usr/bin/python3"
        ]
        return paths.first { FileManager.default.isExecutableFile(atPath: $0) }
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
    
    private func writeDebugLog(_ message: String) {
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
                "PYTHONDONTWRITEBYTECODE": "1"
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
                        
                        # Apply custom parameters to config
                        print(f'Config instance id: {id(config)}')
                        applied_count = 0
                        for key, value in custom_params.items():
                            if hasattr(config, key):
                                old_value = getattr(config, key)
                                setattr(config, key, value)
                                print(f'Applied parameter: {key} = {value} (was {old_value})')
                                # Verify the attribute was set
                                verify_value = getattr(config, key)
                                print(f'Verification: {key} is now {verify_value}')
                                applied_count += 1
                            else:
                                print(f'Warning: Config has no attribute {key}')
                        
                        print(f'Successfully applied {applied_count} out of {len(custom_params)} parameters')
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
                    
                    # Process the CSV file (this will regenerate the plot)
                    result = process_csv_file('\(escapedCSVPath)', graphs_dir, sample_names, verbose=True)
                    
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
                            
                            print(f'UPDATED_RESULT:{json.dumps(serializable_result)}')
                        else:
                            print('UPDATED_RESULT:{"well": "\(wellName)", "status": "regenerated", "plot_path": "' + plot_path + '"}')
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
            process.standardOutput = outputPipe
            process.standardError = outputPipe
            
            do {
                self?.writeDebugLog("🔧 REGEN: Starting process...")
                try process.run()
                self?.writeDebugLog("🔧 REGEN: Process started, waiting for completion...")
                
                // Add timeout handling
                DispatchQueue.global(qos: .userInitiated).async {
                    process.waitUntilExit()
                    
                    let data = outputPipe.fileHandleForReading.readDataToEndOfFile()
                    let output = String(data: data, encoding: .utf8) ?? ""
                    
                    DispatchQueue.main.async { [weak self] in
                        self?.hideCornerSpinner()
                        self?.writeDebugLog("🔧 REGEN: Process completed with exit code: \(process.terminationStatus)")
                        self?.writeDebugLog("🔧 REGEN_OUTPUT: Raw output length: \(output.count) characters")
                        self?.writeDebugLog("🔧 REGEN_OUTPUT: First 500 chars: \(String(output.prefix(500)))")
                        self?.writeDebugLog("🔧 REGEN_OUTPUT: Contains EARLY_REMOVAL: \(output.contains("EARLY_REMOVAL"))")
                        self?.writeDebugLog("🔧 REGEN_OUTPUT: Contains PLOT_CREATED: \(output.contains("PLOT_CREATED"))")
                        self?.writeDebugLog("🔧 REGEN_OUTPUT: Contains UPDATED_RESULT: \(output.contains("UPDATED_RESULT"))")
                        self?.writeDebugLog("🔧 REGEN_OUTPUT: Contains ERROR: \(output.contains("ERROR"))")
                        
                        // Check for exit code errors
                        if process.terminationStatus != 0 {
                            self?.writeDebugLog("🔧 REGEN_ERROR: Process failed with exit code \(process.terminationStatus)")
                            self?.showError("Plot regeneration failed with exit code \(process.terminationStatus)")
                        }
                        
                        // Process the output
                        self?.handleWellRegenerationResult(output: output, wellName: wellName)
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
        do {
            let data = resultJson.data(using: .utf8) ?? Data()
            if let updatedResult = try JSONSerialization.jsonObject(with: data, options: []) as? [String: Any] {
                // Find and update the corresponding entry in cachedResults
                if let index = cachedResults.firstIndex(where: { ($0["well"] as? String) == wellName }) {
                    cachedResults[index] = updatedResult
                    print("✅ Updated cached results for well \(wellName)")
                } else {
                    // If not found, append it
                    cachedResults.append(updatedResult)
                    print("✅ Added new cached result for well \(wellName)")
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
        
        DispatchQueue.global().async { [weak self] in
            guard let self = self else { return }
            
            // Save cachedResults to temporary JSON file
            do {
                let jsonData = try JSONSerialization.data(withJSONObject: self.cachedResults, options: [.prettyPrinted])
                let tempDir = FileManager.default.temporaryDirectory
                let tempJsonFile = tempDir.appendingPathComponent("ddquint_cached_results_\(UUID().uuidString).json")
                
                try jsonData.write(to: tempJsonFile)
                print("💾 Saved cached results to temp file: \(tempJsonFile.path)")
                
                self.executeExcelExportWithTempFile(tempJsonFile: tempJsonFile, saveURL: saveURL, ddquintPath: ddquintPath, pythonPath: pythonPath)
                
            } catch {
                DispatchQueue.main.async {
                    self.showError("Failed to serialize cached results: \(error)")
                }
                return
            }
        }
    }
    
    private func executeExcelExportWithTempFile(tempJsonFile: URL, saveURL: URL, ddquintPath: String, pythonPath: String) {
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
                
                # Export to Excel using cached results
                create_list_report(results, '\(escapedSavePath)')
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
                    
                    # Export to Excel using existing results
                    create_list_report(results, '\(escapedSavePath)')
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

// MARK: - Table View Data Source & Delegate

extension InteractiveMainWindowController: NSTableViewDataSource, NSTableViewDelegate {
    
    func numberOfRows(in tableView: NSTableView) -> Int {
        return filteredWellData.count
    }
    
    func tableView(_ tableView: NSTableView, viewFor tableColumn: NSTableColumn?, row: Int) -> NSView? {
        let cellView = NSTableCellView()
        
        guard row < filteredWellData.count else { return nil }
        let well = filteredWellData[row]
        
        // Create well ID label (left side)
        let wellIdLabel = NSTextField()
        wellIdLabel.isBordered = false
        wellIdLabel.isEditable = false
        wellIdLabel.backgroundColor = .clear
        wellIdLabel.stringValue = well.well
        wellIdLabel.font = NSFont.boldSystemFont(ofSize: NSFont.systemFontSize)
        wellIdLabel.textColor = well.hasData ? .controlTextColor : .secondaryLabelColor
        
        // Create status indicator
        let statusIndicator = WellStatusIndicatorView(frame: NSRect(x: 0, y: 0, width: 12, height: 12))
        statusIndicator.status = well.status
        statusIndicator.isEdited = well.isEdited
        
        cellView.addSubview(wellIdLabel)
        cellView.addSubview(statusIndicator)
        wellIdLabel.translatesAutoresizingMaskIntoConstraints = false
        statusIndicator.translatesAutoresizingMaskIntoConstraints = false
        
        // Create sample name label (right side) if there's a sample name
        if !well.sampleName.isEmpty {
            let sampleLabel = NSTextField()
            sampleLabel.isBordered = false
            sampleLabel.isEditable = false
            sampleLabel.backgroundColor = .clear
            sampleLabel.stringValue = well.sampleName
            sampleLabel.font = NSFont.systemFont(ofSize: NSFont.systemFontSize)
            sampleLabel.textColor = well.hasData ? .secondaryLabelColor : .tertiaryLabelColor
            sampleLabel.alignment = .right
            
            cellView.addSubview(sampleLabel)
            sampleLabel.translatesAutoresizingMaskIntoConstraints = false
            
            NSLayoutConstraint.activate([
                wellIdLabel.leadingAnchor.constraint(equalTo: cellView.leadingAnchor, constant: 4),
                wellIdLabel.centerYAnchor.constraint(equalTo: cellView.centerYAnchor),
                wellIdLabel.widthAnchor.constraint(equalToConstant: 36),
                
                statusIndicator.leadingAnchor.constraint(equalTo: wellIdLabel.trailingAnchor, constant: 0),
                statusIndicator.centerYAnchor.constraint(equalTo: cellView.centerYAnchor),
                statusIndicator.widthAnchor.constraint(equalToConstant: 12),
                statusIndicator.heightAnchor.constraint(equalToConstant: 12),
                
                sampleLabel.leadingAnchor.constraint(equalTo: statusIndicator.trailingAnchor, constant: 8),
                sampleLabel.trailingAnchor.constraint(equalTo: cellView.trailingAnchor, constant: -4),
                sampleLabel.centerYAnchor.constraint(equalTo: cellView.centerYAnchor)
            ])
        } else {
            NSLayoutConstraint.activate([
                wellIdLabel.leadingAnchor.constraint(equalTo: cellView.leadingAnchor, constant: 4),
                wellIdLabel.centerYAnchor.constraint(equalTo: cellView.centerYAnchor),
                wellIdLabel.widthAnchor.constraint(equalToConstant: 36),
                
                statusIndicator.leadingAnchor.constraint(equalTo: wellIdLabel.trailingAnchor, constant: 0),
                statusIndicator.centerYAnchor.constraint(equalTo: cellView.centerYAnchor),
                statusIndicator.widthAnchor.constraint(equalToConstant: 12),
                statusIndicator.heightAnchor.constraint(equalToConstant: 12),
                
                statusIndicator.trailingAnchor.constraint(lessThanOrEqualTo: cellView.trailingAnchor, constant: -4)
            ])
        }
        
        return cellView
    }
    
    func tableViewSelectionDidChange(_ notification: Notification) {
        let selectedRow = wellListView.selectedRow
        print("Well selection changed to row: \(selectedRow)")
        
        if selectedRow >= 0 && selectedRow < filteredWellData.count {
            let selectedWell = filteredWellData[selectedRow]
            // Find the original index in wellData
            if let originalIndex = wellData.firstIndex(where: { $0.well == selectedWell.well }) {
                selectedWellIndex = originalIndex
                print("Loading plot for well: \(selectedWell.well)")
                loadPlotForSelectedWell()
            }
        }
    }
}

// MARK: - Data Models

struct WellData {
    let well: String
    let sampleName: String
    let dropletCount: Int
    let hasData: Bool
    let status: WellStatus
    let isEdited: Bool
}

extension InteractiveMainWindowController {
    // Determine well status from analysis results
    func determineWellStatus(from result: [String: Any], wellName: String) -> WellStatus {
        print("🟡 Determining status for well \(wellName)")
        print("   Available keys: \(result.keys.sorted())")
        
        // Check for warnings first (red takes priority)
        if let error = result["error"] as? String, !error.isEmpty {
            print("   ❌ Found error: \(error) -> WARNING")
            return .warning
        }
        
        // Check for low droplet count
        if let totalDroplets = result["total_droplets"] as? Int {
            print("   💧 Total droplets: \(totalDroplets)")
            if totalDroplets < 100 {
                print("   ⚠️ Low droplet count -> WARNING")
                return .warning
            }
        }
        
        // Check for reclustering flag (could be a warning)
        if let reclustered = result["chrom3_reclustered"] as? Bool, reclustered {
            print("   🔄 Reclustered -> WARNING")
            return .warning
        }
        
        // Check biological status
        if let hasBuffer = result["has_buffer_zone"] as? Bool {
            print("   🔘 has_buffer_zone: \(hasBuffer)")
            if hasBuffer {
                print("   -> BUFFER")
                return .buffer
            }
        }
        
        if let hasAneuploidy = result["has_aneuploidy"] as? Bool {
            print("   🌸 has_aneuploidy: \(hasAneuploidy)")
            if hasAneuploidy {
                print("   -> ANEUPLOID")
                return .aneuploid
            }
        }
        
        // Default to euploid
        print("   ⚪ -> EUPLOID (default)")
        return .euploid
    }
    
    // Check if well has been edited
    func isWellEdited(_ wellName: String) -> Bool {
        return wellParametersMap.keys.contains(wellName)
    }
    
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

// MARK: - Drag and Drop Support

protocol DragDropDelegate: AnyObject {
    func didReceiveDroppedFolder(url: URL)
}

class DragDropView: NSView {
    weak var dragDropDelegate: DragDropDelegate?
    weak var clickTarget: AnyObject?
    var clickAction: Selector?
    
    override init(frame frameRect: NSRect) {
        super.init(frame: frameRect)
        registerForDraggedTypes([.fileURL])
    }
    
    required init?(coder: NSCoder) {
        super.init(coder: coder)
        registerForDraggedTypes([.fileURL])
    }
    
    override func mouseUp(with event: NSEvent) {
        // Handle click events - call the click action if set
        if let target = clickTarget, let action = clickAction {
            _ = target.perform(action)
        }
        super.mouseUp(with: event)
    }
    
    override func draggingEntered(_ sender: NSDraggingInfo) -> NSDragOperation {
        if let urls = sender.draggingPasteboard.readObjects(forClasses: [NSURL.self]) as? [URL],
           let url = urls.first,
           url.hasDirectoryPath {
            return .copy
        }
        return []
    }
    
    override func performDragOperation(_ sender: NSDraggingInfo) -> Bool {
        if let urls = sender.draggingPasteboard.readObjects(forClasses: [NSURL.self]) as? [URL],
           let url = urls.first,
           url.hasDirectoryPath {
            dragDropDelegate?.didReceiveDroppedFolder(url: url)
            return true
        }
        return false
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
}

extension InteractiveMainWindowController: DragDropDelegate {
    func didReceiveDroppedFolder(url: URL) {
        selectedFolderURL = url
        showAnalysisProgress()
        startAnalysis(folderURL: url)
    }
}

 
