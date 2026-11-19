"""
TruthLens GenImage Extraction & Dataset Splitter
=================================================
Extracts real and AI-generated image samples directly from the downloaded
Arrow shards of GenImage (nebula/GenImage-arrow).

Partitions:
- Training generators: BigGAN + ADM (Seen generators)
- Unseen generator: Midjourney (Held-out generator for test set)
- Real images: authentic ImageNet photographs from GenImage 'nature' set

Deduplicates using SHA-256, validates image integrity, partitions without leakage,
and writes data/train.csv, data/val.csv, data/test.csv and data/dataset_report.json.
"""
import os
import sys
import io
import csv
import json
import random
import hashlib
from pathlib import Path
from datetime import datetime, timezone
from PIL import Image
import pyarrow.ipc as ipc

PROJECT_ROOT = Path("D:/Truthlens/image_model_training")
DATA_DIR = PROJECT_ROOT / "data"
IMAGES_DIR = DATA_DIR / "images"

# Target allocation for balanced, robust CPU training
# Train: 3,000 images (1,500 Real + 1,500 AI from BigGAN & ADM)
# Val:     800 images (  400 Real +   400 AI from BigGAN & ADM)
# Test:  1,000 images (  500 Real +   250 Seen AI [BigGAN/ADM] + 250 Unseen AI [Midjourney])
TARGET_TRAIN_REAL = 1500
TARGET_TRAIN_AI = 1500
TARGET_VAL_REAL = 400
TARGET_VAL_AI = 400
TARGET_TEST_REAL = 500
TARGET_TEST_SEEN_AI = 250
TARGET_TEST_UNSEEN_AI = 250

SEED = 42

CACHE_DIR = Path(os.path.expanduser("~/.cache/huggingface/hub/datasets--nebula--GenImage-arrow/snapshots/3f4b9f921a673be09a93b335ed728cea0c6ecf33/data/test"))

