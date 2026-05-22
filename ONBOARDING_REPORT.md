# ONBOARDING REPORT — nempa-boltz

Purpose: concise, read-only technical onboarding for the local nempa-boltz repository. This document is intended to be used standalone: it contains the top-level folder layout, the key code excerpts you need to understand data flow, tokenization, featurization, model forward and training logic, and the primary losses and metrics. No code executed. Only this file was created/modified.

**Repository Summary**
- **Language:** Python (primary). Core libs: PyTorch, PyTorch Lightning, Hydra/OmegaConf, NumPy. Telemetry: Weights & Biases.
- **Primary areas:** data preprocessing (rcsb/NPZ), featurization/tokenization, trunk/Evoformer-like pair/msa stacks, diffusion-based structure generator, optional confidence module, training scripts (Hydra configs).

**Files Changed vs tag `v1.0.0` (src/ only)**
- Modified (tracked by git diff v1.0.0..HEAD -- src/):
  - [src/boltz/data/feature/featurizer.py](src/boltz/data/feature/featurizer.py)
  - [src/boltz/data/module/inference.py](src/boltz/data/module/inference.py)
  - [src/boltz/data/module/training.py](src/boltz/data/module/training.py)
  - [src/boltz/data/write/writer.py](src/boltz/data/write/writer.py)
  - [src/boltz/main.py](src/boltz/main.py)
  - [src/boltz/model/modules/diffusion.py](src/boltz/model/modules/diffusion.py)
  - [src/boltz/model/optim/scheduler.py](src/boltz/model/optim/scheduler.py)

**Files Added Locally (new vs v1.0.0)**
- High-level additions (selected):
  - nempa analysis & scripts: [filter_mhc.py](filter_mhc.py), [auditar_dados.py](auditar_dados.py), [analise_descartes.py](analise_descartes.py).
  - MHC experiment data and helpers: `mhc_data/` (templated JSONs, TCR3d CSV, filtered manifests), `mhc_finetune/` (wandb runs, checkpoints), `mhc_split.txt`, `mhc_train.txt`.
  - Supporting utilities: `raio_x_npz.py`, `iniciar_treino.sh`, `get_subsamples.py`, various mapping/text files.

**Large data/artifact locations (local)**
- MHC and processed RCSB artifacts (too large to include in repo):
  - `mhc_data/` — templated jsons and many .npz structure files (dataset artifacts).
  - `rcsb_processed_targets/manifest.json` — very large manifest.
  - `mhc_finetune/` — local WandB run folders, run YAMLs and `checkpoints/` with epoch=*.ckpt and last.ckpt.
  - `boltz_checkpoints/` — `boltz1.ckpt`, `boltz1_conf.ckpt` present.

**Data pipeline (high-level flow)**
1. Manifest / templates / NPZ inputs: manifests (JSON), structure NPZs (per-target structures), MSA files (.npz / a3m-like).
2. Loader: `src/boltz/data/module/*` (BoltzTrainingDataModule, TrainingDataset, ValidationDataset) — loads records via `load_input()` then tokenizes.
3. Tokenization: `src/boltz/data/tokenize/boltz.py` → Tokenized objects (tokens, chain info, `cyclic_period` added when missing).
4. Featurization: `src/boltz/data/feature/featurizer.py` → `BoltzFeaturizer.process()` produces feature dict keys used by model: token features (`res_type`, `profile`, `deletion_mean`, `pocket_feature`, `token_pad_mask`, `msa`, ...), atom features (`atom_coords`, `atom_pad_mask`, `atom_to_token`, ...), MSA features, and optional constraint/symmetry features.
5. Model input: `feats` dict passed to `Boltz1.input_embedder` and to trunk (MSAModule, PairformerModule) and structure module (AtomDiffusion).
6. Outputs: distogram (`pdistogram`), sampled atom coords (`sample_atom_coords`), confidence outputs (when enabled): `plddt`, `pde`, `pae`, `ptm`, `iptm`, etc.

