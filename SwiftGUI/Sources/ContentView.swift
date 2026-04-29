import SwiftUI

// MARK: - Main Content View

struct ContentView: View {
    @Environment(BackendClient.self) private var backend
    @Environment(BackendManager.self) private var backendManager

    var body: some View {
        ZStack {
            VisualEffectBlur(
                material: LiquidGlassDesign.windowMaterial,
                blendingMode: LiquidGlassDesign.windowBlending
            )
            .ignoresSafeArea()

            VStack(spacing: 0) {
                HeaderView()
                    .background {
                        if macOSVersion.is26OrLater {
                            // Subtle top-down luminance gradient — Liquid Glass depth cue
                            VStack(spacing: 0) {
                                LinearGradient(
                                    colors: [.white.opacity(0.06), .clear],
                                    startPoint: .top, endPoint: .bottom
                                )
                                .frame(height: 120)
                                Spacer()
                            }
                        }
                    }

                ScrollView {
                    VStack(spacing: 12) {
                        ModelCard()
                        ImageGenCard()
                        SystemStatusCard()
                        ConsoleCard()
                    }
                    .padding(.horizontal, 24)
                    .padding(.vertical, 16)
                }
            }
        }
        .frame(minWidth: 840, minHeight: 920)
    }
}

// MARK: - Header with Connection Status

struct HeaderView: View {
    @Environment(BackendClient.self) private var backend
    @Environment(BackendManager.self) private var backendManager

    var body: some View {
        HStack(spacing: 12) {
            Image(systemName: "shippingbox.fill")
                .font(.system(size: 28, weight: .semibold))
                .foregroundStyle(.primary)

            VStack(alignment: .leading, spacing: 2) {
                HStack(spacing: 6) {
                    Text(verbatim: "\(L10n.appName)")
                        .font(.system(size: 26, weight: .bold))
                    connectionDot
                }
                Text(verbatim: "\(L10n.appSubtitle)")
                    .font(.system(size: 11))
                    .foregroundStyle(.secondary)
            }
            Spacer()

            if case .disconnected = backend.connectionState {
                PillButton("\(L10n.retry)") { [backendManager] in
                    backendManager.start()
                }
            }
        }
        .padding(.horizontal, 28)
        .padding(.top, 32)
    }

    @ViewBuilder
    private var connectionDot: some View {
        HStack(spacing: 4) {
            Circle()
                .fill(dotColor)
                .frame(width: 7, height: 7)
            Text(dotText)
                .font(.system(size: 10))
                .foregroundStyle(.secondary)
        }
    }

    private var dotColor: Color {
        switch backend.connectionState {
        case .disconnected: .gray
        case .connecting:   .orange
        case .connected:    .green
        case .error:        .red
        }
    }

    private var dotText: String {
        switch backend.connectionState {
        case .disconnected: "\(L10n.disconnected)"
        case .connecting:   "\(L10n.starting)"
        case .connected:    "\(L10n.connected)"
        case .error(let m): m
        }
    }
}
