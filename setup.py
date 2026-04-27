"""Build script for TinyGrad Manager .app bundle.

Architecture: Apple Silicon (arm64) only.
The Swift GUI (SwiftGUI/) compiles separately via swift build.
This script packages the Python backend + Swift binary into a macOS .app.
"""

import os
import sys
import subprocess
from setuptools import setup
import importlib.util

APP = ['TinyGradManager/backend_main.py']
DATA_FILES = []

_packages = [
    'tinygrad',
    'fastapi', 'uvicorn', 'pydantic',
    'numpy', 'certifi', 'charset_normalizer', 'idna', 'requests',
    'urllib3', 'anyio', 'sniffio', 'h11', 'click', 'starlette',
]

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
        'CFBundleIdentifier': 'com.tinygrad.manager',
        'CFBundleVersion': '2.0.0',
        'CFBundleShortVersionString': '2.0.0',
        'NSHumanReadableCopyright': 'Copyright © 2025',
        'NSHighResolutionCapable': True,
        'LSUIElement': True,
        'LSMinimumSystemVersion': '14.0',
        'LSArchitecturePriority': ['arm64'],
        'NSAppleScriptEnabled': False,
    },
    'site_packages': True,
    'arch': 'arm64',
}

setup(
    name='TinyGradManager',
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
