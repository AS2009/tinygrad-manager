from setuptools import setup

APP = ['TinyGradManager/main.py']
DATA_FILES = []
OPTIONS = {
    'argv_emulation': False,
    'packages': ['tinygrad', 'fastapi', 'uvicorn', 'pydantic', 'PIL'],
    'includes': ['AppKit', 'Foundation', 'objc'],
    'plist': {
        'CFBundleName': 'TinyGradManager',
        'CFBundleDisplayName': 'TinyGrad Manager',
        'CFBundleIdentifier': 'com.yourcompany.tinygradmanager',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'NSHumanReadableCopyright': 'Copyright © 2025',
        'NSHighResolutionCapable': True,
    },
    # 将依赖项放在 options 中，而不是 setup() 的 install_requires
    'install_requires': [
        'tinygrad',
        'pyobjc',
        'fastapi',
        'uvicorn',
        'pydantic',
        'Pillow',
    ],
}

setup(
    name='TinyGradManager',
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
    # 此处不再包含 install_requires
)
