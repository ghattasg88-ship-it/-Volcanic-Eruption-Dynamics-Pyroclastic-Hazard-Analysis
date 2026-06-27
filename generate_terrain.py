#!/usr/bin/env python3
"""
generate_terrain.py
==================
Standalone utility to generate and export the procedural volcano heightfield
as a NumPy .npy array and a greyscale PNG heightmap (for inspection or reuse
in other tools). Runs WITHOUT Panda3D so it can be used in headless CI.

Usage:
    python scripts/generate_terrain.py --out data/terrain --resolution 256
"""

import argparse
import os

import numpy as np


def build_heightfield(size, res, summit, crater_radius):
    half = size / 2.0
    xs = np.linspace(-half, half, res)
    ys = np.linspace(-half, half, res)
    X, Y = np.meshgrid(xs, ys)
    R = np.sqrt(X ** 2 + Y ** 2)

    cone = summit * np.exp(-(R / (half * 0.42)) ** 2)
    crater = np.where(R < crater_radius,
                      -0.35 * summit * (1 - (R / crater_radius) ** 2), 0.0)
    theta = np.arctan2(Y, X)
    valleys = 90.0 * np.sin(8 * theta) * np.exp(-(R / (half * 0.5)) ** 2)
    rough = (60.0 * np.sin(X / 1500.0) * np.cos(Y / 1700.0) +
             30.0 * np.sin(X / 600.0 + 1.3) * np.cos(Y / 550.0))
    return (cone + crater + valleys + rough * (R / half)).astype(np.float32)


def save_png(height, path):
    """Write a normalised 8-bit greyscale PNG without external imaging libs."""
    h = height - height.min()
    h = (h / max(h.max(), 1e-6) * 255).astype(np.uint8)
    # Minimal PNG writer (greyscale) via zlib + struct
    import struct, zlib

    def chunk(tag, data):
        c = tag + data
        return (struct.pack(">I", len(data)) + c +
                struct.pack(">I", zlib.crc32(c) & 0xffffffff))

    H, W = h.shape
    raw = bytearray()
    for row in h:
        raw.append(0)              # filter type 0
        raw.extend(row.tobytes())
    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 0, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    png += chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/terrain")
    ap.add_argument("--size", type=float, default=20000.0)
    ap.add_argument("--resolution", type=int, default=256)
    ap.add_argument("--summit", type=float, default=2800.0)
    ap.add_argument("--crater", type=float, default=400.0)
    args = ap.parse_args()

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    h = build_heightfield(args.size, args.resolution, args.summit, args.crater)

    np.save(args.out + ".npy", h)
    save_png(h, args.out + ".png")

    print(f"Heightfield {h.shape}  range [{h.min():.1f}, {h.max():.1f}] m")
    print(f"Saved {args.out}.npy and {args.out}.png")


if __name__ == "__main__":
    main()
