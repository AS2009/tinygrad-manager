import Foundation

// MARK: - Localization

enum L10n {
    case appName
    case appSubtitle
    case showHide
    case quit
    case modelFile
    case noModel
    case loadedModel(String)
    case browse
    case noFileSelected
    case gpu
    case detectingDevices
    case loadModel
    case loadImageModel
    case textToImage
    case imageModelFile
    case noLocalFile
    case orHFID
    case prompt
    case generateImage
    case generating
    case statusNoModel
    case statusLoading
    case statusReady
    case statusLoadFailed
    case statusFailed
    case statusDone(Double, String)
    case systemStatus
    case gpuService
    case startGpuService
    case stopGpuService
    case checkEnv
    case console
    case clear
    case disconnected
    case starting
    case connected
    case retry
    case errorSelectFile
    case errorLoadModel
    case errorLoadImageModel
    case errorGenerate

    var key: String {
        switch self {
        case .appName:              "app_name"
        case .appSubtitle:          "app_subtitle"
        case .showHide:             "show_hide"
        case .quit:                 "quit"
        case .modelFile:            "model_file"
        case .noModel:              "no_model"
        case .loadedModel(let s):   "loaded_model_\(s)"
        case .browse:               "browse"
        case .noFileSelected:       "no_file_selected"
        case .gpu:                  "gpu"
        case .detectingDevices:     "detecting_devices"
        case .loadModel:            "load_model"
        case .loadImageModel:       "load_image_model"
        case .textToImage:          "text_to_image"
        case .imageModelFile:       "image_model_file"
        case .noLocalFile:          "no_local_file"
        case .orHFID:               "or_hf_id"
        case .prompt:               "prompt"
        case .generateImage:        "generate_image"
        case .generating:           "generating"
        case .statusNoModel:        "status_no_model"
        case .statusLoading:        "status_loading"
        case .statusReady:          "status_ready"
        case .statusLoadFailed:     "status_load_failed"
        case .statusFailed:         "status_failed"
        case .statusDone:           "status_done"
        case .systemStatus:         "system_status"
        case .gpuService:           "gpu_service"
        case .startGpuService:      "start_gpu_service"
        case .stopGpuService:       "stop_gpu_service"
        case .checkEnv:             "check_env"
        case .console:              "console"
        case .clear:                "clear"
        case .disconnected:         "disconnected"
        case .starting:             "starting"
        case .connected:            "connected"
        case .retry:                "retry"
        case .errorSelectFile:      "error_select_file"
        case .errorLoadModel:       "error_load_model"
        case .errorLoadImageModel:  "error_load_image_model"
        case .errorGenerate:        "error_generate"
        }
    }
}

extension L10n: CustomStringConvertible {
    var description: String {
        let isChinese = Locale.current.language.languageCode?.identifier == "zh"
        return isChinese ? chinese : english
    }

    private var english: String {
        switch self {
        case .appName:              "TinyGrad Manager"
        case .appSubtitle:          "Model Management & GPU Control"
        case .showHide:             "Show/Hide TinyGrad Manager"
        case .quit:                 "Quit TinyGrad Manager"
        case .modelFile:            "Model File"
        case .noModel:              "No model"
        case .loadedModel(let s):   "Loaded: \(s)"
        case .browse:               "Browse..."
        case .noFileSelected:       "No file selected"
        case .gpu:                  "GPU:"
        case .detectingDevices:     "Detecting devices..."
        case .loadModel:            "Load Model"
        case .loadImageModel:       "Load Image Model"
        case .textToImage:          "Text-to-Image"
        case .imageModelFile:       "Model File:"
        case .noLocalFile:          "No local file"
        case .orHFID:               "Or HF ID:"
        case .prompt:               "Prompt:"
        case .generateImage:        "Generate"
        case .generating:           "Generating..."
        case .statusNoModel:        "Status: No model loaded"
        case .statusLoading:        "Status: Loading model..."
        case .statusReady:          "Status: Ready"
        case .statusLoadFailed:     "Status: Load failed"
        case .statusFailed:         "Generation failed"
        case .statusDone(let t, let f): "Done in \(t)s → \(f)"
        case .systemStatus:         "System Status"
        case .gpuService:           "GPU Service"
        case .startGpuService:      "Start GPU Service"
        case .stopGpuService:       "Stop GPU Service"
        case .checkEnv:             "Check Env"
        case .console:              "Console"
        case .clear:                "Clear"
        case .disconnected:         "Disconnected"
        case .starting:             "Starting..."
        case .connected:            "Connected"
        case .retry:                "Retry"
        case .errorSelectFile:      "Error: no file selected"
        case .errorLoadModel:       "Error: failed to load model"
        case .errorLoadImageModel:  "Error: failed to load image model"
        case .errorGenerate:        "Error: generation failed"
        }
    }

    private var chinese: String {
        switch self {
        case .appName:              "TinyGrad 管理器"
        case .appSubtitle:          "模型管理 & GPU 控制"
        case .showHide:             "显示/隐藏 TinyGrad 管理器"
        case .quit:                 "退出 TinyGrad 管理器"
        case .modelFile:            "模型文件"
        case .noModel:              "未加载模型"
        case .loadedModel(let s):   "已加载: \(s)"
        case .browse:               "浏览..."
        case .noFileSelected:       "未选择文件"
        case .gpu:                  "GPU:"
        case .detectingDevices:     "正在检测设备..."
        case .loadModel:            "加载模型"
        case .loadImageModel:       "加载图像模型"
        case .textToImage:          "文生图"
        case .imageModelFile:       "模型文件:"
        case .noLocalFile:          "未选择本地文件"
        case .orHFID:               "或 HuggingFace ID:"
        case .prompt:               "提示词:"
        case .generateImage:        "生成图像"
        case .generating:           "正在生成..."
        case .statusNoModel:        "状态: 未加载模型"
        case .statusLoading:        "状态: 正在加载模型..."
        case .statusReady:          "状态: 就绪"
        case .statusLoadFailed:     "状态: 加载失败"
        case .statusFailed:         "生成失败"
        case .statusDone(let t, let f): "完成 \(t)秒 → \(f)"
        case .systemStatus:         "系统状态"
        case .gpuService:           "GPU 服务"
        case .startGpuService:      "启动 GPU 服务"
        case .stopGpuService:       "停止 GPU 服务"
        case .checkEnv:             "环境检测"
        case .console:              "控制台"
        case .clear:                "清空"
        case .disconnected:         "未连接"
        case .starting:             "启动中..."
        case .connected:            "已连接"
        case .retry:                "重试"
        case .errorSelectFile:      "错误: 未选择文件"
        case .errorLoadModel:       "错误: 模型加载失败"
        case .errorLoadImageModel:  "错误: 图像模型加载失败"
        case .errorGenerate:        "错误: 生成失败"
        }
    }
}

extension String {
    /// Interpolate a localized string
    init(loc: L10n) {
        self = loc.description
    }
}
