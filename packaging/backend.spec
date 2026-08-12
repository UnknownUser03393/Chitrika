# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the Chitrika backend.

onedir (not onefile): the app ships ~1.6GB of ONNX models as *separate*
extraResources, and a onefile exe would decompress the whole bundle into a
temp dir on every launch. onedir runs in place, fast.

The ONNX models are deliberately NOT included here — they're read-only and
live in the install dir's resources/models/, pointed at via
EMOTION_CLASSIFIER_MODEL_DIR / EMBEDDING_MODEL_DIR from the Electron shell.
"""

import os

from PyInstaller.utils.hooks import collect_all, collect_submodules

datas: list = []
binaries: list = []
hiddenimports: list = []

# repo root = one level above this spec file. pathex must be absolute —
# relative entries are resolved against the spec dir inconsistently and the
# src package silently didn't get collected on the first build.
_REPO_ROOT = os.path.abspath(os.path.join(SPECPATH, os.pardir))

# onnxruntime + tokenizers resolve their native DLLs at runtime — collect_all
# grabs every .dll/.pyd/data file they ship. Missing these = crash on first
# model load.
for _pkg in ("onnxruntime", "tokenizers"):
    _d, _b, _h = collect_all(_pkg)
    datas += _d
    binaries += _b
    hiddenimports += _h

hiddenimports += [
    # uvicorn[standard] dynamically imports protocol/loop/lifespan plugins
    "uvicorn.logging",
    "uvicorn.loops.auto",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.http.h11_impl",
    "uvicorn.protocols.http.httptools_impl",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan.on",
    "uvicorn.lifespan.off",
    "websockets",
    "httptools",
    # apscheduler resolves jobstores/executors/triggers by string name
    "apscheduler.executors.pool",
    "apscheduler.executors.asyncio",
    "apscheduler.schedulers.background",
    "apscheduler.triggers.interval",
    "apscheduler.jobstores.memory",
]

a = Analysis(
    ["backend_launcher.py"],
    pathex=[_REPO_ROOT],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # Exclude heavy inference frameworks that get pulled in transitively:
    # onnxruntime.backend imports onnx, whose PyInstaller hook drags in torch.
    # We only call InferenceSession, which needs neither. Dropping these cuts
    # the bundle by ~500MB.
    excludes=[
        "tkinter",
        "matplotlib",
        "pytest",
        "setuptools",
        "torch",
        "torchvision",
        "torchaudio",
        "onnx",
        "optimum",
        "sklearn",
        "scipy",
        "PIL",
        "cv2",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="backend",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,  # windowed: Electron pipes stdout/stderr + file log
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="backend",
)
