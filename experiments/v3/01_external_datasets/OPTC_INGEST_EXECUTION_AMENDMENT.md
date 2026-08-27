# V3-OPTC-INGEST-001 — execution amendment

## Status

FROZEN before the resumed execution of V3-OPTC-INGEST-001.

## Reason

The original protocol, mapping, source identity, endpoints, exclusions, and claim boundary remain unchanged. The earlier non-execution was caused only by connector/container transfer limitations, not by a scientific defect.

This amendment changes execution orchestration only: a dedicated pull-request-triggered GitHub Actions workflow is added so the already frozen `run_optc_ingest.py` can retrieve the immutable public sample directly from `raw.githubusercontent.com` on the GitHub-hosted runner.

## Immutable scientific inputs

- source repository: `brbickel/ecar-challenge`
- commit: `45b7c7c85ddce4b44f84f68af7822c5466a7077d`
- path: `data.json`
- expected byte size: `5,649,857`
- expected Git blob SHA-1: `25279a41030981ead9bf6134432aa6112429eb82`
- mapping code: `optc_adapter.py`, unchanged
- ingestion code: `run_optc_ingest.py`, unchanged
- red-team ground truth remains excluded from ingestion.

## Execution guardrails

- no change to H/P/T mapping;
- no attack/red-team labels read;
- no C/control variable inferred;
- no causal-effect estimate produced;
- aggregate-only result retained;
- a failed acquisition/hash check is retained as failure evidence and must not be bypassed by substituting another source.

## Claim boundary

Only observational schema/typing coverage and temporal/identifier completeness may be promoted. No causal-effect, attacker-intent, or control-effectiveness claim is permitted.
