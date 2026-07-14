#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import math
import os
import shutil
import subprocess
import sys
from pathlib import Path


DEFAULT_WIDTH = 3840
DEFAULT_HEIGHT = 2160
DEFAULT_FPS = 60
DEFAULT_DURATION = 3.2


def parseArgs() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Render an animated SVG to a frame-accurate 4K/60fps MP4 using Chromium and FFmpeg.'
    )
    parser.add_argument('input', type=Path, help='Input animated SVG file')
    parser.add_argument('-o', '--output', type=Path, default=Path('output.mp4'), help='Output MP4 path')
    parser.add_argument('--width', type=int, default=DEFAULT_WIDTH, help='Output width')
    parser.add_argument('--height', type=int, default=DEFAULT_HEIGHT, help='Output height')
    parser.add_argument('--fps', type=int, default=DEFAULT_FPS, help='Output frame rate')
    parser.add_argument(
        '--duration',
        type=float,
        default=DEFAULT_DURATION,
        help='Video duration in seconds; 3.2s includes a short final hold for this SVG',
    )
    parser.add_argument(
        '--fit',
        choices=('contain', 'cover', 'stretch'),
        default='contain',
        help='How the SVG fits into the video frame',
    )
    parser.add_argument(
        '--background',
        default='#070B14',
        help='Page/background color used outside the SVG viewBox',
    )
    parser.add_argument(
        '--encoder',
        choices=('auto', 'nvenc', 'x264'),
        default='auto',
        help='Video encoder; auto prefers NVIDIA NVENC when available',
    )
    parser.add_argument('--crf', type=int, default=16, help='x264 CRF quality, lower is better')
    parser.add_argument('--cq', type=int, default=16, help='NVENC constant-quality value, lower is better')
    parser.add_argument('--chromium', type=Path, help='Optional Chromium/Chrome executable path')
    return parser.parse_args()


def validateArgs(args: argparse.Namespace) -> None:
    if not args.input.is_file():
        raise SystemExit(f'Input SVG not found: {args.input}')
    if args.input.suffix.lower() != '.svg':
        raise SystemExit('Input must be an .svg file')
    if args.width <= 0 or args.height <= 0 or args.fps <= 0 or args.duration <= 0:
        raise SystemExit('width, height, fps and duration must be positive')
    if args.width % 2 or args.height % 2:
        raise SystemExit('width and height must both be even for yuv420p MP4 output')
    if shutil.which('ffmpeg') is None:
        raise SystemExit('ffmpeg is not in PATH')


def ffmpegHasEncoder(name: str) -> bool:
    result = subprocess.run(
        ['ffmpeg', '-hide_banner', '-encoders'],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding='utf-8',
        errors='replace',
        check=False,
    )
    return name in result.stdout


