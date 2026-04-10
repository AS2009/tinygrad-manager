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
    # 不要在此放置 install_requires
}

setup(
    name='TinyGradManager',
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
    install_requires=[
        'tinygrad',
        'pyobjc',
        'fastapi',
        'uvicorn',
        'pydantic',
        'Pillow',
    ],
)
