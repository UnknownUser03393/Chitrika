import base64
import os
from pathlib import Path
import subprocess

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "promo" / "recordings"
FRAMES_DIR = OUTPUT_DIR / "chitrika-promo-2k-frames"
EDGE = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
PROMO_URL = "http://127.0.0.1:8090/promo/concept/?capture=1"
CAPTURE_DURATION_MS = 63_000
FPS = int(os.environ.get("PROMO_FPS", "60"))
FINAL_VIDEO = OUTPUT_DIR / f"chitrika-promo-2k{FPS}-native.mp4"


def clear_frames() -> None:
    FRAMES_DIR.mkdir(parents=True, exist_ok=True)
    for frame in FRAMES_DIR.glob("*.jpg"):
        frame.unlink()


def record_frames() -> int:
    clear_frames()
    state = {
        "active": False,
        "count": 0,
        "started_at": None,
        "next_frame_at": 0.0,
    }

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            executable_path=str(EDGE),
        )
        context = browser.new_context(
            viewport={"width": 2560, "height": 1440},
            screen={"width": 2560, "height": 1440},
            locale="zh-CN",
        )
        page = context.new_page()
        page.goto(PROMO_URL, wait_until="networkidle")
        session = context.new_cdp_session(page)

        def save_frame(params: dict) -> None:
            try:
                if state["active"]:
                    timestamp = params["metadata"]["timestamp"]
                    if state["started_at"] is None:
                        state["started_at"] = timestamp
                    elapsed = timestamp - state["started_at"]
                    if elapsed >= state["next_frame_at"]:
                        image = base64.b64decode(params["data"])
                        while elapsed >= state["next_frame_at"]:
                            path = FRAMES_DIR / f"{state['count']:06d}.jpg"
                            path.write_bytes(image)
                            state["count"] += 1
                            state["next_frame_at"] += 1 / FPS
                session.send(
                    "Page.screencastFrameAck",
                    {"sessionId": params["sessionId"]},
                )
            except Exception:
                if state["active"]:
                    raise

        session.on("Page.screencastFrame", save_frame)
        session.send(
            "Page.startScreencast",
            {
                "format": "jpeg",
                "quality": 96,
                "maxWidth": 2560,
                "maxHeight": 1440,
                "everyNthFrame": 1,
            },
        )
        page.evaluate("window.startPromoPlayback()")
        state["active"] = True
        page.wait_for_timeout(CAPTURE_DURATION_MS)
        state["active"] = False
        session.send("Page.stopScreencast")
        page.wait_for_timeout(250)
        context.close()
        browser.close()

    return state["count"]


def encode_frames() -> None:
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-framerate",
            str(FPS),
            "-i",
            str(FRAMES_DIR / "%06d.jpg"),
            "-vf",
            "scale=in_range=pc:out_range=tv,format=nv12",
            "-c:v",
            "h264_mf",
            "-b:v",
            "35M",
            "-pix_fmt",
            "nv12",
            "-movflags",
            "+faststart",
            str(FINAL_VIDEO),
        ],
        check=True,
    )


if __name__ == "__main__":
    frame_count = record_frames()
    print(f"Captured {frame_count} frames")
    encode_frames()
    print(FINAL_VIDEO)
