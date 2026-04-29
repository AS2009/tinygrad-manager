import SwiftUI

// MARK: - Card 4: Console

struct ConsoleCard: View {
    @Environment(BackendClient.self) private var backend

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            HStack(spacing: 6) {
                Image(systemName: "terminal.fill").font(.system(size: 13))
                Text("Console").font(.system(size: 13, weight: .semibold))
                Spacer()
                Button("Clear") { backend.clearLogs() }
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
                .onChange(of: backend.logs.count) {
                    withAnimation { proxy.scrollTo("bottom", anchor: .bottom) }
                }
            }
        }
        .padding(14)
        .glassCard()
    }
}