SHARDS = {
    "BigGAN_0": CACHE_DIR / "BigGAN/data-00000-of-00002.arrow",
    "BigGAN_1": CACHE_DIR / "BigGAN/data-00001-of-00002.arrow",
    "ADM_2":    CACHE_DIR / "ADM/data-00002-of-00003.arrow",
    "MJ_17":    CACHE_DIR / "Midjourney/data-00017-of-00019.arrow",
    "MJ_18":    CACHE_DIR / "Midjourney/data-00018-of-00019.arrow",
}


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def extract_and_prepare():
    print("=" * 60)
    print("TruthLens GenImage Extraction & Dataset Manifest Generation")
    print("=" * 60)

    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    for sub in ["real", "ai_biggan", "ai_adm", "ai_midjourney"]:
        (IMAGES_DIR / sub).mkdir(parents=True, exist_ok=True)

    random.seed(SEED)

    real_entries = []
    biggan_entries = []
    adm_entries = []
    midjourney_entries = []
    seen_hashes = set()

    # 1. Extract Real images from BigGAN shard 0 & shard 1
    print("\n[1/4] Extracting Real images from GenImage...")
    for shard_key in ["BigGAN_0", "BigGAN_1"]:
        shard_path = SHARDS[shard_key]
        if not shard_path.exists():
            continue
        with open(shard_path, "rb") as f:
            reader = ipc.RecordBatchStreamReader(f)
            for batch in reader:
                d = batch.to_pydict()
                for i in range(len(d["label"])):
                    if d["label"][i] == 0:  # Real
                        img_bytes = d["image"][i]
                        h = sha256_bytes(img_bytes)
                        if h in seen_hashes:
                            continue
                        seen_hashes.add(h)

                        # Validate can open
                        try:
                            im = Image.open(io.BytesIO(img_bytes))
                            im.verify()
                        except Exception:
                            continue

                        fn = f"real_{len(real_entries):06d}.jpg"
                        out_path = IMAGES_DIR / "real" / fn
                        with open(out_path, "wb") as out_f:
                            out_f.write(img_bytes)

                        real_entries.append({
                            "filepath": str(out_path).replace("\\", "/"),
                            "label": 0,
                            "label_name": "REAL",
                            "generator": "ImageNet_Real",
                            "sha256": h,
                        })

                        if len(real_entries) >= (TARGET_TRAIN_REAL + TARGET_VAL_REAL + TARGET_TEST_REAL):
                            break
                if len(real_entries) >= (TARGET_TRAIN_REAL + TARGET_VAL_REAL + TARGET_TEST_REAL):
                    break
    print(f"  Extracted {len(real_entries)} genuine real-world images.")

    # 2. Extract BigGAN AI images from BigGAN shard 1
    print("\n[2/4] Extracting BigGAN synthetic images...")
    with open(SHARDS["BigGAN_1"], "rb") as f:
        reader = ipc.RecordBatchStreamReader(f)
        for batch in reader:
            d = batch.to_pydict()
            for i in range(len(d["label"])):
                if d["label"][i] == 1:  # AI
                    img_bytes = d["image"][i]
                    h = sha256_bytes(img_bytes)
                    if h in seen_hashes:
                        continue
                    seen_hashes.add(h)

                    try:
                        im = Image.open(io.BytesIO(img_bytes))
                        im.verify()
                    except Exception:
                        continue

                    fn = f"biggan_{len(biggan_entries):06d}.jpg"
                    out_path = IMAGES_DIR / "ai_biggan" / fn
                    with open(out_path, "wb") as out_f:
                        out_f.write(img_bytes)

                    biggan_entries.append({
                        "filepath": str(out_path).replace("\\", "/"),
                        "label": 1,
                        "label_name": "AI_GENERATED",
                        "generator": "BigGAN",
                        "sha256": h,
                    })

                    if len(biggan_entries) >= 1500:
                        break
            if len(biggan_entries) >= 1500:
                break
    print(f"  Extracted {len(biggan_entries)} BigGAN synthetic images.")

    # 3. Extract ADM AI images from ADM shard 2
    print("\n[3/4] Extracting ADM synthetic images...")
    with open(SHARDS["ADM_2"], "rb") as f:
        reader = ipc.RecordBatchStreamReader(f)
        for batch in reader:
            d = batch.to_pydict()
            for i in range(len(d["label"])):
                if d["label"][i] == 1:  # AI
                    img_bytes = d["image"][i]
                    h = sha256_bytes(img_bytes)
                    if h in seen_hashes:
                        continue
                    seen_hashes.add(h)

                    try:
                        im = Image.open(io.BytesIO(img_bytes))
                        im.verify()
                    except Exception:
                        continue

                    fn = f"adm_{len(adm_entries):06d}.jpg"
                    out_path = IMAGES_DIR / "ai_adm" / fn
                    with open(out_path, "wb") as out_f:
                        out_f.write(img_bytes)

                    adm_entries.append({
                        "filepath": str(out_path).replace("\\", "/"),
                        "label": 1,
                        "label_name": "AI_GENERATED",
                        "generator": "ADM",
                        "sha256": h,
                    })

                    if len(adm_entries) >= 1500:
                        break
            if len(adm_entries) >= 1500:
                break
    print(f"  Extracted {len(adm_entries)} ADM synthetic images.")

    # 4. Extract Midjourney AI images from MJ shards 17 & 18 (unseen generator)
    print("\n[4/4] Extracting Midjourney synthetic images (held-out unseen generator)...")
    for shard_key in ["MJ_17", "MJ_18"]:
        with open(SHARDS[shard_key], "rb") as f:
            reader = ipc.RecordBatchStreamReader(f)
            for batch in reader:
                d = batch.to_pydict()
                for i in range(len(d["label"])):
                    if d["label"][i] == 1:
                        img_bytes = d["image"][i]
                        h = sha256_bytes(img_bytes)
                        if h in seen_hashes:
                            continue
                        seen_hashes.add(h)

                        try:
                            im = Image.open(io.BytesIO(img_bytes))
                            im.verify()
                        except Exception:
                            continue

                        fn = f"mj_{len(midjourney_entries):06d}.jpg"
                        out_path = IMAGES_DIR / "ai_midjourney" / fn
                        with open(out_path, "wb") as out_f:
                            out_f.write(img_bytes)

                        midjourney_entries.append({
                            "filepath": str(out_path).replace("\\", "/"),
                            "label": 1,
                            "label_name": "AI_GENERATED",
                            "generator": "Midjourney",
                            "sha256": h,
                        })

                        if len(midjourney_entries) >= 400:
                            break
                if len(midjourney_entries) >= 400:
                    break
    print(f"  Extracted {len(midjourney_entries)} Midjourney synthetic images.")

    # 5. Form Partition Splits without Leakage
    print("\n[5/5] Partitioning splits...")
    random.shuffle(real_entries)
    random.shuffle(biggan_entries)
    random.shuffle(adm_entries)
    random.shuffle(midjourney_entries)

    # Real splits
    train_real = real_entries[:TARGET_TRAIN_REAL]
    val_real = real_entries[TARGET_TRAIN_REAL : TARGET_TRAIN_REAL + TARGET_VAL_REAL]
    test_real = real_entries[TARGET_TRAIN_REAL + TARGET_VAL_REAL : TARGET_TRAIN_REAL + TARGET_VAL_REAL + TARGET_TEST_REAL]

    # AI Training pool: 50% BigGAN, 50% ADM
    train_ai = biggan_entries[:TARGET_TRAIN_AI // 2] + adm_entries[:TARGET_TRAIN_AI // 2]
    val_ai = biggan_entries[TARGET_TRAIN_AI // 2 : (TARGET_TRAIN_AI // 2) + (TARGET_VAL_AI // 2)] + \
             adm_entries[TARGET_TRAIN_AI // 2 : (TARGET_TRAIN_AI // 2) + (TARGET_VAL_AI // 2)]

    # Test Seen AI: remaining BigGAN + ADM
    test_seen_ai = biggan_entries[(TARGET_TRAIN_AI // 2) + (TARGET_VAL_AI // 2) : (TARGET_TRAIN_AI // 2) + (TARGET_VAL_AI // 2) + (TARGET_TEST_SEEN_AI // 2)] + \
                   adm_entries[(TARGET_TRAIN_AI // 2) + (TARGET_VAL_AI // 2) : (TARGET_TRAIN_AI // 2) + (TARGET_VAL_AI // 2) + (TARGET_TEST_SEEN_AI // 2)]

    # Test Unseen AI: Midjourney only
    test_unseen_ai = midjourney_entries[:TARGET_TEST_UNSEEN_AI]

    train_set = train_real + train_ai
    val_set = val_real + val_ai
    test_set = test_real + test_seen_ai + test_unseen_ai

    random.shuffle(train_set)
    random.shuffle(val_set)
    random.shuffle(test_set)

    # Verify no hash overlap
    h_train = {e["sha256"] for e in train_set}
    h_val = {e["sha256"] for e in val_set}
    h_test = {e["sha256"] for e in test_set}

    assert len(h_train & h_val) == 0, "Leakage train-val!"
    assert len(h_train & h_test) == 0, "Leakage train-test!"
    assert len(h_val & h_test) == 0, "Leakage val-test!"
    print("  Zero data leakage verified across train, val, and test splits.")

    # Write CSV manifests
    for name, split in [("train", train_set), ("val", val_set), ("test", test_set)]:
        p = DATA_DIR / f"{name}.csv"
        with open(p, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["filepath", "label", "label_name", "generator", "sha256"])
            writer.writeheader()
            writer.writerows(split)
        print(f"  Saved {p.name}: {len(split)} samples")

    # Generate dataset_report.json
    def gen_dist(entries):
        d = {}
        for e in entries:
            k = f"{e['label_name']} - {e['generator']}"
            d[k] = d.get(k, 0) + 1
        return d

    report = {
        "dataset_name": "GenImage (Subsampled Multi-Generator Forensic Benchmark)",
        "source": "https://github.com/GenImage-Dataset/GenImage (Hugging Face mirror nebula/GenImage-arrow)",
        "license": "Apache-2.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_images": len(train_set) + len(val_set) + len(test_set),
        "training_generators": ["BigGAN", "ADM"],
        "unseen_test_generator": "Midjourney",
        "split_counts": {
            "train": len(train_set),
            "val": len(val_set),
            "test": len(test_set),
        },
        "split_distributions": {
            "train": gen_dist(train_set),
            "val": gen_dist(val_set),
            "test": gen_dist(test_set),
        },
        "leakage_check": {
            "train_val_overlap": 0,
            "train_test_overlap": 0,
            "val_test_overlap": 0,
            "status": "PASSED_ZERO_LEAKAGE",
        },
    }

    report_path = DATA_DIR / "dataset_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"  Dataset report saved to {report_path.name}")
    print("\nDataset acquisition & validation successfully finished.")


if __name__ == "__main__":
    extract_and_prepare()
