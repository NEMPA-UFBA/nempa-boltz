import argparse
import json
import os
import tempfile
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Filter a Boltz manifest to records with structure NPZ files."
    )
    parser.add_argument("manifest", type=Path)
    parser.add_argument(
        "--structures",
        type=Path,
        help="Directory containing structure NPZ files (default: manifest sibling structures/).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output sidecar path (default: manifest.physical.json beside the input).",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Write the filtered sidecar. Without this flag, only report counts.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow replacing the output sidecar if it already exists.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest_path = args.manifest.resolve()
    structures_dir = (args.structures or manifest_path.parent / "structures").resolve()
    output_path = (
        args.output or manifest_path.with_name("manifest.physical.json")
    ).resolve()

    if output_path == manifest_path:
        raise SystemExit("Refusing to overwrite the source manifest.")

    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        records = data
        wrap_output = lambda filtered: filtered
    elif isinstance(data, dict) and isinstance(data.get("records"), list):
        records = data["records"]
        wrap_output = lambda filtered: {**data, "records": filtered}
    else:
        raise SystemExit("Expected a list of records or an object with a records list.")

    structure_ids = {path.stem.lower() for path in structures_dir.glob("*.npz")}
    record_ids = [str(record["id"]).lower() for record in records]
    if len(record_ids) != len(set(record_ids)):
        raise SystemExit("Source manifest contains duplicate record IDs; refusing to write.")

    filtered = [
        record
        for record, record_id in zip(records, record_ids, strict=True)
        if record_id in structure_ids
    ]
    manifest_ids = set(record_ids)
    print(f"Manifest records: {len(records)}")
    print(f"Structure NPZ files: {len(structure_ids)}")
    print(f"Records retained: {len(filtered)}")
    print(f"Manifest records without NPZ: {len(manifest_ids - structure_ids)}")
    print(f"NPZ files without manifest record: {len(structure_ids - manifest_ids)}")

    if not args.write:
        print("Dry run; no files written. Pass --write to create the sidecar.")
        return 0

    if output_path.exists() and not args.overwrite:
        raise SystemExit(f"Output already exists: {output_path} (use --overwrite to replace it).")

    payload = json.dumps(wrap_output(filtered), ensure_ascii=False, indent=2) + "\n"
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=output_path.parent,
        prefix=f".{output_path.name}.",
        suffix=".tmp",
        delete=False,
    ) as temporary:
        temporary.write(payload)
        temporary_path = Path(temporary.name)

    os.replace(temporary_path, output_path)
    print(f"Wrote sidecar: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())