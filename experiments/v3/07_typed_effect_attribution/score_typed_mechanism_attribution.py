from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
SEMISYNTH = HERE.parent / "02_semisynthetic"
for p in (HERE, SEMISYNTH):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import select_semisynthetic_estimator as sel
import tma_common as tma

MODELS = ("DCHAG_Learned", "Dense_Sequential_GFormula")


def write_json(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def verify_estimation(epath: Path) -> dict:
    m = json.loads((epath / "FREEZE_MANIFEST.json").read_text())
    if m.get("experiment_id") != tma.EXPERIMENT_ID or m.get("status") != "estimation_outputs_frozen_before_private_scoring":
        raise RuntimeError(f"invalid estimator freeze: {epath.name}")
    for name, digest in m["files"].items():
        if tma.sha256_file(epath / name) != digest:
            raise RuntimeError(f"estimator hash mismatch {epath.name}/{name}")
    md = json.loads((epath / "run_metadata.json").read_text())
    if md["estimator_private_SCM_access"] or md["confirmatory_hyperparameter_tuning"] or md["confirmatory_world_replacement"]:
        raise RuntimeError(f"guardrail violation in {epath.name}")
    if not md["common_random_numbers_across_coalitions"] or md["coalitions_per_control"] != 32:
        raise RuntimeError("C1 coalition-randomness guardrail failed")
    if md["standardization_anchor_units"] != 1500 or md["mc_reps_per_anchor"] != 100:
        raise RuntimeError("frozen MC/anchor setting mismatch")
    return md


def family_from_world(world: str) -> str:
    return world[len("confirm_"):].rsplit("_", 1)[0]


def dominant_component(mapping: dict[str, float]) -> str:
    maximum = max(abs(v) for v in mapping.values())
    ties = sorted(k for k, v in mapping.items() if abs(abs(v) - maximum) <= 1e-12)
    return ties[0]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--estimation-root", type=Path, required=True)
    ap.add_argument("--public-root", type=Path, required=True)
    ap.add_argument("--private-root", type=Path, required=True)
    ap.add_argument("--outdir", type=Path, required=True)
    args = ap.parse_args()
    args.outdir.mkdir(parents=True, exist_ok=True)

    worlds = sorted(p.name for p in args.estimation_root.iterdir() if p.is_dir() and p.name.startswith("confirm_"))
    if len(worlds) != 16:
        raise RuntimeError(f"expected 16 frozen estimator worlds, got {len(worlds)}")
    if worlds != sorted(p.name for p in args.private_root.iterdir() if p.is_dir() and p.name.startswith("confirm_")):
        raise RuntimeError("private world set mismatch")
    if worlds != sorted(p.name for p in args.public_root.iterdir() if p.is_dir() and p.name.startswith("confirm_")):
        raise RuntimeError("public world set mismatch")

    accuracy_rows = []; world_rows = []; dominant_rows = []; sign_rows = []
    oracle_rows = []; oracle_coalition_rows = []; diagnostics = []

    for world in worlds:
        md = verify_estimation(args.estimation_root / world)
        est = pd.read_csv(args.estimation_root / world / "typed_attribution.csv")
        if len(est) != 2 * 4 * 6:
            raise RuntimeError(f"unexpected estimator attribution rows for {world}: {len(est)}")
        pub = args.public_root / world
        schema = json.loads((pub / "schema.json").read_text())
        train = pd.read_csv(pub / "train.csv"); test = pd.read_csv(pub / "test.csv")
        anchors = np.concatenate([sel.anchor_tensor_one_split(train, int(schema["horizon"])),
                                  sel.anchor_tensor_one_split(test, int(schema["horizon"]))], axis=0)
        if len(anchors) != 1500:
            raise RuntimeError("oracle standardization anchor invariant failed")
        spec = json.loads((args.private_root / world / "world.json").read_text())
        family = family_from_world(world)
        oracle_by_control = {}
        for control in schema["controls"]:
            o = tma.oracle_attribution(spec, anchors, world, control, mc_reps=tma.MC_REPS)
            if o["closure_error"] > 1e-10 or o["replay_consistency_error"] > 1e-10:
                raise RuntimeError(f"oracle decomposition identity failed {world}/{control}")
            oracle_by_control[control] = dict(o["components"])
            for component, value in o["components"].items():
                oracle_rows.append({"world": world, "family": family, "control": control,
                                    "component": component, "oracle_attribution": value,
                                    "oracle_total_effect_replay": o["total_effect_replay"],
                                    "closure_error": o["closure_error"],
                                    "replay_consistency_error": o["replay_consistency_error"], "seed": o["seed"]})
            for coalition, value in o["coalition_values"].items():
                oracle_coalition_rows.append({"world": world, "family": family, "control": control,
                                              "coalition": coalition, "oracle_value": value, "seed": o["seed"]})

        for model in MODELS:
            q = est[est.model == model].copy(); errors = []
            for control in schema["controls"]:
                qq = q[q.control == control]
                estimates = {str(r.component): float(r.attribution) for _, r in qq.iterrows()}
                if set(estimates) != set(tma.COMPONENTS):
                    raise RuntimeError(f"component mismatch {world}/{model}/{control}")
                truth = oracle_by_control[control]
                for component in tma.COMPONENTS:
                    err = estimates[component] - truth[component]; errors.append(abs(err))
                    accuracy_rows.append({"world": world, "family": family, "model": model, "control": control,
                                          "component": component, "estimated_attribution": estimates[component],
                                          "oracle_attribution": truth[component], "signed_error": err, "abs_error": abs(err)})
                    if abs(truth[component]) >= 0.005:
                        sign_rows.append({"world": world, "family": family, "model": model, "control": control,
                                          "component": component, "oracle_attribution": truth[component],
                                          "estimated_attribution": estimates[component],
                                          "sign_agree": bool(np.sign(estimates[component]) == np.sign(truth[component]))})
                dom_t = dominant_component(truth); dom_e = dominant_component(estimates)
                dominant_rows.append({"world": world, "family": family, "model": model, "control": control,
                                      "oracle_dominant": dom_t, "estimated_dominant": dom_e, "correct": dom_t == dom_e})
            world_rows.append({"world": world, "family": family, "model": model, "tmae": float(np.mean(errors))})

        diagnostics.append({"world": world, "family": family,
                            "max_estimator_closure_error": float(est.closure_error.max()),
                            "max_estimator_replay_error": float(est.replay_consistency_error.max()),
                            "dchag_learned_edges": md["dchag_learned_edges"]})

    acc = pd.DataFrame(accuracy_rows); wdf = pd.DataFrame(world_rows); dom = pd.DataFrame(dominant_rows)
    sdf = pd.DataFrame(sign_rows); odf = pd.DataFrame(oracle_rows); ocdf = pd.DataFrame(oracle_coalition_rows)
    ddf = pd.DataFrame(diagnostics)
    acc.to_csv(args.outdir / "typed_attribution_accuracy.csv", index=False)
    wdf.to_csv(args.outdir / "world_tmae.csv", index=False)
    dom.to_csv(args.outdir / "dominant_mechanism_accuracy.csv", index=False)
    sdf.to_csv(args.outdir / "component_sign_agreement.csv", index=False)
    odf.to_csv(args.outdir / "oracle_typed_attribution.csv", index=False)
    ocdf.to_csv(args.outdir / "oracle_coalition_values.csv", index=False)
    ddf.to_csv(args.outdir / "diagnostics.csv", index=False)

    model_summary = []
    for model in MODELS:
        wm = wdf[wdf.model == model]; dm = dom[dom.model == model]; sm = sdf[sdf.model == model]
        model_summary.append({"model": model, "mean_world_tmae": float(wm.tmae.mean()),
                              "median_world_tmae": float(wm.tmae.median()),
                              "dominant_mechanism_accuracy": float(dm.correct.mean()),
                              "dominant_correct": int(dm.correct.sum()), "dominant_total": int(len(dm)),
                              "component_sign_agreement": float(sm.sign_agree.mean()) if len(sm) else None,
                              "sign_agree": int(sm.sign_agree.sum()) if len(sm) else 0, "sign_total": int(len(sm))})
    pd.DataFrame(model_summary).to_csv(args.outdir / "model_summary.csv", index=False)
    wdf.groupby(["family", "model"], as_index=False).tmae.mean().to_csv(args.outdir / "family_summary.csv", index=False)

    pivot = wdf.pivot(index="world", columns="model", values="tmae").loc[worlds]
    diffs = (pivot["DCHAG_Learned"] - pivot["Dense_Sequential_GFormula"]).to_numpy(float)
    lo, hi = tma.bootstrap_ci(diffs)
    paired = {"n_independent_worlds": 16, "mean_dchag_minus_dense_tmae": float(diffs.mean()),
              "bootstrap_reps": tma.BOOTSTRAP_REPS, "bootstrap_seed": tma.BOOTSTRAP_SEED,
              "bootstrap95_low": lo, "bootstrap95_high": hi, "exact_signflip_assignments": 65536,
              "exact_two_sided_signflip_p": tma.exact_signflip_p(diffs)}
    write_json(args.outdir / "paired_dchag_dense_tmae_inference.json", paired)

    summary_map = {r["model"]: r for r in model_summary}
    result = {"experiment_id": tma.EXPERIMENT_ID, "base_experiment_id": tma.BASE_EXPERIMENT_ID,
              "status": "PASS", "n_worlds": 16, "controls_per_world": 4,
              "components": list(tma.COMPONENTS), "coalitions_per_control": 32,
              "anchor_units_per_world": 1500, "mc_reps_per_anchor": 100,
              "models": summary_map, "paired_dchag_dense_tmae_inference": paired,
              "max_estimator_closure_error": float(ddf.max_estimator_closure_error.max()),
              "max_estimator_replay_consistency_error": float(ddf.max_estimator_replay_error.max()),
              "max_oracle_closure_error": float(odf.closure_error.max()),
              "max_oracle_replay_consistency_error": float(odf.replay_consistency_error.max()),
              "guardrails": {"common_random_numbers_across_coalitions": True,
                             "confirmatory_hyperparameter_tuning": False,
                             "confirmatory_world_replacement": False,
                             "estimator_private_SCM_access": False,
                             "estimation_outputs_frozen_before_private_scoring": True,
                             "negative_and_null_components_retained": True},
              "claim_boundary": "Typed mechanism-replay attribution is validated only against the explicit semi-synthetic SCM oracle; it is not a natural indirect effect and does not establish real LANL causal mechanisms or real defensive-control effectiveness."}
    write_json(args.outdir / "TYPED_MECHANISM_ATTRIBUTION_RESULTS.json", result)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
