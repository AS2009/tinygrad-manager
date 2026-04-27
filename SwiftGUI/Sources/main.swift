import SwiftUI
import AppKit

// MARK: - App Entry

@main
struct TinyGradManagerApp: App {
    @NSApplicationDelegateAdaptor(AppController.self) var controller

    var body: some Scene {
        Settings { EmptyView() }
    }
}

// MARK: - App Controller (Menu Bar + Window)

final class AppController: NSObject, NSApplicationDelegate, ObservableObject {
    private var statusItem: NSStatusItem!
    private var window: NSWindow!

    func applicationDidFinishLaunching(_ notification: Notification) {
        NSApp.setActivationPolicy(.accessory)

        // Menu bar
        statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)
        if let btn = statusItem.button {
            btn.image = NSImage(systemSymbolName: "cpu.fill", accessibilityDescription: "TG")
            btn.toolTip = "TinyGrad Manager"
        }
        let menu = NSMenu()
        let showItem = menu.addItem(withTitle: "Show/Hide TinyGrad Manager",
                                     action: #selector(toggleWindow), keyEquivalent: "")
        showItem.target = self
        menu.addItem(.separator())
        let quitItem = menu.addItem(withTitle: "Quit TinyGrad Manager",
                                     action: #selector(quitApp), keyEquivalent: "q")
        quitItem.target = self
        statusItem.menu = menu

        // Window
        let contentView = ContentView()
        let hosting = NSHostingView(rootView: contentView)
        hosting.frame = NSRect(x: 0, y: 0, width: 840, height: 920)

        window = NSWindow(
            contentRect: NSRect(x: 100, y: 100, width: 840, height: 920),
            styleMask: [.titled, .closable, .miniaturizable, .resizable, .fullSizeContentView],
            backing: .buffered, defer: false
        )
        window.title = "TinyGrad Manager"
        window.titlebarAppearsTransparent = true
        window.titleVisibility = .hidden
        window.isMovableByWindowBackground = true
        window.contentView = hosting
        window.delegate = self
        window.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
    }

    @objc func toggleWindow() {
        if window.isVisible {
            window.orderOut(nil)
        } else {
            window.makeKeyAndOrderFront(nil)
            NSApp.activate(ignoringOtherApps: true)
        }
    }

    @objc func quitApp() { NSApp.terminate(nil) }

    func applicationShouldTerminate(_ sender: NSApplication) -> NSApplication.TerminateReply {
        return .terminateNow
    }

    func windowShouldClose(_ sender: NSWindow) -> Bool {
        window.orderOut(nil)
        return false
    }
}

// MARK: - Main Content View

struct ContentView: View {
    @StateObject private var backend = BackendClient.shared

    var body: some View {
        ZStack {
            // Full-window glass background
            VisualEffectBlur(material: .underWindowBackground, blendingMode: .behindWindow)
                .ignoresSafeArea()

            VStack(spacing: 0) {
                // Header
                HStack(spacing: 12) {
                    Image(systemName: "shippingbox.fill")
                        .font(.system(size: 28, weight: .semibold))
                        .foregroundStyle(.primary)
                    VStack(alignment: .leading, spacing: 2) {
                        Text("TinyGrad Manager")
                            .font(.system(size: 26, weight: .bold))
                        Text("Model Management & GPU Control")
                            .font(.system(size: 11))
                            .foregroundStyle(.secondary)
                    }
                    Spacer()
                }
                .padding(.horizontal, 28)
                .padding(.top, 32)

                // Cards
                ScrollView {
                    VStack(spacing: 12) {
                        ModelCard()
                        ImageGenCard()
                        SystemCard()
                        ConsoleCard()
                    }
                    .padding(.horizontal, 24)
                    .padding(.vertical, 16)
                }
            }
        }
        .frame(minWidth: 840, minHeight: 920)
        .onAppear { backend.startPolling() }
        .onDisappear { backend.stopPolling() }
    }
}

// MARK: - Visual Effect (NSVisualEffectView bridge)

struct VisualEffectBlur: NSViewRepresentable {
    let material: NSVisualEffectView.Material
    let blendingMode: NSVisualEffectView.BlendingMode

    func makeNSView(context: Context) -> NSVisualEffectView {
        let v = NSVisualEffectView()
        v.material = material
        v.blendingMode = blendingMode
        v.state = .active
        return v
    }

