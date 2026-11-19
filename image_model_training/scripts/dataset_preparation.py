"""
TruthLens Dataset Acquisition & Preparation
============================================
Downloads a subset of GenImage via Hugging Face (nebula/GenImage-arrow),
validates images, removes duplicates, splits into train/val/test,
and generates CSV manifests + dataset report.

GenImage License: Apache-2.0 (research & academic use)
Source: https://github.com/GenImage-Dataset/GenImage
HF Mirror: nebula/GenImage-arrow

Training generators:   Stable Diffusion 1.4 + BigGAN   (seen generators)
Unseen test generator: Midjourney                        (held-out for generalisation test)
"""
import os
import sys
import json
import csv
import hashlib
import random
import shutil
from pathlib import Path
from datetime import datetime, timezone

# ---- Configuration ----
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"

TRAIN_GENERATORS = ["sd14", "biggan"]
TEST_UNSEEN_GENERATOR = "midjourney"

# Target counts per class (real / ai_generated)
TARGET_TRAIN_PER_CLASS = 2400
TARGET_VAL_PER_CLASS = 600
TARGET_TEST_SEEN_PER_CLASS = 500      # from training generators
TARGET_TEST_UNSEEN_PER_CLASS = 500    # from held-out midjourney

SEED = 42
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff"}


def sha256_file(filepath: str) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def validate_image(filepath: str) -> bool:
    """Check that the file is a valid, openable image."""
    try:
        from PIL import Image
        with Image.open(filepath) as img:
            img.verify()
        return True
    except Exception:
        return False


def download_genimage_subset():
    """
    Download GenImage subsets from Hugging Face using the datasets library.
    Downloads only the generators we need, keeping download size manageable.
    """
    print("\n=== GenImage Dataset Acquisition ===")
    print(f"Training generators: {TRAIN_GENERATORS}")
    print(f"Unseen test generator: {TEST_UNSEEN_GENERATOR}")

    try:
        from datasets import load_dataset
    except ImportError:
        print("ERROR: 'datasets' library not found. Install with: pip install datasets")
        sys.exit(1)

    RAW_DIR.mkdir(parents=True, exist_ok=True)

    all_generators = TRAIN_GENERATORS + [TEST_UNSEEN_GENERATOR]
    for gen in all_generators:
        gen_dir = RAW_DIR / gen
        if gen_dir.exists() and len(list(gen_dir.glob("*/*"))) > 100:
            print(f"  [{gen}] Already downloaded ({len(list(gen_dir.glob('*/*')))} files), skipping.")
            continue

        print(f"  [{gen}] Downloading from nebula/GenImage-arrow...")
        gen_dir.mkdir(parents=True, exist_ok=True)

        for split_name in ["train", "test"]:
            config_name = f"{gen}-{split_name}"
            try:
                ds = load_dataset("nebula/GenImage-arrow", config_name, split=split_name, trust_remote_code=True)
                print(f"    Config '{config_name}': {len(ds)} samples loaded")

                class_dirs = {0: gen_dir / "real", 1: gen_dir / "ai"}
                for d in class_dirs.values():
                    d.mkdir(parents=True, exist_ok=True)

                saved = 0
                for idx, sample in enumerate(ds):
                    label = sample.get("label", sample.get("labels", None))
                    image = sample.get("image", None)
                    if image is None or label is None:
                        continue

                    dest = class_dirs[int(label)] / f"{gen}_{split_name}_{idx:06d}.png"
                    if not dest.exists():
                        image.save(str(dest), format="PNG")
                        saved += 1

                    # Limit downloads to keep things manageable
                    max_per_split = 2000
                    if saved >= max_per_split:
                        break

                print(f"    Saved {saved} images for {config_name}")
                # Free memory
                del ds
                import gc; gc.collect()

            except Exception as e:
                print(f"    WARNING: Could not load '{config_name}': {e}")

    print("Dataset acquisition complete.")


