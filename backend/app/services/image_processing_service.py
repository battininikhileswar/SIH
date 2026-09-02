import os
import json
import logging
from typing import Dict, Any, Tuple, Optional
from PIL import Image, ImageOps

from app.config import SATELLITE_IMAGE_SIZE, SATELLITE_CACHE_DIR

logger = logging.getLogger(__name__)


def validate_satellite_image(image_path: str) -> Tuple[bool, Optional[str]]:
    """
    Validate whether a satellite image file exists, is readable, and is an uncorrupted image.
    Returns (is_valid, error_message).
    """
    if not os.path.exists(image_path):
        return False, f"File does not exist: {image_path}"
    
    if os.path.getsize(image_path) == 0:
        return False, f"Empty image file (0 bytes): {image_path}"

    try:
        with Image.open(image_path) as img:
            img.verify()
        return True, None
    except Exception as e:
        return False, f"Corrupted or invalid image file: {str(e)}"


def preprocess_satellite_image(
    image_path: str,
    target_size: Tuple[int, int] = (SATELLITE_IMAGE_SIZE, SATELLITE_IMAGE_SIZE)
) -> Dict[str, Any]:
    """
    Validate, resize, normalize, and extract metadata for a satellite image patch.
    Deterministic preprocessing utility for pipeline ingestion.
    """
    is_valid, err = validate_satellite_image(image_path)
    if not is_valid:
        logger.error(f"Image preprocessing failed validation: {err}")
        return {
            "success": False,
            "error": err,
            "dimensions": None,
            "processed_path": None
        }

    try:
        with Image.open(image_path) as img:
            original_size = img.size
            format_name = img.format or "PNG"
            
            # Convert RGBA/grayscale to RGB
            if img.mode != "RGB":
                img = img.convert("RGB")

            # Resize to standardized dimensions using Lanczos filter
            if img.size != target_size:
                img = ImageOps.fit(img, target_size, Image.Resampling.LANCZOS)
                img.save(image_path, format=format_name)

            # Generate thumbnail image in same directory
            thumb_filename = f"thumb_{os.path.basename(image_path)}"
            thumb_path = os.path.join(os.path.dirname(image_path), thumb_filename)
            thumb = img.copy()
            thumb.thumbnail((64, 64), Image.Resampling.LANCZOS)
            thumb.save(thumb_path, format="PNG")

            return {
                "success": True,
                "error": None,
                "original_dimensions": list(original_size),
                "processed_dimensions": list(target_size),
                "mode": img.mode,
                "format": format_name,
                "processed_path": image_path,
                "thumbnail_path": thumb_path
            }
    except Exception as ex:
        logger.error(f"Image preprocessing error: {ex}")
        return {
            "success": False,
            "error": str(ex),
            "dimensions": None,
            "processed_path": None
        }


def save_image_metadata(image_id: str, metadata: Dict[str, Any], metadata_dir: Optional[str] = None) -> str:
    """Save image metadata JSON file to satellite metadata folder."""
    target_dir = metadata_dir or os.path.join(SATELLITE_CACHE_DIR, "metadata")
    os.makedirs(target_dir, exist_ok=True)
    
    meta_path = os.path.join(target_dir, f"{image_id}_meta.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    
    return meta_path
