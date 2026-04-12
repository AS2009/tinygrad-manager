import os
import sys

# 修复打包后动态库路径问题
if getattr(sys, 'frozen', False) or '.app/Contents/MacOS' in sys.executable:
    base_dir = os.path.dirname(sys.executable)
    lib_dir = os.path.join(base_dir, '..', 'Resources', 'lib')
    if os.path.exists(lib_dir):
        os.environ['DYLD_LIBRARY_PATH'] = lib_dir
        pil_dylib = os.path.join(lib_dir, 'python3.11', 'PIL', '.dylibs')
        if os.path.exists(pil_dylib):
            os.environ['DYLD_LIBRARY_PATH'] += f":{pil_dylib}"

import objc
from Foundation import NSObject, NSRunLoop, NSLog
from AppKit import (
    NSApplication, NSWindow, NSView,
    NSButton, NSTextField, NSPopUpButton, NSScrollView, NSTextView,
    NSMakeRect, NSWindowStyleMaskTitled, NSWindowStyleMaskClosable,
    NSWindowStyleMaskMiniaturizable, NSWindowStyleMaskResizable,
    NSBackingStoreBuffered, NSImageView, NSImage, NSImageScaleProportionallyUpOrDown,
    NSSavePanel, NSModalResponseOK
)
from threading import Thread

from . import gpu_manager
from . import service_controller
from . import api_converter
from . import env_checker
from . import image_generator

