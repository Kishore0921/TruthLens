"""
TruthLens Image CNN — Custom forensic image classifier trained from scratch.
Architecture: 4-block CNN with BatchNorm, GlobalAvgPool, Dropout.
Task: Binary classification — REAL (class 0) vs AI_GENERATED (class 1).
"""
import torch
import torch.nn as nn


class ConvBlock(nn.Module):
    """Conv2d → BatchNorm → ReLU → MaxPool."""
    def __init__(self, in_channels: int, out_channels: int, kernel_size: int = 3,
                 padding: int = 1, pool_size: int = 2):
        super().__init__()
        self.block = nn.Sequential(
            nn.Conv2d(in_channels, out_channels, kernel_size=kernel_size, padding=padding),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(pool_size),
        )

    def forward(self, x):
        return self.block(x)


class TruthLensImageCNN(nn.Module):
    """
    4-block CNN for binary AI-generated image detection.

    Input  : RGB 128×128 (3 channels)
    Output : 2-class logits [REAL, AI_GENERATED]
    """
    def __init__(self, num_classes: int = 2, dropout: float = 0.4):
        super().__init__()
        self.features = nn.Sequential(
            ConvBlock(3, 32),     # 128→64
            ConvBlock(32, 64),    # 64→32
            ConvBlock(64, 128),   # 32→16
            ConvBlock(128, 256),  # 16→8
        )
        self.global_pool = nn.AdaptiveAvgPool2d(1)   # 8→1
        self.classifier = nn.Sequential(
            nn.Dropout(dropout),
            nn.Linear(256, num_classes),
        )
        self._init_weights()

    def _init_weights(self):
        """Kaiming uniform initialisation for conv, constant for BN."""
        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                nn.init.kaiming_uniform_(m.weight, nonlinearity="relu")
                if m.bias is not None:
                    nn.init.zeros_(m.bias)
            elif isinstance(m, nn.BatchNorm2d):
                nn.init.ones_(m.weight)
                nn.init.zeros_(m.bias)
            elif isinstance(m, nn.Linear):
                nn.init.kaiming_uniform_(m.weight, nonlinearity="relu")
                nn.init.zeros_(m.bias)

    def forward(self, x):
        x = self.features(x)
        x = self.global_pool(x)
        x = x.view(x.size(0), -1)
        x = self.classifier(x)
        return x

    @staticmethod
    def get_config() -> dict:
        return {
            "model_name": "TruthLens Image CNN",
            "model_version": "1.0",
            "architecture": "4-block CNN (Conv-BN-ReLU-MaxPool) + GAP + Dropout + FC",
            "input_size": 128,
            "num_classes": 2,
            "class_map": {0: "REAL", 1: "AI_GENERATED"},
            "model_type": "custom_cnn_trained_from_scratch",
            "pretrained": False,
        }


if __name__ == "__main__":
    model = TruthLensImageCNN()
    dummy = torch.randn(1, 3, 128, 128)
    out = model(dummy)
    total_params = sum(p.numel() for p in model.parameters())
    print(f"Output shape: {out.shape}")
    print(f"Total parameters: {total_params:,}")
    print(f"Config: {model.get_config()}")