**Model & training architecture (concise)**
- Model class: `src/boltz/model/model.py` — `Boltz1` LightningModule.
- Core components:
  - InputEmbedder (atom encoder + token concatenation) → produces `s_inputs`.
  - Pairwise / MSA stack: `MSAModule`, `PairformerModule` produce pairwise `z` and single `s` representations (Evoformer-like flow).
  - Distogram head: `DistogramModule` predicts categorical distance distributions.
  - Structure module: `AtomDiffusion` — diffusion-based score model produces atom coordinates (training via compute_loss in structure_module).
  - Optional `ConfidenceModule` predicts pLDDT/pTM-like metrics and can be initialized to imitate trunk weights (broadcast behavior in training script).
- Forward-pass (summary): featurizer -> input_embedder -> s_init/z_init -> pairformer (msa + pair updates) -> distogram; structure_module consumes s,z and atom features to compute diffusion loss and sample coordinates; confidence_module optionally consumes trunk outputs + sampled coords to predict confidence.

**Losses & metrics (where implemented)**
- Distogram: `src/boltz/model/loss/distogram.py` — cross-entropy / negative log-likelihood on binned distances.
- Diffusion/structure losses: implemented inside structure module; helper losses include `weighted_rigid_align`, `smooth_lddt_loss` (see `src/boltz/model/loss/diffusion.py`).
- Validation/metric functions: `factored_lddt_loss`, `factored_token_lddt_dist_loss`, `compute_plddt_mae`, `compute_pde_mae`, `compute_pae_mae` in `src/boltz/model/loss/validation.py` and `src/boltz/model/loss/confidence.py`.
- Logged metrics (validation): `val/lddt_<type>`, `val/disto_lddt_<type>`, `val/complex_lddt_<type>`, `val/rmsd`, `val/best_rmsd`, pLDDT/PAE/PDE MAEs when confidence enabled. Training logs include `train/distogram_loss`, `train/diffusion_loss`, `train/loss`, grads and param norms.

**Notable read-only findings (issues & compatibility fixes observed)**
- Backwards-compatibility: `cyclic_period` missing in older NPZs — handled defensively in `src/boltz/data/module/training.py` (insertion when absent) and `src/boltz/data/tokenize/boltz.py`.
- Robust writer: `src/boltz/data/write/writer.py` updated to tolerate missing `prediction["confidence_score"]` and to fallback to ranking logic.
- Debug prints: Several debug/temporary prints (strings like "IKARO ESTEVE AQ...") were found in exception handlers in dataset/featurizer code — present in repo (not modified here).
- Diffs vs v1.0.0 include plumbing for `compute_constraint_features` and symmetry features and minor scheduler/diffusion imports updates.

**Standalone reference — folder structure (top-level, trimmed)**
- nempa-boltz/
  - scripts/
    - train/
      - configs/
        - full.yaml
        - structure.yaml
      - assets/
        - validation_ids.txt
  - src/
    - boltz/
      - data/
        - module/
          - training.py
          - inference.py
        - tokenize/
          - boltz.py
        - feature/
          - featurizer.py
        - write/
          - writer.py
        - parse/
          - schema.py
        - types.py
      - model/
        - model.py
        - modules/
          - trunk.py
          - diffusion.py
          - encoders.py
        - loss/
          - distogram.py
          - validation.py
          - diffusion.py
        - optim/
          - scheduler.py
      - main.py
  - mhc_data/ (templated jsons, NPZs)
  - mhc_finetune/ (wandb runs + checkpoints)
  - boltz_checkpoints/ (boltz1.ckpt, boltz1_conf.ckpt)
  - filter_mhc.py, auditar_dados.py, analise_descartes.py, etc.

**Standalone reference — key code excerpts (read-only)**

1) Data loader: `load_input` (adds missing `cyclic_period` to chains)

