import os
import sys

# 修复动态库路径
if getattr(sys, 'frozen', False) or '.app/Contents/MacOS' in sys.executable:
    base_dir = os.path.dirname(sys.executable)
    lib_dir = os.path.join(base_dir, '..', 'Resources', 'lib')
    if os.path.exists(lib_dir):
        os.environ['DYLD_LIBRARY_PATH'] = lib_dir

sys.path.insert(0, os.path.dirname(__file__))

import objc
from Foundation import NSObject, NSRunLoop, NSLog
from AppKit import (
    NSApplication, NSWindow, NSView,
    NSButton, NSTextField, NSScrollView, NSTextView, NSImageView,
    NSVisualEffectView, NSStatusBar, NSMenu, NSMenuItem,
    NSMakeRect, NSPopUpButton,
    NSWindowStyleMaskTitled, NSWindowStyleMaskClosable,
    NSWindowStyleMaskMiniaturizable, NSWindowStyleMaskResizable,
    NSBackingStoreBuffered,
    NSOpenPanel, NSModalResponseOK,
)
import gpu_manager
import service_controller
import api_converter
import env_checker
import image_generator

# ── Look up classes that may not have direct pyobjc wrappers ──────────────
NSFont = objc.lookUpClass("NSFont")
NSColor = objc.lookUpClass("NSColor")
NSImage = objc.lookUpClass("NSImage")
NSImageSymbolConfiguration = objc.lookUpClass("NSImageSymbolConfiguration")

# ── Visual effect constants ────────────────────────────────────────────────
# AppKit enums — using integer values for safety with pyobjc
_BlendBehindWindow = 1    # NSVisualEffectBlendingModeBehindWindow
_BlendWithinWindow = 0    # NSVisualEffectBlendingModeWithinWindow
_MatUnderWindowBg = 12    # NSVisualEffectMaterialUnderWindowBackground (10.14+)
_MatContentBg = 11        # NSVisualEffectMaterialContentBackground (10.14+)
_MatHUD = 8               # NSVisualEffectMaterialHUDWindow
_StateActive = 1          # NSVisualEffectStateActive


def _sf_symbol(name, size=16.0, weight=0.0):
    """Load an SF Symbol as NSImage at the given point size and weight."""
    try:
        img = NSImage.imageWithSystemSymbolName_accessibilityDescription_(name, "")
    except Exception:
        return None
    if img is None:
        return None
    try:
        cfg = NSImageSymbolConfiguration.configurationWithPointSize_weight_scale_(
            size, weight, 1  # scale: 1 = medium
        )
        configured = img.imageWithSymbolConfiguration_(cfg)
        if configured is not None:
            return configured
    except Exception:
        pass
    # Fallback: resize the image view instead
    img.setSize_((size, size))
    return img


def _icon_view(name, x, y, w, h, size=0):
    """Create an NSImageView preloaded with an SF Symbol."""
    if size == 0:
        size = h
    img = _sf_symbol(name, size)
    v = NSImageView.alloc().initWithFrame_(NSMakeRect(x, y, w, h))
    if img:
        v.setImage_(img)
    v.setImageScaling_(3)  # proportionally up or down
    return v


def _label(text, x, y, w, h, font_size=13, weight=0.0, color=None):
    """Create an NSTextField label with system font."""
    tf = NSTextField.labelWithString_(text)
    tf.setFrame_(NSMakeRect(x, y, w, h))
    tf.setFont_(NSFont.systemFontOfSize_weight_(font_size, weight))
    if color:
        tf.setTextColor_(color)
    return tf


def _glass_card(x, y, w, h):
    """Create a glass card: NSVisualEffectView with rounded corners."""
    card = NSVisualEffectView.alloc().initWithFrame_(NSMakeRect(x, y, w, h))
    card.setBlendingMode_(_BlendWithinWindow)
    card.setMaterial_(_MatContentBg)
    card.setState_(_StateActive)
    card.setWantsLayer_(True)
    card.layer().setCornerRadius_(14.0)
    card.layer().setMasksToBounds_(True)
    try:
        card.layer().setBorderWidth_(0.5)
        sep = NSColor.separatorColor().colorWithAlphaComponent_(0.4)
        card.layer().setBorderColor_(sep.CGColor())
    except Exception:
        pass  # border is cosmetic; non-critical if it fails
    return card


