import math
from dataclasses import dataclass, field
from typing import List

import torch
import torch.nn as nn

@dataclass
class LoRAConfig:
    r: int = 8
    lora_alpha: int = 16
    lora_dropout: float = 0.0
    target_modules: List[str] = field(default_factory=list)
    bias: str = "none"  # "none", "all", or "lora_only"

    def __post_init__(self) -> None:
        if self.r <= 0:
            raise ValueError(f"LoRA rank r must be positive, got {self.r}.")
        if self.lora_alpha <= 0:
            raise ValueError(
                f"LoRA lora_alpha must be positive, got {self.lora_alpha}."
            )
        if not 0.0 <= self.lora_dropout < 1.0:
            raise ValueError(
                "LoRA lora_dropout must be in [0, 1), "
                f"got {self.lora_dropout}."
            )
        if not self.target_modules or not all(
            isinstance(name, str) and name for name in self.target_modules
        ):
            raise ValueError(
                "LoRA target_modules must be a non-empty list of module-name "
                "substrings."
            )
        if self.bias not in {"none", "all", "lora_only"}:
            raise ValueError(
                "LoRA bias must be 'none', 'all', or 'lora_only', "
                f"got {self.bias!r}."
            )

class LoRALinear(nn.Module):
    def __init__(
        self, 
        linear_layer: nn.Linear,
        r: int,
        lora_alpha: int,
        lora_dropout: float,
    ):
        super().__init__()
        self.r = r
        self.lora_alpha = lora_alpha
        self.lora_dropout = nn.Dropout(p=lora_dropout) if lora_dropout > 0.0 else nn.Identity()
        self.original_layer = linear_layer
        self.in_features = linear_layer.in_features
        self.out_features = linear_layer.out_features

        self.lora_A = nn.Parameter(torch.empty(self.in_features, r))
        self.lora_B = nn.Parameter(torch.zeros(r, self.out_features))
        self.scaling = self.lora_alpha / self.r
        nn.init.kaiming_uniform_(self.lora_A.T, a=math.sqrt(5))

        # Keep pretrained base weights fixed and train only the adapters.
        self.original_layer.weight.requires_grad_(False)
        if self.original_layer.bias is not None:
            self.original_layer.bias.requires_grad_(False)

    def forward(self, x: torch.Tensor):
        base_output = self.original_layer(x)
        lora_output = self.lora_dropout(x) @ self.lora_A @ self.lora_B
        return base_output + (lora_output * self.scaling).to(base_output.dtype)

def mark_only_lora_as_trainable(model: nn.Module, bias: str = "none") -> None:
    for n, p in model.named_parameters():
        p.requires_grad_("lora_A" in n or "lora_B" in n)

    if bias == "all":
        for n, p in model.named_parameters():
            if "bias" in n:
                p.requires_grad_(True)
    elif bias == "lora_only":
        for module in model.modules():
            if isinstance(module, LoRALinear) and module.original_layer.bias is not None:
                module.original_layer.bias.requires_grad_(True)

def apply_lora_to_linear_layers(model: nn.Module, config: LoRAConfig) -> int:
    replacements = []
    for name, module in model.named_modules():
        if isinstance(module, nn.Linear) and any(
            target_key in name for target_key in config.target_modules
        ):
            replacements.append((name, module))

    if not replacements:
        available = [
            name
            for name, module in model.named_modules()
            if isinstance(module, nn.Linear)
        ]
        raise ValueError(
            "LoRA target_modules matched no nn.Linear layers. "
            f"Requested={config.target_modules!r}; example available layers: "
            f"{available[:20]}"
        )

    for name, module in replacements:
        parts = name.split(".")
        parent_module = model
        for part in parts[:-1]:
            parent_module = getattr(parent_module, part)
        setattr(
            parent_module,
            parts[-1],
            LoRALinear(
                module,
                config.r,
                config.lora_alpha,
                config.lora_dropout,
            ),
        )

    mark_only_lora_as_trainable(model, config.bias)
    return len(replacements)
