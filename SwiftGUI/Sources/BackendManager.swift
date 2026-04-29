import Foundation
import Observation

// MARK: - Python Backend Process Manager

@MainActor
@Observable
final class BackendManager {
    var processState: ProcessState = .stopped
    var launchAttempts = 0
    private let maxAttempts = 3
    private var process: Process?
    private var logCallback: ((String) -> Void)?

    // MARK: - Backend Script Discovery

    func findBackendScript() -> URL? {
        // 1. Check environment variable
        if let envPath = ProcessInfo.processInfo.environment["TINYGRAD_BACKEND_PATH"] {
            let url = URL(fileURLWithPath: envPath)
            if FileManager.default.fileExists(atPath: url.path) {
                return url
            }
        }

        // 2. Check bundled Resources (for .app bundle)
        if let execURL = Bundle.main.executableURL {
            let resourcesURL = execURL
                .deletingLastPathComponent()
                .deletingLastPathComponent()
                .appendingPathComponent("Resources")
                .appendingPathComponent("backend_main.py")
            if FileManager.default.fileExists(atPath: resourcesURL.path) {
                return resourcesURL
            }

            // Also check Resources/TinyGradManager/backend_main.py
            let altURL = execURL
                .deletingLastPathComponent()
                .deletingLastPathComponent()
                .appendingPathComponent("Resources")
                .appendingPathComponent("TinyGradManager")
                .appendingPathComponent("backend_main.py")
            if FileManager.default.fileExists(atPath: altURL.path) {
                return altURL
            }
        }

        // 3. Dev mode: relative to SwiftGUI build directory
        let devURL = URL(fileURLWithPath: #file)
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .appendingPathComponent("TinyGradManager")
            .appendingPathComponent("backend_main.py")
        if FileManager.default.fileExists(atPath: devURL.path) {
            return devURL
        }

        return nil
    }

    func findPython() -> String {
        // Try python3 from common locations
        let candidates = [
            "/usr/bin/python3",
            "/opt/homebrew/bin/python3",
            "/usr/local/bin/python3",
        ]
        for path in candidates {
            if FileManager.default.fileExists(atPath: path) {
                return path
            }
        }
        return "python3" // fallback to PATH lookup
    }

    // MARK: - Lifecycle

    func setLogCallback(_ callback: @escaping (String) -> Void) {
        logCallback = callback
    }

    func start() {
        guard case .stopped = processState else { return }

        guard let scriptURL = findBackendScript() else {
            processState = .crashed("Cannot find backend_main.py")
            return
        }

        launchAttempts += 1
        processState = .starting

        let python = findPython()
        log("Starting backend: \(python) \(scriptURL.path)")

        let proc = Process()
        proc.executableURL = URL(fileURLWithPath: python)
        proc.arguments = ["-u", scriptURL.path, "--port", "1234"]
        proc.currentDirectoryURL = scriptURL.deletingLastPathComponent()

        // Set PYTHONPATH to include the backend script directory
        var env = ProcessInfo.processInfo.environment
        let scriptDir = scriptURL.deletingLastPathComponent().path
        if let existingPath = env["PYTHONPATH"] {
            env["PYTHONPATH"] = "\(scriptDir):\(existingPath)"
        } else {
            env["PYTHONPATH"] = scriptDir
        }
        proc.environment = env

        // Capture stdout
        let stdoutPipe = Pipe()
        let stderrPipe = Pipe()
        proc.standardOutput = stdoutPipe
        proc.standardError = stderrPipe

        stdoutPipe.fileHandleForReading.readabilityHandler = { [weak self] handle in
            let data = handle.availableData
            guard !data.isEmpty, let line = String(data: data, encoding: .utf8)?.trimmingCharacters(in: .whitespacesAndNewlines), !line.isEmpty else { return }
            Task { @MainActor [weak self] in
                self?.log(line)
            }
        }

        stderrPipe.fileHandleForReading.readabilityHandler = { [weak self] handle in
            let data = handle.availableData
            guard !data.isEmpty, let line = String(data: data, encoding: .utf8)?.trimmingCharacters(in: .whitespacesAndNewlines), !line.isEmpty else { return }
            Task { @MainActor [weak self] in
                self?.log("[ERR] \(line)")
            }
        }

        proc.terminationHandler = { [weak self] p in
            let code = p.terminationStatus
            Task { @MainActor [weak self] in
                guard let self else { return }
                if code == 0 || self.process != p {
                    // Clean exit or replaced process — don't restart
                    if self.process == p { self.processState = .stopped }
                } else {
                    // Unexpected exit
                    if self.launchAttempts < self.maxAttempts {
                        self.processState = .restarting(attempt: self.launchAttempts + 1, maxAttempts: self.maxAttempts)
                        self.log("Backend exited with code \(code). Restarting in 1s (attempt \(self.launchAttempts + 1)/\(self.maxAttempts))...")
                        try? await Task.sleep(nanoseconds: 1_000_000_000)
                        self.start()
                    } else {
                        self.processState = .crashed("Backend crashed \(self.maxAttempts) times. Giving up.")
                        self.log("Backend crashed \(self.maxAttempts) times. Giving up.")
                    }
                }
            }
        }

        do {
            try proc.run()
            process = proc
            processState = .running
            log("Backend process started (PID: \(proc.processIdentifier))")
        } catch {
            processState = .crashed("Failed to launch: \(error.localizedDescription)")
            log("Failed to launch backend: \(error.localizedDescription)")
        }
    }

    func stop() {
        guard let proc = process, proc.isRunning else {
            processState = .stopped
            process = nil
            return
        }

        log("Stopping backend (PID: \(proc.processIdentifier))...")
        proc.terminate() // SIGTERM

        // Wait up to 3 seconds for graceful exit
        DispatchQueue.main.asyncAfter(deadline: .now() + 3) { [weak self] in
            guard let self, let p = self.process, p.isRunning else { return }
            self.log("Backend did not exit gracefully, force killing...")
            p.interrupt() // SIGKILL fallback
        }

        // Wait for process to actually exit
        DispatchQueue.main.asyncAfter(deadline: .now() + 4) { [weak self] in
            guard let self else { return }
            self.process = nil
            self.processState = .stopped
            self.launchAttempts = 0
            self.log("Backend stopped.")
        }
    }

    // MARK: - Internal

    private func log(_ message: String) {
        logCallback?(message)
        let ts = DateFormatter()
        ts.dateFormat = "HH:mm:ss"
        print("[\(ts.string(from: Date()))] [BackendManager] \(message)")
    }
}
