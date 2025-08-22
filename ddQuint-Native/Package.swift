// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "ddQuint",
    platforms: [
        .macOS(.v11)
    ],
    products: [
        .executable(name: "ddQuint", targets: ["ddQuint"])
    ],
    targets: [
        .executableTarget(
            name: "ddQuint",
            dependencies: [],
            path: "Sources"
        )
    ]
)