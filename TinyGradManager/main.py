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
    NSButton, NSTextField, NSPopUpButton, NSScrollView, NSTextView,
    NSMakeRect, NSWindowStyleMaskTitled, NSWindowStyleMaskClosable,
    NSWindowStyleMaskMiniaturizable, NSWindowStyleMaskResizable,
    NSBackingStoreBuffered,
    NSOpenPanel, NSModalResponseOK  # ← 这两个必须从 AppKit 导入！
)
from threading import Thread

# 导入自定义模块
import gpu_manager
import service_controller
import api_converter
import env_checker

class AppDelegate(NSObject):
    def applicationDidFinishLaunching_(self, notification):
        # 窗口尺寸
        rect = NSMakeRect(100, 100, 750, 600)
        mask = (NSWindowStyleMaskTitled | NSWindowStyleMaskClosable |
                NSWindowStyleMaskMiniaturizable | NSWindowStyleMaskResizable)
        self.window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            rect, mask, NSBackingStoreBuffered, False)
        self.window.setTitle_("TinyGrad Manager")
        self.window.makeKeyAndOrderFront_(None)

        content_view = self.window.contentView()

        # 标题
        title_label = NSTextField.labelWithString_("🚀 TinyGrad Model Manager")
        title_label.setFrame_(NSMakeRect(20, 530, 710, 40))
        title_label.setFont_(objc.lookUpClass("NSFont").fontWithName_size_("Helvetica-Bold", 24))
        content_view.addSubview_(title_label)

        # ---------- 模型选择区域 ----------
        model_label = NSTextField.labelWithString_("Select Model File:")
        model_label.setFrame_(NSMakeRect(20, 470, 150, 25))
        content_view.addSubview_(model_label)

        # 显示所选文件路径的标签
        self.model_path_label = NSTextField.labelWithString_("No file selected")
        self.model_path_label.setFrame_(NSMakeRect(20, 440, 500, 25))
        content_view.addSubview_(self.model_path_label)

        # 选择文件按钮
        select_btn = NSButton.buttonWithTitle_target_action_("Browse...", self, "selectModelFile:")
        select_btn.setFrame_(NSMakeRect(530, 435, 100, 32))
        select_btn.setBezelStyle_(1)
        content_view.addSubview_(select_btn)

        # 加载模型按钮
        load_btn = NSButton.buttonWithTitle_target_action_("Load Model", self, "loadModel:")
        load_btn.setFrame_(NSMakeRect(640, 435, 90, 32))
        load_btn.setBezelStyle_(1)
        content_view.addSubview_(load_btn)

        # GPU 信息
        self.gpu_info_label = NSTextField.labelWithString_("🔍 Detecting GPU...")
        self.gpu_info_label.setFrame_(NSMakeRect(20, 390, 560, 25))
        content_view.addSubview_(self.gpu_info_label)

        # GPU 服务控制
        self.start_service_btn = NSButton.buttonWithTitle_target_action_("Start GPU Service", self, "toggleService:")
        self.start_service_btn.setFrame_(NSMakeRect(150, 340, 150, 32))
        self.start_service_btn.setBezelStyle_(1)
        content_view.addSubview_(self.start_service_btn)

        # API 转换器状态
        self.api_status_label = NSTextField.labelWithString_("🌐 API Service: Inactive")
        self.api_status_label.setFrame_(NSMakeRect(20, 290, 250, 25))
        content_view.addSubview_(self.api_status_label)

        self.toggle_api_btn = NSButton.buttonWithTitle_target_action_("Start API Service", self, "toggleApiService:")
        self.toggle_api_btn.setFrame_(NSMakeRect(280, 285, 150, 32))
        self.toggle_api_btn.setBezelStyle_(1)
        content_view.addSubview_(self.toggle_api_btn)

        # 日志区域
        scroll_view = NSScrollView.alloc().initWithFrame_(NSMakeRect(20, 20, 710, 250))
        scroll_view.setHasVerticalScroller_(True)
        scroll_view.setBorderType_(2)

        self.log_textview = NSTextView.alloc().initWithFrame_(scroll_view.contentView().frame())
        self.log_textview.setEditable_(False)
        self.log_textview.setSelectable_(True)
        scroll_view.setDocumentView_(self.log_textview)
        content_view.addSubview_(scroll_view)

        # 初始化组件
        self.api_converter = api_converter.ApiConverter()
        self.loaded_model = None      # 保存加载的模型对象
        self.model_path = None        # 保存模型文件路径

        self.detectGPU_(None)
        self.checkLocalEnvironment()

    def selectModelFile_(self, sender):
        """打开文件选择对话框，选择模型权重文件"""
        panel = NSOpenPanel.openPanel()
        panel.setCanChooseFiles_(True)
        panel.setCanChooseDirectories_(False)
        panel.setAllowsMultipleSelection_(False)
        panel.setTitle_("Select Model File")
        panel.setMessage_("Choose a model weight file (.safetensors, .pth, .gguf, etc.)")
        panel.setAllowedFileTypes_(["safetensors", "pth", "pt", "gguf", "bin", "json"])

        if panel.runModal() == NSModalResponseOK:
            url = panel.URLs()[0]
            file_path = url.path()
            self.model_path = file_path
            self.model_path_label.setStringValue_(f"📁 {os.path.basename(file_path)}")
            self.appendLog_(f"Selected: {file_path}")

    def loadModel_(self, sender):
        """加载选中的模型文件"""
        if not self.model_path:
            self.appendLog_("❌ No model file selected.")
            return

        self.appendLog_(f"⏳ Loading model from {self.model_path}...")
        try:
            from tinygrad.nn.state import safe_load, torch_load
            import json

            # 根据扩展名加载权重
            if self.model_path.endswith('.safetensors'):
                state_dict = safe_load(self.model_path)
            elif self.model_path.endswith(('.pth', '.pt')):
                state_dict = torch_load(self.model_path)
            elif self.model_path.endswith('.json'):
                # 可能是模型配置
                with open(self.model_path, 'r') as f:
                    config = json.load(f)
                self.appendLog_(f"Loaded config: {list(config.keys())}")
                # 暂存配置，实际使用时需根据配置构建模型
                self.loaded_model = config
                self.appendLog_("✅ Config loaded. (Model architecture not yet implemented)")
                return
            else:
                self.appendLog_(f"❌ Unsupported file type: {self.model_path}")
                return

            # 这里简单保存 state_dict，实际使用时需构建对应的网络结构并加载权重
            self.loaded_model = state_dict
            self.appendLog_(f"✅ Model weights loaded. Keys count: {len(state_dict)}")

            # 将模型传递给 API 转换器
            self.api_converter.set_model(self.loaded_model, os.path.basename(self.model_path))
            self.appendLog_("✅ Model transferred to API converter.")

        except Exception as e:
            self.appendLog_(f"❌ Failed to load model: {str(e)}")

    def detectGPU_(self, sender):
        gpu_info = gpu_manager.get_gpu_info()
        self.gpu_info_label.setStringValue_(f"💻 GPU Info: {gpu_info}")
        self.appendLog_(f"GPU detected: {gpu_info}")

    def checkLocalEnvironment(self):
        env_info = env_checker.check_environment()
        report = env_checker.format_env_report(env_info)
        self.appendLog_(report)

    def toggleService_(self, sender):
        if self.start_service_btn.title() == "Start GPU Service":
            self.appendLog_("⚙️ Starting GPU service...")
            success = service_controller.start_service()
            if success:
                self.start_service_btn.setTitle_("Stop GPU Service")
                self.appendLog_("✅ GPU service started (tinygrad runtime initialized).")
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

    def toggleApiService_(self, sender):
        if self.toggle_api_btn.title() == "Start API Service":
            self.appendLog_("🌐 Starting API conversion service...")
            if not self.api_converter.is_ready():
                self.appendLog_("❌ No model loaded for API service. Please load a model first.")
                return
            self.api_converter.start_service(port=1234)
            self.toggle_api_btn.setTitle_("Stop API Service")
            self.api_status_label.setStringValue_("🌐 API Service: Active (Port 1234)")
            self.appendLog_("✅ API service started on http://localhost:1234")
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