```python
def load_input(record: Record, target_dir: Path, msa_dir: Path) -> Input:
    structure = np.load(target_dir / "structures" / f"{record.id}.npz")
    chains = structure["chains"]
    if "cyclic_period" not in chains.dtype.names:
        new_dtype = chains.dtype.descr + [("cyclic_period", "i4")]
        new_chains = np.empty(chains.shape, dtype=new_dtype)
        for name in chains.dtype.names:
            new_chains[name] = chains[name]
        new_chains["cyclic_period"] = 0
        chains = new_chains
    structure = Structure(..., chains=chains, ...)
    # load per-chain MSAs if present
    msas = {}
    for chain in record.chains:
        msa_id = chain.msa_id
        if msa_id != -1 and msa_id != "":
            msa = np.load(msa_dir / f"{msa_id}.npz")
            msas[chain.chain_id] = MSA(**msa)
    return Input(structure, msas)
```

2) Tokenization: `BoltzTokenizer.tokenize` (tokens include `cyclic_period`)

```python
class BoltzTokenizer(Tokenizer):
    def tokenize(self, data: Input) -> Tokenized:
        struct = data.structure
        token_data = []
        token_idx = 0
        atom_to_token = {}
        chains = struct.chains[struct.mask]
        for chain in chains:
            res_start = chain["res_idx"]
            res_end = chain["res_idx"] + chain["res_num"]
            for res in struct.residues[res_start:res_end]:
                if res["is_standard"]:
                    token = TokenData(..., cyclic_period=chain["cyclic_period"],)
                    token_data.append(astuple(token))
                    token_idx += 1
                else:
                    token = TokenData(..., cyclic_period=chain["cyclic_period"],)
                    token_data.append(astuple(token))
        tokenized = Tokenized(token_data, token_bonds, data.structure, data.msa, data.residue_constraints)
        return tokenized
```

3) Featurizer: `BoltzFeaturizer.process` (high-level signature and outputs)

```python
class BoltzFeaturizer:
    def process(self, data: Tokenized, training: bool, max_seqs: int = 4096, ..., compute_constraint_features: bool = False) -> dict[str, Tensor]:
        token_features = process_token_features(data, ...)
        atom_features = process_atom_features(data, ...)
        msa_features = process_msa_features(data, ...)
        symmetry_features = process_symmetry_features(data, ...) if compute_symmetries else {}
        residue_constraint_features = {}
        chain_constraint_features = {}
        if compute_constraint_features:
            residue_constraint_features = process_residue_constraint_features(data)
            chain_constraint_features = process_chain_feature_constraints(data)
        return {**token_features, **atom_features, **msa_features, **symmetry_features, **residue_constraint_features, **chain_constraint_features}
```

Common output keys (examples): `res_type`, `profile`, `deletion_mean`, `pocket_feature`, `token_pad_mask`, `msa`, `atom_coords`, `atom_pad_mask`, `atom_to_token`, `token_bonds`, `token_disto_mask`, `disto_target`, `disto_center`, `cyclic_period`.

4) Model forward (core parts) — `Boltz1.forward` (simplified)

```python
def forward(self, feats: dict[str, Tensor], recycling_steps: int = 0, ...):
    s_inputs = self.input_embedder(feats)
    s_init = self.s_init(s_inputs)
    z_init = self.z_init_1(s_inputs)[:, :, None] + self.z_init_2(s_inputs)[:, None, :]
    relative_position_encoding = self.rel_pos(feats)
    z_init = z_init + relative_position_encoding + self.token_bonds(feats["token_bonds"].float())
    s = torch.zeros_like(s_init)
    z = torch.zeros_like(z_init)
    for i in range(recycling_steps + 1):
        s = s_init + self.s_recycle(self.s_norm(s))
        z = z_init + self.z_recycle(self.z_norm(z))
        if not self.no_msa:
            z = z + self.msa_module(z, s_inputs, feats)
        s, z = self.pairformer_module(s, z, mask=mask, pair_mask=pair_mask)
    dict_out = {"pdistogram": self.distogram_module(z)}
    if self.training and self.structure_prediction_training:
        dict_out.update(self.structure_module(...))
    if not self.training or self.confidence_prediction:
        dict_out.update(self.structure_module.sample(...))
    if self.confidence_prediction:
        dict_out.update(self.confidence_module(...))
    return dict_out
```

