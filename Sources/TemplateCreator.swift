import Cocoa

class TemplateCreatorWindowController: NSWindowController, NSWindowDelegate {
    private var inputPathField: NSTextField!
    private var browseButton: NSButton!
    private var previewContainer: NSView!
    private var gridScroll: NSScrollView!
    private var gridContainer: NSGridView!
    private var supermixPopup: NSPopUpButton!
    private var assayPopup: NSPopUpButton!
    private var experimentPopup: NSPopUpButton!
    private var sampleTypePopup: NSPopUpButton!
    private var exportButton: NSButton!
    private var targetFields: [NSTextField] = []
    private var targetHintLabel: NSTextField!
    private var placeholderLabel: NSTextField!
    private var dropOverlayView: TemplateDropView!
    private var dropClickView: NSView!
    private var dropImageView: NSImageView!
    private var helpPopover: NSPopover?
    private var helpButton: NSButton!
    private var selectedNamesFileURL: URL?

    private var sampleNames: [String] = [] // display list (row-major)
    private var sampleCol1: [String] = []
    private var sampleCol2: [String] = []
    private var sampleCol3: [String] = []
    private var sampleCol4: [String] = []

    private let findPython: () -> String?
    private let findDDQuint: () -> String?

    convenience init(findPython: @escaping () -> String?, findDDQuint: @escaping () -> String?) {
        let window = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 1000, height: 580),
                              styleMask: [.titled, .closable, .resizable],
                              backing: .buffered,
                              defer: false)
        self.init(window: window, findPython: findPython, findDDQuint: findDDQuint)
    }

    init(window: NSWindow?, findPython: @escaping () -> String?, findDDQuint: @escaping () -> String?) {
        self.findPython = findPython
        self.findDDQuint = findDDQuint
        super.init(window: window)
        self._init(findPython: findPython, findDDQuint: findDDQuint)
    }

    required init?(coder: NSCoder) {
        fatalError("init(coder:) has not been implemented")
    }

    private func _init(findPython: @escaping () -> String?, findDDQuint: @escaping () -> String?) {
        window?.title = "Template Creator"
        // Position window more to the left for smaller screens
        if let screen = NSScreen.main {
            let screenFrame = screen.visibleFrame
            let windowFrame = window?.frame ?? NSRect.zero
            let x = screenFrame.minX + 100  // 100 points from left edge
            let y = screenFrame.midY - windowFrame.height / 2
            window?.setFrameOrigin(NSPoint(x: x, y: y))
        } else {
            window?.center()
        }
        window?.isReleasedWhenClosed = false
        window?.delegate = self
        addHelpTitlebarAccessory()
        setupUI()
        setupDefaults()
        resetSampleData()
    }

    
    private func addHelpTitlebarAccessory() {
        guard let window = self.window else { return }
        let vc = NSTitlebarAccessoryViewController()
        vc.layoutAttribute = .trailing
        let container = NSView()
        container.translatesAutoresizingMaskIntoConstraints = false
        let helpButton = NSButton()
        helpButton.bezelStyle = .helpButton
        helpButton.isBordered = false
        helpButton.toolTip = "Sample names file: CSV or XLSX, no header row; up to 4 columns. Columns 1–3 are shown per well; 4th is used for export."
        helpButton.translatesAutoresizingMaskIntoConstraints = false
        container.addSubview(helpButton)
        NSLayoutConstraint.activate([
            helpButton.leadingAnchor.constraint(equalTo: container.leadingAnchor),
            helpButton.trailingAnchor.constraint(equalTo: container.trailingAnchor),
            helpButton.topAnchor.constraint(equalTo: container.topAnchor),
            helpButton.bottomAnchor.constraint(equalTo: container.bottomAnchor),
            helpButton.widthAnchor.constraint(equalToConstant: 20),
            helpButton.heightAnchor.constraint(equalToConstant: 20)
        ])
        vc.view = container
        window.addTitlebarAccessoryViewController(vc)
    }

    @objc private func showHelpPopover(_ sender: NSButton) {
        let message = "Use a CSV/XLSX without a header row. Each row is read as a sample with up to 4 description fields."
        if helpPopover == nil {
            let pop = NSPopover()
            pop.behavior = .transient
            let vc = NSViewController()
            let container = NSView()
            container.translatesAutoresizingMaskIntoConstraints = false
            let label = NSTextField(labelWithString: message)
            label.lineBreakMode = .byWordWrapping
            if let cell = label.cell as? NSTextFieldCell {
                cell.wraps = true
                cell.isScrollable = false
                cell.usesSingleLineMode = false
            }
            label.translatesAutoresizingMaskIntoConstraints = false
            container.addSubview(label)
            NSLayoutConstraint.activate([
                label.leadingAnchor.constraint(equalTo: container.leadingAnchor, constant: 12),
                label.trailingAnchor.constraint(equalTo: container.trailingAnchor, constant: -12),
                label.topAnchor.constraint(equalTo: container.topAnchor, constant: 10),
                label.bottomAnchor.constraint(equalTo: container.bottomAnchor, constant: -10),
                container.widthAnchor.constraint(equalToConstant: 360)
            ])
            vc.view = container
            pop.contentViewController = vc
            helpPopover = pop
        } else {
            if let label = helpPopover?.contentViewController?.view.subviews.first as? NSTextField {
                label.stringValue = message
            }
        }
        helpPopover?.show(relativeTo: sender.bounds, of: sender, preferredEdge: .maxY)
    }


