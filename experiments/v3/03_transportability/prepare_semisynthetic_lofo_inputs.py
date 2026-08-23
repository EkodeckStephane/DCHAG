from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

EXPERIMENT_ID = "V3-SS-LOFO-001"
ANCHORS = ["A_person", "A_process", "A_technical"]
FAMILIES = ["bec_payment", "exfiltration", "helpdesk_identity", "itot_change"]
WORLDS = sorted([f"confirm_{family}_{i}" for family in FAMILIES for i in range(1, 5)])


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def write_json(path: str | Path, obj) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def family_from_world(world: str) -> str:
    for family in FAMILIES:
        if world.startswith(f"confirm_{family}_"):
            return family
    raise ValueError(world)


def schema_signature(schema: dict) -> dict:
    return {
        "horizon": int(schema["horizon"]),
        "order": list(schema["order"]),
        "anchor_nodes": list(schema["anchor_nodes"]),
        "controls": list(schema["controls"]),
        "target": schema["target"],
        "types": dict(schema["types"]),
    }


def anchor_tensor_one_split(df: pd.DataFrame, horizon: int) -> tuple[np.ndarray, np.ndarray]:
    data = df.sort_values(["trajectory_id", "time"]).reset_index(drop=True)
    ids = np.array(sorted(data["trajectory_id"].unique()), dtype=np.int64)
    if len(data) != len(ids) * horizon:
        raise RuntimeError("target split does not contain complete trajectory blocks")
    if not np.array_equal(data["trajectory_id"].to_numpy(np.int64), np.repeat(ids, horizon)):
        raise RuntimeError("target split trajectory blocks are not contiguous after sorting")
    if not np.array_equal(data["time"].to_numpy(np.int64), np.tile(np.arange(horizon), len(ids))):
        raise RuntimeError("target split trajectory time grid mismatch")
    anchors = data[ANCHORS].to_numpy(np.int8).reshape(len(ids), horizon, len(ANCHORS))
    return ids, anchors


