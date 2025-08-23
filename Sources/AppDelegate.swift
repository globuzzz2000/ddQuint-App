import Cocoa

class AppDelegate: NSObject, NSApplicationDelegate {
    
    // Keep a strong reference to the window controller
    private var mainWindowController: InteractiveMainWindowController?
    
    func applicationDidFinishLaunching(_ aNotification: Notification) {
        // Clear all cached plots and data on app launch
        clearAllCaches()
        
        // Create and show main window
        mainWindowController = InteractiveMainWindowController()
        mainWindowController?.showWindow(nil)
        mainWindowController?.window?.makeKeyAndOrderFront(nil)
        
        // Make sure app doesn't quit when window is closed
        NSApp.setActivationPolicy(.regular)
        
        // Setup menu bar
        setupMenuBar()
    }
    
    func applicationWillTerminate(_ aNotification: Notification) {
        // Insert code here to tear down your application
    }
    
    func applicationSupportsSecureRestorableState(_ app: NSApplication) -> Bool {
        return true
    }
    
    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool {
        return true
    }
    
    private func clearAllCaches() {
        let fileManager = FileManager.default
        
        // Clear temp plot files in /tmp/
        do {
            let tempContents = try fileManager.contentsOfDirectory(atPath: "/tmp")
            for item in tempContents {
                if item.hasPrefix("ddquint_plot_") && item.hasSuffix(".png") {
                    let fullPath = "/tmp/\(item)"
                    try fileManager.removeItem(atPath: fullPath)
                    print("CACHE_CLEAR: Removed temp plot: \(fullPath)")
                }
            }
        } catch {
            print("CACHE_CLEAR: Error clearing /tmp/ plots: \(error)")
        }
        
        // Clear analysis plots directory
        let tempBase = NSTemporaryDirectory()
        let graphsDir = tempBase.appending("ddquint_analysis_plots")
        if fileManager.fileExists(atPath: graphsDir) {
            do {
                try fileManager.removeItem(atPath: graphsDir)
                print("CACHE_CLEAR: Removed analysis plots directory: \(graphsDir)")
            } catch {
                print("CACHE_CLEAR: Error removing analysis plots directory: \(error)")
            }
        }
        
        // Clear any parameter temp files
        do {
            let tempContents = try fileManager.contentsOfDirectory(atPath: tempBase)
            for item in tempContents {
                if item.hasPrefix("ddquint_params_") && item.hasSuffix(".json") {
                    let fullPath = tempBase.appending(item)
                    try fileManager.removeItem(atPath: fullPath)
                    print("CACHE_CLEAR: Removed param file: \(fullPath)")
                }
            }
        } catch {
            print("CACHE_CLEAR: Error clearing param files: \(error)")
        }
        
        print("CACHE_CLEAR: Cache clearing completed")
    }
    
