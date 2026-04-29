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

        // Setup backend manager log forwarding
        backendManager.setLogCallback { [weak self] line in
            Task { @MainActor [weak self] in
                self?.backendClient.appendLog(line)
            }
        }

        // Create menu bar
        statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)
        if let btn = statusItem.button {
            btn.image = NSImage(systemSymbolName: "cpu.fill", accessibilityDescription: "TG")
            btn.toolTip = "TinyGrad Manager"
        }
        let menu = NSMenu()
        let showItem = menu.addItem(
            withTitle: "Show/Hide TinyGrad Manager",
            action: #selector(toggleWindow), keyEquivalent: ""
        )
        showItem.target = self
        menu.addItem(.separator())
        let quitItem = menu.addItem(
            withTitle: "Quit TinyGrad Manager",
            action: #selector(quitApp), keyEquivalent: "q"
        )
        quitItem.target = self
        statusItem.menu = menu

        // Create window
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
        window.title = "TinyGrad Manager"
        window.titlebarAppearsTransparent = true
        window.titleVisibility = .hidden
        window.isMovableByWindowBackground = true
        window.contentView = hosting
        window.delegate = self
        window.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)

        // Start backend and polling
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