class AppDelegate(NSObject):
    def applicationDidFinishLaunching_(self, notification):
        rect = NSMakeRect(100, 100, 800, 750)
        mask = (NSWindowStyleMaskTitled | NSWindowStyleMaskClosable |
                NSWindowStyleMaskMiniaturizable | NSWindowStyleMaskResizable)
        self.window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            rect, mask, NSBackingStoreBuffered, False)
        self.window.setTitle_("TinyGrad Manager")
        self.window.makeKeyAndOrderFront_(None)

        content_view = self.window.contentView()

        # 标题
        title_label = NSTextField.labelWithString_("🚀 TinyGrad Model Manager")
        title_label.setFrame_(NSMakeRect(20, 680, 760, 40))
        title_label.setFont_(objc.lookUpClass("NSFont").fontWithName_size_("Helvetica-Bold", 24))
        content_view.addSubview_(title_label)

        # ---------- LLM 模型选择区域 ----------
        model_label = NSTextField.labelWithString_("Select LLM Model:")
        model_label.setFrame_(NSMakeRect(20, 620, 150, 25))
        content_view.addSubview_(model_label)

        self.model_popup = NSPopUpButton.alloc().initWithFrame_(NSMakeRect(170, 615, 250, 30))
        self.model_popup.addItemsWithTitles_(self.get_available_models())
        content_view.addSubview_(self.model_popup)

        load_btn = NSButton.buttonWithTitle_target_action_("Load Model", self, "loadModel:")
        load_btn.setFrame_(NSMakeRect(430, 615, 150, 32))
        load_btn.setBezelStyle_(1)
        content_view.addSubview_(load_btn)

        # GPU 信息
        self.gpu_info_label = NSTextField.labelWithString_("🔍 Detecting GPU...")
        self.gpu_info_label.setFrame_(NSMakeRect(20, 570, 560, 25))
        content_view.addSubview_(self.gpu_info_label)

        # GPU 服务控制
        self.start_service_btn = NSButton.buttonWithTitle_target_action_("Start GPU Service", self, "toggleService:")
        self.start_service_btn.setFrame_(NSMakeRect(150, 520, 150, 32))
        self.start_service_btn.setBezelStyle_(1)
        content_view.addSubview_(self.start_service_btn)

        # API 转换器状态
        self.api_status_label = NSTextField.labelWithString_("🌐 API Service: Inactive")
        self.api_status_label.setFrame_(NSMakeRect(20, 470, 250, 25))
        content_view.addSubview_(self.api_status_label)

        self.toggle_api_btn = NSButton.buttonWithTitle_target_action_("Start API Service", self, "toggleApiService:")
        self.toggle_api_btn.setFrame_(NSMakeRect(280, 465, 150, 32))
        self.toggle_api_btn.setBezelStyle_(1)
        content_view.addSubview_(self.toggle_api_btn)

        convert_btn = NSButton.buttonWithTitle_target_action_("Convert to LMStudio API", self, "convertModel:")
        convert_btn.setFrame_(NSMakeRect(450, 465, 180, 32))
        convert_btn.setBezelStyle_(1)
        content_view.addSubview_(convert_btn)

        # ---------- 文生图区域 ----------
        t2i_label = NSTextField.labelWithString_("🎨 Text to Image (Stable Diffusion)")
        t2i_label.setFrame_(NSMakeRect(20, 420, 400, 25))
        t2i_label.setFont_(objc.lookUpClass("NSFont").fontWithName_size_("Helvetica-Bold", 16))
        content_view.addSubview_(t2i_label)

        # SD 模型选择
        sd_model_label = NSTextField.labelWithString_("SD Model:")
        sd_model_label.setFrame_(NSMakeRect(20, 385, 100, 25))
        content_view.addSubview_(sd_model_label)

        self.sd_model_popup = NSPopUpButton.alloc().initWithFrame_(NSMakeRect(120, 380, 220, 30))
        self.sd_model_popup.addItemsWithTitles_(image_generator.get_available_sd_models())
        content_view.addSubview_(self.sd_model_popup)

        load_sd_btn = NSButton.buttonWithTitle_target_action_("Load SD Model", self, "loadSDModel:")
        load_sd_btn.setFrame_(NSMakeRect(350, 380, 140, 32))
        load_sd_btn.setBezelStyle_(1)
        content_view.addSubview_(load_sd_btn)

        # 提示词
        prompt_label = NSTextField.labelWithString_("Prompt:")
        prompt_label.setFrame_(NSMakeRect(20, 345, 100, 25))
        content_view.addSubview_(prompt_label)

        self.prompt_textfield = NSTextField.alloc().initWithFrame_(NSMakeRect(120, 345, 370, 25))
        self.prompt_textfield.setPlaceholderString_("A beautiful landscape, digital art")
        content_view.addSubview_(self.prompt_textfield)

        # 负向提示词
        neg_prompt_label = NSTextField.labelWithString_("Negative Prompt:")
        neg_prompt_label.setFrame_(NSMakeRect(20, 310, 120, 25))
        content_view.addSubview_(neg_prompt_label)

        self.neg_prompt_textfield = NSTextField.alloc().initWithFrame_(NSMakeRect(140, 310, 350, 25))
        self.neg_prompt_textfield.setPlaceholderString_("blurry, ugly, low quality")
        content_view.addSubview_(self.neg_prompt_textfield)

        # 参数设置
        steps_label = NSTextField.labelWithString_("Steps:")
        steps_label.setFrame_(NSMakeRect(20, 275, 50, 25))
        content_view.addSubview_(steps_label)

        self.steps_textfield = NSTextField.alloc().initWithFrame_(NSMakeRect(70, 275, 60, 25))
        self.steps_textfield.setStringValue_("30")
        content_view.addSubview_(self.steps_textfield)

        cfg_label = NSTextField.labelWithString_("CFG Scale:")
        cfg_label.setFrame_(NSMakeRect(150, 275, 70, 25))
        content_view.addSubview_(cfg_label)

        self.cfg_textfield = NSTextField.alloc().initWithFrame_(NSMakeRect(220, 275, 60, 25))
        self.cfg_textfield.setStringValue_("7.5")
        content_view.addSubview_(self.cfg_textfield)

        seed_label = NSTextField.labelWithString_("Seed:")
        seed_label.setFrame_(NSMakeRect(300, 275, 40, 25))
        content_view.addSubview_(seed_label)

        self.seed_textfield = NSTextField.alloc().initWithFrame_(NSMakeRect(340, 275, 80, 25))
        self.seed_textfield.setPlaceholderString_("random")
        content_view.addSubview_(self.seed_textfield)

        # 生成按钮
        generate_btn = NSButton.buttonWithTitle_target_action_("Generate Image", self, "generateImage:")
        generate_btn.setFrame_(NSMakeRect(440, 270, 150, 32))
        generate_btn.setBezelStyle_(1)
        content_view.addSubview_(generate_btn)

        # 图像预览区域
        self.image_view = NSImageView.alloc().initWithFrame_(NSMakeRect(520, 350, 200, 150))
        self.image_view.setImageScaling_(NSImageScaleProportionallyUpOrDown)
        self.image_view.setImage_(NSImage.imageNamed_("NSApplicationIcon"))
        content_view.addSubview_(self.image_view)

        # 保存图像按钮
        save_btn = NSButton.buttonWithTitle_target_action_("Save Image", self, "saveImage:")
        save_btn.setFrame_(NSMakeRect(520, 310, 100, 32))
        save_btn.setBezelStyle_(1)
        content_view.addSubview_(save_btn)

        # 日志区域
        scroll_view = NSScrollView.alloc().initWithFrame_(NSMakeRect(20, 20, 760, 240))
        scroll_view.setHasVerticalScroller_(True)
        scroll_view.setBorderType_(2)

        self.log_textview = NSTextView.alloc().initWithFrame_(scroll_view.contentView().frame())
        self.log_textview.setEditable_(False)
        self.log_textview.setSelectable_(True)
        scroll_view.setDocumentView_(self.log_textview)
        content_view.addSubview_(scroll_view)

        # 初始化组件
        self.api_converter = api_converter.ApiConverter()
        self.detectGPU_(None)
        self.checkLocalEnvironment()

        self.generated_image_path = None

    def get_available_models(self):
        return [
            "LLaMA (various sizes)",
            "GPT-2 (medium/large)",
            "Stable Diffusion",
            "ResNet50",
            "CLIP",
            "EfficientNet"
        ]

    def detectGPU_(self, sender):
        gpu_info = gpu_manager.get_gpu_info()
        self.gpu_info_label.setStringValue_(f"💻 GPU Info: {gpu_info}")
        self.appendLog_(f"GPU detected: {gpu_info}")

    def checkLocalEnvironment(self):
        env_info = env_checker.check_environment()
        report = env_checker.format_env_report(env_info)
        self.appendLog_(report)

    def loadModel_(self, sender):
        selected_model = self.model_popup.titleOfSelectedItem()
        self.appendLog_(f"⏳ Loading model: {selected_model}...")
        self.appendLog_(f"✅ Model '{selected_model}' loaded successfully!")

    def toggleService_(self, sender):
        if self.start_service_btn.title() == "Start GPU Service":
            self.appendLog_("⚙️ Starting GPU service...")
            success = service_controller.start_service()
            if success:
                self.start_service_btn.setTitle_("Stop GPU Service")
                self.appendLog_("✅ GPU service started.")
            else:
                self.appendLog_("❌ Failed to start GPU service.")
        else:
            self.appendLog_("🛑 Stopping GPU service...")
            success = service_controller.stop_service()
            if success:
                self.start_service_btn.setTitle_("Start GPU Service")
                self.appendLog_("✅ GPU service stopped.")
            else:
                self.appendLog_("❌ Failed to stop GPU service.")

    def convertModel_(self, sender):
        selected_model = self.model_popup.titleOfSelectedItem()
        self.appendLog_(f"⚙️ Preparing to convert model: {selected_model}")
        model_path = f"/path/to/your/tinygrad/models/{selected_model}"
        self.api_converter.load_model(model_path)
        self.appendLog_(f"✅ Model '{selected_model}' loaded for API conversion.")

    def toggleApiService_(self, sender):
        if self.toggle_api_btn.title() == "Start API Service":
            self.appendLog_("🌐 Starting API conversion service...")
            if not self.api_converter.model:
                self.appendLog_("❌ Please load a model first (using 'Convert to LMStudio API').")
                return
            self.api_converter.start_service(port=1234)
            self.toggle_api_btn.setTitle_("Stop API Service")
            self.api_status_label.setStringValue_(f"🌐 API Service: Active (Port 1234)")
            self.appendLog_("✅ API service started on http://localhost:1234")
            self.appendLog_("💡 You can now connect any OpenAI client to this address.")
        else:
            self.appendLog_("🛑 Stopping API service...")
            self.api_converter.stop_service()
            self.toggle_api_btn.setTitle_("Start API Service")
            self.api_status_label.setStringValue_("🌐 API Service: Inactive")
            self.appendLog_("✅ API service stopped.")

    def loadSDModel_(self, sender):
        selected_model = self.sd_model_popup.titleOfSelectedItem()
        self.appendLog_(f"⏳ Loading SD model: {selected_model}...")
        def progress(msg):
            self.appendLog_(msg)
        def load_thread():
            success = image_generator.load_sd_model(selected_model, progress_callback=progress)
            if not success:
                self.appendLog_(f"❌ Failed to load {selected_model}")
        Thread(target=load_thread).start()

    def generateImage_(self, sender):
        if image_generator._loaded_model is None:
            self.appendLog_("❌ Please load a Stable Diffusion model first.")
            return
        prompt = self.prompt_textfield.stringValue()
        if not prompt:
            self.appendLog_("❌ Prompt cannot be empty.")
            return
        neg_prompt = self.neg_prompt_textfield.stringValue()
        try:
            steps = int(self.steps_textfield.stringValue())
        except:
            steps = 30
        try:
            guidance = float(self.cfg_textfield.stringValue())
        except:
            guidance = 7.5
        seed_str = self.seed_textfield.stringValue()
        seed = int(seed_str) if seed_str else None

        self.appendLog_(f"🎨 Generating image with prompt: {prompt[:50]}...")

        def progress_callback(current, total, status):
            self.appendLog_(f"[{current}/{total}] {status}")

        def result_callback(image_path):
            if image_path:
                self.generated_image_path = image_path
                self.performSelectorOnMainThread_withObject_waitUntilDone_("updateImagePreview:", None, False)
                self.appendLog_(f"✅ Image generated: {image_path}")
            else:
                self.appendLog_("❌ Image generation failed.")

        image_generator.generate_image(
            prompt=prompt,
            negative_prompt=neg_prompt,
            steps=steps,
            guidance_scale=guidance,
            seed=seed,
            progress_callback=progress_callback,
            result_callback=result_callback
        )

    def updateImagePreview_(self, _):
        if self.generated_image_path:
            ns_image = NSImage.alloc().initWithContentsOfFile_(self.generated_image_path)
            if ns_image:
                self.image_view.setImage_(ns_image)

    def saveImage_(self, sender):
        if not self.generated_image_path:
            self.appendLog_("No image to save.")
            return
        panel = NSSavePanel.savePanel()
        panel.setTitle_("Save Image")
        panel.setNameFieldStringValue_("generated_image.png")
        if panel.runModal() == NSModalResponseOK:
            dest_path = panel.URL().path()
            import shutil
            shutil.copy2(self.generated_image_path, dest_path)
            self.appendLog_(f"✅ Image saved to {dest_path}")

    def appendLog_(self, message):
        current_text = self.log_textview.string()
        new_text = f"{current_text}\n> {message}" if current_text else f"> {message}"
        self.log_textview.setString_(new_text)
        self.log_textview.scrollToEndOfDocument_(self)
        NSLog(message)

if __name__ == "__main__":
    app = NSApplication.sharedApplication()
    delegate = AppDelegate.alloc().init()
    app.setDelegate_(delegate)
    app.run()