private func setupUI() {
        guard let contentView = window?.contentView else { return }
        // Root vertical stack contains controls and preview
        let rootVStack = NSStackView()
        rootVStack.orientation = .vertical
        rootVStack.spacing = 8
        rootVStack.alignment = .width
        rootVStack.distribution = .fill
        rootVStack.translatesAutoresizingMaskIntoConstraints = false
        contentView.addSubview(rootVStack)
        NSLayoutConstraint.activate([
            rootVStack.topAnchor.constraint(equalTo: contentView.topAnchor, constant: 12),
            rootVStack.leadingAnchor.constraint(equalTo: contentView.leadingAnchor, constant: 12),
            rootVStack.trailingAnchor.constraint(equalTo: contentView.trailingAnchor, constant: -12),
            rootVStack.bottomAnchor.constraint(equalTo: contentView.bottomAnchor, constant: -12)
        ])

        // Use two-row layout to fit smaller screens (inside root stack)
        let topVStack = NSStackView()
        topVStack.orientation = .vertical
        topVStack.spacing = 4
        topVStack.translatesAutoresizingMaskIntoConstraints = false
        topVStack.alignment = .width
        // Ensure the control stack stays compact and does not grab extra height
        topVStack.distribution = .gravityAreas
        topVStack.setContentHuggingPriority(NSLayoutConstraint.Priority(1000), for: NSLayoutConstraint.Orientation.vertical)
        topVStack.setContentCompressionResistancePriority(NSLayoutConstraint.Priority(1000), for: NSLayoutConstraint.Orientation.vertical)
        rootVStack.addArrangedSubview(topVStack)

        // Keep the controls compact on a single row in the stack

        // Dropdowns on second row
        supermixPopup = NSPopUpButton()
        assayPopup = NSPopUpButton()
        experimentPopup = NSPopUpButton()
        sampleTypePopup = NSPopUpButton()
        let row2 = NSStackView()
        row2.orientation = .horizontal
        row2.alignment = .centerY
        row2.spacing = 6
        row2.translatesAutoresizingMaskIntoConstraints = false
        topVStack.addArrangedSubview(row2)
        row2.setContentHuggingPriority(NSLayoutConstraint.Priority(1000), for: NSLayoutConstraint.Orientation.vertical)
        row2.setContentCompressionResistancePriority(NSLayoutConstraint.Priority(1000), for: NSLayoutConstraint.Orientation.vertical)
        row2.addArrangedSubview(NSTextField(labelWithString: "Supermix:"))
        row2.addArrangedSubview(supermixPopup)
        row2.addArrangedSubview(NSTextField(labelWithString: "Assay:"))
        row2.addArrangedSubview(assayPopup)
        row2.addArrangedSubview(NSTextField(labelWithString: "Experiment:"))
        row2.addArrangedSubview(experimentPopup)

        // Export button will be added to the targets row below

        // Targets row (user can enter up to 4 target names)
        let targetsBar = NSStackView()
        targetsBar.orientation = .horizontal
        targetsBar.alignment = .centerY
        targetsBar.spacing = 6
        targetsBar.translatesAutoresizingMaskIntoConstraints = false
        // Place directly under dropdown row inside the vertical stack to avoid extra gap
        topVStack.addArrangedSubview(targetsBar)
        targetsBar.setContentHuggingPriority(NSLayoutConstraint.Priority(1000), for: NSLayoutConstraint.Orientation.vertical)
        targetsBar.setContentCompressionResistancePriority(NSLayoutConstraint.Priority(1000), for: NSLayoutConstraint.Orientation.vertical)
        
        targetsBar.addArrangedSubview(NSTextField(labelWithString: "Targets:"))
        targetHintLabel = NSTextField(labelWithString: "")
        targetHintLabel.textColor = .secondaryLabelColor
        targetsBar.addArrangedSubview(targetHintLabel)
        for i in 1...4 {
            let tf = NSTextField()
            tf.placeholderString = "Target \(i)"
            tf.translatesAutoresizingMaskIntoConstraints = false
            tf.widthAnchor.constraint(equalToConstant: 120).isActive = true
            tf.target = self
            tf.action = #selector(targetFieldChanged)
            targetsBar.addArrangedSubview(tf)
            targetFields.append(tf)
        }
        // Flexible spacer to push actions to the far right
        let spacer = NSView()
        spacer.translatesAutoresizingMaskIntoConstraints = false
        spacer.setContentHuggingPriority(.defaultLow, for: .horizontal)
        spacer.setContentCompressionResistancePriority(.defaultLow, for: .horizontal)
        targetsBar.addArrangedSubview(spacer)
        // Inline help button left of Export
        helpButton = NSButton()
        helpButton.bezelStyle = .helpButton
        helpButton.title = ""
        helpButton.toolTip = "Use a CSV/XLSX without a header row. Each row is read as a sample with up to 4 description fields."
        helpButton.translatesAutoresizingMaskIntoConstraints = false
        helpButton.target = self
        helpButton.action = #selector(showHelpPopover(_:))
        targetsBar.addArrangedSubview(helpButton)
        // Add export button on this row
        exportButton = NSButton(title: "Export Template...", target: self, action: #selector(exportTemplate))
        exportButton.isEnabled = false
        exportButton.bezelStyle = .rounded
        if #available(macOS 10.14, *) { exportButton.contentTintColor = NSColor.systemGray }
        targetsBar.addArrangedSubview(exportButton)

        // Preview container that will host either the drop/click prompt or the grid
        previewContainer = NSView()
        previewContainer.wantsLayer = true
        previewContainer.translatesAutoresizingMaskIntoConstraints = false
        rootVStack.addArrangedSubview(previewContainer)
        NSLayoutConstraint.activate([
            previewContainer.heightAnchor.constraint(greaterThanOrEqualToConstant: 490),
            previewContainer.widthAnchor.constraint(greaterThanOrEqualToConstant: 990)
        ])
        // Let the preview container take remaining vertical space
        previewContainer.setContentHuggingPriority(NSLayoutConstraint.Priority(1), for: NSLayoutConstraint.Orientation.vertical)
        previewContainer.setContentCompressionResistancePriority(NSLayoutConstraint.Priority(1), for: NSLayoutConstraint.Orientation.vertical)

        // Drop/click prompt overlay (like main window)
        dropClickView = NSView()
        dropClickView.wantsLayer = true
        dropClickView.layer?.backgroundColor = NSColor.clear.cgColor
        dropClickView.translatesAutoresizingMaskIntoConstraints = false
        previewContainer.addSubview(dropClickView)
        dropImageView = NSImageView()
        dropImageView.imageScaling = .scaleNone
        dropImageView.imageAlignment = .alignCenter
        dropImageView.translatesAutoresizingMaskIntoConstraints = false
        dropClickView.addSubview(dropImageView)
        dropOverlayView = TemplateDropView()
        dropOverlayView.onFileDropped = { [weak self] url in self?.loadSampleNames(from: url) }
        dropOverlayView.onClicked = { [weak self] in self?.openFileChooser() }
        dropOverlayView.translatesAutoresizingMaskIntoConstraints = false
        dropClickView.addSubview(dropOverlayView)
        NSLayoutConstraint.activate([
            dropClickView.topAnchor.constraint(equalTo: previewContainer.topAnchor),
            dropClickView.leadingAnchor.constraint(equalTo: previewContainer.leadingAnchor),
            dropClickView.trailingAnchor.constraint(equalTo: previewContainer.trailingAnchor),
            dropClickView.bottomAnchor.constraint(equalTo: previewContainer.bottomAnchor),
            dropImageView.topAnchor.constraint(equalTo: dropClickView.topAnchor),
            dropImageView.leadingAnchor.constraint(equalTo: dropClickView.leadingAnchor),
            dropImageView.trailingAnchor.constraint(equalTo: dropClickView.trailingAnchor),
            dropImageView.bottomAnchor.constraint(equalTo: dropClickView.bottomAnchor),
            dropOverlayView.topAnchor.constraint(equalTo: dropClickView.topAnchor),
            dropOverlayView.leadingAnchor.constraint(equalTo: dropClickView.leadingAnchor),
            dropOverlayView.trailingAnchor.constraint(equalTo: dropClickView.trailingAnchor),
            dropOverlayView.bottomAnchor.constraint(equalTo: dropClickView.bottomAnchor)
        ])

        // No extra constraints needed here; rootVStack manages vertical layout
        // Create the prompt image after layout settles; ensure layout is up to date
        DispatchQueue.main.async { [weak self] in
            self?.dropClickView.layoutSubtreeIfNeeded()
            self?.createFileSelectionImage()
        }
    }

    private func setupDefaults() {
        // Hard-coded options from provided list, default is the first
        supermixPopup.removeAllItems()
        supermixPopup.addItems(withTitles: [
            "ddPCR Supermix for Probes (No dUTP)",
            "ddPCR EvaGreen Supermix",
            "ddPCR Supermix for Probes",
            "ddPCR Multiplex Supermix",
            "ddPCR Supermix for Residual DNA Quantification"
        ])
        
        assayPopup.removeAllItems()
        assayPopup.addItems(withTitles: [
            "Probe Mix Triplex",
            "Amplitude Multiplex",
            "Single Target per Channel"
        ])
        
        experimentPopup.removeAllItems()
        experimentPopup.addItems(withTitles: [
            "Copy Number Variation (CNV)",
            "Direct Quantification (DQ)",
            "Mutation Detection (MUT)",
            "Rare Event Detection (RED)",
            "Drop Off (DOF)",
            "Gene Expression (GEX)",
            "Residual DNA Quantification (RDQ)"
        ])
        
        sampleTypePopup.removeAllItems()
        sampleTypePopup.addItems(withTitles: [
            "Unknown",
            "NTC",
            "Pos Ctrl",
            "Neg Ctrl"
        ])
        
        // Load saved settings or use defaults
        loadSettings()
        
        // Hook to update target hint on change and save settings
        supermixPopup.target = self
        supermixPopup.action = #selector(settingChanged)
        assayPopup.target = self
        assayPopup.action = #selector(assayChanged)
        experimentPopup.target = self
        experimentPopup.action = #selector(settingChanged)
        
        updateTargetHint()
    }
    
    private func loadSettings() {
        let defaults = UserDefaults.standard
        
        if let savedSupermix = defaults.string(forKey: "TemplateCreator.Supermix") {
            supermixPopup.selectItem(withTitle: savedSupermix)
        } else {
            supermixPopup.selectItem(at: 0)
        }
        
        if let savedAssay = defaults.string(forKey: "TemplateCreator.Assay") {
            assayPopup.selectItem(withTitle: savedAssay)
        } else {
            assayPopup.selectItem(at: 0)
        }
        
        if let savedExperiment = defaults.string(forKey: "TemplateCreator.Experiment") {
            experimentPopup.selectItem(withTitle: savedExperiment)
        } else {
            experimentPopup.selectItem(at: 0)
        }
        
        // Load target field values
        for (i, tf) in targetFields.enumerated() {
            if let savedTarget = defaults.string(forKey: "TemplateCreator.Target\(i)") {
                tf.stringValue = savedTarget
            }
        }
    }
    
    private func saveSettings() {
        let defaults = UserDefaults.standard
        
        defaults.set(supermixPopup.titleOfSelectedItem, forKey: "TemplateCreator.Supermix")
        defaults.set(assayPopup.titleOfSelectedItem, forKey: "TemplateCreator.Assay")
        defaults.set(experimentPopup.titleOfSelectedItem, forKey: "TemplateCreator.Experiment")
        
        // Save target field values
        for (i, tf) in targetFields.enumerated() {
            defaults.set(tf.stringValue, forKey: "TemplateCreator.Target\(i)")
        }
    }

    private func openFileChooser() {
        let openPanel = NSOpenPanel()
        openPanel.canChooseFiles = true
        openPanel.canChooseDirectories = false
        openPanel.allowsMultipleSelection = false
        openPanel.allowedFileTypes = ["csv", "xlsx", "xls"]
        openPanel.prompt = "Select"
        if let last = UserDefaults.standard.string(forKey: "LastDir.TemplateCreator.Input") {
            openPanel.directoryURL = URL(fileURLWithPath: last)
        }
        if openPanel.runModal() == .OK, let url = openPanel.url {
            UserDefaults.standard.set(url.deletingLastPathComponent().path, forKey: "LastDir.TemplateCreator.Input")
            loadSampleNames(from: url)
        }
    }

    private func loadSampleNames(from url: URL) {
        selectedNamesFileURL = url
        guard let pythonPath = findPython(), let ddqPath = findDDQuint() else { return }
        let process = Process()
        process.executableURL = URL(fileURLWithPath: pythonPath)
        let escapedPath = url.path.replacingOccurrences(of: "'", with: "\\'")
        let escapedDDQ = ddqPath.replacingOccurrences(of: "'", with: "\\'")
        let py = [
            "import sys, os, json",
            "sys.path.insert(0, '\(escapedDDQ)')",
            "disp = []\nc1=c2=c3=c4=[]",
            "try:",
            "    import pandas as pd",
            "    p = '\(escapedPath)'",
            "    ext = os.path.splitext(p)[1].lower()",
            "    if ext == '.csv':",
            "        df = pd.read_csv(p, header=None).fillna('')",
            "    elif ext in ('.xlsx', '.xls'):",
            "        df = pd.read_excel(p, header=None).fillna('')",
            "    else:",
            "        df = None",
            "    if df is not None and len(df)>0:",
            "        # Extract up to 4 columns as strings",
            "        def col(i):",
            "            return [str(x).strip() for x in (df.iloc[:,i].tolist() if i < df.shape[1] else [])]",
            "        c1 = col(0)",
            "        c2 = col(1)",
            "        c3 = col(2)",
            "        c4 = col(3)",
            "        n = max(len(c1), len(c2), len(c3), len(c4), 0)",
            "        def pad(lst): return (lst + ['']*(n-len(lst)))[:n]",
            "        c1, c2, c3, c4 = pad(c1), pad(c2), pad(c3), pad(c4)",
            "        # Combine first three columns for display",
            "        def combine(a,b,c):",
            "            parts = [x for x in [a,b,c] if str(x).strip()!='']",
            "            return ' | '.join(parts)",
            "        disp = [combine(a,b,c) for a,b,c in zip(c1,c2,c3)]",
            "    out = {'disp': disp, 'c1': c1, 'c2': c2, 'c3': c3, 'c4': c4}",
            "    print('NAMES:'+json.dumps(out))",
            "except Exception as e:",
            "    print('ERROR:'+str(e))"
        ].joined(separator: "\n")
        process.arguments = ["-c", py]
        let pipe = Pipe()
        process.standardOutput = pipe
        process.standardError = pipe
        do {
            try process.run()
            process.waitUntilExit()
            let data = pipe.fileHandleForReading.readDataToEndOfFile()
            let out = String(data: data, encoding: .utf8) ?? ""
            if let range = out.range(of: "NAMES:") {
                let jsonStr = String(out[range.upperBound...]).trimmingCharacters(in: .whitespacesAndNewlines)
                if let jdata = jsonStr.data(using: .utf8),
                   let obj = try? JSONSerialization.jsonObject(with: jdata) as? [String: Any] {
                    let disp = obj["disp"] as? [String] ?? []
                    let c1 = obj["c1"] as? [String] ?? []
                    let c2 = obj["c2"] as? [String] ?? []
                    let c3 = obj["c3"] as? [String] ?? []
                    let c4 = obj["c4"] as? [String] ?? []
                    DispatchQueue.main.async {
                        self.sampleNames = disp
                        self.sampleCol1 = c1
                        self.sampleCol2 = c2
                        self.sampleCol3 = c3
                        self.sampleCol4 = c4
                        self.renderGrid()
                        self.exportButton.isEnabled = !disp.isEmpty
                        if !disp.isEmpty {
                            if #available(macOS 10.14, *) { 
                                self.exportButton.contentTintColor = NSColor.lightGray 
                            }
                            self.exportButton.bezelStyle = .rounded
                            // Lock window size when preview loads
                            self.window?.minSize = NSSize(width: 1000, height: 580)
                            self.window?.maxSize = NSSize(width: 1000, height: 580)
                        }
                    }
                }
            }
        } catch {}
    }

    private func renderGrid() {
        // Remove existing
        if gridContainer != nil {
            while gridContainer.numberOfRows > 0 { gridContainer.removeRow(at: 0) }
        }
        // Build headers
        var rows: [[NSView]] = []
        // Header row: empty corner + 12 columns
        var headerViews: [NSView] = [TemplateCreatorWindowController.cellBox(with: "")] 
        for col in 1...12 {
            headerViews.append(TemplateCreatorWindowController.cellBox(with: String(format: "%02d", col), centered: true))
        }
        rows.append(headerViews)
        // Rows A..H
        for (idx, rowChar) in ["A","B","C","D","E","F","G","H"].enumerated() {
            var rowViews: [NSView] = [TemplateCreatorWindowController.cellBox(with: rowChar, centered: true)]
            for col in 1...12 {
                // Column-major mapping: column-first then rows
                let dataIdx = (col - 1) * 8 + idx
                let n1 = dataIdx < sampleCol1.count ? sampleCol1[dataIdx] : (dataIdx < sampleNames.count ? sampleNames[dataIdx] : "")
                let n2 = dataIdx < sampleCol2.count ? sampleCol2[dataIdx] : ""
                let n3 = dataIdx < sampleCol3.count ? sampleCol3[dataIdx] : ""
                // Build multi-line content: col1, col2, col3 on separate lines (skip empty)
                let parts = [n1, n2, n3].filter { !$0.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty }
                let text = parts.joined(separator: "\n")
                rowViews.append(TemplateCreatorWindowController.cellBox(with: text))
            }
            rows.append(rowViews)
        }
        let newGrid = NSGridView(views: rows)
        newGrid.translatesAutoresizingMaskIntoConstraints = false
        newGrid.rowSpacing = 4
        newGrid.columnSpacing = 6
        if gridScroll == nil {
            gridScroll = NSScrollView()
            gridScroll.hasVerticalScroller = false
            gridScroll.hasHorizontalScroller = false
            gridScroll.translatesAutoresizingMaskIntoConstraints = false
            previewContainer.addSubview(gridScroll)
            NSLayoutConstraint.activate([
                gridScroll.topAnchor.constraint(equalTo: previewContainer.topAnchor),
                gridScroll.leadingAnchor.constraint(equalTo: previewContainer.leadingAnchor),
                gridScroll.trailingAnchor.constraint(equalTo: previewContainer.trailingAnchor),
                gridScroll.bottomAnchor.constraint(equalTo: previewContainer.bottomAnchor)
            ])
        }
        gridScroll.documentView = newGrid
        gridScroll.isHidden = false
        // Center the grid in the scroll view
        NSLayoutConstraint.activate([
            newGrid.centerXAnchor.constraint(equalTo: gridScroll.contentView.centerXAnchor),
            newGrid.centerYAnchor.constraint(equalTo: gridScroll.contentView.centerYAnchor),
            newGrid.topAnchor.constraint(greaterThanOrEqualTo: gridScroll.contentView.topAnchor),
            newGrid.leadingAnchor.constraint(greaterThanOrEqualTo: gridScroll.contentView.leadingAnchor)
        ])
        gridContainer = newGrid
        dropClickView.isHidden = true
    }

    // Create a dashed-border prompt image asking for a file selection
    private func createFileSelectionImage() {
        guard dropClickView != nil, dropImageView != nil else { return }
        let size = dropClickView.frame.size
        let imageWidth = max(size.width, 400)
        let imageHeight = max(size.height, 300)

        let image = NSImage(size: NSSize(width: imageWidth, height: imageHeight))
        image.lockFocus()

        // Background
        NSColor.controlBackgroundColor.setFill()
        NSRect(x: 0, y: 0, width: imageWidth, height: imageHeight).fill()

        // Dashed border with margin
        let margin: CGFloat = 20
        NSColor.separatorColor.setStroke()
        let borderPath = NSBezierPath(rect: NSRect(x: margin, y: margin, width: imageWidth - 2*margin, height: imageHeight - 2*margin))
        borderPath.setLineDash([5, 5], count: 2, phase: 0)
        borderPath.lineWidth = 2
        borderPath.stroke()

        // Centered text
        let text = "Click here to select file\nwith sample names"
        let paragraph = NSMutableParagraphStyle()
        paragraph.alignment = .center
        paragraph.lineSpacing = 4
        let attrs: [NSAttributedString.Key: Any] = [
            .font: NSFont.systemFont(ofSize: 18),
            .foregroundColor: NSColor.controlTextColor,
            .paragraphStyle: paragraph
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

        dropImageView.image = image
    }

    // Redraw the prompt image to match the new size when resizing
    func windowDidResize(_ notification: Notification) {
        if dropClickView != nil, dropImageView != nil, dropClickView.isHidden == false {
            createFileSelectionImage()
        }
    }
    
    // Track if we should reset on next show
    private var shouldResetOnShow = true
    
    func windowDidBecomeKey(_ notification: Notification) {
        // Only reset when window becomes key after being closed
        if shouldResetOnShow {
            resetSampleData()
            shouldResetOnShow = false
        }
    }
    
    func windowWillClose(_ notification: Notification) {
        // Mark for reset when window is closed and will be reopened
        shouldResetOnShow = true
    }
    
    private func resetSampleData() {
        // Clear sample names and reset UI when window is reopened
        sampleNames = []
        exportButton.isEnabled = false
        if #available(macOS 10.14, *) { exportButton.contentTintColor = NSColor.systemGray }
        
        // Show drop/click view and hide grid
        dropClickView.isHidden = false
        if let gridScroll = gridScroll {
            gridScroll.isHidden = true
            gridScroll.documentView = nil
        }
        gridContainer = nil
        
        // Reset window resize constraints
        window?.minSize = NSSize(width: 400, height: 300)
        window?.maxSize = NSSize(width: CGFloat.greatestFiniteMagnitude, height: CGFloat.greatestFiniteMagnitude)
        
        // Recreate the file selection image
        DispatchQueue.main.async { [weak self] in
            self?.createFileSelectionImage()
        }
    }

    // Build a boxed cell with border for gridlines
    static func cellBox(with text: String, centered: Bool = false) -> NSView {
        let box = NSBox()
        box.boxType = .custom
        box.borderType = .lineBorder
        box.borderWidth = 1.0
        box.contentViewMargins = NSSize(width: 8, height: 6)
        let label = NSTextField(labelWithString: text)
        if centered {
            // Headers are much bigger and bold
            label.font = NSFont.boldSystemFont(ofSize: 16)
        } else {
            // Sample names are smaller
            label.font = NSFont.systemFont(ofSize: 9)
        }
        label.lineBreakMode = .byTruncatingTail
        label.alignment = .center
        box.translatesAutoresizingMaskIntoConstraints = false
        label.translatesAutoresizingMaskIntoConstraints = false
        box.addSubview(label)
        NSLayoutConstraint.activate([
            label.leadingAnchor.constraint(equalTo: box.leadingAnchor, constant: 8),
            label.trailingAnchor.constraint(equalTo: box.trailingAnchor, constant: -8),
            label.topAnchor.constraint(equalTo: box.topAnchor, constant: 6),
            label.bottomAnchor.constraint(equalTo: box.bottomAnchor, constant: -6),
            box.widthAnchor.constraint(equalToConstant: 70),
            box.heightAnchor.constraint(equalToConstant: 50)
        ])
        return box
    }

    @objc private func exportTemplate() {
        guard let pythonPath = findPython(), let ddqPath = findDDQuint(), !sampleNames.isEmpty else { return }
        let savePanel = NSSavePanel()
        savePanel.allowedContentTypes = [.commaSeparatedText]
        // Default file name based on input file
        if let inURL = selectedNamesFileURL {
            let base = inURL.deletingPathExtension().lastPathComponent
            savePanel.nameFieldStringValue = "\(base).csv"
        } else {
            savePanel.nameFieldStringValue = "plate_template.csv"
        }
        if let last = UserDefaults.standard.string(forKey: "LastDir.TemplateCreator.Export") {
            savePanel.directoryURL = URL(fileURLWithPath: last)
        }
        savePanel.prompt = "Export"
        if savePanel.runModal() != .OK { return }
        guard let outURL = savePanel.url else { return }
        UserDefaults.standard.set(outURL.deletingLastPathComponent().path, forKey: "LastDir.TemplateCreator.Export")

        let process = Process()
        process.executableURL = URL(fileURLWithPath: pythonPath)
        let escapedDDQ = ddqPath.replacingOccurrences(of: "'", with: "\\'")
        let outputPath = outURL.path.replacingOccurrences(of: "'", with: "\\'")
        func toJSON(_ arr: [String]) -> String {
            if let data = try? JSONSerialization.data(withJSONObject: arr, options: []),
               let s = String(data: data, encoding: .utf8) { return s }
            return "[]"
        }
        let namesJSON = toJSON(sampleNames)
        let names2JSON = toJSON(sampleCol2)
        let names3JSON = toJSON(sampleCol3)
        let names4JSON = toJSON(sampleCol4)
        let supermix = supermixPopup.titleOfSelectedItem ?? "ddPCR Supermix for Probes (No dUTP)"
        let assay = assayPopup.titleOfSelectedItem ?? "Probe Mix Triplex"
        let experiment = experimentPopup.titleOfSelectedItem ?? "Copy Number Variation (CNV)"
        let sampleType = "Unknown"
        // Collect targets (up to 4)
        let targets = targetFields.map { $0.stringValue.trimmingCharacters(in: .whitespacesAndNewlines) }
        let targetsJSON: String
        if let tdata = try? JSONSerialization.data(withJSONObject: targets, options: []), let ts = String(data: tdata, encoding: .utf8) { targetsJSON = ts } else { targetsJSON = "[]" }
        let escSupermix = supermix.replacingOccurrences(of: "'", with: "\\'")
        let escAssay = assay.replacingOccurrences(of: "'", with: "\\'")
        let escExperiment = experiment.replacingOccurrences(of: "'", with: "\\'")
        let escSampleType = sampleType.replacingOccurrences(of: "'", with: "\\'")

        let py2 = [
            "import sys, os, json, csv, datetime",
            "sys.path.insert(0, '\(escapedDDQ)')",
            "names = json.loads('''\(namesJSON)''')",
            "names2 = json.loads('''\(names2JSON)''')",
            "names3 = json.loads('''\(names3JSON)''')",
            "names4 = json.loads('''\(names4JSON)''')",
            "targets = [t for t in json.loads('''\(targetsJSON)''') if t]",
            "supermix = '\(escSupermix)'",
            "assay = '\(escAssay)'",
            "experiment = '\(escExperiment)'",
            "sample_type = '\(escSampleType)'",
            "out_path = '\(outputPath)'",
            "",
            "def header():",
            "    now = datetime.datetime.now()",
            "    return [",
            "        [\"ddplate - DO NOT MODIFY THIS LINE\", \"Version=1\",",
            "         \"ApplicationName=QX Manager Standard Edition\", \"ApplicationVersion=2.3.0.32\",",
            "         \"ApplicationEdition=ResearchEmbedded\", \"User=\\\\\\\\QX User\",",
            "         f\"CreatedDate={now.strftime('%m/%d/%Y %H:%M:%S')}\", \"\"],",
            "        [\"\"], [\"PlateSize=GCR96\"], [\"PlateNotes=\"],",
            "        [\"Well\",\"Perform Droplet Reading\",\"ExperimentType\",\"Sample description 1\",",
            "         \"Sample description 2\",\"Sample description 3\",\"Sample description 4\",",
            "         \"SampleType\",\"SupermixName\",\"AssayType\",\"TargetName\",\"TargetType\",",
            "         \"Signal Ch1\",\"Signal Ch2\",\"Reference Copies\",\"Well Notes\",\"Plot?\",",
            "         \"RdqConversionFactor\"]",
            "    ]",
            "",
            "def rows_for_well(well_id, name, n2, n3, n4):",
            "    base = [well_id, \"Yes\", experiment, name, n2, n3, n4, sample_type, supermix, assay]",
            "    at = assay.lower()",
            "    if 'single target per channel' in at:",
            "        count = 2",
            "    elif 'amplitude multiplex' in at:",
            "        count = 4",
            "    else:",
            "        count = 3",
            "    chosen = targets[:count]",
            "    while len(chosen) < count:",
            "        chosen.append(f'Target{len(chosen)+1}')",
            "    rows = []",
            "    # Use EvaGreen instead of FAM if EvaGreen supermix is selected",
            "    fam_signal = 'EvaGreen' if 'evagreen' in supermix.lower() else 'FAM'",
            "    if count == 2:",
            "        patterns = [(f\"{fam_signal}\", \"None\"), (\"None\", \"HEX\")]",
            "    elif count == 3:",
            "        patterns = [(\"None\", \"HEX\"), (f\"{fam_signal}\", \"HEX\"), (f\"{fam_signal}\", \"None\")]",
            "    else:",
            "        patterns = [(f\"{fam_signal} Lo\", \"None\"), (f\"{fam_signal} Hi\", \"None\"), (\"None\", \"HEX Lo\"), (\"None\", \"HEX Hi\")]",
            "    for i in range(count):",
            "        target_name = chosen[i]",
            "        sig1, sig2 = patterns[i]",
            "        row = base + [target_name, \"Unknown\", sig1, sig2, \"\", \"\", \"False\", \"\"]",
            "        rows.append(row)",
            "    return rows",
            "",
            "lines = header()",
            "for row_idx, row_letter in enumerate('ABCDEFGH'):",
            "    for col in range(1,13):",
            "        well = f'{row_letter}{col:02d}'",
            "        idx = (col-1)*8 + row_idx",
            "        if idx < len(names):",
            "            nm = str(names[idx])",
            "            n2 = str(names2[idx]) if idx < len(names2) else ''",
            "            n3 = str(names3[idx]) if idx < len(names3) else ''",
            "            n4 = str(names4[idx]) if idx < len(names4) else ''",
            "            lines.extend(rows_for_well(well, nm, n2, n3, n4))",
            "        else:",
            "            lines.append([well, \"No\"] + [\"\"]*16)",
            "",
            "with open(out_path, 'w', newline='') as f:",
            "    csv.writer(f).writerows(lines)",
            "print('EXPORTED:'+out_path)"
        ].joined(separator: "\n")
        process.arguments = ["-c", py2]
        let pipe = Pipe()
        process.standardOutput = pipe
        process.standardError = pipe
        do {
            try process.run()
            process.waitUntilExit()
            let data = pipe.fileHandleForReading.readDataToEndOfFile()
            let out = String(data: data, encoding: .utf8) ?? ""
            if out.contains("EXPORTED:") {
                NSWorkspace.shared.activateFileViewerSelecting([outURL])
            } else {
                let alert = NSAlert()
                alert.messageText = "Export Failed"
                alert.informativeText = out
                alert.alertStyle = .warning
                alert.runModal()
            }
        } catch {
            let alert = NSAlert()
            alert.messageText = "Export Failed"
            alert.informativeText = error.localizedDescription
            alert.alertStyle = .warning
            alert.runModal()
        }
    }

    // MARK: - Target hint logic
    @objc private func assayChanged() {
        updateTargetHint()
        saveSettings()
    }
    
    @objc private func settingChanged() {
        saveSettings()
    }
    
    @objc private func targetFieldChanged() {
        saveSettings()
    }

    private func updateTargetHint() {
        let sel = assayPopup.titleOfSelectedItem?.lowercased() ?? ""
        let supermix = supermixPopup.titleOfSelectedItem ?? ""
        let famSignal = supermix.lowercased().contains("evagreen") ? "EvaGreen" : "FAM"
        
        var hint = ""
        var needed = 3
        var placeholders: [String] = []
        
        if sel.contains("single target per channel") {
            hint = "2 targets"
            needed = 2
            placeholders = ["\(famSignal) / None", "None / HEX"]
        } else if sel.contains("amplitude multiplex") {
            hint = "4 targets"
            needed = 4
            placeholders = ["\(famSignal) Lo / None", "\(famSignal) Hi / None", "None / HEX Lo", "None / HEX Hi"]
        } else {
            hint = "3 targets"
            needed = 3
            placeholders = ["None / HEX", "\(famSignal) / HEX", "\(famSignal) / None"]
        }
        
        targetHintLabel.stringValue = hint
        for (i, tf) in targetFields.enumerated() { 
            tf.isHidden = i >= needed 
            if i < placeholders.count {
                tf.placeholderString = placeholders[i]
            }
        }
    }

}

// Simple drag/drop view to accept file URLs
class TemplateDropView: NSView {
    var onFileDropped: ((URL) -> Void)?
    var onClicked: (() -> Void)?
    override init(frame frameRect: NSRect) {
        super.init(frame: frameRect)
        registerForDraggedTypes([.fileURL])
        translatesAutoresizingMaskIntoConstraints = false
        wantsLayer = true
        layer?.backgroundColor = NSColor.clear.cgColor
    }
    required init?(coder: NSCoder) {
        super.init(coder: coder)
        registerForDraggedTypes([.fileURL])
        translatesAutoresizingMaskIntoConstraints = false
        wantsLayer = true
        layer?.backgroundColor = NSColor.clear.cgColor
    }
    override func draggingEntered(_ sender: NSDraggingInfo) -> NSDragOperation {
        return .copy
    }
    override func performDragOperation(_ sender: NSDraggingInfo) -> Bool {
        if let urls = sender.draggingPasteboard.readObjects(forClasses: [NSURL.self]) as? [URL], let url = urls.first {
            onFileDropped?(url)
            return true
        }
        return false
    }
    override func mouseUp(with event: NSEvent) {
        onClicked?()
    }
}
