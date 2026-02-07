# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for VoiceInput macOS app.

Build:
    cd voice-input-tool
    pyinstaller VoiceInput.spec

Requirements:
    pip install pyinstaller pyinstaller-hooks-contrib

Notes:
    - The ASR model (~1.2 GB) is NOT bundled. It downloads automatically
      on first launch via Hugging Face Hub to ~/.cache/huggingface/.
    - The resulting .app is still large (~2-3 GB) due to torch + transformers.
    - UPX compression is disabled as it causes issues on macOS ARM64.
"""

import os
from PyInstaller.utils.hooks import (
    collect_all,
    collect_data_files,
    collect_dynamic_libs,
    collect_submodules,
)

# ── Collect packages without built-in PyInstaller hooks ────────

# qwen_asr: the ASR model wrapper (no built-in hook)
qwen_datas, qwen_binaries, qwen_hiddenimports = collect_all('qwen_asr')

# accelerate: model device management (may lack a complete hook)
accel_datas, accel_binaries, accel_hiddenimports = collect_all('accelerate')

# sounddevice: needs the PortAudio shared library from _sounddevice_data
sd_datas = collect_data_files('_sounddevice_data')
sd_binaries = collect_dynamic_libs('sounddevice')

# ── Aggregate datas / binaries / hidden-imports ────────────────

datas = qwen_datas + accel_datas + sd_datas

binaries = qwen_binaries + accel_binaries + sd_binaries

hiddenimports = qwen_hiddenimports + accel_hiddenimports + [
    # pynput macOS-specific backends
    'pynput.keyboard._darwin',
    'pynput.mouse._darwin',
    # Rust-based fast tokenizer
    'tokenizers',
    # safetensors for efficient model loading
    'safetensors',
    'safetensors.torch',
    # Hugging Face Hub (model download on first launch)
    'huggingface_hub',
    # SentencePiece tokenizer
    'sentencepiece',
    # Clipboard / input automation
    'pyperclip',
    'pyautogui',
]

# ── Exclusions (reduce bundle size on macOS) ───────────────────

excludes = [
    # CUDA/distributed not needed on macOS (use MPS or CPU)
    'torch.cuda.nccl',
    'torch.distributed',
    # Dev / profiling tools
    'torch.testing',
    'torch.utils.tensorboard',
    'torch.utils.bottleneck',
    'torch.utils.benchmark',
    # GUI toolkits we don't use
    'tkinter',
    'matplotlib',
    # IPython / Jupyter
    'IPython',
    'jupyter',
    'notebook',
    # Test frameworks
    'pytest',
    '_pytest',
]

# ── Analysis ───────────────────────────────────────────────────

a = Analysis(
    ['run.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
)

# ── Build artefacts ────────────────────────────────────────────

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,     # one-dir mode
    name='VoiceInput',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,                 # UPX not recommended on macOS
    console=False,             # windowed (no terminal)
    disable_windowed_traceback=False,
    argv_emulation=True,       # handle macOS open-file events
    target_arch=None,          # build for current arch
    codesign_identity=None,    # set to your ID for signing
    entitlements_file=None,    # set to scripts/entitlements.plist if signing
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='VoiceInput',
)

# ── macOS .app bundle ──────────────────────────────────────────

icon_path = 'assets/icon.icns'

app = BUNDLE(
    coll,
    name='VoiceInput.app',
    icon=icon_path if os.path.exists(icon_path) else None,
    bundle_identifier='com.desktopwhisper.voiceinput',
    version='0.1.0',
    info_plist={
        'CFBundleName': 'VoiceInput',
        'CFBundleDisplayName': 'VoiceInput — 語音輸入',
        'CFBundleShortVersionString': '0.1.0',
        'CFBundleVersion': '0.1.0',
        # Privacy permission descriptions (shown in system prompts)
        'NSMicrophoneUsageDescription':
            '語音輸入需要使用麥克風來錄製語音。',
        'NSAppleEventsUsageDescription':
            '語音輸入需要控制其他應用程式來貼上文字。',
        # Menu-bar-only app (no Dock icon)
        'LSUIElement': True,
        'NSHighResolutionCapable': True,
    },
)