def verify_parent_manifest(root: Path) -> None:
    manifest_path = root / "PUBLIC_MANIFEST.json"
    if not manifest_path.is_file():
        raise RuntimeError("parent PUBLIC_MANIFEST.json missing")
    manifest = json.loads(manifest_path.read_text())
    if manifest.get("experiment_id") != "V3-SS-CONF-001" or manifest.get("worlds") != 16:
        raise RuntimeError("unexpected parent public manifest")
    if manifest.get("contains_private_SCM_or_oracle") is not False:
        raise RuntimeError("parent public artifact claims private SCM/oracle material")
    for rel, digest in manifest.get("files", {}).items():
        p = root / rel
        if not p.is_file() or sha256_file(p) != digest:
            raise RuntimeError(f"parent public manifest hash mismatch: {rel}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--public-root", required=True, help="root containing PUBLIC_MANIFEST.json and public/<world>/")
    parser.add_argument("--outroot", required=True)
    args = parser.parse_args()

    root = Path(args.public_root)
    pub = root / "public"
    outroot = Path(args.outroot)
    verify_parent_manifest(root)
    worlds = sorted(p.name for p in pub.iterdir() if p.is_dir())
    if worlds != WORLDS:
        raise RuntimeError(f"unexpected parent world set: {worlds}")

    schemas = {}
    signatures = {}
    for world in worlds:
        schema = json.loads((pub / world / "schema.json").read_text())
        schemas[world] = schema
        signatures[world] = schema_signature(schema)
    first_sig = signatures[worlds[0]]
    if any(sig != first_sig for sig in signatures.values()):
        raise RuntimeError("LOFO requires identical structural schemas across all 16 worlds")
    if first_sig["horizon"] != 6 or first_sig["anchor_nodes"] != ANCHORS:
        raise RuntimeError("unexpected semisynthetic schema invariant")

    for heldout in FAMILIES:
        fold_root = outroot / heldout
        source_root = fold_root / "source_train"
        target_root = fold_root / "target_anchors"
        source_root.mkdir(parents=True, exist_ok=True)
        target_root.mkdir(parents=True, exist_ok=True)

        target_worlds = [f"confirm_{heldout}_{i}" for i in range(1, 5)]
        source_worlds = sorted(w for w in worlds if w not in set(target_worlds))
        if len(source_worlds) != 12:
            raise RuntimeError("LOFO source-world count mismatch")

        for world in source_worlds:
            if family_from_world(world) == heldout:
                raise RuntimeError("held-out family leaked into source training set")
            train = pd.read_csv(pub / world / "train.csv")
            if train["trajectory_id"].nunique() != 1100 or len(train) != 6600:
                raise RuntimeError(f"source train count mismatch: {world}")
            train.to_csv(source_root / f"{world}.csv", index=False)

        for world in target_worlds:
            train = pd.read_csv(pub / world / "train.csv")
            test = pd.read_csv(pub / world / "test.csv")
            train_ids, train_anchors = anchor_tensor_one_split(train, 6)
            test_ids, test_anchors = anchor_tensor_one_split(test, 6)
            if len(train_ids) != 1100 or len(test_ids) != 400:
                raise RuntimeError(f"target split count mismatch: {world}")
            if not np.array_equal(train_ids, np.arange(1100)) or not np.array_equal(test_ids, np.arange(400)):
                raise RuntimeError(f"unexpected target split-local IDs: {world}")
            np.savez_compressed(
                target_root / f"{world}.npz",
                train_anchors=train_anchors,
                test_anchors=test_anchors,
                test_ids=test_ids,
            )

        canonical = dict(schemas[source_worlds[0]])
        canonical["family"] = "LOFO_source_pool"
        canonical["world"] = f"LOFO_source_pool_excluding_{heldout}"
        write_json(fold_root / "canonical_schema.json", canonical)
        write_json(fold_root / "fold.json", {
            "experiment_id": EXPERIMENT_ID,
            "analysis_class": "locked_secondary_post_RQ1",
            "heldout_family": heldout,
            "source_families": sorted(set(FAMILIES) - {heldout}),
            "source_worlds": source_worlds,
            "target_worlds": target_worlds,
            "source_train_trajectories_per_world": 1100,
            "source_train_total_trajectories": 13200,
            "target_train_anchor_units_per_world": 1100,
            "target_test_anchor_units_per_world": 400,
            "target_standardization_anchor_units_per_world": 1500,
            "target_endogenous_or_outcome_columns_exported": False,
            "private_SCM_or_oracle_exported": False,
        })

        files = sorted(p for p in fold_root.rglob("*") if p.is_file())
        if any(p.name in {"test.csv", "world.json", "oracle_effects.json", "true_edges.json"} for p in files):
            raise RuntimeError(f"forbidden target/private file leaked into clean LOFO input for {heldout}")
        if any(p.suffix == ".csv" and family_from_world(p.stem) == heldout for p in source_root.glob("*.csv")):
            raise RuntimeError(f"held-out family source CSV leaked for {heldout}")
        manifest_files = {str(p.relative_to(fold_root)): sha256_file(p) for p in files}
        write_json(fold_root / "LOFO_INPUT_MANIFEST.json", {
            "experiment_id": EXPERIMENT_ID,
            "heldout_family": heldout,
            "parent_public_artifact_id": 9489870327,
            "parent_public_artifact_sha256": "0f1c6ebe2c46b65a649d9b3e27d8f4c3b375fa6797cae39a76b8dcd9645a9ff3",
            "files": manifest_files,
            "target_endogenous_or_outcome_data_present": False,
            "private_SCM_or_oracle_present": False,
        })

    print(json.dumps({
        "experiment_id": EXPERIMENT_ID,
        "folds": 4,
        "source_worlds_per_fold": 12,
        "target_worlds_per_fold": 4,
        "physical_target_family_firewall": "PASS",
    }, sort_keys=True))


if __name__ == "__main__":
    main()
