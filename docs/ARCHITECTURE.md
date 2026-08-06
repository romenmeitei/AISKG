# Architecture

## Design principles

1. **Immutable manuscript compatibility.** The original Section 1 and Section 2 engines are version-pinned under `src/aiskg/legacy/`.
2. **Central configuration.** New orchestration and ablation behavior is controlled by YAML, not hidden function defaults.
3. **Additive extension.** Unified modules, audits, and ablations are written beside legacy outputs.
4. **Deterministic release.** Fixed seeds, frozen inputs, expected results, manifests, and deterministic ZIP timestamps are used.
5. **Auditable boundaries.** Snapshot reproducibility and optional live refresh are explicitly separated.

## Execution flow

```text
Frozen Section 1 inputs
        │
        ▼
Legacy Section 1 engine
        │  checksummed bridge ZIP
        ▼
Legacy Section 2 engine
        │
        ├── graph / temporal / pathway
        ├── validation / benchmarking
        └── representation / robustness
        │
        ▼
Nine ablation checkpoints and comparisons
        │
        ▼
285-check audit → manifest → checksums → release ZIP
```

## Module map

- `aiskg.config`: strict YAML loading and validation.
- `aiskg.pipeline`: full orchestration and compatibility API.
- `aiskg.stages`: independently executable stage groups.
- `aiskg.ablation`: frozen-corpus variant replay, verification, reports, and figures.
- `aiskg.reproducibility`: run verification and release support.
- `aiskg.legacy`: exact Section 1 and Section 2 engines.
- Domain folders (`graph`, `pathway`, `validation`, etc.) expose independent entry points through the stage runner.

## Why the legacy engines remain intact

The manuscript results were produced by long, validated scripts. Rewriting every numerical operation would risk silent changes in ordering, floating-point behavior, spreadsheet serialization, and graph partitioning. The compatibility engines are therefore retained unchanged and wrapped by tested modules. Configuration values are injected where the legacy engine exposes constants; immutable expected-result checks guard the remaining frozen behavior.
