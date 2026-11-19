"""
TruthLens Image CNN — Training & Evaluation Pipeline
=====================================================
Trains the custom TruthLens CNN from scratch on GenImage data,
evaluates on a held-out test set (including unseen generators),
generates all metrics, curves, and exports the checkpoint.

Supports both CPU and CUDA GPU execution.
"""
import os
import sys
import json
import csv
import time
import random
import gc
from pathlib import Path
from datetime import datetime, timezone

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms
from PIL import Image

# Add scripts dir to path
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))

from model import TruthLensImageCNN

# ---- Configuration ----
IMAGE_SIZE = 128
BATCH_SIZE = 16          # Will be reduced for CPU if needed
EPOCHS = 5
LEARNING_RATE = 0.001
SEED = 42
NUM_CLASSES = 2
DROPOUT = 0.4
NUM_WORKERS = 0          # Safe for Windows / limited CPU

DATA_DIR = PROJECT_ROOT / "data"
MODELS_DIR = PROJECT_ROOT / "models"
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
REPORTS_DIR = PROJECT_ROOT / "reports"


def set_seed(seed: int):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


class GenImageCSVDataset(Dataset):
    """Loads images from CSV manifest with filepath and label columns."""
    def __init__(self, csv_path: str, transform=None):
        self.entries = []
        self.transform = transform
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.entries.append({
                    "filepath": row["filepath"],
                    "label": int(row["label"]),
                    "generator": row.get("generator", "unknown"),
                })

    def __len__(self):
        return len(self.entries)

    def __getitem__(self, idx):
        entry = self.entries[idx]
        try:
            img = Image.open(entry["filepath"]).convert("RGB")
        except Exception:
            # Return a black image on failure rather than crashing
            img = Image.new("RGB", (IMAGE_SIZE, IMAGE_SIZE), (0, 0, 0))

        if self.transform:
            img = self.transform(img)

        return img, entry["label"]


def get_transforms(is_train: bool):
    if is_train:
        return transforms.Compose([
            transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
            transforms.RandomHorizontalFlip(p=0.5),
            transforms.RandomRotation(10),
            transforms.ColorJitter(brightness=0.1, contrast=0.1, saturation=0.1),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406],
                                 std=[0.229, 0.224, 0.225]),
        ])
    else:
        return transforms.Compose([
            transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406],
                                 std=[0.229, 0.224, 0.225]),
        ])


def compute_metrics(all_labels, all_preds, all_probs):
    """Compute accuracy, precision, recall, F1, ROC-AUC."""
    from sklearn.metrics import (
        accuracy_score, precision_score, recall_score, f1_score,
        roc_auc_score, confusion_matrix
    )
    acc = accuracy_score(all_labels, all_preds)
    prec = precision_score(all_labels, all_preds, zero_division=0)
    rec = recall_score(all_labels, all_preds, zero_division=0)
    f1 = f1_score(all_labels, all_preds, zero_division=0)
    try:
        auc = roc_auc_score(all_labels, all_probs)
    except ValueError:
        auc = 0.0
    cm = confusion_matrix(all_labels, all_preds)
    return {
        "accuracy": float(acc),
        "precision": float(prec),
        "recall": float(rec),
        "f1_score": float(f1),
        "roc_auc": float(auc),
        "confusion_matrix": cm.tolist(),
    }


def train_one_epoch(model, loader, criterion, optimizer, device):
    model.train()
    running_loss = 0.0
    all_labels, all_preds, all_probs = [], [], []

    for batch_idx, (images, labels) in enumerate(loader):
        images, labels = images.to(device), labels.to(device)
        optimizer.zero_grad()
        outputs = model(images)
        loss = criterion(outputs, labels)
        loss.backward()
        optimizer.step()

        running_loss += loss.item() * images.size(0)
        probs = torch.softmax(outputs, dim=1)
        preds = probs.argmax(dim=1)
        all_labels.extend(labels.cpu().numpy())
        all_preds.extend(preds.cpu().numpy())
        all_probs.extend(probs[:, 1].detach().cpu().numpy())

        if (batch_idx + 1) % 50 == 0:
            print(f"    Batch {batch_idx+1}/{len(loader)}, Loss: {loss.item():.4f}")

    epoch_loss = running_loss / len(loader.dataset)
    metrics = compute_metrics(all_labels, all_preds, all_probs)
    return epoch_loss, metrics


