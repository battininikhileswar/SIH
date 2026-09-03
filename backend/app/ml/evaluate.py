import os
import sys
import json
import time
import argparse
import logging
from typing import Dict, Any, List

import torch
from torch.utils.data import DataLoader
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, confusion_matrix, classification_report

# Add backend directory to sys.path
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app.config import SATELLITE_DATASET_DIR, SATELLITE_MODEL_DIR, SATELLITE_METRICS_DIR
from app.ml.dataset import SatellitePatchDataset, ID_TO_CLASS_NAME
from app.ml.model import build_satellite_model, NUM_CLASSES, CLASS_NAMES

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("evaluate_satellite_model")


def evaluate_model(
    model_dir: str = SATELLITE_MODEL_DIR,
    dataset_dir: str = SATELLITE_DATASET_DIR,
    output_dir: str = SATELLITE_METRICS_DIR
) -> Dict[str, Any]:
    """
    Evaluate trained Satellite Computer Vision Model on test split.
    Calculates Accuracy, Precision, Recall, F1-Score, Per-Class metrics, and Confusion Matrix.
    """
    os.makedirs(output_dir, exist_ok=True)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model_weights_path = os.path.join(model_dir, "best_model.pth")
    meta_path = os.path.join(model_dir, "metadata.json")

    if not os.path.exists(model_weights_path):
        raise FileNotFoundError(f"Trained model weights file not found at {model_weights_path}. Run training first.")

    # Load Model Metadata
    arch_name = "resnet18"
    if os.path.exists(meta_path):
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
                arch_name = meta.get("model", "resnet18")
        except Exception:
            pass

    # Load Model
    model = build_satellite_model(architecture=arch_name, num_classes=NUM_CLASSES, pretrained=False)
    model.load_state_dict(torch.load(model_weights_path, map_location=device))
    model.to(device)
    model.eval()

    # Load Test Dataset (fallback to val or train if test split is small)
    test_dataset = SatellitePatchDataset(dataset_dir=dataset_dir, split="test")
    if len(test_dataset) == 0:
        test_dataset = SatellitePatchDataset(dataset_dir=dataset_dir, split="val")
    if len(test_dataset) == 0:
        test_dataset = SatellitePatchDataset(dataset_dir=dataset_dir, split="train")

    if len(test_dataset) == 0:
        raise ValueError(f"No evaluation samples found in dataset directory {dataset_dir}")

    test_loader = DataLoader(test_dataset, batch_size=16, shuffle=False)
    logger.info(f"Evaluating {arch_name} on {len(test_dataset)} test patch samples...")

    y_true = []
    y_pred = []
    y_scores = []

    with torch.no_grad():
        for images, labels, _ in test_loader:
            images = images.to(device)
            outputs = model(images)
            probs = torch.softmax(outputs, dim=1)
            _, preds = torch.max(outputs, 1)

            y_true.extend(labels.cpu().numpy().tolist())
            y_pred.extend(preds.cpu().numpy().tolist())
            y_scores.extend(probs.cpu().numpy().tolist())

    # Compute Standard ML Metrics
    acc = round(float(accuracy_score(y_true, y_pred)), 4)
    precision_macro, recall_macro, f1_macro, _ = precision_recall_fscore_support(y_true, y_pred, average="macro", zero_division=0)
    precision_weighted, recall_weighted, f1_weighted, _ = precision_recall_fscore_support(y_true, y_pred, average="weighted", zero_division=0)

    # Per-Class Precision, Recall, F1
    per_class_precision, per_class_recall, per_class_f1, per_class_support = precision_recall_fscore_support(
        y_true, y_pred, average=None, labels=list(range(NUM_CLASSES)), zero_division=0
    )

    per_class_metrics = {}
    for i, name in enumerate(CLASS_NAMES):
        per_class_metrics[name] = {
            "precision": round(float(per_class_precision[i]), 4),
            "recall": round(float(per_class_recall[i]), 4),
            "f1_score": round(float(per_class_f1[i]), 4),
            "support": int(per_class_support[i])
        }

    # Confusion Matrix
    cm = confusion_matrix(y_true, y_pred, labels=list(range(NUM_CLASSES)))
    cm_list = cm.tolist()

    # Classification Report
    clf_report = classification_report(y_true, y_pred, labels=list(range(NUM_CLASSES)), target_names=CLASS_NAMES, zero_division=0, output_dict=True)

    metrics_result = {
        "model_name": arch_name,
        "eval_samples": len(test_dataset),
        "accuracy": acc,
        "accuracy_percentage": round(acc * 100, 2),
        "precision_macro": round(float(precision_macro), 4),
        "recall_macro": round(float(recall_macro), 4),
        "f1_macro": round(float(f1_macro), 4),
        "precision_weighted": round(float(precision_weighted), 4),
        "recall_weighted": round(float(recall_weighted), 4),
        "f1_weighted": round(float(f1_weighted), 4),
        "per_class_metrics": per_class_metrics,
        "confusion_matrix": cm_list,
        "evaluated_at": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
    }

    # Save Output Metrics
    with open(os.path.join(output_dir, "metrics.json"), "w", encoding="utf-8") as f:
        json.dump(metrics_result, f, indent=2)

    with open(os.path.join(output_dir, "classification_report.json"), "w", encoding="utf-8") as f:
        json.dump(clf_report, f, indent=2)

    with open(os.path.join(output_dir, "confusion_matrix.json"), "w", encoding="utf-8") as f:
        json.dump({"labels": CLASS_NAMES, "matrix": cm_list}, f, indent=2)

    # Optional Plotting of Confusion Matrix PNG using Matplotlib
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(7, 6))
        cax = ax.matshow(cm, cmap=plt.cm.Blues)
        fig.colorbar(cax)

        ax.set_xticks(range(NUM_CLASSES))
        ax.set_yticks(range(NUM_CLASSES))
        ax.set_xticklabels(CLASS_NAMES, rotation=45, ha="left")
        ax.set_yticklabels(CLASS_NAMES)
        ax.set_xlabel("Predicted Label")
        ax.set_ylabel("True Label")
        plt.title(f"Confusion Matrix - {arch_name} (Acc: {acc*100:.1f}%)")

        # Annotate cell counts
        for i in range(NUM_CLASSES):
            for j in range(NUM_CLASSES):
                ax.text(j, i, str(cm[i, j]), ha="center", va="center", color="red" if cm[i, j] > 0 else "gray")

        plt.tight_layout()
        plot_path = os.path.join(output_dir, "confusion_matrix.png")
        plt.savefig(plot_path, dpi=200)
        plt.close(fig)
        logger.info(f"Saved confusion matrix plot to {plot_path}")
    except Exception as ex:
        logger.warning(f"Could not render confusion matrix plot PNG ({ex})")

    logger.info("✅ Model Evaluation Completed Successfully!")
    logger.info(f"Test Accuracy: {acc*100:.2f}%, Macro F1: {f1_macro:.4f}")

    return metrics_result


def main():
    parser = argparse.ArgumentParser(description="SIH 26162 Phase 9 Satellite Model Evaluator")
    parser.add_argument("--model-dir", type=str, default=SATELLITE_MODEL_DIR, help="Model directory")
    parser.add_argument("--dataset-dir", type=str, default=SATELLITE_DATASET_DIR, help="Dataset directory")
    parser.add_argument("--output-dir", type=str, default=SATELLITE_METRICS_DIR, help="Metrics output directory")

    args = parser.parse_args()

    evaluate_model(
        model_dir=args.model_dir,
        dataset_dir=args.dataset_dir,
        output_dir=args.output_dir
    )


if __name__ == "__main__":
    main()
