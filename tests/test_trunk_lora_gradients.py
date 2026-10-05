import torch

from boltz.model.layers.lora import LoRAConfig, apply_lora_to_linear_layers
from boltz.model.modules.trunk import PairformerModule


def test_pairformer_lora_backward_with_activation_checkpointing():
    torch.manual_seed(0)
    targets = [
        "attention.proj_q",
        "attention.proj_k",
        "attention.proj_v",
        "attention.proj_g",
        "attention.proj_o",
    ]
    module = PairformerModule(
        token_s=8,
        token_z=8,
        num_blocks=1,
        num_heads=2,
        dropout=0.0,
        pairwise_head_width=4,
        pairwise_num_heads=2,
        activation_checkpointing=True,
    )
    for parameter in module.parameters():
        parameter.requires_grad_(False)

    replaced = apply_lora_to_linear_layers(
        module,
        LoRAConfig(r=2, lora_alpha=4, target_modules=targets),
    )
    module.train()
    s = torch.randn(1, 3, 8)
    z = torch.randn(1, 3, 3, 8)
    mask = torch.ones(1, 3)
    pair_mask = torch.ones(1, 3, 3)

    s_out, z_out = module(s, z, mask, pair_mask)
    (s_out.square().mean() + z_out.square().mean()).backward()

    assert replaced == len(targets)
    assert any(
        parameter.grad is not None
        and torch.isfinite(parameter.grad).all()
        and torch.count_nonzero(parameter.grad).item() > 0
        for name, parameter in module.named_parameters()
        if "lora_B" in name
    )