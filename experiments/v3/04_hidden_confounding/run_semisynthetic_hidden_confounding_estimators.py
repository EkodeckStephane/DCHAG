from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SEMISYNTH = HERE.parent / "02_semisynthetic"
if str(SEMISYNTH) not in sys.path:
    sys.path.insert(0, str(SEMISYNTH))

import run_semisynthetic_confirmatory_estimators as base  # noqa: E402
import run_semisynthetic_confirmatory_estimators_c1 as c1  # noqa: E402

EXPERIMENT_ID = "V3-SS-HC-001"
LEVELS = {"moderate": 0.50, "strong": 1.00}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--public-root", type=Path, required=True)
    parser.add_argument("--frozen-estimator", type=Path, required=True)
    parser.add_argument("--level", choices=sorted(LEVELS), required=True)
    parser.add_argument("--world", required=True)
    parser.add_argument("--outdir", type=Path, required=True)
    args = parser.parse_args()

    c1.run_world(args.public_root, args.frozen_estimator, args.world, args.outdir)
    out = args.outdir / args.world
    metadata_path = out / "run_metadata.json"
    metadata = json.loads(metadata_path.read_text())
    metadata.update({
        "experiment_id": EXPERIMENT_ID,
        "analysis": "hidden_confounding_sensitivity",
        "hidden_confounding_level": args.level,
        "hidden_confounding_lambda": LEVELS[args.level],
        "hidden_confounder_observed_by_estimator": False,
        "estimator_private_SCM_access": False,
        "hyperparameter_retuning_for_hidden_confounding": False,
        "estimator_mc_seed_namespace": "V3-SS-CONF-001 reused unchanged across severity levels for paired Monte Carlo comparability",
    })
    base.write_json(metadata_path, metadata)

    manifest_path = out / "freeze_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest.update({
        "experiment_id": EXPERIMENT_ID,
        "hidden_confounding_level": args.level,
        "hidden_confounding_lambda": LEVELS[args.level],
        "hidden_confounder_observed_by_estimator": False,
        "frozen_before_private_scoring": True,
    })
    for name in list(manifest["files"]):
        manifest["files"][name] = base.sha256_file(out / name)
    base.write_json(manifest_path, manifest)
    print(json.dumps({"experiment_id": EXPERIMENT_ID, "level": args.level, "world": args.world, "status": "FROZEN"}, sort_keys=True))


if __name__ == "__main__":
    main()
