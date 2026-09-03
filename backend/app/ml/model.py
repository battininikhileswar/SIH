import logging
import torch
import torch.nn as nn
import torchvision.models as models

logger = logging.getLogger(__name__)

NUM_CLASSES = 4
CLASS_NAMES = [
    "NON_FIRE",
    "NATURAL_FIRE",
    "INDUSTRIAL_FIRE",
    "PERSISTENT_THERMAL_SOURCE"
]


class CustomSimpleConvNet(nn.Module):
    """
    Lightweight 4-layer Convolutional Neural Network.
    Used as an offline fallback model if pretrained torchvision weights download fails.
    """
    def __init__(self, num_classes: int = NUM_CLASSES):
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(3, 32, kernel_size=3, padding=1),
            nn.BatchNorm2d(32),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2, 2),
            
            nn.Conv2d(32, 64, kernel_size=3, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2, 2),

            nn.Conv2d(64, 128, kernel_size=3, padding=1),
            nn.BatchNorm2d(128),
            nn.ReLU(inplace=True),
            nn.AdaptiveAvgPool2d((4, 4))
        )
        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Linear(128 * 4 * 4, 128),
            nn.ReLU(inplace=True),
            nn.Dropout(0.3),
            nn.Linear(128, num_classes)
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.features(x)
        return self.classifier(x)


class SatelliteVisionModel(nn.Module):
    """
    Trainable Computer Vision Model for Satellite Optical Patch Classification.
    Supports Transfer Learning with ResNet18 and EfficientNet-B0.
    """

    def __init__(
        self,
        architecture: str = "resnet18",
        num_classes: int = NUM_CLASSES,
        pretrained: bool = True
    ):
        super().__init__()
        self.architecture = architecture.lower()
        self.num_classes = num_classes

        if "resnet" in self.architecture:
            try:
                weights = models.ResNet18_Weights.DEFAULT if pretrained else None
                base_model = models.resnet18(weights=weights)
            except Exception as e:
                logger.warning(f"Could not load pretrained ResNet18 weights ({e}). Initializing without pretrained weights.")
                base_model = models.resnet18(weights=None)

            in_features = base_model.fc.in_features
            base_model.fc = nn.Linear(in_features, num_classes)
            self.backbone = base_model

        elif "efficientnet" in self.architecture:
            try:
                weights = models.EfficientNet_B0_Weights.DEFAULT if pretrained else None
                base_model = models.efficientnet_b0(weights=weights)
            except Exception as e:
                logger.warning(f"Could not load pretrained EfficientNet weights ({e}). Initializing without pretrained weights.")
                base_model = models.efficientnet_b0(weights=None)

            in_features = base_model.classifier[1].in_features
            base_model.classifier[1] = nn.Linear(in_features, num_classes)
            self.backbone = base_model

        else:
            logger.info(f"Using CustomSimpleConvNet architecture for {self.architecture}")
            self.backbone = CustomSimpleConvNet(num_classes=num_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.backbone(x)

    def predict_proba(self, x: torch.Tensor) -> torch.Tensor:
        logits = self.forward(x)
        return torch.softmax(logits, dim=1)


def build_satellite_model(
    architecture: str = "resnet18",
    num_classes: int = NUM_CLASSES,
    pretrained: bool = True
) -> SatelliteVisionModel:
    """Factory function creating a SatelliteVisionModel instance."""
    return SatelliteVisionModel(architecture=architecture, num_classes=num_classes, pretrained=pretrained)
