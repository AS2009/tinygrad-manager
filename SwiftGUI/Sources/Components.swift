import SwiftUI
import AppKit

// MARK: - macOS Version Detection

enum macOSVersion {
    static let current: OperatingSystemVersion = ProcessInfo.processInfo.operatingSystemVersion
    static let is26OrLater: Bool = current.majorVersion >= 26
    static let isMajor: Int = current.majorVersion
}

// MARK: - Liquid Glass Design Tokens

enum LiquidGlassDesign {
    /// Corner radius for glass cards — larger on macOS 26 for the liquid look
    static var cardCornerRadius: CGFloat { macOSVersion.is26OrLater ? 18 : 14 }

    /// Border width for glass cards
    static var cardBorderWidth: CGFloat { macOSVersion.is26OrLater ? 0.5 : 0.5 }

    /// Border opacity for glass cards — more visible on macOS 26
    static var cardBorderOpacity: CGFloat { macOSVersion.is26OrLater ? 0.12 : 0.08 }

    /// Shadow radius for depth on glass cards — macOS 26 adds subtle depth shadow
    static var cardShadowRadius: CGFloat { macOSVersion.is26OrLater ? 2 : 0 }

    /// Shadow opacity
    static var cardShadowOpacity: CGFloat { macOSVersion.is26OrLater ? 0.06 : 0 }

    /// Background material for full-window glass
    static var windowMaterial: NSVisualEffectView.Material {
        if #available(macOS 26, *) {
            // macOS 26 "Liquid Glass" — use the new system glass material
            return .underWindowBackground
        } else {
            return .underWindowBackground
        }
    }

    /// Background material for cards
    static var cardMaterial: NSVisualEffectView.Material {
        if #available(macOS 26, *) {
            return .contentBackground
        } else {
            return .contentBackground
        }
    }

    /// Console card material — darker for readability
    static var consoleMaterial: NSVisualEffectView.Material {
        if #available(macOS 26, *) {
            return .hudWindow
        } else {
            return .hudWindow
        }
    }

    /// Window blending mode — behind-window for full translucency
    static var windowBlending: NSVisualEffectView.BlendingMode { .behindWindow }

    /// Card blending mode — within-window to respect card boundaries
    static var cardBlending: NSVisualEffectView.BlendingMode { .withinWindow }

    /// Whether to use the enhanced liquid glass window appearance
    static var useLiquidGlassWindow: Bool { macOSVersion.is26OrLater }
}

// MARK: - Visual Effect (NSVisualEffectView bridge, version-adaptive)

struct VisualEffectBlur: NSViewRepresentable {
    let material: NSVisualEffectView.Material
    let blendingMode: NSVisualEffectView.BlendingMode

    func makeNSView(context: Context) -> NSVisualEffectView {
        let v = NSVisualEffectView()
        applyConfig(to: v)
        return v
    }

    func updateNSView(_ v: NSVisualEffectView, context: Context) {
        applyConfig(to: v)
    }

    private func applyConfig(to v: NSVisualEffectView) {
        v.material = material
        v.blendingMode = blendingMode
        v.state = .active

        if #available(macOS 26, *) {
            // macOS 26 Liquid Glass enhancements:
            // Use the most translucent variant available
            v.wantsLayer = true
            if let layer = v.layer {
                layer.cornerRadius = 0 // full-window blur, no clipping
                layer.masksToBounds = false
            }
        }
    }
}

// MARK: - Glass Card Modifier (version-adaptive)

struct GlassCard: ViewModifier {
    var cornerRadius: CGFloat = LiquidGlassDesign.cardCornerRadius

    func body(content: Content) -> some View {
        content
            .background {
                if #available(macOS 26, *) {
                    // macOS 26 Liquid Glass card:
                    // richer material + subtle depth shadow + refined border
                    RoundedRectangle(cornerRadius: cornerRadius)
                        .fill(.ultraThinMaterial)
                        .shadow(
                            color: .primary.opacity(LiquidGlassDesign.cardShadowOpacity),
                            radius: LiquidGlassDesign.cardShadowRadius,
                            y: 1
                        )
                } else {
                    RoundedRectangle(cornerRadius: cornerRadius)
                        .fill(.ultraThinMaterial)
                }
            }
            .clipShape(RoundedRectangle(cornerRadius: cornerRadius))
            .overlay(
                RoundedRectangle(cornerRadius: cornerRadius)
                    .stroke(
                        .primary.opacity(LiquidGlassDesign.cardBorderOpacity),
                        lineWidth: LiquidGlassDesign.cardBorderWidth
                    )
            )
    }
}

extension View {
    func glassCard() -> some View {
        modifier(GlassCard())
    }
}

// MARK: - Pill Button (unchanged from before)

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
                Text(verbatim: title)
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
