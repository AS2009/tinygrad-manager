from setuptools import setup

APP = ['TinyGradManager/main.py']
DATA_FILES = []
OPTIONS = {
    'argv_emulation': False,
    'packages': [
        'tinygrad', 'fastapi', 'uvicorn', 'pydantic', 'PIL',
        'numpy', 'certifi', 'charset_normalizer', 'idna', 'requests',
    ],
    'includes': [
        'AppKit', 'Foundation', 'objc',
        'pydantic_core', 'pydantic_core._pydantic_core',
        'pydantic.deprecated.decorator',
        'PIL._imaging', 'PIL.Image', 'PIL.ImageFile', 'PIL.ImageDraw',
        'PIL.ImageFont', 'PIL.ImageFilter', 'PIL.ImageOps',
    ],
    'excludes': ['tkinter', 'matplotlib', 'pandas'],
    'plist': {
        'CFBundleName': 'TinyGradManager',
        'CFBundleDisplayName': 'TinyGrad Manager',
        'CFBundleIdentifier': 'com.yourcompany.tinygradmanager',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'NSHumanReadableCopyright': 'Copyright © 2025',
        'NSHighResolutionCapable': True,
        'LSMinimumSystemVersion': '10.13',
    },
    # 强制包含 Pillow 的 C 扩展及其依赖的动态库
    'frameworks': [],
    'resources': [],
    'iconfile': None,
}

setup(
    name='TinyGradManager',
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
