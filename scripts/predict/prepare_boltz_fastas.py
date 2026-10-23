#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

import gemmi
from Bio import Align


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_IDS = ROOT / "mhc_data/test_templated.txt"
DEFAULT_CSV = ROOT / "mhc_data/TCR3d_data.csv"
DEFAULT_OUTPUT = Path("/home/gpu/test_yamls_boltz")
DEFAULT_CIF_CACHE = Path("/home/gpu/test_yamls_cif")
CONTACT_RADIUS_ANGSTROM = 4.0
MIN_INTERFACE_CONTACTS = 10
MIN_MHC_RESIDUES = 100
MIN_PEPTIDE_RESIDUES = 8
MAX_PEPTIDE_RESIDUES = 25


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build Boltz-compatible MHC-peptide FASTAs from RCSB mmCIF structures."
        )
    )
    parser.add_argument("--ids", type=Path, default=DEFAULT_IDS)
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--cif-cache", type=Path, default=DEFAULT_CIF_CACHE)
    parser.add_argument(
        "--pdb-ids",
        nargs="+",
        help="Prepare only these IDs (useful for a smoke test).",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow replacing output FASTAs and the selection report.",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Reuse successful FASTAs already recorded in selection_report.tsv.",
    )
    return parser.parse_args()


def read_catalog(csv_path: Path) -> dict[str, dict[str, str]]:
    with csv_path.open(newline="", encoding="utf-8-sig") as handle:
        rows = csv.DictReader(handle)
        return {
            row["PDB ID"].strip().upper(): row
            for row in rows
            if row.get("PDB ID", "").strip()
        }


def download_cif(pdb_id: str, cif_cache: Path) -> Path:
    cif_cache.mkdir(parents=True, exist_ok=True)
    cif_path = cif_cache / f"{pdb_id}.cif"
    if cif_path.is_file() and cif_path.stat().st_size > 0:
        return cif_path

    url = f"https://files.rcsb.org/download/{pdb_id.lower()}.cif"
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "nempa-boltz-mhc-predict-preparer/1.0"},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        content = response.read()
    if not content:
        raise ValueError(f"RCSB returned an empty CIF for {pdb_id}.")
    cif_path.write_bytes(content)
    return cif_path


def load_model(cif_path: Path) -> tuple[gemmi.Structure, gemmi.Model]:
    document = gemmi.cif.read(str(cif_path))
    structure = gemmi.make_structure_from_block(document.sole_block())
    structure.setup_entities()
    if len(structure) == 0:
        raise ValueError(f"CIF has no coordinate model: {cif_path}")
    return structure, structure[0]


def protein_sequence(chain: gemmi.Chain) -> str:
    polymer = chain.get_polymer()
    if not polymer or polymer.check_polymer_type() != gemmi.PolymerType.PeptideL:
        return ""
    return polymer.make_one_letter_sequence().replace("-", "").upper()


def reference_mhc_sequence(reference_cif: Path) -> str:
    _, model = load_model(reference_cif)
    reference_chain = model.find_chain("A")
    if reference_chain is None:
        raise ValueError("The 1A1M reference CIF has no chain A.")
    sequence = protein_sequence(reference_chain)
    if not sequence:
        raise ValueError("Could not extract the 1A1M MHC reference sequence.")
    return sequence


def choose_mhc(model: gemmi.Model, reference_sequence: str) -> gemmi.Chain:
    aligner = Align.PairwiseAligner()
    aligner.mode = "local"
    candidates = [
        (aligner.score(reference_sequence, sequence), chain)
        for chain in model
        if len(sequence := protein_sequence(chain)) >= MIN_MHC_RESIDUES
    ]
    if not candidates:
        raise ValueError("No protein chain long enough to be an MHC candidate.")
    candidates.sort(key=lambda item: (-item[0], item[1].name))
    if candidates[0][0] <= 0:
        raise ValueError("No target chain aligned to the 1A1M MHC reference.")
    return candidates[0][1]


