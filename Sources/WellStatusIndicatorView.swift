import Cocoa

enum WellStatus {
    case euploid
    case buffer
    case aneuploid
    case warning
}

class WellStatusIndicatorView: NSView {
    var status: WellStatus = .euploid {
        didSet {
            needsDisplay = true
        }
    }
    
    var isEdited: Bool = false {
        didSet {
            needsDisplay = true
        }
    }
    
    override init(frame frameRect: NSRect) {
        super.init(frame: frameRect)
        self.wantsLayer = true
    }
    
    required init?(coder: NSCoder) {
        super.init(coder: coder)
        self.wantsLayer = true
    }
    
    override func draw(_ dirtyRect: NSRect) {
        super.draw(dirtyRect)
        
        let bounds = self.bounds
        let size = min(bounds.width, bounds.height) - 2 // Leave space for border
        let rect = NSRect(x: (bounds.width - size) / 2, 
                         y: (bounds.height - size) / 2, 
                         width: size, 
                         height: size)
        
        // Determine fill color based on status
        let fillColor: NSColor
        switch status {
        case .euploid:
            fillColor = NSColor.white
        case .buffer:
            // Stronger grey for better visibility
            fillColor = NSColor(calibratedWhite: 0.4, alpha: 1.0) // ~#666666
        case .aneuploid:
            // Strong, saturated pink (approx #E91E63)
            fillColor = NSColor(calibratedRed: 0.847, green: 0.427, blue: 0.804, alpha: 1.0)
        case .warning:
            fillColor = NSColor.red
        }
        
        // Debug: Print status for troubleshooting
        print("🔵 Drawing indicator with status: \(status), isEdited: \(isEdited), color: \(fillColor)")
        
        // Draw shape (circle for normal, square for edited)
        let path: NSBezierPath
        if isEdited {
            path = NSBezierPath(rect: rect)
        } else {
            path = NSBezierPath(ovalIn: rect)
        }
        
        // Fill the shape
        fillColor.setFill()
        path.fill()
        
        // Draw black border
        NSColor.black.setStroke()
        path.lineWidth = 1.0
        path.stroke()
    }
    
    override var intrinsicContentSize: NSSize {
        return NSSize(width: 12, height: 12)
    }
}
