import os
import sys
import json
import time
import argparse
import logging
from typing import Dict, Any, List

import torch
import torch.nn as nn
from torch.utils.data import DataLoader

# Add backend directory to path if executed as script
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.config import SATELLITE_DATASET_DIR, SATELLITE_MODEL_DIR
from app.ml.dataset import SatellitePatchDataset, CLASS_NAME_TO_ID, ID_TO_CLASS_NAME
from app.ml.model import build_satellite_model, NUM_CLASSES, CLASS_NAMES

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("train_satellite_model")


def train_model(
    epochs: int = 10,
    batch_size: int = 16,
    learning_rate: float = 0.0001,
    model_name: str = "resnet18",
    dataset_dir: str = SATELLITE_DATASET_DIR,
    output_dir: str = SATELLITE_MODEL_DIR
) -> Dict[str, Any]:
    """
    Train Satellite Computer Vision Model using PyTorch.
    Tracks epoch loss, training/validation accuracy, and saves best model artifacts.
    """
    os.makedirs(output_dir, exist_ok=True)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info(f"Using compute device: {device}")

    # 1. Load Datasets
    train_dataset = SatellitePatchDataset(dataset_dir=dataset_dir, split="train")
    val_dataset = SatellitePatchDataset(dataset_dir=dataset_dir, split="val")

    if len(train_dataset) == 0:
        logger.warning("Train dataset is empty! Attempting to build dataset first...")
        from data.satellite.build_dataset import build_dataset
        import asyncio
        asyncio.run(build_dataset(limit_per_class=30, output_dir=dataset_dir))
        train_dataset = SatellitePatchDataset(dataset_dir=dataset_dir, split="train")
        val_dataset = SatellitePatchDataset(dataset_dir=dataset_dir, split="val")

    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False) if len(val_dataset) > 0 else train_loader

    logger.info(f"Loaded {len(train_dataset)} training samples and {len(val_dataset)} validation samples.")

    # 2. Build Model
    model = build_satellite_model(architecture=model_name, num_classes=NUM_CLASSES, pretrained=True)
    model.to(device)

    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.AdamW(model.parameters(), lr=learning_rate, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=max(1, epochs))

    history = {
        "train_loss": [],
        "train_acc": [],
        "val_loss": [],
        "val_acc": []
    }

    best_val_acc = -1.0
    best_model_path = os.path.join(output_dir, "best_model.pth")

    logger.info(f"Starting training loop for {epochs} epochs (Model: {model_name})...")
    start_time = time.time()

    for epoch in range(1, epochs + 1):
        # Training Phase
        model.train()
        running_loss = 0.0
        correct_train = 0
        total_train = 0

        for images, labels, _ in train_loader:
            images = images.to(device)
            labels = labels.to(device)

            optimizer.zero_grad()
            outputs = model(images)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()

            running_loss += loss.item() * images.size(0)
            _, preds = torch.max(outputs, 1)
            correct_train += (preds == labels).sum().item()
            total_train += labels.size(0)

        scheduler.step()

        epoch_train_loss = round(running_loss / max(1, total_train), 4)
        epoch_train_acc = round(correct_train / max(1, total_train), 4)

        # Validation Phase
        model.eval()
        val_loss = 0.0
        correct_val = 0
        total_val = 0

        with torch.no_grad():
            for images, labels, _ in val_loader:
                images = images.to(device)
                labels = labels.to(device)

                outputs = model(images)
                loss = criterion(outputs, labels)

                val_loss += loss.item() * images.size(0)
                _, preds = torch.max(outputs, 1)
                correct_val += (preds == labels).sum().item()
                total_val += labels.size(0)

        epoch_val_loss = round(val_loss / max(1, total_val), 4)
        epoch_val_acc = round(correct_val / max(1, total_val), 4)

        history["train_loss"].append(epoch_train_loss)
        history["train_acc"].append(epoch_train_acc)
        history["val_loss"].append(epoch_val_loss)
        history["val_acc"].append(epoch_val_acc)

        logger.info(
            f"Epoch [{epoch:02d}/{epochs:02d}] - "
            f"Train Loss: {epoch_train_loss:.4f}, Train Acc: {epoch_train_acc*100:.1f}% | "
            f"Val Loss: {epoch_val_loss:.4f}, Val Acc: {epoch_val_acc*100:.1f}%"
        )

        # Save Best Model Weights
        if epoch_val_acc >= best_val_acc:
            best_val_acc = epoch_val_acc
            torch.save(model.state_dict(), best_model_path)
            logger.info(f"  --> Saved new best model checkpoint to {best_model_path} (Val Acc: {best_val_acc*100:.1f}%)")

    total_duration = round(time.time() - start_time, 2)

    # Save Class Names JSON
    with open(os.path.join(output_dir, "class_names.json"), "w", encoding="utf-8") as f:
        json.dump({
            "class_to_id": CLASS_NAME_TO_ID,
            "id_to_class": ID_TO_CLASS_NAME,
            "classes": CLASS_NAMES
        }, f, indent=2)

    # Save Training Metrics JSON
    training_metrics = {
        "model_name": model_name,
        "epochs_trained": epochs,
        "batch_size": batch_size,
        "learning_rate": learning_rate,
        "best_val_accuracy": best_val_acc,
        "best_val_accuracy_percentage": round(best_val_acc * 100, 2),
        "total_duration_seconds": total_duration,
        "history": history,
        "trained_at": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
    }

    with open(os.path.join(output_dir, "training_metrics.json"), "w", encoding="utf-8") as f:
        json.dump(training_metrics, f, indent=2)

    # Save Model Metadata JSON
    model_metadata = {
        "model": model_name,
        "model_version": "1.0",
        "input_channels": 3,
        "image_size": 256,
        "num_classes": NUM_CLASSES,
        "classes": CLASS_NAMES,
        "best_val_accuracy": best_val_acc,
        "weights_file": "best_model.pth"
    }

    with open(os.path.join(output_dir, "metadata.json"), "w", encoding="utf-8") as f:
        json.dump(model_metadata, f, indent=2)

    logger.info("🎉 Satellite Model Training Completed Successfully!")
    logger.info(f"Model artifacts saved under: {output_dir}")

    return training_metrics


def main():
    parser = argparse.ArgumentParser(description="SIH 26162 Phase 9 Satellite Vision Model Trainer")
    parser.add_argument("--epochs", type=int, default=10, help="Number of epochs to train (default: 10)")
    parser.add_argument("--batch-size", type=int, default=16, help="Batch size (default: 16)")
    parser.add_argument("--lr", type=float, default=0.0001, help="Learning rate (default: 0.0001)")
    parser.add_argument("--model-name", type=str, default="resnet18", help="Model architecture: resnet18 or efficientnet_b0")
    parser.add_argument("--dataset-dir", type=str, default=SATELLITE_DATASET_DIR, help="Dataset directory")
    parser.add_argument("--output-dir", type=str, default=SATELLITE_MODEL_DIR, help="Output model directory")

    args = parser.parse_args()

    train_model(
        epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.lr,
        model_name=args.model_name,
        dataset_dir=args.dataset_dir,
        output_dir=args.output_dir
    )


if __name__ == "__main__":
    main()
