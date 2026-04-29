import SwiftUI
import AppKit

// MARK: - Card 2: Image Generation

struct ImageGenCard: View {
    @Environment(BackendClient.self) private var backend

    @State private var modelSource: String = ""
    @State private var selectedDevice: String = ""
    @State private var prompt: String = "a cat sitting on a cloud, digital art"
    @State private var hfModelID: String = "runwayml/stable-diffusion-v1-5"
    @State private var statusText: String = "\(L10n.statusNoModel)"
    @State private var isGenerating = false
    @State private var isLoading = false

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack(spacing: 6) {
                Image(systemName: "photo.fill").font(.system(size: 13))
                Text(verbatim: "\(L10n.textToImage)")
                    .font(.system(size: 13, weight: .semibold))
                Spacer()
                Text(statusText).font(.system(size: 11)).foregroundStyle(.secondary)
            }

            HStack(spacing: 8) {
                Text(verbatim: "\(L10n.imageModelFile)")
                    .font(.system(size: 10)).foregroundStyle(.secondary)
                Button { browseImageModel() } label: { Text(verbatim: "\(L10n.browse)") }
                    .buttonStyle(.bordered)
                    .controlSize(.small)
                Text(modelSource.isEmpty
                    ? "\(L10n.noLocalFile)"
                    : (URL(fileURLWithPath: modelSource).lastPathComponent))
                    .font(.system(size: 11))
                    .foregroundStyle(.secondary)
                    .lineLimit(1)
                Spacer()
            }

            HStack(spacing: 8) {
                Text(verbatim: "\(L10n.orHFID)")
                    .font(.system(size: 10)).foregroundStyle(.secondary)
                TextField("runwayml/stable-diffusion-v1-5", text: $hfModelID)
                    .textFieldStyle(.roundedBorder)
                    .font(.system(size: 11))
                    .frame(width: 200)

                if backend.gpuInfo.available_devices.isEmpty {
                    Text(verbatim: "\(L10n.detectingDevices)")
                        .font(.system(size: 11))
                        .foregroundStyle(.secondary)
                } else {
                    Picker("", selection: $selectedDevice) {
                        ForEach(backend.gpuInfo.available_devices, id: \.self) { d in
                            Text(d).tag(d)
                        }
                    }
                    .pickerStyle(.menu)
                    .frame(width: 180)
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
                PillButton("\(L10n.loadImageModel)", primary: true, isLoading: isLoading) {
                    let src = modelSource.isEmpty ? hfModelID : modelSource
                    isLoading = true
                    statusText = "\(L10n.statusLoading)"
                    Task {
                        let msg = await backend.loadImageModel(
                            source: src,
                            device: parseDeviceKey(from: selectedDevice)
                        )
                        statusText = msg.hasPrefix("Error")
                            ? msg : "\(L10n.statusReady) — \(msg)"
                        isLoading = false
                    }
                }
            }

            HStack(spacing: 8) {
                Text(verbatim: "\(L10n.prompt)")
                    .font(.system(size: 10)).foregroundStyle(.secondary)
                TextField("Enter prompt...", text: $prompt)
                    .textFieldStyle(.roundedBorder)
                    .font(.system(size: 11))
                PillButton("\(L10n.generateImage)", primary: true, isLoading: isGenerating) {
                    isGenerating = true
                    statusText = "\(L10n.generating)"
                    Task {
                        if let r = await backend.generateImage(prompt: prompt) {
                            statusText = r.success
                                ? "\(L10n.statusDone(r.elapsed_seconds ?? 0, r.filepath ?? ""))"
                                : "\(L10n.statusFailed)"
                        } else {
                            statusText = "\(L10n.statusFailed)"
                        }
                        isGenerating = false
                    }
                }
            }
        }
        .padding(14)
        .glassCard()
    }

    private func browseImageModel() {
        let panel = NSOpenPanel()
        panel.canChooseFiles = true
        panel.canChooseDirectories = true
        panel.allowsMultipleSelection = false
        panel.allowedContentTypes = []
        if panel.runModal() == .OK, let url = panel.url {
            modelSource = url.path
        }
    }
}