@torch.no_grad()
def evaluate(model, loader, criterion, device):
    model.eval()
    running_loss = 0.0
    all_labels, all_preds, all_probs = [], [], []

    for images, labels in loader:
        images, labels = images.to(device), labels.to(device)
        outputs = model(images)
        loss = criterion(outputs, labels)
        running_loss += loss.item() * images.size(0)

        probs = torch.softmax(outputs, dim=1)
        preds = probs.argmax(dim=1)
        all_labels.extend(labels.cpu().numpy())
        all_preds.extend(preds.cpu().numpy())
        all_probs.extend(probs[:, 1].detach().cpu().numpy())

    epoch_loss = running_loss / len(loader.dataset)
    metrics = compute_metrics(all_labels, all_preds, all_probs)
    return epoch_loss, metrics, all_labels, all_preds, all_probs


def save_training_plots(history, outputs_dir):
    """Generate loss, accuracy, and ROC curves."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    epochs = range(1, len(history["train_loss"]) + 1)

    # Loss curve
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(epochs, history["train_loss"], "o-", label="Train Loss", color="#2563eb")
    ax.plot(epochs, history["val_loss"], "s-", label="Val Loss", color="#dc2626")
    ax.set_xlabel("Epoch")
    ax.set_ylabel("Loss")
    ax.set_title("TruthLens CNN — Training & Validation Loss")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(str(outputs_dir / "loss_curve.png"), dpi=150)
    plt.close(fig)

    # Accuracy curve
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(epochs, history["train_acc"], "o-", label="Train Accuracy", color="#2563eb")
    ax.plot(epochs, history["val_acc"], "s-", label="Val Accuracy", color="#dc2626")
    ax.set_xlabel("Epoch")
    ax.set_ylabel("Accuracy")
    ax.set_title("TruthLens CNN — Training & Validation Accuracy")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(str(outputs_dir / "accuracy_curve.png"), dpi=150)
    plt.close(fig)

    print(f"  Saved loss_curve.png and accuracy_curve.png to {outputs_dir}")


def save_evaluation_plots(test_labels, test_preds, test_probs, test_metrics, outputs_dir):
    """Generate confusion matrix and ROC curve."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from sklearn.metrics import ConfusionMatrixDisplay, roc_curve

    # Confusion matrix
    fig, ax = plt.subplots(figsize=(6, 5))
    ConfusionMatrixDisplay.from_predictions(
        test_labels, test_preds,
        display_labels=["REAL", "AI_GENERATED"],
        cmap="Blues", ax=ax
    )
    ax.set_title("TruthLens CNN — Test Set Confusion Matrix")
    fig.tight_layout()
    fig.savefig(str(outputs_dir / "confusion_matrix.png"), dpi=150)
    plt.close(fig)

    # ROC curve
    fpr, tpr, _ = roc_curve(test_labels, test_probs)
    fig, ax = plt.subplots(figsize=(7, 6))
    ax.plot(fpr, tpr, color="#2563eb", lw=2,
            label=f"ROC (AUC = {test_metrics['roc_auc']:.4f})")
    ax.plot([0, 1], [0, 1], "k--", lw=1, alpha=0.5)
    ax.set_xlabel("False Positive Rate")
    ax.set_ylabel("True Positive Rate")
    ax.set_title("TruthLens CNN — ROC Curve")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(str(outputs_dir / "roc_curve.png"), dpi=150)
    plt.close(fig)

    print(f"  Saved confusion_matrix.png and roc_curve.png to {outputs_dir}")