    func updateNSView(_ v: NSVisualEffectView, context: Context) {
        v.material = material
        v.blendingMode = blendingMode
    }
}

// MARK: - Glass Card Modifier

struct GlassCard: ViewModifier {
    func body(content: Content) -> some View {
        content
            .background(.ultraThinMaterial)
            .clipShape(RoundedRectangle(cornerRadius: 14))
            .overlay(
                RoundedRectangle(cornerRadius: 14)
                    .stroke(.primary.opacity(0.08), lineWidth: 0.5)
            )
    }
}

extension View {
    func glassCard() -> some View {
        modifier(GlassCard())
    }
}

// MARK: - Pill Button

struct PillButton: View {
    let title: String
    let primary: Bool
    let action: () -> Void

    init(_ title: String, primary: Bool = false, action: @escaping () -> Void) {
        self.title = title
        self.primary = primary
        self.action = action
    }

    var body: some View {
        Button(action: action) {
            Text(title)
                .font(.system(size: 12, weight: .medium))
                .frame(height: 28)
                .padding(.horizontal, 14)
        }
        .buttonStyle(.plain)
        .background(primary ? Color.accentColor : Color.primary.opacity(0.12))
        .foregroundColor(primary ? .white : .primary)
        .clipShape(Capsule())
    }
}

// MARK: - Card 1: Model File

struct ModelCard: View {
    @StateObject private var backend = BackendClient.shared
    @State private var modelFile: String = ""
    @State private var selectedDevice: String = "cpu"
    @State private var loadResult: String = ""

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(spacing: 6) {
                Image(systemName: "doc.fill").font(.system(size: 13))
                Text("Model File").font(.system(size: 13, weight: .semibold))
                Spacer()
                Text(backend.status.llm_loaded ? "Loaded: \(backend.status.llm_model ?? "")" : "No model")
                    .font(.system(size: 11))
                    .foregroundStyle(.secondary)
            }

            HStack(spacing: 10) {
                Button("Browse...") { browseModelFile() }
                    .buttonStyle(.bordered)
                    .controlSize(.small)
                Text(modelFile.isEmpty ? "No file selected" : (URL(fileURLWithPath: modelFile).lastPathComponent))
                    .font(.system(size: 11))
                    .foregroundStyle(.secondary)
                    .lineLimit(1)
                    .truncationMode(.middle)
                Spacer()
            }

            HStack(spacing: 10) {
                Text("GPU:").font(.system(size: 10)).foregroundStyle(.secondary)
                Picker("", selection: $selectedDevice) {
                    ForEach(backend.gpuInfo.available_devices, id: \.self) { d in
                        Text(d).tag(d)
                    }
                }
                .pickerStyle(.menu)
                .frame(width: 200)
                .labelsHidden()
                Spacer()
                PillButton("Load Model", primary: true) {
                    guard !modelFile.isEmpty else {
                        loadResult = "Error: no file selected"
                        return
                    }
                    Task { loadResult = await backend.loadLLMModel(filePath: modelFile, device: keyFor(selectedDevice)) }
                }
            }

            if !loadResult.isEmpty {
                Text(loadResult).font(.system(size: 10)).foregroundStyle(.secondary)
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
        panel.allowedContentTypes = []  // allow all file types (non-standard extensions like safetensors/gguf/mlx)
        if panel.runModal() == .OK, let url = panel.url {
            modelFile = url.path
        }
    }

    private func keyFor(_ display: String) -> String {
        if display.hasPrefix("cuda:") { return String(display.split(separator: " ")[0]) }
        if display.hasPrefix("mps") { return "mps" }
        return "cpu"
    }
}

// MARK: - Card 2: Image Generation

struct ImageGenCard: View {
    @StateObject private var backend = BackendClient.shared
    @State private var modelSource: String = ""
    @State private var selectedDevice: String = "cpu"
    @State private var prompt: String = "a cat sitting on a cloud, digital art"
    @State private var hfModelID: String = "runwayml/stable-diffusion-v1-5"
    @State private var statusText: String = "Status: No model loaded"
    @State private var isGenerating = false

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack(spacing: 6) {
                Image(systemName: "photo.fill").font(.system(size: 13))
                Text("Text-to-Image").font(.system(size: 13, weight: .semibold))
                Spacer()
                Text(statusText).font(.system(size: 11)).foregroundStyle(.secondary)
            }

            // Local file picker
            HStack(spacing: 8) {
                Text("Model File:").font(.system(size: 10)).foregroundStyle(.secondary)
                Button("Browse...") { browseImageModel() }
                    .buttonStyle(.bordered)
                    .controlSize(.small)
                Text(modelSource.isEmpty ? "No local file" : (URL(fileURLWithPath: modelSource).lastPathComponent))
                    .font(.system(size: 11))
                    .foregroundStyle(.secondary)
                    .lineLimit(1)
                Spacer()
            }

