import os
import sys

# 修复动态库路径（虽然无 Pillow，但保留以备用）
if getattr(sys, 'frozen', False) or '.app/Contents/MacOS' in sys.executable:
    base_dir = os.path.dirname(sys.executable)
    lib_dir = os.path.join(base_dir, '..', 'Resources', 'lib')
    if os.path.exists(lib_dir):
        os.environ['DYLD_LIBRARY_PATH'] = lib_dir

# 将当前目录加入搜索路径，使绝对导入可用
sys.path.insert(0, os.path.dirname(__file__))

import objc
from Foundation import NSObject, NSRunLoop, NSLog
from AppKit import (
    NSApplication, NSWindow, NSView,
    NSButton, NSTextField, NSPopUpButton, NSScrollView, NSTextView,
    NSMakeRect, NSWindowStyleMaskTitled, NSWindowStyleMaskClosable,
    NSWindowStyleMaskMiniaturizable, NSWindowStyleMaskResizable,
    NSBackingStoreBuffered, NSAlert
)
from threading import Thread

# 绝对导入自定义模块
import gpu_manager
import service_controller
import api_converter
import env_checker

class AppDelegate(NSObject):
    def applicationDidFinishLaunching_(self, notification):
        rect = NSMakeRect(100, 100, 700, 550)
        mask = (NSWindowStyleMaskTitled | NSWindowStyleMaskClosable |
                NSWindowStyleMaskMiniaturizable | NSWindowStyleMaskResizable)
        self.window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            rect, mask, NSBackingStoreBuffered, False)
        self.window.setTitle_("TinyGrad Manager")
        self.window.makeKeyAndOrderFront_(None)

        content_view = self.window.contentView()

        # 标题
        title_label = NSTextField.labelWithString_("🚀 TinyGrad Model Manager")
        title_label.setFrame_(NSMakeRect(20, 480, 660, 40))
        title_label.setFont_(objc.lookUpClass("NSFont").fontWithName_size_("Helvetica-Bold", 24))
        content_view.addSubview_(title_label)

        # LLM 模型选择区域
        model_label = NSTextField.labelWithString_("Select LLM Model:")
        model_label.setFrame_(NSMakeRect(20, 420, 150, 25))
        content_view.addSubview_(model_label)

        self.model_popup = NSPopUpButton.alloc().initWithFrame_(NSMakeRect(170, 415, 250, 30))
        self.model_popup.addItemsWithTitles_(self.get_available_models())
        content_view.addSubview_(self.model_popup)

        load_btn = NSButton.buttonWithTitle_target_action_("Load Model", self, "loadModel:")
        load_btn.setFrame_(NSMakeRect(430, 415, 150, 32))
        load_btn.setBezelStyle_(1)
        content_view.addSubview_(load_btn)

        # GPU 信息
        self.gpu_info_label = NSTextField.labelWithString_("🔍 Detecting GPU...")
        self.gpu_info_label.setFrame_(NSMakeRect(20, 360, 560, 25))
        content_view.addSubview_(self.gpu_info_label)

        # GPU 服务控制
        self.start_service_btn = NSButton.buttonWithTitle_target_action_("Start GPU Service", self, "toggleService:")
        self.start_service_btn.setFrame_(NSMakeRect(150, 310, 150, 32))
        self.start_service_btn.setBezelStyle_(1)
        content_view.addSubview_(self.start_service_btn)

        # API 转换器状态
        self.api_status_label = NSTextField.labelWithString_("🌐 API Service: Inactive")
        self.api_status_label.setFrame_(NSMakeRect(20, 260, 250, 25))
        content_view.addSubview_(self.api_status_label)

        self.toggle_api_btn = NSButton.buttonWithTitle_target_action_("Start API Service", self, "toggleApiService:")
        self.toggle_api_btn.setFrame_(NSMakeRect(280, 255, 150, 32))
        self.toggle_api_btn.setBezelStyle_(1)
        content_view.addSubview_(self.toggle_api_btn)

        convert_btn = NSButton.buttonWithTitle_target_action_("Convert to LMStudio API", self, "convertModel:")
        convert_btn.setFrame_(NSMakeRect(450, 255, 180, 32))
        convert_btn.setBezelStyle_(1)
        content_view.addSubview_(convert_btn)

        # 日志区域
        scroll_view = NSScrollView.alloc().initWithFrame_(NSMakeRect(20, 20, 660, 200))
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