def hasWorkingNvidiaGpu() -> bool:
    nvidiaSmi = shutil.which('nvidia-smi')
    if nvidiaSmi is None:
        return False
    result = subprocess.run(
        [nvidiaSmi, '-L'],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.returncode == 0


def chooseEncoder(requested: str) -> str:
    if requested == 'nvenc':
        if not ffmpegHasEncoder('h264_nvenc'):
            raise SystemExit('This FFmpeg build does not provide h264_nvenc')
        return 'nvenc'
    if requested == 'x264':
        if not ffmpegHasEncoder('libx264'):
            raise SystemExit('This FFmpeg build does not provide libx264')
        return 'x264'
    if ffmpegHasEncoder('h264_nvenc') and hasWorkingNvidiaGpu():
        return 'nvenc'
    if ffmpegHasEncoder('libx264'):
        return 'x264'
    raise SystemExit('FFmpeg has neither h264_nvenc nor libx264')


def buildFfmpegCommand(args: argparse.Namespace, encoder: str) -> list[str]:
    command = [
        'ffmpeg',
        '-y',
        '-hide_banner',
        '-loglevel', 'warning',
        '-f', 'image2pipe',
        '-vcodec', 'png',
        '-framerate', str(args.fps),
        '-i', 'pipe:0',
        '-an',
    ]

    if encoder == 'nvenc':
        command.extend([
            '-c:v', 'h264_nvenc',
            '-preset', 'p7',
            '-tune', 'hq',
            '-rc', 'vbr',
            '-cq', str(args.cq),
            '-b:v', '0',
            '-profile:v', 'high',
        ])
    else:
        command.extend([
            '-c:v', 'libx264',
            '-preset', 'slow',
            '-crf', str(args.crf),
            '-profile:v', 'high',
        ])

    command.extend([
        '-pix_fmt', 'yuv420p',
        '-colorspace', 'bt709',
        '-color_primaries', 'bt709',
        '-color_trc', 'bt709',
        '-movflags', '+faststart',
        '-r', str(args.fps),
        str(args.output),
    ])
    return command


def buildHtml(svg: str, fit: str, background: str) -> str:
    if fit == 'stretch':
        svgSizing = 'width:100vw;height:100vh;'
        preserveAspectRatioScript = "svg.setAttribute('preserveAspectRatio', 'none');"
    elif fit == 'cover':
        svgSizing = 'width:100vw;height:100vh;'
        preserveAspectRatioScript = "svg.setAttribute('preserveAspectRatio', 'xMidYMid slice');"
    else:
        svgSizing = 'width:100vw;height:100vh;'
        preserveAspectRatioScript = "svg.setAttribute('preserveAspectRatio', 'xMidYMid meet');"

    return f'''<!doctype html>
<html>
<head>
<meta charset="utf-8">
<style>
html, body {{
    margin: 0;
    width: 100%;
    height: 100%;
    overflow: hidden;
    background: {background};
}}
body {{
    display: grid;
    place-items: center;
}}
body > svg {{
    display: block;
    {svgSizing}
}}
</style>
</head>
<body>
{svg}
<script>
(() => {{
    const svg = document.querySelector('svg');
    {preserveAspectRatioScript}

    window.__setRenderTime = (seconds) => {{
        if (typeof svg.pauseAnimations === 'function') svg.pauseAnimations();
        if (typeof svg.setCurrentTime === 'function') svg.setCurrentTime(seconds);

        for (const animation of document.getAnimations({{ subtree: true }})) {{
            animation.pause();
            animation.currentTime = seconds * 1000;
        }}
    }};

    window.__setRenderTime(0);
}})();
</script>
</body>
</html>'''


def findSystemChromium() -> Path | None:
    executableNames = (
        'msedge', 'msedge.exe',
        'chrome', 'chrome.exe',
        'chromium', 'chromium.exe',
        'google-chrome', 'google-chrome-stable',
    )
    for name in executableNames:
        path = shutil.which(name)
        if path:
            return Path(path)

    roots = [
        os.environ.get('PROGRAMFILES'),
        os.environ.get('PROGRAMFILES(X86)'),
        os.environ.get('LOCALAPPDATA'),
    ]
    relativePaths = (
        Path('Microsoft/Edge/Application/msedge.exe'),
        Path('Google/Chrome/Application/chrome.exe'),
        Path('Chromium/Application/chrome.exe'),
    )
    for root in roots:
        if not root:
            continue
        for relativePath in relativePaths:
            candidate = Path(root) / relativePath
            if candidate.is_file():
                return candidate
    return None


async def launchChromium(playwright, requestedPath: Path | None, launchArgs: list[str]):
    if requestedPath:
        return await playwright.chromium.launch(
            headless=True,
            executable_path=str(requestedPath),
            args=launchArgs,
        )

    try:
        return await playwright.chromium.launch(headless=True, args=launchArgs)
    except Exception as bundledError:
        systemChromium = findSystemChromium()
        if systemChromium is None:
            raise SystemExit(
                'Chromium was not found. Install the Playwright browser with:\n'
                '  python -m playwright install chromium\n'
                'or pass --chromium path/to/chrome.exe'
            ) from bundledError

        print(f'[+] browser : {systemChromium}')
        return await playwright.chromium.launch(
            headless=True,
            executable_path=str(systemChromium),
            args=launchArgs,
        )


async def render(args: argparse.Namespace) -> None:
    try:
        from playwright.async_api import async_playwright
    except ImportError as error:
        raise SystemExit(
            'Playwright is not installed. Run:\n'
            '  python -m pip install playwright\n'
            '  python -m playwright install chromium'
        ) from error

    svg = args.input.read_text(encoding='utf-8-sig')
    html = buildHtml(svg, args.fit, args.background)
    encoder = chooseEncoder(args.encoder)
    args.output.parent.mkdir(parents=True, exist_ok=True)

    ffmpegCommand = buildFfmpegCommand(args, encoder)
    totalFrames = math.ceil(args.duration * args.fps)
    print(f'[+] encoder : {encoder}')
    print(f'[+] frames  : {totalFrames}')
    print(f'[+] output  : {args.output.resolve()}')

    ffmpeg: subprocess.Popen[bytes] | None = None

    try:
        async with async_playwright() as playwright:
            chromiumArgs = [
                '--hide-scrollbars',
                '--force-color-profile=srgb',
                '--disable-background-timer-throttling',
                '--disable-renderer-backgrounding',
                '--disable-backgrounding-occluded-windows',
            ]
            browser = await launchChromium(playwright, args.chromium, chromiumArgs)
            context = await browser.new_context(
                viewport={'width': args.width, 'height': args.height},
                device_scale_factor=1,
                color_scheme='dark',
                reduced_motion='no-preference',
            )
            page = await context.new_page()
            await page.set_content(html, wait_until='load')
            await page.evaluate('document.fonts.ready')

            ffmpeg = subprocess.Popen(ffmpegCommand, stdin=subprocess.PIPE)
            if ffmpeg.stdin is None:
                raise SystemExit('Failed to open FFmpeg stdin')

            for frameIndex in range(totalFrames):
                timeSeconds = frameIndex / args.fps
                await page.evaluate('(t) => window.__setRenderTime(t)', timeSeconds)
                frame = await page.screenshot(
                    type='png',
                    full_page=False,
                    omit_background=False,
                    timeout=0,
                )
                ffmpeg.stdin.write(frame)

                if frameIndex == 0 or (frameIndex + 1) % args.fps == 0 or frameIndex + 1 == totalFrames:
                    print(f'[{frameIndex + 1:4d}/{totalFrames}] {timeSeconds:6.3f}s')

            await context.close()
            await browser.close()
    except BrokenPipeError as error:
        raise SystemExit('FFmpeg stopped while receiving frames') from error
    finally:
        if ffmpeg is not None and ffmpeg.stdin is not None:
            try:
                ffmpeg.stdin.close()
            except (BrokenPipeError, OSError):
                pass

    if ffmpeg is None:
        raise SystemExit('FFmpeg was not started')

    returnCode = ffmpeg.wait()
    if returnCode != 0:
        raise SystemExit(f'FFmpeg exited with code {returnCode}')

    print('[done] render complete')


def main() -> None:
    args = parseArgs()
    validateArgs(args)
    try:
        asyncio.run(render(args))
    except KeyboardInterrupt:
        raise SystemExit('\nInterrupted')


if __name__ == '__main__':
    main()
