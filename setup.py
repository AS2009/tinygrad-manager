from setuptools import setup

APP = ['TinyGradManager/main.py']
DATA_FILES = []
OPTIONS = {
    'argv_emulation': False,
    'packages': [
        'tinygrad',
        'fastapi', 'uvicorn', 'pydantic',
        'numpy', 'certifi', 'charset_normalizer', 'idna', 'requests',
        'urllib3', 'anyio', 'sniffio', 'h11', 'click', 'starlette',
    ],
    'includes': [
        'AppKit', 'Foundation', 'objc',
        'pydantic_core', 'pydantic_core._pydantic_core',
        'requests', 'urllib3', 'certifi', 'idna', 'charset_normalizer',
    ],
    'excludes': ['tkinter', 'matplotlib', 'pandas', 'test', 'PIL'],
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
    'site_packages': True,
}

setup(
    name='TinyGradManager',
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)