5) Training step (loss aggregation) — `Boltz1.training_step`

```python
def training_step(self, batch, batch_idx):
    recycling_steps = random.randint(0, self.training_args.recycling_steps)
    out = self(feats=batch, recycling_steps=recycling_steps, ...)
    if self.structure_prediction_training:
        disto_loss, _ = distogram_loss(out, batch)
        diffusion_loss_dict = self.structure_module.compute_loss(batch, out, ...)
    else:
        disto_loss = 0.0
        diffusion_loss_dict = {"loss": 0.0, "loss_breakdown": {}}
    if self.confidence_prediction:
        true_coords, _, _, true_coords_resolved_mask = self.get_true_coordinates(...)
        confidence_loss_dict = confidence_loss(out, batch, true_coords, true_coords_resolved_mask, ...)
    else:
        confidence_loss_dict = {"loss": torch.tensor(0.0).to(batch["token_index"].device), "loss_breakdown": {}}
    loss = (self.training_args.confidence_loss_weight * confidence_loss_dict["loss"] + self.training_args.diffusion_loss_weight * diffusion_loss_dict["loss"] + self.training_args.distogram_loss_weight * disto_loss)
    self.log("train/loss", loss)
    return loss
```

6) Distogram loss (exact formula)

```python
def distogram_loss(output, feats):
    pred = output["pdistogram"]
    target = feats["disto_target"]
    mask = feats["token_disto_mask"]
    mask = mask[:, None, :] * mask[:, :, None]
    mask = mask * (1 - torch.eye(mask.shape[1])[None]).to(pred)
    errors = -1 * torch.sum(target * torch.nn.functional.log_softmax(pred, dim=-1), dim=-1)
    denom = 1e-5 + torch.sum(mask, dim=(-1, -2))
    mean = errors * mask
    mean = torch.sum(mean, dim=-1)
    mean = mean / denom[..., None]
    batch_loss = torch.sum(mean, dim=-1)
    global_loss = torch.mean(batch_loss)
    return global_loss, batch_loss
```

7) Factored LDDT loss (modalities) — key excerpt

```python
def factored_lddt_loss(true_atom_coords, pred_atom_coords, feats, atom_mask, multiplicity=1, cardinality_weighted=False):
    atom_type = (torch.bmm(feats["atom_to_token"].float(), feats["mol_type"].unsqueeze(-1).float()).squeeze(-1).long())
    atom_type = atom_type.repeat_interleave(multiplicity, 0)
    ligand_mask = (atom_type == const.chain_type_ids["NONPOLYMER"]).float()
    dna_mask = (atom_type == const.chain_type_ids["DNA"]).float()
    rna_mask = (atom_type == const.chain_type_ids["RNA"]).float()
    protein_mask = (atom_type == const.chain_type_ids["PROTEIN"]).float()
    true_d = torch.cdist(true_atom_coords, true_atom_coords)
    pred_d = torch.cdist(pred_atom_coords, pred_atom_coords)
    pair_mask = atom_mask[:, :, None] * atom_mask[:, None, :]
    pair_mask = pair_mask * (1 - torch.eye(pair_mask.shape[1], device=pair_mask.device))[None, :, :]
    # compute modality masks like dna_protein_mask, ligand_protein_mask, intra_* etc., then call lddt_dist(pred_d, true_d, mask, cutoff)
```

**Notes on completeness and limits**
- This report includes the most relevant code excerpts and the trimmed folder layout so it can be used standalone for onboarding and code reading.
- The repository contains many additional helper functions and modules (atom encoders, pairformer internals, diffusion sampling internals, featurizer internals). If you want, I can append additional code excerpts (e.g., `AtomDiffusion.compute_loss`, `PairformerModule` core loop, or `ConfidenceModule`) — tell me which components you want next.

Progress update: I updated the active TODOs and expanded the onboarding report with a standalone folder tree and selected, copy-pasteable code excerpts. Next: produce exhaustive file inventory (TASK 1) unless you request additional code excerpts first.

Prepared by GitHub Copilot.
