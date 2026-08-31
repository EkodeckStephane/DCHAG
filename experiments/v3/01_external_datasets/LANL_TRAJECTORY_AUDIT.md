# V3-LANL-TRAJ-001 — audited result

## Execution identity

- GitHub Actions run: `32498616088`
- Head commit: `946580c9f112d7ba87c0e509f249299f20b2eea0`
- Aggregate artifact: `dchag-v3-lanl-trajectory-results`
- Aggregate artifact ZIP SHA-256: `c0880c97d82906fc6e0bf06fbc1016cd1a702e77e83d3b08001fb61374338046`
- Aggregate JSON SHA-256: `2664df7f44c8df0630e41ed5152b9b6ae9ea566431d15505b41c6ef9d668a36`
- Primary trajectory artifact: `dchag-v3-lanl-trajectory-300s`
- Primary artifact ZIP SHA-256: `d6cb979953d4f68bd45b464ee74105dcd4b41ed1d41c976889d7bb931028150b`
- `LANL_TRAJECTORY_300S.csv.gz` SHA-256: `6c45852d95ce583aa95e39d6560ce2ef61a8f1e84e51c01cc38292c113cd1d22`

## Frozen overlap interval

The operational joint interval is `[118781, 172799]`. Host observations before the network stream begins are excluded from the joint trajectory construction. The host side excluded `22,619,980` pre-overlap records and retained `42,224,164` overlap records with canonical entities. The network side retained `115,949,436` overlap records. No malformed host or network record was observed in this run.

## Primary 300-s result

The primary representation contains `2,642,689` active device-window rows over `31,243` devices and window indices `0..180`.

- H present: `282,373` rows (`10.6851%`)
- P present: `1,543,478` rows (`58.4056%`)
- T present: `2,464,790` rows (`93.2683%`)
- all H/P/T present: `262,856` rows (`9.9465%`)
- H or P together with T: `1,367,251` rows (`51.7371%`)
- at least two evidence types: `1,385,096` rows (`52.4124%`)
- devices observed in both host and network modalities: `9,899` (`31.6839%` of retained devices)

## Granularity sensitivity

The 60-s representation contains `9,454,133` active device-window rows; the 900-s representation contains `1,080,204`. The multimodal-device fraction is invariant (`0.3168389719`) because modality membership is device-level. Co-occurrence increases with wider temporal aggregation: all-H/P/T rows are `3.6352%` at 60 s, `9.9465%` at 300 s and `16.3385%` at 900 s. Therefore co-occurrence counts must not be interpreted independently of window width.

## Continuity correction

The frozen protocol requested longest consecutive active-window continuity, but the original aggregate script reported only counts of active windows per device. `V3-LANL-TRAJ-001-C1` computes the omitted endpoint from the immutable retained 300-s artifact without changing the parent run.

At 300 s, the longest consecutive active-window run per device has median `7`, p90 `181`, and maximum `181`. `4,274` devices are active in all 181 windows; `9,512` have a run of at least 90 windows.

## Guardrails and claim boundary

The workflow guardrails passed: no attack/red-team labels were read, no defensive control `C` was inferred, and no counterfactual-effect claim is made. This result supports only operational trajectory construction, temporal persistence, cross-modal linkage and external observational plausibility. It does not validate causal intervention effects or causal edge direction.
