import SwiftUI

// MARK: - Card 3: System Status

struct SystemStatusCard: View {
    @Environment(BackendClient.self) private var backend
    @Environment(BackendManager.self) private var backendManager

    @State private var envReport: String = ""
    @State private var isLoadingEnv = false
    @State private var isTogglingService = false

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(spacing: 6) {
                Image(systemName: "cpu.fill").font(.system(size: 13))
                Text("System Status").font(.system(size: 13, weight: .semibold))
            }

            Text("GPU: \(backend.gpuInfo.gpu_info)")
                .font(.system(size: 12))

            HStack(spacing: 10) {
                Text("GPU Service").font(.system(size: 12, weight: .medium))
                PillButton(
                    backend.serviceRunning ? "Stop GPU Service" : "Start GPU Service",
                    isLoading: isTogglingService
                ) {
                    isTogglingService = true
                    Task {
                        if backend.serviceRunning {
                            _ = await backend.stopService()
                        } else {
                            _ = await backend.startService()
                        }
                        isTogglingService = false
                    }
                }
                Spacer()
                PillButton("Check Env", isLoading: isLoadingEnv) {
                    isLoadingEnv = true
                    Task {
                        if let env = await backend.fetchEnv() {
                            envReport = env.report
                        }
                        isLoadingEnv = false
                    }
                }
            }

            if !envReport.isEmpty {
                Text(envReport)
                    .font(.system(size: 10, design: .monospaced))
                    .foregroundStyle(.secondary)
            }
        }
        .padding(14)
        .glassCard()
    }
}
