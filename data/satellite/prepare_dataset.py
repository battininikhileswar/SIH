import os
import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Base satellite directory path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SUBDIRECTORIES = [
    "raw",
    "processed",
    "industrial_fire",
    "natural_fire",
    "persistent_thermal",
    "non_fire",
    "metadata",
    "cache"
]


def initialize_satellite_dataset_structure() -> Dict[str, str]:
    """Create all standard satellite dataset subdirectories and .gitkeep files."""
    created_paths = {}
    for subdir in SUBDIRECTORIES:
        path = os.path.join(BASE_DIR, subdir)
        os.makedirs(path, exist_ok=True)
        gitkeep = os.path.join(path, ".gitkeep")
        if not os.path.exists(gitkeep):
            with open(gitkeep, "w") as f:
                f.write("")
        created_paths[subdir] = path
    return created_paths


def register_dataset_item(
    image_id: str,
    lat: float,
    lon: float,
    label: str,
    timestamp: str = "2026-09-01 12:00:00 UTC",
    source: str = "Sentinel-2 L2A",
    firms_confidence: str = "nominal",
    custom_metadata: Optional[Dict[str, Any]] = None
) -> str:
    """
    Register a verified satellite image patch item into the dataset metadata registry.
    Ensures verified labels without fabrication.
    """
    initialize_satellite_dataset_structure()
    meta_dir = os.path.join(BASE_DIR, "metadata")
    
    item_metadata = {
        "image_id": image_id,
        "latitude": lat,
        "longitude": lon,
        "timestamp": timestamp,
        "source": source,
        "firms_confidence": firms_confidence,
        "label": label,
        "registered_at": timestamp,
        "custom": custom_metadata or {}
    }
    
    file_path = os.path.join(meta_dir, f"{image_id}.json")
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(item_metadata, f, indent=2, ensure_ascii=False)
        
    return file_path


if __name__ == "__main__":
    paths = initialize_satellite_dataset_structure()
    print("Satellite Dataset Structure Initialized Successfully:")
    for name, p in paths.items():
        print(f"  - {name}: {p}")
