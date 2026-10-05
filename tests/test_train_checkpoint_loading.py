import torch
from torch import nn

from boltz.model.layers.lora import LoRALinear
from scripts.train.train import load_pretrained_weights


def test_load_pretrained_weights_copies_trunk_into_lora_confidence_module(tmp_path):
    model = nn.Module()
    model.linear = nn.Linear(2, 3)
    model.confidence_module = nn.Module()
    model.confidence_module.linear = LoRALinear(
        nn.Linear(2, 3), r=2, lora_alpha=4, lora_dropout=0.0
    )
    initial_lora_a = model.confidence_module.linear.lora_A.detach().clone()
    initial_lora_b = model.confidence_module.linear.lora_B.detach().clone()
    expected_weight = torch.full((3, 2), 2.0)
    expected_bias = torch.full((3,), 3.0)
    checkpoint_path = tmp_path / "synthetic.ckpt"
    torch.save(
        {
            "state_dict": {
                "linear.weight": expected_weight,
                "linear.bias": expected_bias,
            }
        },
        checkpoint_path,
    )

    load_pretrained_weights(
        model,
        str(checkpoint_path),
        load_confidence_from_trunk=True,
    )

    assert torch.equal(model.linear.weight, expected_weight)
    assert torch.equal(model.linear.bias, expected_bias)
    assert torch.equal(
        model.confidence_module.linear.original_layer.weight,
        expected_weight,
    )
    assert torch.equal(
        model.confidence_module.linear.original_layer.bias,
        expected_bias,
    )
    assert torch.equal(model.confidence_module.linear.lora_A, initial_lora_a)
    assert torch.equal(model.confidence_module.linear.lora_B, initial_lora_b)