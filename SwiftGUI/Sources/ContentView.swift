import SwiftUI

// MARK: - Main Content View

struct ContentView: View {
    @Environment(BackendClient.self) private var backend
    @Environment(BackendManager.self) private var backendManager

    var body: some View {
        ZStack {
            VisualEffectBlur(material: .underWindowBackground, blendingMode: .behindWindow)
                .ignoresSafeArea()

            VStack(spacing: 0) {
                HeaderView()

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
                    Text("TinyGrad Manager")
                        .font(.system(size: 26, weight: .bold))
                    connectionDot
                }
                Text("Model Management & GPU Control")
                    .font(.system(size: 11))
                    .foregroundStyle(.secondary)
            }
            Spacer()

            // Retry button when disconnected
            if case .disconnected = backend.connectionState {
                PillButton("Retry") { [backendManager] in
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
        case .disconnected: "Disconnected"
        case .connecting:   "Starting..."
        case .connected:    "Connected"
        case .error(let m): m
        }
    }
}
