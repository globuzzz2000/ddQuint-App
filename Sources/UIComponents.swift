import Cocoa

// MARK: - Custom UI Components

/// Helper class for proper coordinate system in scroll views
class FlippedView: NSView {
    override var isFlipped: Bool {
        return true
    }
}

// MARK: - High Quality Image View

/// Custom NSView for displaying images with high-quality scaling
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

// MARK: - Drag and Drop Support

/// Protocol for handling drag and drop operations
protocol DragDropDelegate: AnyObject {
    func didReceiveDroppedFolder(url: URL)
}

/// Custom view that supports folder drag and drop operations
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