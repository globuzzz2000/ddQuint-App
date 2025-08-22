#!/usr/bin/env swift

import Foundation

print("🔍 Testing parameter loading behavior...")

// Check if parameters file exists
let homeDir = FileManager.default.homeDirectoryForCurrentUser
let ddquintDir = homeDir.appendingPathComponent(".ddQuint")
let parametersFile = ddquintDir.appendingPathComponent("parameters.json")

print("Home directory: \(homeDir.path)")
print("ddQuint directory: \(ddquintDir.path)")
print("Parameters file: \(parametersFile.path)")
print("File exists: \(FileManager.default.fileExists(atPath: parametersFile.path))")

if FileManager.default.fileExists(atPath: parametersFile.path) {
    do {
        let data = try Data(contentsOf: parametersFile)
        print("File size: \(data.count) bytes")
        
        let parameters = try JSONSerialization.jsonObject(with: data) as? [String: Any] ?? [:]
        print("Parameters loaded: \(parameters.count) keys")
        
        if !parameters.isEmpty {
            print("Parameter keys: \(Array(parameters.keys).sorted())")
            
            // Show a few sample parameter values
            for key in Array(parameters.keys).sorted().prefix(5) {
                if let value = parameters[key] {
                    print("  \(key): \(value)")
                }
            }
        } else {
            print("⚠️ Parameters dictionary is empty after parsing")
        }
        
    } catch {
        print("❌ Error loading parameters: \(error)")
    }
} else {
    print("❌ Parameters file does not exist")
    
    // Check if the directory exists
    if FileManager.default.fileExists(atPath: ddquintDir.path) {
        print("✅ .ddquint directory exists")
    } else {
        print("❌ .ddquint directory does not exist")
    }
}

print("✨ Test complete")