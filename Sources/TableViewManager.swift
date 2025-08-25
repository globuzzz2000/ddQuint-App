import Cocoa

// MARK: - Data Models

/// Represents data for a single well in the analysis
struct WellData {
    let well: String
    let sampleName: String
    let dropletCount: Int
    let hasData: Bool
    let status: WellStatus
    let isEdited: Bool
}

// MARK: - Table View Management

/// Extension providing NSTableView data source and delegate functionality
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
        let selectedRows = wellListView.selectedRowIndexes
        print("Well selection changed to rows: \(Array(selectedRows))")
        
        // Update button text based on selection count
        if selectedRows.isEmpty {
            editWellButton.title = "Edit Well"
            editWellButton.isEnabled = false
            selectedWellIndex = -1
        } else if selectedRows.count == 1 {
            let selectedRow = selectedRows.first!
            editWellButton.title = "Edit This Well"
            
            if selectedRow >= 0 && selectedRow < filteredWellData.count {
                let selectedWell = filteredWellData[selectedRow]
                // Find the original index in wellData
                if let originalIndex = wellData.firstIndex(where: { $0.well == selectedWell.well }) {
                    selectedWellIndex = originalIndex
                    let well = wellData[originalIndex]
                    editWellButton.isEnabled = well.hasData
                    print("Loading plot for well: \(selectedWell.well)")
                    loadPlotForSelectedWell()
                }
            }
        } else {
            // Multiple selection
            editWellButton.title = "Edit \(selectedRows.count) Wells"
            
            // Enable if all selected wells have data
            let allHaveData = selectedRows.allSatisfy { row in
                guard row >= 0 && row < filteredWellData.count else { return false }
                let selectedWell = filteredWellData[row]
                if let originalIndex = wellData.firstIndex(where: { $0.well == selectedWell.well }) {
                    return wellData[originalIndex].hasData
                }
                return false
            }
            editWellButton.isEnabled = allHaveData
            
            // For multiple selection, show the first well's plot
            if let firstRow = selectedRows.first,
               firstRow >= 0 && firstRow < filteredWellData.count {
                let firstWell = filteredWellData[firstRow]
                if let originalIndex = wellData.firstIndex(where: { $0.well == firstWell.well }) {
                    selectedWellIndex = originalIndex
                    print("Loading plot for first selected well: \(firstWell.well)")
                    loadPlotForSelectedWell()
                }
            }
        }
    }
}

// MARK: - Well Status Management

extension InteractiveMainWindowController {
    
    /// Determine well status from analysis results
    func determineWellStatus(from result: [String: Any], wellName: String) -> WellStatus {
        print("🟡 Determining status for well \(wellName)")
        writeDebugLog("🟡 determineWellStatus called for well: \(wellName)")
        print("   Available keys: \(result.keys.sorted())")
        writeDebugLog("🟡 Available keys: \(result.keys.sorted())")
        
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
        writeDebugLog("🟡 Final status for well \(wellName): EUPLOID (default)")
        return .euploid
    }
    
    /// Check if well has been edited
    func isWellEdited(_ wellName: String) -> Bool {
        return wellParametersMap.keys.contains(wellName)
    }
}