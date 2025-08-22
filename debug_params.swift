#!/usr/bin/env swift

import Foundation

print("🔍 Debug: Parameter loading test")

let homeDir = FileManager.default.homeDirectoryForCurrentUser
let ddquintDir = homeDir.appendingPathComponent(".ddQuint")
let parametersFile = ddquintDir.appendingPathComponent("parameters.json")

print("Home dir: \(homeDir.path)")
print("ddQuint dir: \(ddquintDir.path)")
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
            
            // Check specific values
            if let hdbscanSize = parameters["HDBSCAN_MIN_CLUSTER_SIZE"] {
                print("HDBSCAN_MIN_CLUSTER_SIZE: \(hdbscanSize)")
            }
            if let targets = parameters["ANEUPLOIDY_TARGETS"] as? [String: Any] {
                print("ANEUPLOIDY_TARGETS: \(targets)")
            }
        } else {
            print("❌ Parameters dictionary is empty after parsing")
        }
        
    } catch {
        print("❌ Error loading parameters: \(error)")
    }
} else {
    print("❌ Parameters file does not exist")
}

print("✨ Debug complete")