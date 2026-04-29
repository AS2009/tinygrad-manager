import Foundation

// MARK: - Connection & Process State

enum ConnectionState: Equatable {
    case disconnected
    case connecting
    case connected
    case error(String)
}

enum ProcessState: Equatable {
    case stopped
    case starting
    case running
    case crashed(String)
    case restarting(attempt: Int, maxAttempts: Int)
}

// MARK: - API Response Models

struct StatusInfo: Codable {
    let llm_loaded: Bool
    let llm_model: String?
    let llm_format: String?
    let image_model_loaded: Bool
    let image_model_id: String?
    let image_model_device: String?
    let has_image_gen: Bool

    static let empty = StatusInfo(
        llm_loaded: false, llm_model: nil, llm_format: nil,
        image_model_loaded: false, image_model_id: nil, image_model_device: nil,
        has_image_gen: false
    )
}

struct GPUInfo: Codable {
    let gpu_info: String
    let available_devices: [String]

    static let empty = GPUInfo(gpu_info: "Detecting...", available_devices: [])
}

struct EnvInfo: Codable {
    let report: String
    let details: EnvDetails
    let diffusers: [String: Bool]?
}

struct EnvDetails: Codable {
    let tinygrad: TinyGradInfo?
    let metal: Bool
    let cuda: Bool
    let platform: String
    let python_version: String
}

struct TinyGradInfo: Codable {
    let installed: Bool?
    let version: String?
    let default_device: String?
    let error: String?
}

struct LogResponse: Codable {
    let entries: [String]
    let total: Int
}

struct LoadResponse: Codable {
    let success: Bool?
    let model_name: String?
    let detail: String?
    let error: String?
    let message: String?
}

struct ImageGenResponse: Codable {
    let success: Bool
    let filepath: String?
    let elapsed_seconds: Double?
    let width: Int?
    let height: Int?
}

// MARK: - Shared Helpers

/// Convert backend display string (e.g. "cuda:0 (NVIDIA RTX 3080)") to device key (e.g. "cuda:0").
func parseDeviceKey(from display: String) -> String {
    if display.hasPrefix("cuda:") {
        if let spaceIdx = display.firstIndex(of: " ") {
            return String(display[display.startIndex..<spaceIdx])
        }
        return display
    }
    if display.lowercased().hasPrefix("mps") {
        return "mps"
    }
    return "mps"
}