def interface_contacts(
    structure: gemmi.Structure,
    model: gemmi.Model,
    mhc_chain: gemmi.Chain,
    peptide_chain: gemmi.Chain,
) -> int:
    neighbor_search = gemmi.NeighborSearch(
        model, structure.cell, CONTACT_RADIUS_ANGSTROM
    )
    neighbor_search.populate(include_h=False)
    contacts = 0
    for residue in peptide_chain:
        if residue.is_water():
            continue
        for atom in residue:
            if atom.element.name == "H":
                continue
            for mark in neighbor_search.find_atoms(
                atom.pos, "\0", radius=CONTACT_RADIUS_ANGSTROM
            ):
                if mark.to_cra(model).chain.name == mhc_chain.name:
                    contacts += 1
    return contacts


def choose_peptide(
    structure: gemmi.Structure,
    model: gemmi.Model,
    mhc_chain: gemmi.Chain,
    expected_sequence: str,
) -> tuple[gemmi.Chain, str, int]:
    candidates: list[tuple[int, str, gemmi.Chain]] = []
    for chain in model:
        if chain.name == mhc_chain.name:
            continue
        sequence = protein_sequence(chain)
        if not MIN_PEPTIDE_RESIDUES <= len(sequence) <= MAX_PEPTIDE_RESIDUES:
            continue
        if expected_sequence and sequence != expected_sequence:
            continue
        contacts = interface_contacts(structure, model, mhc_chain, chain)
        if contacts >= MIN_INTERFACE_CONTACTS:
            candidates.append((contacts, sequence, chain))

    if not candidates:
        if expected_sequence:
            raise ValueError(
                "CSV peptide sequence has no matching 8-25 residue chain with "
                f"at least {MIN_INTERFACE_CONTACTS} MHC contacts at "
                f"{CONTACT_RADIUS_ANGSTROM} A. Expected {expected_sequence}."
            )
        raise ValueError(
            "No 8-25 residue protein chain has at least "
            f"{MIN_INTERFACE_CONTACTS} MHC contacts at "
            f"{CONTACT_RADIUS_ANGSTROM} A."
        )

    candidates.sort(key=lambda item: (-item[0], item[2].name))
    contacts, sequence, chain = candidates[0]
    return chain, sequence, contacts


def format_boltz_fasta(mhc_sequence: str, peptide_sequence: str) -> str:
    return (
        f">A|protein\n{mhc_sequence}\n"
        f">B|protein\n{peptide_sequence}\n"
    )


