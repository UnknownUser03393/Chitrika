"""Generate packaging/icon.png — a 256x256 app icon, pure Python (no deps).

Draws a dark-navy rounded square with an infinity-knot in a coral→mint
gradient. Written by hand as RGBA pixels → PNG via zlib/struct.
"""

from __future__ import annotations

import struct
import zlib
from pathlib import Path

SIZE = 256
CORNER = 52  # rounded-corner radius
OUT = Path(__file__).resolve().parent / "icon.png"


def smoothstep(edge: float, width: float, d: float) -> float:
    """0..1 coverage of a signed distance *d* across a transition band."""
    x = (edge - d) / max(width, 1e-6)
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def rounded_square_alpha(x: int, y: int) -> float:
    dx = min(x, SIZE - 1 - x)
    dy = min(y, SIZE - 1 - y)
    if dx < CORNER and dy < CORNER:
        # distance to the corner circle center
        cx, cy = CORNER, CORNER
        d = ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5
        return smoothstep(CORNER, 1.6, d)
    return 1.0


def knot_alpha(x: float, y: float) -> tuple[float, float]:
    """Signed coverage + gradient t for the infinity knot (two circles)."""
    centers = ((86.0, 128.0), (170.0, 128.0))
    radii = (46.0, 46.0)
    best = -1e9
    t = 0.0
    for i, (cx, cy) in enumerate(centers):
        d = ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5
        if -d > best:
            best = -d
            t = 0.0 if i == 0 else 1.0
    # boundary distance of the union: max of (radius - dist) is wrong for
    # union, so approximate with the min of negative distances of each circle.
    d1 = ((x - centers[0][0]) ** 2 + (y - centers[0][1]) ** 2) ** 0.5
    d2 = ((x - centers[1][0]) ** 2 + (y - centers[1][1]) ** 2) ** 0.5
    dist = min(d1, d2)
    coverage = smoothstep(radii[0], 1.6, dist)
    return coverage, t


def pixel(x: int, y: int) -> tuple[int, int, int, int]:
    bg = (0x0E, 0x16, 0x21)  # Chitrika dark navy
    a_bg = rounded_square_alpha(x, y)
    cov, t = knot_alpha(x + 0.5, y + 0.5)
    # coral -> mint gradient
    c = tuple(round((1 - t) * a + t * b) for a, b in
              zip((0xEC, 0x84, 0x68), (0x5E, 0xC9, 0xB0)))
    if cov <= 0:
        return (bg[0], bg[1], bg[2], round(255 * a_bg))
    # blend knot over bg inside the square
    r = round(c[0] * cov + bg[0] * (1 - cov))
    g = round(c[1] * cov + bg[1] * (1 - cov))
    b = round(c[2] * cov + bg[2] * (1 - cov))
    return (r, g, b, round(255 * a_bg))


def chunk(tag: bytes, data: bytes) -> bytes:
    return (struct.pack(">I", len(data)) + tag + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))


def main() -> None:
    raw = bytearray()
    for y in range(SIZE):
        raw.append(0)  # filter: None
        for x in range(SIZE):
            raw.extend(pixel(x, y))
    png = (b"\x89PNG\r\n\x1a\n"
           + chunk(b"IHDR", struct.pack(">IIBBBBB", SIZE, SIZE, 8, 6, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
           + chunk(b"IEND", b""))
    OUT.write_bytes(png)
    print(f"wrote {OUT} ({len(png)} bytes)")


if __name__ == "__main__":
    main()