def _pill_button(title, target, action, x, y, w, h, primary=False):
    """Create a rounded pill-style button."""
    btn = NSButton.buttonWithTitle_target_action_(title, target, action)
    btn.setFrame_(NSMakeRect(x, y, w, h))
    btn.setBezelStyle_(1)  # rounded
    if primary:
        try:
            btn.setContentTintColor_(NSColor.controlAccentColor())
        except Exception:
            pass  # fallback: use default button appearance
    return btn


class AppDelegate(NSObject):

    def applicationDidFinishLaunching_(self, notification):
        # ── Window ────────────────────────────────────────────────────────
        win_w, win_h = 840, 920
        rect = NSMakeRect(100, 100, win_w, win_h)
        mask = (
            NSWindowStyleMaskTitled
            | NSWindowStyleMaskClosable
            | NSWindowStyleMaskMiniaturizable
            | NSWindowStyleMaskResizable
            | (1 << 15)  # NSWindowStyleMaskFullSizeContentView
        )
        self.window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            rect, mask, NSBackingStoreBuffered, False
        )
        self.window.setTitle_("TinyGrad Manager")
        self.window.setTitlebarAppearsTransparent_(True)
        self.window.setTitleVisibility_(1)  # NSWindowTitleHidden
        self.window.makeKeyAndOrderFront_(None)

        content_view = self.window.contentView()

        # ── Full-window glass background ──────────────────────────────────
        bg = NSVisualEffectView.alloc().initWithFrame_(
            NSMakeRect(0, 0, win_w, win_h)
        )
        bg.setBlendingMode_(_BlendBehindWindow)
        bg.setMaterial_(_MatUnderWindowBg)
        bg.setState_(_StateActive)
        bg.setAutoresizingMask_(2 | 4)  # width | height
        content_view.addSubview_(bg)

        # ── Status Bar & Window Delegate ──────────────────────────────────
        self.window.setDelegate_(self)

        self.status_item = NSStatusBar.systemStatusBar().statusItemWithLength_(-1)
        status_btn = self.status_item.button()
        status_icon = _sf_symbol("cpu", 15.0)
        if status_icon:
            status_btn.setImage_(status_icon)
        else:
            status_btn.setTitle_("TG")
            status_btn.setFont_(NSFont.systemFontOfSize_weight_(11, 0.4))
        status_btn.setToolTip_("TinyGrad Manager")

        status_menu = NSMenu.alloc().init()
        show_item = status_menu.addItemWithTitle_action_keyEquivalent_(
            "Show/Hide TinyGrad Manager", "toggleWindow:", ""
        )
        show_item.setTarget_(self)
        status_menu.addItem_(NSMenuItem.separatorItem())
        quit_item = status_menu.addItemWithTitle_action_keyEquivalent_(
            "Quit TinyGrad Manager", "quitApp:", "q"
        )
        quit_item.setTarget_(self)
        self.status_item.setMenu_(status_menu)

        # ── Header ────────────────────────────────────────────────────────
        header_y = win_h - 64  # 64px from top, clears traffic-light buttons

        icon = _icon_view("shippingbox.fill", 68, header_y, 36, 36, 32)
        bg.addSubview_(icon)

        title_lbl = _label(
            "TinyGrad Manager", 112, header_y + 4, 500, 32,
            font_size=26, weight=0.4  # bold
        )
        bg.addSubview_(title_lbl)

        sub_lbl = _label(
            "Model Management & GPU Control", 114, header_y - 16, 500, 16,
            font_size=11, weight=0.0,
            color=NSColor.secondaryLabelColor()
        )
        bg.addSubview_(sub_lbl)

        # ── Card 1: Model ─────────────────────────────────────────────────
        c1_y, c1_h = 680, 175
        card1 = _glass_card(24, c1_y, win_w - 48, c1_h)
        bg.addSubview_(card1)

        # card header
        card1.addSubview_(_icon_view("doc.fill", 16, c1_h - 26, 18, 18, 14))
        card1.addSubview_(_label("Model File", 40, c1_h - 28, 200, 20,
                                 font_size=13, weight=0.23))

        # file path
        self.model_path_label = _label(
            "No file selected", 16, c1_h - 58, 600, 22,
            font_size=12,
            color=NSColor.secondaryLabelColor()
        )
        card1.addSubview_(self.model_path_label)

        # GPU device for LLM
        c1_w = win_w - 48  # card content width
        lbl_gpu = _label("GPU for LLM:", 16, c1_h - 86, 110, 22,
                         font_size=11, color=NSColor.secondaryLabelColor())
        card1.addSubview_(lbl_gpu)

        gpu_devices = env_checker.get_available_gpu_devices()
        self.llm_gpu_popup = NSPopUpButton.alloc().initWithFrame_pullsDown_(
            NSMakeRect(16, c1_h - 114, 260, 26), False
        )
        self.llm_gpu_popup.addItemsWithTitles_(gpu_devices)
        if gpu_devices:
            self.llm_gpu_popup.selectItemAtIndex_(0)
        card1.addSubview_(self.llm_gpu_popup)

        # buttons
        btn_y = 22
        browse_btn = _pill_button(
            "Browse...", self, "selectModelFile:",
            c1_w - 240, btn_y, 100, 32
        )
        card1.addSubview_(browse_btn)

        load_btn = _pill_button(
            "Load Model", self, "loadModel:",
            c1_w - 128, btn_y, 106, 32, primary=True
        )
        card1.addSubview_(load_btn)

        # ── Card 2: Text-to-Image ──────────────────────────────────────────
        c2_y, c2_h = 470, 200
        card_img = _glass_card(24, c2_y, win_w - 48, c2_h)
        bg.addSubview_(card_img)

        card_img.addSubview_(_icon_view("photo.fill", 16, c2_h - 26, 18, 18, 14))
        card_img.addSubview_(_label("Text-to-Image", 40, c2_h - 28, 200, 20,
                                    font_size=13, weight=0.23))

        # GPU device for image model
        card_img.addSubview_(_label("GPU for Image:", 16, c2_h - 56, 110, 22,
                                    font_size=11, color=NSColor.secondaryLabelColor()))
        self.img_gpu_popup = NSPopUpButton.alloc().initWithFrame_pullsDown_(
            NSMakeRect(16, c2_h - 80, 260, 26), False
        )
        self.img_gpu_popup.addItemsWithTitles_(gpu_devices)
        if gpu_devices:
            self.img_gpu_popup.selectItemAtIndex_(0)
        card_img.addSubview_(self.img_gpu_popup)

        # Model ID field
        card_img.addSubview_(_label("Model ID:", 290, c2_h - 56, 60, 22,
                                    font_size=11, color=NSColor.secondaryLabelColor()))
        self.img_model_field = NSTextField.alloc().initWithFrame_(
            NSMakeRect(290, c2_h - 80, 320, 26)
        )
        self.img_model_field.setStringValue_("runwayml/stable-diffusion-v1-5")
        self.img_model_field.setFont_(NSFont.systemFontOfSize_weight_(11, 0.0))
        self.img_model_field.setBezeled_(True)
        self.img_model_field.setBezelStyle_(1)  # square bezel
        card_img.addSubview_(self.img_model_field)

        # Load Image Model button
        load_img_btn = _pill_button(
            "Load Image Model", self, "loadImageModel:",
            c1_w - 160, c2_h - 82, 146, 32, primary=True
        )
        card_img.addSubview_(load_img_btn)

        # Prompt field
        card_img.addSubview_(_label("Prompt:", 16, c2_h - 116, 60, 22,
                                    font_size=11, color=NSColor.secondaryLabelColor()))
        self.img_prompt_field = NSTextField.alloc().initWithFrame_(
            NSMakeRect(16, c2_h - 140, c1_w - 180, 26)
        )
        self.img_prompt_field.setStringValue_("a cat sitting on a cloud, digital art")
        self.img_prompt_field.setFont_(NSFont.systemFontOfSize_weight_(11, 0.0))
        self.img_prompt_field.setBezeled_(True)
        self.img_prompt_field.setBezelStyle_(1)
        card_img.addSubview_(self.img_prompt_field)

        # Generate button
        gen_btn = _pill_button(
            "Generate Image", self, "generateImage:",
            c1_w - 148, c2_h - 142, 134, 32, primary=True
        )
        card_img.addSubview_(gen_btn)

        # Status label
        self.img_status_label = _label(
            "Status: No model loaded", 16, c2_h - 170, c1_w - 40, 22,
            font_size=11,
            color=NSColor.secondaryLabelColor()
        )
        card_img.addSubview_(self.img_status_label)

        # ── Card 3: System ────────────────────────────────────────────────
        c3_y, c3_h = 250, 200
        card3 = _glass_card(24, c3_y, win_w - 48, c3_h)
        bg.addSubview_(card3)

        card3.addSubview_(_icon_view("cpu.fill", 16, c3_h - 26, 18, 18, 14))
        card3.addSubview_(_label("System Status", 40, c3_h - 28, 200, 20,
                                 font_size=13, weight=0.23))

        # GPU info
        self.gpu_info_label = _label(
            "Detecting GPU...", 16, c3_h - 56, 600, 22,
            font_size=12
        )
        card3.addSubview_(self.gpu_info_label)

        # GPU service row
        card3.addSubview_(_label("GPU Service", 16, c3_h - 94, 120, 22,
                                 font_size=12, weight=0.23))
        self.start_service_btn = _pill_button(
            "Start GPU Service", self, "toggleService:",
            c1_w - 232, c3_h - 100, 180, 32
        )
        card3.addSubview_(self.start_service_btn)

        # API service row
        self.api_status_label = _label(
            "API Service: Inactive", 16, c3_h - 138, 250, 22,
            font_size=12,
            color=NSColor.secondaryLabelColor()
        )
        card3.addSubview_(self.api_status_label)

        self.toggle_api_btn = _pill_button(
            "Start API Service", self, "toggleApiService:",
            c1_w - 232, c3_h - 144, 180, 32
        )
        card3.addSubview_(self.toggle_api_btn)

        # ── Card 4: Console ───────────────────────────────────────────────
        c4_y, c4_h = 20, 230
        card4 = _glass_card(24, c4_y, win_w - 48, c4_h)
        card4.setMaterial_(_MatHUD)  # darker glass for console
        bg.addSubview_(card4)

        card4.addSubview_(_icon_view("terminal.fill", 16, c4_h - 26, 18, 18, 14))
        card4.addSubview_(_label("Console", 40, c4_h - 28, 200, 20,
                                 font_size=13, weight=0.23))

        # log area
        scroll_view = NSScrollView.alloc().initWithFrame_(
            NSMakeRect(12, 10, win_w - 72, c4_h - 50)
        )
        scroll_view.setHasVerticalScroller_(True)
        scroll_view.setBorderType_(0)  # no border — card already has one
        scroll_view.setDrawsBackground_(False)

        self.log_textview = NSTextView.alloc().initWithFrame_(
            scroll_view.contentView().frame()
        )
        self.log_textview.setEditable_(False)
        self.log_textview.setSelectable_(True)
        self.log_textview.setBackgroundColor_(NSColor.clearColor())
        try:
            mono_font = NSFont.monospacedSystemFontOfSize_weight_(11, 0.0)
        except Exception:
            mono_font = NSFont.fontWithName_size_("Menlo", 11)
            if mono_font is None:
                mono_font = NSFont.systemFontOfSize_weight_(11, 0.0)
        self.log_textview.setFont_(mono_font)
        self.log_textview.setTextColor_(NSColor.labelColor())
        scroll_view.setDocumentView_(self.log_textview)
        card4.addSubview_(scroll_view)

        # ── Init ──────────────────────────────────────────────────────────
        self.image_gen = image_generator.ImageGenerator()
        self.image_gen.set_log_callback(self.appendLog_)
        self.api_converter = api_converter.ApiConverter()
        self.api_converter.set_image_generator(self.image_gen)
        self.loaded_model = None
        self.model_path = None

        self.detectGPU_(None)
        self.checkLocalEnvironment()

        # Bring window to front (needed in accessory mode)
        NSApp.activateIgnoringOtherApps_(True)

    # ── Window / Status Bar ──────────────────────────────────────────────

    def applicationShouldTerminate_(self, app):
        """Allow termination without prompt."""
        return 0  # NSTerminateNow

    def windowShouldClose_(self, notification):
        """Close button hides to menu bar instead of quitting."""
        self.window.orderOut_(None)
        return False

    def toggleWindow_(self, sender):
        """Toggle window visibility from status bar menu."""
        if self.window.isVisible():
            self.window.orderOut_(None)
        else:
            self.window.makeKeyAndOrderFront_(None)
            NSApp.activateIgnoringOtherApps_(True)

    def quitApp_(self, sender):
        """Explicit quit — terminate the application."""
        NSApp.terminate_(None)

    # ── Actions (unchanged logic) ────────────────────────────────────────

    def selectModelFile_(self, sender):
        panel = NSOpenPanel.openPanel()
        panel.setCanChooseFiles_(True)
        panel.setCanChooseDirectories_(False)
        panel.setAllowsMultipleSelection_(False)
        panel.setTitle_("Select Model File")
        panel.setMessage_("Choose a model weight file (.safetensors, .pth, .gguf, .mlx, etc.)")
        panel.setAllowedFileTypes_(["safetensors", "pth", "pt", "gguf", "mlx", "bin", "json"])

        if panel.runModal() == NSModalResponseOK:
            url = panel.URLs()[0]
            file_path = url.path()
            self.model_path = file_path
            self.model_path_label.setStringValue_(os.path.basename(file_path))
            self.appendLog_(f"[FILE] Selected: {file_path}")

    def loadModel_(self, sender):
        if not self.model_path:
            self.appendLog_("[ERROR] No model file selected.")
            return

        # Set GPU device for LLM
        selected_device = self.llm_gpu_popup.titleOfSelectedItem()
        if selected_device:
            device_key = env_checker.parse_gpu_device_key(selected_device)
            self.appendLog_(f"[GPU] Setting LLM device to: {device_key}")
            try:
                from tinygrad import Device
                Device.DEFAULT = device_key.upper()
                if device_key.startswith("cuda"):
                    cuda_idx = device_key.split(":")[-1]
                    Device.DEFAULT = f"CUDA:{cuda_idx}"
                elif device_key == "mps":
                    Device.DEFAULT = "METAL"
            except Exception as e:
                self.appendLog_(f"[WARN] Could not set tinygrad device: {e}")

        self.appendLog_(f"[...] Loading model from {self.model_path}...")
        try:
            from tinygrad.nn.state import safe_load, torch_load
            import json

            if self.model_path.endswith('.safetensors'):
                state_dict = safe_load(self.model_path)
                self.loaded_model = state_dict
                self.appendLog_(f"[OK] Model weights loaded. Keys count: {len(state_dict)}")
            elif self.model_path.endswith(('.pth', '.pt')):
                state_dict = torch_load(self.model_path)
                self.loaded_model = state_dict
                self.appendLog_(f"[OK] Model weights loaded. Keys count: {len(state_dict)}")
            elif self.model_path.endswith('.json'):
                with open(self.model_path, 'r') as f:
                    config = json.load(f)
                self.appendLog_(f"Loaded config: {list(config.keys())}")
                self.loaded_model = config
                self.appendLog_("[OK] Config loaded. (Model architecture not yet implemented)")
            elif self.model_path.endswith('.gguf'):
                try:
                    import gguf
                    reader = gguf.GGUFReader(self.model_path)
                    self.appendLog_(f"[OK] GGUF model loaded. Tensors count: {len(reader.tensors)}")
                    self.appendLog_(f"   Model architecture: {reader.fields.get('general.architecture', None)}")
                    self.loaded_model = {
                        "format": "gguf",
                        "path": self.model_path,
                        "reader": reader,
                        "tensor_count": len(reader.tensors),
                    }
                except ImportError:
                    self.appendLog_("[WARN] 'gguf' package not found. Install with: pip install gguf")
                    return
            elif self.model_path.endswith('.mlx'):
                try:
                    import mlx.core as mx
                    weights = mx.load(self.model_path)
                    self.loaded_model = {
                        "format": "mlx",
                        "path": self.model_path,
                        "weights": weights,
                        "tensor_count": len(weights),
                    }
                    self.appendLog_(f"[OK] MLX model loaded. Weights count: {len(weights)}")
                except ImportError:
                    self.appendLog_("[WARN] 'mlx' package not found. Install with: pip install mlx")
                    return
            else:
                self.appendLog_(f"[ERROR] Unsupported file type: {self.model_path}")
                return

            self.api_converter.set_model(self.loaded_model, os.path.basename(self.model_path))
            self.appendLog_("[OK] Model transferred to API converter.")

        except Exception as e:
            import traceback
            self.appendLog_(f"[ERROR] Failed to load model: {str(e)}")
            self.appendLog_(f"   {traceback.format_exc()}")

    def loadImageModel_(self, sender):
        """Load a Stable Diffusion model on the selected GPU."""
        model_id = self.img_model_field.stringValue()
        if not model_id.strip():
            self.appendLog_("[IMG ERROR] No model ID specified.")
            return

        selected_device = self.img_gpu_popup.titleOfSelectedItem()
        device_key = env_checker.parse_gpu_device_key(selected_device or "cpu")
        self.appendLog_(f"[IMG] Loading image model '{model_id}' on {device_key}...")
        self.img_status_label.setStringValue_("Status: Loading model...")

        def _load():
            success, msg = self.image_gen.load_model(model_id, device_key)
            if success:
                self.img_status_label.setStringValue_(f"Status: Ready ({model_id})")
            else:
                self.img_status_label.setStringValue_(f"Status: Load failed")
            self.appendLog_(f"[IMG] {msg}")

        import threading
        t = threading.Thread(target=_load, daemon=True)
        t.start()

    def generateImage_(self, sender):
        """Generate an image from the text prompt."""
        if not self.image_gen.is_ready():
            self.appendLog_("[IMG ERROR] No image model loaded. Load a model first.")
            self.img_status_label.setStringValue_("Status: No model loaded")
            return

        prompt = self.img_prompt_field.stringValue()
        if not prompt.strip():
            self.appendLog_("[IMG ERROR] No prompt specified.")
            return

        self.img_status_label.setStringValue_("Status: Generating...")
        self.appendLog_(f"[IMG] Prompt: {prompt}")

        def _gen():
            image, meta = self.image_gen.generate(prompt=prompt)
            if image is not None:
                self.img_status_label.setStringValue_(
                    f"Status: Done in {meta['elapsed_seconds']}s → {meta['filename']}"
                )
            else:
                self.img_status_label.setStringValue_(f"Status: Error - {meta.get('error', 'unknown')}")

        import threading
        t = threading.Thread(target=_gen, daemon=True)
        t.start()

    def detectGPU_(self, sender):
        gpu_info = gpu_manager.get_gpu_info()
        self.gpu_info_label.setStringValue_(f"GPU: {gpu_info}")
        self.appendLog_(f"[GPU] Detected: {gpu_info}")

    def checkLocalEnvironment(self):
        env_info = env_checker.check_environment()
        report = env_checker.format_env_report(env_info)
        self.appendLog_(report)

    def toggleService_(self, sender):
        if self.start_service_btn.title() == "Start GPU Service":
            self.appendLog_("[SERVICE] Starting GPU service...")
            success = service_controller.start_service()
            if success:
                self.start_service_btn.setTitle_("Stop GPU Service")
                self.appendLog_("[OK] GPU service started (tinygrad runtime initialized).")
            else:
                self.appendLog_("[ERROR] Failed to start GPU service.")
        else:
            self.appendLog_("[STOP] Stopping GPU service...")
            success = service_controller.stop_service()
            if success:
                self.start_service_btn.setTitle_("Start GPU Service")
                self.appendLog_("[OK] GPU service stopped.")
            else:
                self.appendLog_("[ERROR] Failed to stop GPU service.")

    def toggleApiService_(self, sender):
        if self.toggle_api_btn.title() == "Start API Service":
            self.appendLog_("[API] Starting API conversion service...")
            if not self.api_converter.is_ready() and not self.image_gen.is_ready():
                self.appendLog_("[ERROR] No model loaded for API service. Please load an LLM or image model first.")
                return
            success = self.api_converter.start_service(port=1234)
            if success:
                self.toggle_api_btn.setTitle_("Stop API Service")
                self.api_status_label.setStringValue_("API Service: Active (Port 1234)")
                self.appendLog_("[OK] API service started on http://localhost:1234")
            else:
                self.appendLog_("[ERROR] Failed to start API service. Install: pip install fastapi uvicorn pydantic")
        else:
            self.appendLog_("[STOP] Stopping API service...")
            success = self.api_converter.stop_service()
            if success:
                self.toggle_api_btn.setTitle_("Start API Service")
                self.api_status_label.setStringValue_("API Service: Inactive")
                self.appendLog_("[OK] API service stopped.")
            else:
                self.appendLog_("[WARN] API service stop skipped (deps not installed).")

    def appendLog_(self, message):
        current_text = self.log_textview.string()
        new_text = f"{current_text}\n> {message}" if current_text else f"> {message}"
        self.log_textview.setString_(new_text)
        self.log_textview.scrollToEndOfDocument_(self)
        NSLog(message)


if __name__ == "__main__":
    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(1)  # NSApplicationActivationPolicyAccessory — hide Dock icon
    delegate = AppDelegate.alloc().init()
    app.setDelegate_(delegate)
    app.run()
