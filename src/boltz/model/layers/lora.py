import math
from dataclasses import dataclass, field
from typing import List, Optional, Union, Any

import torch
import torch.nn as nn
import torch.nn.functional as F

@dataclass
class LoRAConfig:
    r: int = 8
    lora_alpha: int = 16
    lora_dropout: float = 0.0
    target_modules: List[str] = field(default_factory=list)
    bias: str = "none"  # "none", "all", or "lora_only"

class LoRALinear(nn.Module):
    def __init__(
        self, 
        linear_layer: nn.Linear,
        r: int,
        lora_alpha: int,
        lora_dropout: float,
        fan_in_fan_out: bool = False,
        merge_weights: bool = True,
    ):
        super().__init__()
        self.r = r
        self.lora_alpha = lora_alpha
        self.lora_dropout = nn.Dropout(p=lora_dropout) if lora_dropout > 0.0 else nn.Identity()
        self.fan_in_fan_out = fan_in_fan_out
        self.merge_weights_flag = merge_weights

        self.original_layer = linear_layer
        self.in_features = linear_layer.in_features
        self.out_features = linear_layer.out_features

        if r > 0:
            self.lora_A = nn.Parameter(torch.zeros(self.in_features, r))
            self.lora_B = nn.Parameter(torch.zeros(r, self.out_features))
            self.scaling = self.lora_alpha / self.r

            # Initialize LoRA matrices
            nn.init.kaiming_uniform_(self.lora_A, a=math.sqrt(5))
            nn.init.zeros_(self.lora_B)

            # Freeze original weights
            self.original_layer.weight.requires_grad = False
            if self.original_layer.bias is not None:
                self.original_layer.bias.requires_grad = False
        
        self.merged = False

    def forward(self, x: torch.Tensor):
        original_output = self.original_layer(x)
        if self.r > 0 and not self.merged:
            lora_output = self.lora_dropout(x) @ self.lora_A @ self.lora_B * self.scaling
            return original_output + lora_output.to(original_output.dtype)
        else:
            return original_output

    def merge_weights(self):
        if self.r > 0 and not self.merged:
            if self.fan_in_fan_out:
                self.original_layer.weight.data += (self.lora_B.T @ self.lora_A.T) * self.scaling
            else:
                self.original_layer.weight.data += (self.lora_A @ self.lora_B).T * self.scaling
            self.merged = True

    def unmerge_weights(self):
        if self.r > 0 and self.merged:
            if self.fan_in_fan_out:
                self.original_layer.weight.data -= (self.lora_B.T @ self.lora_A.T) * self.scaling
            else:
                self.original_layer.weight.data -= (self.lora_A @ self.lora_B).T * self.scaling
            self.merged = False

def mark_only_lora_as_trainable(model: nn.Module, bias: str = "none"):
    for n, p in model.named_parameters():
        if "lora_A" not in n and "lora_B" not in n:
            p.requires_grad = False
    
    if bias == "all":
        for n, p in model.named_parameters():
            if "bias" in n:
                p.requires_grad = True
    elif bias == "lora_only":
        for n, p in model.named_parameters():
            if "lora_A" not in n and "lora_B" not in n and "bias" in n:
                p.requires_grad = False

def apply_lora_to_linear_layers(model: nn.Module, config: LoRAConfig):
    replacements = []
    for name, module in model.named_modules():
        if isinstance(module, nn.Linear) and not isinstance(module, LoRALinear):
            if any(target_key in name for target_key in config.target_modules):
                replacements.append((name, module))
    
    for name, module in replacements:
        parts = name.split('.')
        parent_module = model
        for part in parts[:-1]:
            parent_module = getattr(parent_module, part)
        lora_module = LoRALinear(module, config.r, config.lora_alpha, config.lora_dropout, merge_weights=True)
        setattr(parent_module, parts[-1], lora_module)

    mark_only_lora_as_trainable(model, config.bias)