    private func setupMenuBar() {
        let mainMenu = NSMenu()
        
        // App menu
        let appMenuItem = NSMenuItem()
        let appMenu = NSMenu()
        appMenu.addItem(NSMenuItem(title: "About ddQuint", action: nil, keyEquivalent: ""))
        appMenu.addItem(NSMenuItem.separator())
        appMenu.addItem(NSMenuItem(title: "Hide ddQuint", action: #selector(NSApplication.hide(_:)), keyEquivalent: "h"))
        let hideOthersItem = NSMenuItem(title: "Hide Others", action: #selector(NSApplication.hideOtherApplications(_:)), keyEquivalent: "h")
        hideOthersItem.keyEquivalentModifierMask = [.command, .option]
        appMenu.addItem(hideOthersItem)
        appMenu.addItem(NSMenuItem(title: "Show All", action: #selector(NSApplication.unhideAllApplications(_:)), keyEquivalent: ""))
        appMenu.addItem(NSMenuItem.separator())
        appMenu.addItem(NSMenuItem(title: "Quit ddQuint", action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q"))
        appMenuItem.submenu = appMenu
        mainMenu.addItem(appMenuItem)
        
        // File menu (data and documents)
        let fileMenuItem = NSMenuItem()
        let fileMenu = NSMenu(title: "File")
        // Open new input folder
        let openFolderItem = NSMenuItem(title: "Open Folder...", action: #selector(openFolder), keyEquivalent: "o")
        fileMenu.addItem(openFolderItem)
        fileMenu.addItem(NSMenuItem.separator())
        fileMenu.addItem(NSMenuItem(title: "Close", action: #selector(NSWindow.performClose(_:)), keyEquivalent: "w"))
        fileMenuItem.submenu = fileMenu
        mainMenu.addItem(fileMenuItem)
        
        // Template menu (naming and templates)
        let templateMenuItem = NSMenuItem()
        let templateMenu = NSMenu(title: "Template")
        templateMenu.addItem(NSMenuItem(title: "Select Template File...", action: #selector(selectTemplateFile), keyEquivalent: "t"))
        // Sample Description Fields submenu
        let templateOptionsItem = NSMenuItem(title: "Sample Description Fields", action: nil, keyEquivalent: "")
        let templateOptionsMenu = NSMenu(title: "Sample Description Fields")
        for count in 1...4 {
            let item = NSMenuItem(title: "Use \(count)", action: #selector(setSampleDescriptionCount(_:)), keyEquivalent: "")
            item.tag = count
            item.state = (count == (mainWindowController?.getTemplateDescriptionCount() ?? 4)) ? .on : .off
            templateOptionsMenu.addItem(item)
        }
        templateOptionsItem.submenu = templateOptionsMenu
        templateMenu.addItem(templateOptionsItem)
        templateMenu.addItem(NSMenuItem.separator())
        templateMenu.addItem(NSMenuItem(title: "Template Creator...", action: #selector(openTemplateDesigner), keyEquivalent: "n"))
        templateMenuItem.submenu = templateMenu
        mainMenu.addItem(templateMenuItem)

        // Export menu (parameter bundles)
        let exportMenuItem = NSMenuItem()
        let exportMenu = NSMenu(title: "Export")
        exportMenu.addItem(NSMenuItem(title: "Export Parameters...", action: #selector(exportParametersBundle), keyEquivalent: ""))
        exportMenu.addItem(NSMenuItem(title: "Load Parameters...", action: #selector(importParametersBundle), keyEquivalent: ""))
        exportMenuItem.submenu = exportMenu
        mainMenu.addItem(exportMenuItem)
        
        NSApp.mainMenu = mainMenu
    }
    
    @objc private func selectTemplateFile() {
        let openPanel = NSOpenPanel()
        openPanel.canChooseFiles = true
        openPanel.canChooseDirectories = false
        openPanel.allowsMultipleSelection = false
        openPanel.allowedContentTypes = [.text, .plainText]
        openPanel.prompt = "Select Template File"
        openPanel.message = "Choose a template file for sample name assignments"
        if let last = UserDefaults.standard.string(forKey: "LastDir.TemplateFile") { openPanel.directoryURL = URL(fileURLWithPath: last) }
        
        let response = openPanel.runModal()
        if response == .OK, let url = openPanel.url {
            UserDefaults.standard.set(url.deletingLastPathComponent().path, forKey: "LastDir.TemplateFile")
            mainWindowController?.setTemplateFile(url)
            mainWindowController?.applyTemplateChangeAndReanalyze()
        }
    }

    @objc private func openFolder() {
        // Forward to the main window controller to prompt and analyze
        mainWindowController?.openInputFolder()
    }

    @objc private func setSampleDescriptionCount(_ sender: NSMenuItem) {
        let selectedCount = sender.tag
        guard (1...4).contains(selectedCount) else { return }
        
        // Update checkmarks within the submenu
        if let submenu = sender.menu {
            for item in submenu.items { item.state = .off }
            sender.state = .on
        }
        
        // Apply to main controller and trigger reanalysis if a folder is selected
        mainWindowController?.setTemplateDescriptionCount(selectedCount)
        mainWindowController?.applyTemplateChangeAndReanalyze()
    }
    

    @objc private func exportParametersBundle() {
        mainWindowController?.exportParametersBundle()
    }

    @objc private func importParametersBundle() {
        mainWindowController?.importParametersBundle()
    }

    @objc private func openTemplateDesigner() {
        mainWindowController?.openTemplateDesigner()
    }
}
