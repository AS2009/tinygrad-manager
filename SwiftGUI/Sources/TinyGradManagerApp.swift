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

// MARK: - App Controller (Menu Bar + Window + Backend Lifecycle)

@MainActor
final class AppController: NSObject, NSApplicationDelegate, NSWindowDelegate {
    private var statusItem: NSStatusItem!
    private var window: NSWindow!
    private let backendClient = BackendClient()
    private let backendManager = BackendManager()

    func applicationDidFinishLaunching(_ notification: Notification) {
        NSApp.setActivationPolicy(.accessory)

        backendManager.setLogCallback { [weak self] line in
            Task { @MainActor [weak self] in
                self?.backendClient.appendLog(line)
            }
        }

        // Menu bar
        statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)
        if let btn = statusItem.button {
            btn.image = NSImage(systemSymbolName: "cpu.fill", accessibilityDescription: "TG")
            btn.toolTip = "\(L10n.appName)"
        }
        let menu = NSMenu()
        let showItem = menu.addItem(
            withTitle: "\(L10n.showHide)",
            action: #selector(toggleWindow), keyEquivalent: ""
        )
        showItem.target = self
        menu.addItem(.separator())
        let quitItem = menu.addItem(
            withTitle: "\(L10n.quit)",
            action: #selector(quitApp), keyEquivalent: "q"
        )
        quitItem.target = self
        statusItem.menu = menu

        // Window
        let contentView = ContentView()
            .environment(backendClient)
            .environment(backendManager)
        let hosting = NSHostingView(rootView: contentView)
        hosting.frame = NSRect(x: 0, y: 0, width: 840, height: 920)

        window = NSWindow(
            contentRect: NSRect(x: 100, y: 100, width: 840, height: 920),
            styleMask: [.titled, .closable, .miniaturizable, .resizable, .fullSizeContentView],
            backing: .buffered, defer: false
        )
        window.title = "\(L10n.appName)"
        window.titlebarAppearsTransparent = true
        window.titleVisibility = .hidden
        window.isMovableByWindowBackground = true
        window.contentView = hosting
        window.delegate = self

        // macOS 26 Liquid Glass window enhancements
        if LiquidGlassDesign.useLiquidGlassWindow {
            window.backgroundColor = .clear
            window.isOpaque = false
            window.hasShadow = true
            // Use the richest available appearance for deep translucency
            window.appearance = NSAppearance(named: .vibrantDark)
        }

        window.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)

        backendManager.start()
        backendClient.startPolling()
    }

    func applicationWillTerminate(_ notification: Notification) {
        backendClient.stopPolling()
        backendManager.stop()
    }

    func windowShouldClose(_ sender: NSWindow) -> Bool {
        window.orderOut(nil)
        return false
    }

    @objc func toggleWindow() {
        if window.isVisible {
            window.orderOut(nil)
        } else {
            window.makeKeyAndOrderFront(nil)
            NSApp.activate(ignoringOtherApps: true)
        }
    }

    @objc func quitApp() {
        NSApp.terminate(nil)
    }
}
