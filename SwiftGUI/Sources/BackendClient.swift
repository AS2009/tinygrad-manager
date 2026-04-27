import Foundation
import Combine

// MARK: - Data Types

struct StatusInfo: Codable {
    let llm_loaded: Bool
    let llm_model: String?
    let llm_format: String?
    let image_model_loaded: Bool
    let image_model_id: String?
    let image_model_device: String?
    let api_running: Bool
    let has_image_gen: Bool
}

struct GPUInfo: Codable {
    let gpu_info: String
    let available_devices: [String]
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

// MARK: - Backend Client

@MainActor
class BackendClient: ObservableObject {
    static let shared = BackendClient()

    @Published var status = StatusInfo(
        llm_loaded: false, llm_model: nil, llm_format: nil,
        image_model_loaded: false, image_model_id: nil, image_model_device: nil,
        api_running: false, has_image_gen: false
    )
    @Published var gpuInfo = GPUInfo(gpu_info: "Detecting...", available_devices: ["cpu"])
    @Published var logs: [String] = []
    @Published var isBackendRunning = false

    private let base = "http://localhost:1234"
    private var logIndex = 0
    private var timer: Timer?

    func startPolling() {
        timer = Timer.scheduledTimer(withTimeInterval: 2.0, repeats: true) { [weak self] _ in
            Task { @MainActor in await self?.fetchAll() }
        }
        Task { await fetchAll() }
    }

    func stopPolling() {
        timer?.invalidate()
        timer = nil
    }

    func fetchAll() async {
        await withTaskGroup(of: Void.self) { group in
            group.addTask { await self.fetchStatus() }
            group.addTask { await self.fetchGPU() }
            group.addTask { await self.fetchLogs() }
        }
    }

    private func fetchStatus() async {
        guard let data = try? await get("/api/status"),
              let s = try? JSONDecoder().decode(StatusInfo.self, from: data) else { return }
        status = s
        isBackendRunning = s.api_running
    }

    private func fetchGPU() async {
        guard let data = try? await get("/api/gpu"),
              let g = try? JSONDecoder().decode(GPUInfo.self, from: data) else { return }
        gpuInfo = g
        isBackendRunning = true
    }

    func fetchEnv() async -> EnvInfo? {
        guard let data = try? await get("/api/env") else { return nil }
        return try? JSONDecoder().decode(EnvInfo.self, from: data)
    }

    private func fetchLogs() async {
        guard let data = try? await get("/api/logs?since=\(logIndex)"),
              let r = try? JSONDecoder().decode(LogResponse.self, from: data) else { return }
        if !r.entries.isEmpty {
            logs.append(contentsOf: r.entries)
            logIndex = r.total
            if logs.count > 500 { logs.removeFirst(logs.count - 500) }
        }
        isBackendRunning = true
    }

    func loadLLMModel(filePath: String, device: String) async -> String {
        let body: [String: String] = ["file_path": filePath, "device": device]
        guard let data = try? await post("/api/model/load", body: body),
              let r = try? JSONDecoder().decode(LoadResponse.self, from: data) else {
            return "Error: request failed"
        }
        return r.model_name.map { "Loaded: \($0)" } ?? r.error ?? r.message ?? "Unknown"
    }

    func loadImageModel(source: String, device: String) async -> String {
        let body: [String: String] = ["model_source": source, "device": device]
        guard let data = try? await post("/api/image/load", body: body),
              let r = try? JSONDecoder().decode(LoadResponse.self, from: data) else {
            return "Error: request failed"
        }
        return r.message ?? r.error ?? "Unknown"
    }

    func generateImage(prompt: String, steps: Int = 25) async -> ImageGenResponse? {
        let body: [String: Any] = ["prompt": prompt, "steps": steps,
                                     "width": 512, "height": 512, "cfg_scale": 7.5]
        guard let jsonData = try? JSONSerialization.data(withJSONObject: body),
              let data = try? await postData("/api/image/generate", body: jsonData) else { return nil }
        return try? JSONDecoder().decode(ImageGenResponse.self, from: data)
    }

    func startService() async -> Bool {
        guard let data = try? await post("/api/service/start", body: [:] as [String:String]),
              let obj = try? JSONSerialization.jsonObject(with: data) as? [String: Bool] else { return false }
        return obj["success"] ?? false
    }

    func stopService() async -> Bool {
        guard let data = try? await post("/api/service/stop", body: [:] as [String:String]),
              let obj = try? JSONSerialization.jsonObject(with: data) as? [String: Bool] else { return false }
        return obj["success"] ?? false
    }

    // MARK: - HTTP helpers

    private func get(_ path: String) async throws -> Data {
        let url = URL(string: "\(base)\(path)")!
        var req = URLRequest(url: url, timeoutInterval: 5)
        req.httpMethod = "GET"
        let (data, _) = try await URLSession.shared.data(for: req)
        return data
    }

    private func post(_ path: String, body: [String: String]) async throws -> Data {
        let data = try JSONSerialization.data(withJSONObject: body)
        return try await postData(path, body: data)
    }

    private func postData(_ path: String, body: Data) async throws -> Data {
        let url = URL(string: "\(base)\(path)")!
        var req = URLRequest(url: url, timeoutInterval: 30)
        req.httpMethod = "POST"
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        req.httpBody = body
        let (data, _) = try await URLSession.shared.data(for: req)
        return data
    }
}
