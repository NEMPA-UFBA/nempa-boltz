import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import hydra
import omegaconf
import pytorch_lightning as pl
import torch
import torch.multiprocessing
from omegaconf import OmegaConf, listconfig
from pytorch_lightning import LightningModule
from pytorch_lightning.callbacks.model_checkpoint import ModelCheckpoint
from pytorch_lightning.loggers import WandbLogger
from pytorch_lightning.strategies import DDPStrategy
from pytorch_lightning.utilities import rank_zero_only

from boltz.data.module.training import BoltzTrainingDataModule, DataConfig


def load_pretrained_weights(model: LightningModule, checkpoint_path: str) -> None:
    """Load a pretrained Boltz checkpoint into a configured model.

    For LoRA-wrapped linear layers, map the pretrained ``layer.weight`` and
    ``layer.bias`` keys to ``layer.original_layer.weight`` and
    ``layer.original_layer.bias``. Keep newly initialized adapter parameters.
    """
    checkpoint = torch.load(checkpoint_path, map_location="cpu")
    state_dict = checkpoint.get("state_dict", checkpoint)
    model_keys = set(model.state_dict())
    mapped_state_dict = {}

    for key, value in state_dict.items():
        mapped_key = key
        if mapped_key not in model_keys:
            prefix, separator, leaf = key.rpartition(".")
            if separator:
                candidate = f"{prefix}.original_layer.{leaf}"
                if candidate in model_keys:
                    mapped_key = candidate
        mapped_state_dict[mapped_key] = value

    incompatible = model.load_state_dict(mapped_state_dict, strict=False)
    unexpected = list(incompatible.unexpected_keys)
    missing = [
        key
        for key in incompatible.missing_keys
        if ".lora_A" not in key and ".lora_B" not in key
    ]
    if unexpected or missing:
        details = []
        if missing:
            details.append(f"missing model weights: {missing[:20]}")
        if unexpected:
            details.append(f"unexpected checkpoint weights: {unexpected[:20]}")
        raise RuntimeError(
            "The pretrained checkpoint is not compatible with the configured "
            "model (" + "; ".join(details) + "). Refusing to continue with "
            "partially initialized base weights."
        )

    loaded = len(mapped_state_dict) - len(unexpected)
    print(
        f"Loaded {loaded} pretrained tensors from {checkpoint_path}; "
        f"left {len(incompatible.missing_keys)} LoRA adapter tensors initialized."
    )


@dataclass
class TrainConfig:
    """Train configuration.

    Attributes
    ----------
    data : DataConfig
        The data configuration.
    model : ModelConfig
        The model configuration.
    output : str
        The output directory.
    trainer : Optional[dict]
        The trainer configuration.
    resume : Optional[str]
        The resume checkpoint.
    pretrained : Optional[str]
        The pretrained model.
    wandb : Optional[dict]
        The wandb configuration.
    disable_checkpoint : bool
        Disable checkpoint.
    matmul_precision : Optional[str]
        The matmul precision.
    find_unused_parameters : Optional[bool]
        Find unused parameters.
    save_top_k : Optional[int]
        Save top k checkpoints.
    validation_only : bool
        Run validation only.
    debug : bool
        Debug mode.
    strict_loading : bool
        Fail on mismatched checkpoint weights.
    load_confidence_from_trunk: Optional[bool]
        Load pre-trained confidence weights from trunk.

    """

    data: DataConfig
    model: LightningModule
    output: str
    trainer: Optional[dict] = None
    resume: Optional[str] = None
    pretrained: Optional[str] = None
    wandb: Optional[dict] = None
    disable_checkpoint: bool = False
    matmul_precision: Optional[str] = None
    find_unused_parameters: Optional[bool] = False
    save_top_k: Optional[int] = 1
    validation_only: bool = False
    debug: bool = False
    strict_loading: bool = True
    load_confidence_from_trunk: Optional[bool] = False


