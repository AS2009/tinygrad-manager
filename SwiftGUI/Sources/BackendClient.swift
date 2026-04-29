import Foundation
import Observation

// MARK: - Backend HTTP Client

@MainActor
@Observable
final class BackendClient {
    var status = StatusInfo.empty
    var gpuInfo = GPUInfo.empty
    var logs: [String] = []
    var connectionState: ConnectionState = .disconnected
    var lastError: String?
    var serviceRunning = false

    private let base = "http://localhost:1234"
    private var logIndex = 0
    private var pollingTask: Task<Void, Never>?
    private var isPolling = false
    private var failureCount = 0
    private let maxFailures = 3

    // MARK: - Polling Lifecycle

    func startPolling() {
        guard !isPolling else { return }
        isPolling = true
        connectionState = .connecting
        pollingTask = Task {
            while isPolling && !Task.isCancelled {
                await fetchAll()
                try? await Task.sleep(nanoseconds: 2_000_000_000)
            }
        }
    }

    func stopPolling() {
        isPolling = false
        pollingTask?.cancel()
        pollingTask = nil
    }

    // MARK: - Fetch Methods

    func fetchAll() async {
        await withTaskGroup(of: Void.self) { group in
            group.addTask { await self.fetchStatus() }
            group.addTask { await self.fetchGPU() }
            group.addTask { await self.fetchLogs() }
        }
    }

    func fetchStatus() async {
        do {
            let data = try await get("/api/status")
            if let s = try? JSONDecoder().decode(StatusInfo.self, from: data) {
                status = s
                failureCount = 0
                connectionState = .connected
            }
        } catch {
            handleFailure()
        }
    }

    func fetchGPU() async {
        do {
            let data = try await get("/api/gpu")
            if let g = try? JSONDecoder().decode(GPUInfo.self, from: data) {
                gpuInfo = g
                failureCount = 0
                connectionState = .connected
            }
        } catch {
            handleFailure()
        }
    }

    func fetchEnv() async -> EnvInfo? {
        do {
            let data = try await get("/api/env")
            return try? JSONDecoder().decode(EnvInfo.self, from: data)
        } catch {
            handleFailure()
            return nil
        }
    }

    func fetchLogs() async {
        do {
            let data = try await get("/api/logs?since=\(logIndex)")
            if let r = try? JSONDecoder().decode(LogResponse.self, from: data) {
                if !r.entries.isEmpty {
                    logs.append(contentsOf: r.entries)
                    logIndex = r.total
                    if logs.count > 1000 { logs.removeFirst(logs.count - 1000) }
                }
                failureCount = 0
                connectionState = .connected
            }
        } catch {
            handleFailure()
        }
    }

    // MARK: - Action Methods

    func loadLLMModel(filePath: String, device: String) async -> String {
        let body: [String: String] = ["file_path": filePath, "device": device]
        do {
            let data = try await post("/api/model/load", body: body)
            if let r = try? JSONDecoder().decode(LoadResponse.self, from: data) {
                return r.detail ?? r.model_name.map { "Loaded: \($0)" } ?? r.error ?? r.message ?? "Unknown response"
            }
            return "Invalid response"
        } catch {
            return "Error: \(error.localizedDescription)"
        }
    }

    func loadImageModel(source: String, device: String) async -> String {
        let body: [String: String] = ["model_source": source, "device": device]
        do {
            let data = try await post("/api/image/load", body: body)
            if let r = try? JSONDecoder().decode(LoadResponse.self, from: data) {
                return r.message ?? r.error ?? "Unknown response"
            }
            return "Invalid response"
        } catch {
            return "Error: \(error.localizedDescription)"
        }
    }

    func generateImage(prompt: String, steps: Int = 25) async -> ImageGenResponse? {
        let body: [String: Any] = [
            "prompt": prompt, "steps": steps,
            "width": 512, "height": 512, "cfg_scale": 7.5
        ]
        do {
            let jsonData = try JSONSerialization.data(withJSONObject: body)
            let data = try await postData("/api/image/generate", body: jsonData)
            return try? JSONDecoder().decode(ImageGenResponse.self, from: data)
        } catch {
            handleFailure()
            return nil
        }
    }

    func startService() async -> Bool {
        do {
            let data = try await post("/api/service/start", body: [:] as [String: String])
            if let obj = try? JSONSerialization.jsonObject(with: data) as? [String: Bool] {
                if obj["success"] == true { serviceRunning = true }
                return obj["success"] ?? false
            }
            return false
        } catch {
            handleFailure()
            return false
        }
    }

    func stopService() async -> Bool {
        do {
            let data = try await post("/api/service/stop", body: [:] as [String: String])
            if let obj = try? JSONSerialization.jsonObject(with: data) as? [String: Bool] {
                if obj["success"] == true { serviceRunning = false }
                return obj["success"] ?? false
            }
            return false
        } catch {
            handleFailure()
            return false
        }
    }

    // MARK: - Log Management

    func appendLog(_ message: String) {
        logs.append(message)
        if logs.count > 1000 { logs.removeFirst(logs.count - 1000) }
    }

    func clearLogs() {
        logs.removeAll()
        logIndex = 0
    }

    // MARK: - Internal

    private func handleFailure() {
        failureCount += 1
        if failureCount >= maxFailures {
            connectionState = .disconnected
            lastError = "Backend unreachable after \(maxFailures) attempts"
        }
    }

    // MARK: - HTTP Helpers

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
