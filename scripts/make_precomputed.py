#!/usr/bin/env python3
"""
Convert a 3D image stack (micro-CT / histotomography) into Neuroglancer
"precomputed" format so it can be served as a static volume for the
bioatlas.io /3d/ page.

Input:  a directory of 2D slices (TIFF/PNG, sorted by filename) or a single
        3D TIFF stack. 8-bit or 16-bit grayscale.
Output: a sharded, multiscale precomputed volume — plain static files you can
        upload to any web host / bucket that serves CORS.

Requirements:
    pip install "cloud-volume" "igneous-pipeline" tifffile numpy

Usage:
    python3 scripts/make_precomputed.py INPUT OUTPUT_DIR \
        --voxel-size 1.4 1.4 1.4   # micrometres per voxel (x y z)

    # example:
    python3 scripts/make_precomputed.py ./recon_slices/ ./volumes/33dpf/image \
        --voxel-size 1.4 1.4 1.4

Then upload OUTPUT_DIR to your storage (see README "Hosting 3D volumes"),
and add an entry in site/assets/js/volumes.js:
    image: "precomputed://https://<your-host>/volumes/33dpf/image"

Segmentation/annotation volumes work the same way: run this script on a
labeled uint16/uint32 stack with --layer-type segmentation.
"""
import argparse, os, sys
from pathlib import Path

import numpy as np


def read_stack(path):
    import tifffile
    p = Path(path)
    if p.is_dir():
        files = sorted([f for f in p.iterdir()
                        if f.suffix.lower() in (".tif", ".tiff", ".png")])
        if not files:
            sys.exit(f"no .tif/.png slices found in {p}")
        first = tifffile.imread(files[0]) if files[0].suffix.lower().startswith(".tif") \
            else _read_png(files[0])
        vol = np.zeros((len(files),) + first.shape, dtype=first.dtype)
        vol[0] = first
        for i, f in enumerate(files[1:], 1):
            vol[i] = tifffile.imread(f) if f.suffix.lower().startswith(".tif") else _read_png(f)
            if i % 50 == 0:
                print(f"  read {i}/{len(files)} slices", end="\r")
        print()
        return vol  # z, y, x
    return tifffile.imread(p)  # 3D tiff: z, y, x


def _read_png(f):
    from PIL import Image
    return np.asarray(Image.open(f).convert("I;16" if Image.open(f).mode.startswith("I") else "L"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input", help="slice directory or 3D tiff")
    ap.add_argument("output", help="output directory for the precomputed volume")
    ap.add_argument("--voxel-size", nargs=3, type=float, required=True,
                    metavar=("X", "Y", "Z"), help="voxel size in micrometres")
    ap.add_argument("--layer-type", choices=["image", "segmentation"],
                    default="image")
    ap.add_argument("--chunk", type=int, default=64, help="chunk edge (default 64)")
    args = ap.parse_args()

    from cloudvolume import CloudVolume

    vol = read_stack(args.input)          # z, y, x
    vol = np.transpose(vol, (2, 1, 0))    # -> x, y, z (cloudvolume order)
    print("volume shape (x,y,z):", vol.shape, "dtype:", vol.dtype)

    out = "file://" + str(Path(args.output).resolve())
    resolution = [int(v * 1000) for v in args.voxel_size]  # um -> nm

    info = CloudVolume.create_new_info(
        num_channels=1,
        layer_type=args.layer_type,
        data_type=str(vol.dtype),
        encoding="raw" if args.layer_type == "segmentation" else "jpeg"
                 if vol.dtype == np.uint8 else "raw",
        resolution=resolution,
        voxel_offset=[0, 0, 0],
        chunk_size=[args.chunk] * 3,
        volume_size=list(vol.shape),
    )
    cv = CloudVolume(out, info=info, compress=True)
    cv.commit_info()
    cv[:, :, :] = vol[..., np.newaxis]
    print("base scale written")

    # Downsample pyramid (needed for smooth zooming / volume rendering LOD)
    try:
        from igneous.task_creation import create_downsampling_tasks
        from taskqueue import LocalTaskQueue
        tq = LocalTaskQueue(parallel=os.cpu_count() or 4)
        tq.insert(create_downsampling_tasks(out, mip=0, num_mips=5,
                                            compress=True))
        tq.execute()
        print("downsampled 5 mips")
    except ImportError:
        print("igneous not installed — wrote base resolution only.\n"
              "pip install igneous-pipeline for the multiscale pyramid.")

    print(f"\nDone: {args.output}\n"
          "Upload this folder to your host and reference it as\n"
          f"  precomputed://https://<your-host>/{Path(args.output).name}\n"
          "in site/assets/js/volumes.js")


if __name__ == "__main__":
    main()
