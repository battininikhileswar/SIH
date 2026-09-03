import os
import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from PIL import Image

import torch
from torch.utils.data import Dataset
import torchvision.transforms as transforms

from app.config import SATELLITE_DATASET_DIR, SATELLITE_IMAGE_SIZE

logger = logging.getLogger(__name__)

CLASS_NAME_TO_ID = {
    "NON_FIRE": 0,
    "NATURAL_FIRE": 1,
    "INDUSTRIAL_FIRE": 2,
    "PERSISTENT_THERMAL_SOURCE": 3
}

ID_TO_CLASS_NAME = {v: k for k, v in CLASS_NAME_TO_ID.items()}


def get_satellite_transforms(is_train: bool = True, image_size: int = SATELLITE_IMAGE_SIZE):
    """
    Construct conservative data transforms suitable for satellite optical imagery.
    Avoids aggressive distortions that destroy physical multi-spectral scene interpretation.
    """
    if is_train:
        return transforms.Compose([
            transforms.Resize((image_size, image_size)),
            transforms.RandomHorizontalFlip(p=0.5),
            transforms.RandomVerticalFlip(p=0.5),
            transforms.RandomRotation(degrees=(0, 180)),
            transforms.ColorJitter(brightness=0.1, contrast=0.1),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])
    else:
        return transforms.Compose([
            transforms.Resize((image_size, image_size)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])


class SatellitePatchDataset(Dataset):
    """
    PyTorch Dataset for Satellite Optical Patch Classification.
    Loads standardized 256x256 RGB patch images and metadata JSON records.
    """

    def __init__(
        self,
        dataset_dir: str = SATELLITE_DATASET_DIR,
        split: Optional[str] = None,
        transform: Optional[Any] = None,
        image_size: int = SATELLITE_IMAGE_SIZE
    ):
        self.dataset_dir = dataset_dir
        self.split = split
        self.image_size = image_size
        self.transform = transform or get_satellite_transforms(is_train=(split == "train"), image_size=image_size)

        self.metadata_dir = os.path.join(dataset_dir, "metadata")
        self.processed_dir = os.path.join(dataset_dir, "processed")
        self.samples: List[Dict[str, Any]] = []

        self._load_samples()

    def _load_samples(self):
        if not os.path.exists(self.metadata_dir):
            logger.warning(f"Metadata directory not found at {self.metadata_dir}")
            return

        for filename in os.listdir(self.metadata_dir):
            if filename.endswith(".json") and not filename.startswith("."):
                meta_path = os.path.join(self.metadata_dir, filename)
                try:
                    with open(meta_path, "r", encoding="utf-8") as f:
                        meta = json.load(f)

                    item_split = meta.get("split", "train")
                    if self.split and item_split != self.split:
                        continue

                    label_name = meta.get("label", "NON_FIRE")
                    if label_name not in CLASS_NAME_TO_ID:
                        continue

                    image_id = meta.get("image_id")
                    img_path = meta.get("processed_image_path")
                    if not img_path or not os.path.exists(img_path):
                        # Fallback check in processed folder
                        img_path = os.path.join(self.processed_dir, f"{image_id}.png")

                    if os.path.exists(img_path):
                        meta["resolved_image_path"] = img_path
                        meta["label_id"] = CLASS_NAME_TO_ID[label_name]
                        self.samples.append(meta)
                except Exception as e:
                    logger.error(f"Error loading metadata JSON {meta_path}: {e}")

        logger.info(f"Loaded {len(self.samples)} satellite patch samples for split='{self.split or 'all'}'")

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, int, Dict[str, Any]]:
        meta = self.samples[idx]
        img_path = meta["resolved_image_path"]
        label_id = meta["label_id"]

        with Image.open(img_path) as img:
            if img.mode != "RGB":
                img = img.convert("RGB")
            
            image_tensor = self.transform(img)

        # Sanitize metadata dictionary so None values do not fail PyTorch default_collate
        sanitized_meta = {k: (v if v is not None else "") for k, v in meta.items()}

        return image_tensor, label_id, sanitized_meta