def train(raw_config: str, args: list[str]) -> None:  # noqa: C901, PLR0912, PLR0915
    """Run training.

    Parameters
    ----------
    raw_config : str
        The input yaml configuration.
    args : list[str]
        Any command line overrides.

    """
    # Load the configuration
    raw_config = omegaconf.OmegaConf.load(raw_config)

    # Apply input arguments
    args = omegaconf.OmegaConf.from_dotlist(args)
    raw_config = omegaconf.OmegaConf.merge(raw_config, args)

    # Instantiate the task
    cfg = hydra.utils.instantiate(raw_config)
    cfg = TrainConfig(**cfg)

    # Set matmul precision
    if cfg.matmul_precision is not None:
        torch.set_float32_matmul_precision(cfg.matmul_precision)

    # Create trainer dict
    trainer = cfg.trainer
    if trainer is None:
        trainer = {}

    # Flip some arguments in debug mode
    devices = trainer.get("devices", 1)

    wandb = cfg.wandb
    if cfg.debug:
        if isinstance(devices, int):
            devices = 1
        elif isinstance(devices, (list, listconfig.ListConfig)):
            devices = [devices[0]]
        trainer["devices"] = devices
        cfg.data.num_workers = 0
        if wandb:
            wandb = None

    # Create objects
    data_config = DataConfig(**cfg.data)
    data_module = BoltzTrainingDataModule(data_config)
    model_module = cfg.model

    if cfg.pretrained and not cfg.resume:
        # Optionally broadcast the pretrained trunk into the confidence module.
        if cfg.load_confidence_from_trunk:
            checkpoint = torch.load(cfg.pretrained, map_location="cpu")
            state_dict = checkpoint.get("state_dict", checkpoint)
            new_state_dict = {}
            for key, value in state_dict.items():
                if not key.startswith("structure_module") and not key.startswith(
                    "distogram_module"
                ):
                    new_key = "confidence_module." + key
                    new_state_dict[new_key] = value
            new_state_dict.update(state_dict)
            checkpoint["state_dict"] = new_state_dict
            checkpoint_path = cfg.pretrained
            # Load the transformed state dict in memory without writing a temp file.
            model_keys = set(model_module.state_dict())
            mapped_state_dict = {}
            for key, value in new_state_dict.items():
                mapped_key = key
                if mapped_key not in model_keys:
                    prefix, separator, leaf = key.rpartition(".")
                    if separator:
                        candidate = f"{prefix}.original_layer.{leaf}"
                        if candidate in model_keys:
                            mapped_key = candidate
                mapped_state_dict[mapped_key] = value
            incompatible = model_module.load_state_dict(
                mapped_state_dict, strict=False
            )
            unexpected = list(incompatible.unexpected_keys)
            missing = [
                key
                for key in incompatible.missing_keys
                if ".lora_A" not in key and ".lora_B" not in key
            ]
            if unexpected or missing:
                raise RuntimeError(
                    "Checkpoint loading with load_confidence_from_trunk produced "
                    f"unexpected keys {unexpected[:20]} and missing keys "
                    f"{missing[:20]}. Refusing partial initialization."
                )
            print(
                f"Loaded pretrained trunk from {checkpoint_path} into the "
                "configured model; LoRA adapters remain initialized."
            )
        else:
            load_pretrained_weights(model_module, cfg.pretrained)

    # Create checkpoint callback
    callbacks = []
    dirpath = cfg.output
    if not cfg.disable_checkpoint:
        mc = ModelCheckpoint(
            monitor="val/lddt",
            save_top_k=cfg.save_top_k,
            save_last=True,
            mode="max",
            every_n_epochs=1,
        )
        callbacks = [mc]

    # Create wandb logger
    loggers = []
    if wandb:
        wdb_logger = WandbLogger(
            name=wandb["name"],
            group=wandb["name"],
            save_dir=cfg.output,
            project=wandb["project"],
            entity=wandb["entity"],
            log_model=False,
        )
        loggers.append(wdb_logger)
        # Save the config to wandb

        @rank_zero_only
        def save_config_to_wandb() -> None:
            config_out = Path(wdb_logger.experiment.dir) / "run.yaml"
            with Path.open(config_out, "w") as f:
                OmegaConf.save(raw_config, f)
            wdb_logger.experiment.save(str(config_out))

        save_config_to_wandb()

    # Set up trainer
    strategy = "auto"
    if (isinstance(devices, int) and devices > 1) or (
        isinstance(devices, (list, listconfig.ListConfig)) and len(devices) > 1
    ):
        strategy = DDPStrategy(find_unused_parameters=cfg.find_unused_parameters)

    trainer = pl.Trainer(
        default_root_dir=str(dirpath),
        strategy=strategy,
        callbacks=callbacks,
        logger=loggers,
        enable_checkpointing=not cfg.disable_checkpoint,
        reload_dataloaders_every_n_epochs=1,
        **trainer,
    )

    if not cfg.strict_loading:
        model_module.strict_loading = False

    if cfg.validation_only:
        trainer.validate(
            model_module,
            datamodule=data_module,
            ckpt_path=cfg.resume,
        )
    else:
        trainer.fit(
            model_module,
            datamodule=data_module,
            ckpt_path=cfg.resume,
        )


if __name__ == "__main__":
    arg1 = sys.argv[1]
    arg2 = sys.argv[2:]
    train(arg1, arg2)