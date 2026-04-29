import SwiftUI
import AppKit

// MARK: - Card 1: Model File

struct ModelCard: View {
    @Environment(BackendClient.self) private var backend

    @State private var modelFile: String = ""
    @State private var selectedDevice: String = ""
    @State private var loadResult: String = ""
    @State private var isLoading = false

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(spacing: 6) {
                Image(systemName: "doc.fill").font(.system(size: 13))
                Text("Model File").font(.system(size: 13, weight: .semibold))
                Spacer()
                Text(backend.status.llm_loaded
                    ? "Loaded: \(backend.status.llm_model ?? "")"
                    : "No model")
                    .font(.system(size: 11))
                    .foregroundStyle(.secondary)
            }

            // File picker row
            HStack(spacing: 10) {
                Button("Browse...") { browseModelFile() }
                    .buttonStyle(.bordered)
                    .controlSize(.small)
                Text(modelFile.isEmpty
                    ? "No file selected"
                    : (URL(fileURLWithPath: modelFile).lastPathComponent))
                    .font(.system(size: 11))
                    .foregroundStyle(.secondary)
                    .lineLimit(1)
                    .truncationMode(.middle)
                Spacer()
            }

            // GPU picker + Load button
            HStack(spacing: 10) {
                Text("GPU:").font(.system(size: 10)).foregroundStyle(.secondary)
                if backend.gpuInfo.available_devices.isEmpty {
                    Text("Detecting devices...")
                        .font(.system(size: 11))
                        .foregroundStyle(.secondary)
                } else {
                    Picker("", selection: $selectedDevice) {
                        ForEach(backend.gpuInfo.available_devices, id: \.self) { d in
                            Text(d).tag(d)
                        }
                    }
                    .pickerStyle(.menu)
                    .frame(width: 220)
                    .labelsHidden()
                    .onAppear {
                        if selectedDevice.isEmpty, let first = backend.gpuInfo.available_devices.first {
                            selectedDevice = first
                        }
                    }
                    .onChange(of: backend.gpuInfo.available_devices) { _, devices in
                        if selectedDevice.isEmpty || !devices.contains(selectedDevice),
                           let first = devices.first {
                            selectedDevice = first
                        }
                    }
                }
                Spacer()
                PillButton("Load Model", primary: true, isLoading: isLoading) {
                    guard !modelFile.isEmpty else {
                        loadResult = "Error: no file selected"
                        return
                    }
                    isLoading = true
                    Task {
                        loadResult = await backend.loadLLMModel(
                            filePath: modelFile,
                            device: parseDeviceKey(from: selectedDevice)
                        )
                        isLoading = false
                    }
                }
            }

            // Result
            if !loadResult.isEmpty {
                Text(loadResult)
                    .font(.system(size: 10))
                    .foregroundStyle(loadResult.hasPrefix("Error") ? Color.red : Color.secondary)
            }
        }
        .padding(14)
        .glassCard()
    }

    private func browseModelFile() {
        let panel = NSOpenPanel()
        panel.canChooseFiles = true
        panel.canChooseDirectories = false
        panel.allowsMultipleSelection = false
        panel.allowedContentTypes = []
        if panel.runModal() == .OK, let url = panel.url {
            modelFile = url.path
        }
    }
}
