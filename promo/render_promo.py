from pathlib import Path
import subprocess

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "promo" / "recordings"
SOURCE_VIDEO = OUTPUT_DIR / "chitrika-promo-4k-source.webm"
FINAL_VIDEO = OUTPUT_DIR / "chitrika-promo-4k60.mp4"
EDGE = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
PROMO_URL = "http://127.0.0.1:8090/promo/concept/"
CAPTURE_DURATION_MS = 63_000


def record_source() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            executable_path=str(EDGE),
        )
        context = browser.new_context(
            viewport={"width": 3840, "height": 2160},
            screen={"width": 3840, "height": 2160},
            locale="zh-CN",
            record_video_dir=str(OUTPUT_DIR),
            record_video_size={"width": 3840, "height": 2160},
        )
        page = context.new_page()
        page.goto(PROMO_URL, wait_until="networkidle")
        page.wait_for_timeout(CAPTURE_DURATION_MS)
        video = page.video
        context.close()
        recorded_path = Path(video.path())
        browser.close()

    recorded_path.replace(SOURCE_VIDEO)


def encode_4k60() -> None:
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(SOURCE_VIDEO),
            "-vf",
            "fps=60",
            "-c:v",
            "h264_mf",
            "-b:v",
            "35M",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(FINAL_VIDEO),
        ],
        check=True,
    )


if __name__ == "__main__":
    record_source()
    encode_4k60()
    print(FINAL_VIDEO)