            // HF ID + GPU + Load
            HStack(spacing: 8) {
                Text("Or HF ID:").font(.system(size: 10)).foregroundStyle(.secondary)
                TextField("runwayml/stable-diffusion-v1-5", text: $hfModelID)
                    .textFieldStyle(.roundedBorder)
                    .font(.system(size: 11))
                    .frame(width: 200)
                Picker("", selection: $selectedDevice) {
                    ForEach(backend.gpuInfo.available_devices, id: \.self) { d in Text(d).tag(d) }
                }
                .pickerStyle(.menu)
                .frame(width: 160)
                .labelsHidden()
                Spacer()
                PillButton("Load Image Model", primary: true) {
                    let src = modelSource.isEmpty ? hfModelID : modelSource
                    statusText = "Loading..."
                    Task {
                        let msg = await backend.loadImageModel(source: src, device: keyFor(selectedDevice))
                        statusText = msg.contains("True") || msg.contains("loaded") ? "Ready" : "Error: \(msg)"
                    }
                }
            }

            // Prompt + Generate
            HStack(spacing: 8) {
                Text("Prompt:").font(.system(size: 10)).foregroundStyle(.secondary)
                TextField("Enter prompt...", text: $prompt)
                    .textFieldStyle(.roundedBorder)
                    .font(.system(size: 11))
                PillButton("Generate", primary: true) {
                    isGenerating = true
                    statusText = "Generating..."
                    Task {
                        if let r = await backend.generateImage(prompt: prompt) {
                            statusText = r.success ? "Done in \(r.elapsed_seconds ?? 0)s → \(r.filepath ?? "")" : "Failed"
                        } else {
                            statusText = "Generation failed"
                        }
                        isGenerating = false
                    }
                }
                .disabled(isGenerating)
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
        panel.allowedContentTypes = []  // allow all files (non-standard extensions like safetensors/ckpt)
        if panel.runModal() == .OK, let url = panel.url {
            modelSource = url.path
        }
    }

    private func keyFor(_ display: String) -> String {
        if display.hasPrefix("cuda:") { return String(display.split(separator: " ")[0]) }
        if display.hasPrefix("mps") { return "mps" }
        return "cpu"
    }
}

// MARK: - Card 3: System Status

struct SystemCard: View {
    @StateObject private var backend = BackendClient.shared
    @State private var serviceRunning = false
    @State private var envReport: String = ""

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
                PillButton(serviceRunning ? "Stop GPU Service" : "Start GPU Service") {
                    Task {
                        if serviceRunning {
                            let ok = await backend.stopService()
                            if ok { serviceRunning = false }
                        } else {
                            let ok = await backend.startService()
                            if ok { serviceRunning = true }
                        }
                    }
                }
                Spacer()
                PillButton("Check Env") {
                    Task {
                        if let env = await backend.fetchEnv() {
                            envReport = env.report
                        }
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

// MARK: - Card 4: Console

struct ConsoleCard: View {
    @StateObject private var backend = BackendClient.shared
    @State private var scrollProxy: ScrollViewProxy?

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            HStack(spacing: 6) {
                Image(systemName: "terminal.fill").font(.system(size: 13))
                Text("Console").font(.system(size: 13, weight: .semibold))
                Spacer()
                Button("Clear") { backend.logs.removeAll() }
                    .buttonStyle(.plain)
                    .font(.system(size: 10))
                    .foregroundStyle(.secondary)
            }

            ScrollViewReader { proxy in
                ScrollView {
                    LazyVStack(alignment: .leading, spacing: 0) {
                        ForEach(Array(backend.logs.enumerated()), id: \.offset) { _, line in
                            Text(line)
                                .font(.system(size: 10, design: .monospaced))
                                .foregroundStyle(.secondary)
                                .textSelection(.enabled)
                        }
                    }
                    .padding(6)
                    .id("bottom")
                }
                .frame(height: 160)
                .background(.black.opacity(0.15))
                .clipShape(RoundedRectangle(cornerRadius: 8))
                .onAppear { scrollProxy = proxy }
                .onChange(of: backend.logs.count) { _ in
                    withAnimation { proxy.scrollTo("bottom", anchor: .bottom) }
                }
            }
        }
        .padding(14)
        .glassCard()
    }
}
