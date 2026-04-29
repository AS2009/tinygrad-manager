import SwiftUI
import AppKit

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
    let isLoading: Bool
    let action: () -> Void

    init(_ title: String, primary: Bool = false, isLoading: Bool = false, action: @escaping () -> Void) {
        self.title = title
        self.primary = primary
        self.isLoading = isLoading
        self.action = action
    }

    var body: some View {
        Button(action: action) {
            HStack(spacing: 4) {
                if isLoading {
                    ProgressView()
                        .scaleEffect(0.6)
                        .frame(width: 12, height: 12)
                }
                Text(title)
                    .font(.system(size: 12, weight: .medium))
            }
            .frame(height: 28)
            .padding(.horizontal, 14)
        }
        .buttonStyle(.plain)
        .background(primary ? Color.accentColor : Color.primary.opacity(0.12))
        .foregroundColor(primary ? .white : .primary)
        .clipShape(Capsule())
        .disabled(isLoading)
    }
}