def run_training():
    print("=" * 60)
    print("TruthLens Image CNN — Training Pipeline")
    print("=" * 60)

    set_seed(SEED)

    # ---- Device ----
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"\nDevice: {device}")
    if device.type == "cuda":
        print(f"GPU: {torch.cuda.get_device_name(0)}")
        gpu_mem = torch.cuda.get_device_properties(0).total_mem / (1024**3)
        print(f"GPU Memory: {gpu_mem:.1f} GB")

    batch_size = BATCH_SIZE
    if device.type == "cpu":
        batch_size = min(batch_size, 8)
        print(f"CPU mode: batch_size reduced to {batch_size}")

    # ---- Check CSV manifests ----
    train_csv = DATA_DIR / "train.csv"
    val_csv = DATA_DIR / "val.csv"
    test_csv = DATA_DIR / "test.csv"
    for p in [train_csv, val_csv, test_csv]:
        if not p.exists():
            print(f"ERROR: {p} not found. Run dataset_preparation.py first.")
            sys.exit(1)

    # ---- Datasets & Loaders ----
    print("\nLoading datasets...")
    train_ds = GenImageCSVDataset(str(train_csv), transform=get_transforms(True))
    val_ds = GenImageCSVDataset(str(val_csv), transform=get_transforms(False))
    test_ds = GenImageCSVDataset(str(test_csv), transform=get_transforms(False))

    print(f"  Train: {len(train_ds)} samples")
    print(f"  Val:   {len(val_ds)} samples")
    print(f"  Test:  {len(test_ds)} samples")

    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True, num_workers=NUM_WORKERS, pin_memory=False)
    val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False, num_workers=NUM_WORKERS, pin_memory=False)
    test_loader = DataLoader(test_ds, batch_size=batch_size, shuffle=False, num_workers=NUM_WORKERS, pin_memory=False)

    # ---- Model ----
    print("\nInitialising TruthLens Image CNN from scratch...")
    model = TruthLensImageCNN(num_classes=NUM_CLASSES, dropout=DROPOUT).to(device)
    total_params = sum(p.numel() for p in model.parameters())
    print(f"  Total parameters: {total_params:,}")

    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=LEARNING_RATE)
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode="max", factor=0.5, patience=2)

    # ---- Training Loop ----
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    history = {
        "train_loss": [], "val_loss": [],
        "train_acc": [], "val_acc": [],
        "train_f1": [], "val_f1": [],
        "lr": [],
    }
    best_val_f1 = 0.0
    best_epoch = 0
    training_start = time.time()

    print(f"\n{'='*60}")
    print(f"Starting training: {EPOCHS} epochs, batch_size={batch_size}, lr={LEARNING_RATE}")
    print(f"{'='*60}\n")

    for epoch in range(1, EPOCHS + 1):
        epoch_start = time.time()
        current_lr = optimizer.param_groups[0]["lr"]

        print(f"Epoch {epoch}/{EPOCHS} (lr={current_lr:.6f})")
        print("-" * 40)

        train_loss, train_metrics = train_one_epoch(model, train_loader, criterion, optimizer, device)
        val_loss, val_metrics, _, _, _ = evaluate(model, val_loader, criterion, device)

        scheduler.step(val_metrics["f1_score"])

        history["train_loss"].append(train_loss)
        history["val_loss"].append(val_loss)
        history["train_acc"].append(train_metrics["accuracy"])
        history["val_acc"].append(val_metrics["accuracy"])
        history["train_f1"].append(train_metrics["f1_score"])
        history["val_f1"].append(val_metrics["f1_score"])
        history["lr"].append(current_lr)

        epoch_time = time.time() - epoch_start

        print(f"  Train Loss: {train_loss:.4f} | Acc: {train_metrics['accuracy']:.4f} | "
              f"P: {train_metrics['precision']:.4f} | R: {train_metrics['recall']:.4f} | "
              f"F1: {train_metrics['f1_score']:.4f}")
        print(f"  Val   Loss: {val_loss:.4f} | Acc: {val_metrics['accuracy']:.4f} | "
              f"P: {val_metrics['precision']:.4f} | R: {val_metrics['recall']:.4f} | "
              f"F1: {val_metrics['f1_score']:.4f} | AUC: {val_metrics['roc_auc']:.4f}")
        print(f"  Epoch time: {epoch_time:.1f}s")

        # Save best checkpoint by validation F1
        if val_metrics["f1_score"] > best_val_f1:
            best_val_f1 = val_metrics["f1_score"]
            best_epoch = epoch
            checkpoint = {
                "epoch": epoch,
                "model_state_dict": model.state_dict(),
                "optimizer_state_dict": optimizer.state_dict(),
                "val_f1": best_val_f1,
                "val_accuracy": val_metrics["accuracy"],
                "val_loss": val_loss,
                "model_config": TruthLensImageCNN.get_config(),
                "training_config": {
                    "image_size": IMAGE_SIZE,
                    "batch_size": batch_size,
                    "learning_rate": LEARNING_RATE,
                    "epochs": EPOCHS,
                    "seed": SEED,
                    "optimizer": "Adam",
                    "loss": "CrossEntropyLoss",
                },
            }
            torch.save(checkpoint, str(MODELS_DIR / "truthlens_image_cnn.pth"))
            print(f"  ★ New best model saved (val F1={best_val_f1:.4f})")

        print()
        gc.collect()

    total_training_time = time.time() - training_start
    print(f"{'='*60}")
    print(f"Training complete in {total_training_time:.1f}s ({total_training_time/60:.1f} min)")
    print(f"Best checkpoint: epoch {best_epoch} with val F1={best_val_f1:.4f}")
    print(f"{'='*60}\n")

    # ---- Save training history ----
    history_out = {
        "training_config": {
            "image_size": IMAGE_SIZE,
            "batch_size": batch_size,
            "epochs": EPOCHS,
            "learning_rate": LEARNING_RATE,
            "seed": SEED,
            "device": str(device),
            "total_training_time_s": round(total_training_time, 1),
        },
        "best_epoch": best_epoch,
        "best_val_f1": best_val_f1,
        "history": history,
    }
    with open(OUTPUTS_DIR / "training_history.json", "w") as f:
        json.dump(history_out, f, indent=2)

    # ---- Save plots ----
    try:
        save_training_plots(history, OUTPUTS_DIR)
    except Exception as e:
        print(f"  Warning: Could not generate training plots: {e}")

    # ---- Final Test Evaluation ----
    print("\n=== Test Set Evaluation ===")
    print("Loading best checkpoint...")
    ckpt = torch.load(str(MODELS_DIR / "truthlens_image_cnn.pth"), map_location=device, weights_only=False)
    model.load_state_dict(ckpt["model_state_dict"])

    test_loss, test_metrics, test_labels, test_preds, test_probs = evaluate(
        model, test_loader, criterion, device
    )

    cm = test_metrics["confusion_matrix"]
    tn, fp, fn, tp = cm[0][0], cm[0][1], cm[1][0], cm[1][1]
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0
    fnr = fn / (fn + tp) if (fn + tp) > 0 else 0

    print(f"\n  Test Loss:      {test_loss:.4f}")
    print(f"  Accuracy:       {test_metrics['accuracy']:.4f}")
    print(f"  Precision:      {test_metrics['precision']:.4f}")
    print(f"  Recall:         {test_metrics['recall']:.4f}")
    print(f"  F1-Score:       {test_metrics['f1_score']:.4f}")
    print(f"  ROC-AUC:        {test_metrics['roc_auc']:.4f}")
    print(f"  FPR:            {fpr:.4f}")
    print(f"  FNR:            {fnr:.4f}")
    print(f"  Confusion Matrix: TN={tn}, FP={fp}, FN={fn}, TP={tp}")

    # Save evaluation JSON
    eval_report = {
        "model_name": "TruthLens Image CNN",
        "model_version": "1.0",
        "checkpoint": "truthlens_image_cnn.pth",
        "best_training_epoch": best_epoch,
        "device": str(device),
        "test_loss": round(test_loss, 4),
        "accuracy": round(test_metrics["accuracy"], 4),
        "precision": round(test_metrics["precision"], 4),
        "recall": round(test_metrics["recall"], 4),
        "f1_score": round(test_metrics["f1_score"], 4),
        "roc_auc": round(test_metrics["roc_auc"], 4),
        "false_positive_rate": round(fpr, 4),
        "false_negative_rate": round(fnr, 4),
        "confusion_matrix": {
            "true_negative": int(tn), "false_positive": int(fp),
            "false_negative": int(fn), "true_positive": int(tp),
        },
        "test_set_size": len(test_ds),
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "limitations": [
            "Trained on GenImage subset only (Stable Diffusion 1.4, BigGAN); may not generalise to all generators.",
            "Uncalibrated model scores are not definitive forensic evidence.",
            "Does not detect Photoshop edits, copy-move manipulation, inpainting, or object removal.",
            "Performance on unseen generators (e.g., Midjourney) may differ from seen-generator accuracy.",
            "JPEG compression, resizing, and blur degrade detection accuracy.",
        ],
    }
    with open(OUTPUTS_DIR / "evaluation.json", "w") as f:
        json.dump(eval_report, f, indent=2)

    # Save evaluation plots
    try:
        save_evaluation_plots(test_labels, test_preds, test_probs, test_metrics, OUTPUTS_DIR)
    except Exception as e:
        print(f"  Warning: Could not generate evaluation plots: {e}")

    print(f"\n  All outputs saved to: {OUTPUTS_DIR}")
    print(f"  Model checkpoint:     {MODELS_DIR / 'truthlens_image_cnn.pth'}")

    return eval_report


if __name__ == "__main__":
    run_training()
