from setuptools import setup
import importlib.util

APP = ['TinyGradManager/main.py']
DATA_FILES = []

# 核心依赖包
_packages = [
    'tinygrad',
    'fastapi', 'uvicorn', 'pydantic',
    'numpy', 'certifi', 'charset_normalizer', 'idna', 'requests',
    'urllib3', 'anyio', 'sniffio', 'h11', 'click', 'starlette',
]

# 可选格式支持包：仅当已安装时才打包
for _pkg in ['gguf', 'mlx']:
    if importlib.util.find_spec(_pkg):
        _packages.append(_pkg)

OPTIONS = {
    'argv_emulation': False,
    'packages': _packages,
    'includes': [
        'AppKit', 'Foundation', 'objc', 'Quartz',
        'pydantic_core', 'pydantic_core._pydantic_core',
        'requests', 'urllib3', 'certifi', 'idna', 'charset_normalizer',
    ],
    'excludes': ['tkinter', 'matplotlib', 'pandas', 'test', 'PIL',
                 'torch', 'diffusers', 'transformers', 'accelerate', 'safetensors',
                 'image_generator'],
    'plist': {
        'CFBundleName': 'TinyGradManager',
        'CFBundleDisplayName': 'TinyGrad Manager',
        'CFBundleIdentifier': 'com.yourcompany.tinygradmanager',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'NSHumanReadableCopyright': 'Copyright © 2025',
        'NSHighResolutionCapable': True,
        'LSUIElement': True,  # hide Dock icon, menu-bar-only app
        'LSMinimumSystemVersion': '12.0',
    },
    'site_packages': True,
}

setup(
    name='TinyGradManager',
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)