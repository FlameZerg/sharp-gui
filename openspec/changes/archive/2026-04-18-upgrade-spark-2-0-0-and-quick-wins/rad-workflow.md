# Spark RAD Offline Workflow

## Scope

This document defines the offline conversion contract from source splat assets to RAD outputs for this change.

## Verified Upstream References

- Spark docs: https://sparkjs.dev/docs/lod-getting-started/#build-lod-command-line-tool
- Spark migration docs: https://sparkjs.dev/docs/0.1-2.0-migration-guide/#update-spark-dependencies

## Prerequisites

- Spark stable dependency in app: @sparkjsdev/spark ^2.0.0
- Rust toolchain installed via rustup (required by build-lod)
- Input files in one of supported formats: .ply, .spz, .splat, .ksplat, .sog, .zip (SOGS bundle)

## Command Entrypoint

Run from Spark repository root:

```bash
npm run build-lod -- <input-files...> [options]
```

Run directly from Rust crate:

```bash
cd rust/build-lod
cargo run --release -- <input-files...> [options]
```

Get help / options:

```bash
npm run build-lod
```

## Recommended Offline Build Commands

Single model (quality mode):

```bash
npm run build-lod -- /path/to/model.ply --quality
```

Batch conversion:

```bash
npm run build-lod -- /path/to/models/*.spz --quality
```

Chunked RAD for paged streaming:

```bash
npm run build-lod -- /path/to/model.ply --quality --rad-chunked
```

## Output Naming Contract

For input:

- model.ply

Default output:

- model-lod.rad

When --rad-chunked is enabled:

- model-lod.rad (header)
- model-lod-0.radc
- model-lod-1.radc
- ...

The frontend must point URL to the .rad header file; chunk files are fetched automatically by Spark paged loading.

## Frontend Loading Contract

RAD streaming path:

```ts
new SplatMesh({ url: "./model-lod.rad", paged: true })
```

Fallback path when RAD is unavailable or disabled:

```ts
new SplatMesh({ url: "./model.spz" })
```

## Quality / Performance Options (Minimum Required)

- --quick: fast tiny-lod method (default)
- --quality: slower but higher quality bhatt-lod method (recommended for offline)
- --max-sh=# : cap spherical harmonics level (0..3)
- --rad-chunked: split RAD into header + .radc chunks for paged streaming

## Acceptance Checks

- build-lod command exits successfully for representative inputs.
- Output naming follows -lod.rad convention.
- Chunked mode generates both .rad header and .radc chunks.
- Frontend can load .rad with paged enabled and starts rendering before all chunks finish.
- If .rad is unavailable, frontend falls back to SPZ/PLY/SPLAT path without breaking viewer startup.