def main() -> int:
    args = parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    args.cif_cache.mkdir(parents=True, exist_ok=True)

    if args.pdb_ids:
        pdb_ids = [pdb_id.strip().upper() for pdb_id in args.pdb_ids]
    else:
        pdb_ids = [
            line.strip().upper()
            for line in args.ids.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    invalid_ids = [pdb_id for pdb_id in pdb_ids if not re.fullmatch(r"[A-Z0-9]{4}", pdb_id)]
    if invalid_ids:
        raise SystemExit(f"Invalid PDB IDs: {invalid_ids}")
    if len(pdb_ids) != len(set(pdb_ids)):
        raise SystemExit("The input ID list contains duplicates.")

    catalog = read_catalog(args.csv)
    missing_catalog_ids = [pdb_id for pdb_id in pdb_ids if pdb_id not in catalog]
    if missing_catalog_ids:
        raise SystemExit(f"IDs missing from CSV: {missing_catalog_ids}")

    report_path = args.output / "selection_report.tsv"
    if report_path.exists() and not (args.overwrite or args.resume):
        raise SystemExit(f"Report already exists: {report_path} (use --overwrite).")
    existing_fastas = [args.output / f"{pdb_id}.fasta" for pdb_id in pdb_ids]
    collisions = [path for path in existing_fastas if path.exists()]
    if collisions and not (args.overwrite or args.resume):
        raise SystemExit(
            f"Output FASTAs already exist (example: {collisions[0]}); use --overwrite."
        )

    columns = [
        "pdb_id",
        "status",
        "mhc_chain",
        "peptide_chain",
        "peptide_source",
        "peptide_sequence",
        "interface_contacts_4A",
        "error",
    ]
    results_by_id: dict[str, dict[str, str]] = {}
    if args.resume and report_path.exists():
        with report_path.open(encoding="utf-8", newline="") as handle:
            for record in csv.DictReader(handle, delimiter="\t"):
                if (
                    record.get("status") in {"ok", "ok_preexisting"}
                    and (args.output / f"{record.get('pdb_id', '')}.fasta").is_file()
                ):
                    results_by_id[record["pdb_id"]] = record
    elif args.resume:
        for pdb_id in pdb_ids:
            fasta_path = args.output / f"{pdb_id}.fasta"
            if not fasta_path.is_file():
                continue
            lines = [line.strip() for line in fasta_path.read_text().splitlines()]
            if (
                len(lines) == 4
                and lines[0] == ">A|protein"
                and lines[2] == ">B|protein"
                and lines[1]
                and lines[3]
            ):
                results_by_id[pdb_id] = {
                    "pdb_id": pdb_id,
                    "status": "ok_preexisting",
                    "mhc_chain": "",
                    "peptide_chain": "",
                    "peptide_source": "preexisting_fasta",
                    "peptide_sequence": lines[3],
                    "interface_contacts_4A": "",
                    "error": "Selection details were not saved before the previous run stopped.",
                }

    def write_report() -> None:
        temporary_path = report_path.with_suffix(".tsv.tmp")
        with temporary_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=columns, delimiter="\t")
            writer.writeheader()
            for item in pdb_ids:
                if item in results_by_id:
                    writer.writerow(results_by_id[item])
            handle.flush()
        temporary_path.replace(report_path)

    write_report()

    reference_cif = download_cif("1A1M", args.cif_cache)
    reference_sequence = reference_mhc_sequence(reference_cif)

    for index, pdb_id in enumerate(pdb_ids, start=1):
        if args.resume and results_by_id.get(pdb_id, {}).get("status") == "ok":
            print(f"[{index}/{len(pdb_ids)}] {pdb_id} ... JA REGISTRADO")
            continue

        row = catalog[pdb_id]
        expected_sequence = row.get("Peptide*", "").strip().upper()
        if expected_sequence.lower() in {"", "none", "null"}:
            expected_sequence = ""

        print(f"[{index}/{len(pdb_ids)}] {pdb_id} ... ", end="", flush=True)
        record = {
            "pdb_id": pdb_id,
            "status": "error",
            "mhc_chain": "",
            "peptide_chain": "",
            "peptide_source": "",
            "peptide_sequence": "",
            "interface_contacts_4A": "",
            "error": "",
        }
        try:
            cif_path = download_cif(pdb_id, args.cif_cache)
            structure, model = load_model(cif_path)
            mhc_chain = choose_mhc(model, reference_sequence)
            peptide_chain, peptide_sequence, contacts = choose_peptide(
                structure, model, mhc_chain, expected_sequence
            )

            output_path = args.output / f"{pdb_id}.fasta"
            output_path.write_text(
                format_boltz_fasta(
                    protein_sequence(mhc_chain), peptide_sequence
                ),
                encoding="ascii",
            )
            record.update(
                status="ok",
                mhc_chain=mhc_chain.name,
                peptide_chain=peptide_chain.name,
                peptide_source="csv_exact" if expected_sequence else "interface_fallback",
                peptide_sequence=peptide_sequence,
                interface_contacts_4A=str(contacts),
            )
            print(
                f"OK ({mhc_chain.name}+{peptide_chain.name}, "
                f"{contacts} contacts, {record['peptide_source']})"
            )
        except (OSError, ValueError, KeyError, urllib.error.URLError, RuntimeError) as error:
            record["error"] = str(error).replace("\t", " ").replace("\n", " ")
            print(f"ERRO: {record['error']}")
        results_by_id[pdb_id] = record
        write_report()

    successes = sum(
        results_by_id.get(pdb_id, {}).get("status") in {"ok", "ok_preexisting"}
        for pdb_id in pdb_ids
    )
    failures = len(pdb_ids) - successes
    print(f"\nPreparados: {successes}/{len(pdb_ids)}")
    print(f"Relatorio: {report_path}")
    print(f"CIFs em cache: {args.cif_cache}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())