def prepare_dataset():
    """Validate, deduplicate, split, and generate CSV manifests."""
    print("\n=== Dataset Preparation & Validation ===")
    random.seed(SEED)

    all_entries = []  # (filepath, label, generator, sha256)
    hash_set = set()
    corrupted = 0
    duplicates = 0

    for gen_dir in sorted(RAW_DIR.iterdir()):
        if not gen_dir.is_dir():
            continue
        generator = gen_dir.name

        for class_dir in sorted(gen_dir.iterdir()):
            if not class_dir.is_dir():
                continue
            label_name = class_dir.name  # "real" or "ai"
            label = 0 if label_name == "real" else 1

            for img_path in sorted(class_dir.iterdir()):
                if img_path.suffix.lower() not in IMAGE_EXTENSIONS:
                    continue

                if not validate_image(str(img_path)):
                    corrupted += 1
                    continue

                h = sha256_file(str(img_path))
                if h in hash_set:
                    duplicates += 1
                    continue
                hash_set.add(h)

                all_entries.append({
                    "filepath": str(img_path),
                    "label": label,
                    "label_name": "REAL" if label == 0 else "AI_GENERATED",
                    "generator": generator,
                    "sha256": h,
                })

    print(f"  Total valid unique images: {len(all_entries)}")
    print(f"  Corrupted files removed: {corrupted}")
    print(f"  Duplicate files removed: {duplicates}")

    # Split by generator role
    train_gen_entries = [e for e in all_entries if e["generator"] in TRAIN_GENERATORS]
    unseen_gen_entries = [e for e in all_entries if e["generator"] == TEST_UNSEEN_GENERATOR]

    # Sub-split training generators into real/ai
    train_real = [e for e in train_gen_entries if e["label"] == 0]
    train_ai   = [e for e in train_gen_entries if e["label"] == 1]
    unseen_real = [e for e in unseen_gen_entries if e["label"] == 0]
    unseen_ai   = [e for e in unseen_gen_entries if e["label"] == 1]

    random.shuffle(train_real)
    random.shuffle(train_ai)
    random.shuffle(unseen_real)
    random.shuffle(unseen_ai)

    print(f"\n  Training generators pool: {len(train_real)} real, {len(train_ai)} AI")
    print(f"  Unseen generator pool:    {len(unseen_real)} real, {len(unseen_ai)} AI")

    # Allocate splits from training generators
    # Train: TARGET_TRAIN_PER_CLASS, Val: TARGET_VAL_PER_CLASS, Test-seen: TARGET_TEST_SEEN_PER_CLASS
    needed_per_class = TARGET_TRAIN_PER_CLASS + TARGET_VAL_PER_CLASS + TARGET_TEST_SEEN_PER_CLASS

    actual_real = min(len(train_real), needed_per_class)
    actual_ai = min(len(train_ai), needed_per_class)
    actual_min = min(actual_real, actual_ai)

    # Proportional allocation
    ratio_train = TARGET_TRAIN_PER_CLASS / needed_per_class
    ratio_val = TARGET_VAL_PER_CLASS / needed_per_class
    # ratio_test = remainder

    n_train = int(actual_min * ratio_train)
    n_val = int(actual_min * ratio_val)
    n_test_seen = actual_min - n_train - n_val

    print(f"\n  Allocated per class: train={n_train}, val={n_val}, test_seen={n_test_seen}")

    train_set = train_real[:n_train] + train_ai[:n_train]
    val_set = train_real[n_train:n_train+n_val] + train_ai[n_train:n_train+n_val]
    test_seen_set = train_real[n_train+n_val:n_train+n_val+n_test_seen] + \
                    train_ai[n_train+n_val:n_train+n_val+n_test_seen]

    # Unseen-generator test set
    n_unseen = min(TARGET_TEST_UNSEEN_PER_CLASS, len(unseen_real), len(unseen_ai))
    test_unseen_set = unseen_real[:n_unseen] + unseen_ai[:n_unseen]

    test_set = test_seen_set + test_unseen_set

    random.shuffle(train_set)
    random.shuffle(val_set)
    random.shuffle(test_set)

    # Leakage check
    train_hashes = {e["sha256"] for e in train_set}
    val_hashes = {e["sha256"] for e in val_set}
    test_hashes = {e["sha256"] for e in test_set}

    tv_leak = train_hashes & val_hashes
    tt_leak = train_hashes & test_hashes
    vt_leak = val_hashes & test_hashes

    if tv_leak or tt_leak or vt_leak:
        print(f"  WARNING: Data leakage detected! train∩val={len(tv_leak)}, train∩test={len(tt_leak)}, val∩test={len(vt_leak)}")
    else:
        print("  ✓ No data leakage between train/val/test splits.")

    # Write CSVs
    for name, entries in [("train", train_set), ("val", val_set), ("test", test_set)]:
        csv_path = DATA_DIR / f"{name}.csv"
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["filepath", "label", "label_name", "generator", "sha256"])
            writer.writeheader()
            writer.writerows(entries)
        print(f"  Wrote {csv_path.name}: {len(entries)} samples")

    # Class distribution summary
    def class_dist(entries):
        d = {}
        for e in entries:
            key = f"{e['label_name']} ({e['generator']})"
            d[key] = d.get(key, 0) + 1
        return d

    # Dataset report
    report = {
        "dataset_name": "GenImage (Subset)",
        "source": "nebula/GenImage-arrow (Hugging Face mirror of GenImage)",
        "original_source": "https://github.com/GenImage-Dataset/GenImage",
        "license": "Apache-2.0",
        "download_date": datetime.now(timezone.utc).isoformat(),
        "training_generators": TRAIN_GENERATORS,
        "unseen_test_generator": TEST_UNSEEN_GENERATOR,
        "total_valid_unique_images": len(all_entries),
        "corrupted_removed": corrupted,
        "duplicates_removed": duplicates,
        "splits": {
            "train": {"count": len(train_set), "distribution": class_dist(train_set)},
            "val": {"count": len(val_set), "distribution": class_dist(val_set)},
            "test": {"count": len(test_set), "distribution": class_dist(test_set)},
        },
        "leakage_check": {
            "train_val_overlap": len(tv_leak),
            "train_test_overlap": len(tt_leak),
            "val_test_overlap": len(vt_leak),
        },
        "seed": SEED,
    }

    report_path = DATA_DIR / "dataset_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"\n  Dataset report saved to: {report_path}")

    return report


if __name__ == "__main__":
    download_genimage_subset()
    report = prepare_dataset()
    print("\n=== Dataset Summary ===")
    print(json.dumps(report["splits"], indent=2))
