// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "TinyGradManager",
    platforms: [.macOS(.v14)],
    products: [
        .executable(name: "TinyGradManager", targets: ["TinyGradManager"])
    ],
    targets: [
        .executableTarget(
            name: "TinyGradManager",
            path: "Sources",
            swiftSettings: [.unsafeFlags(["-Xlinker", "-rpath", "-Xlinker", "@executable_path/../Frameworks"])]
        )
    ]
)
