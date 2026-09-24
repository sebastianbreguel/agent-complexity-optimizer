# CI Pipelines (build, test, deploy)

Find where the minutes go before optimizing: the slowest job on the critical path sets the total time.

## Find the slow part

```bash
gh run list --workflow ci.yml --limit 20 --json databaseId,conclusion,createdAt,updatedAt   # run durations over time
gh run view <run-id> --json jobs --jq '.jobs[] | {name, startedAt, completedAt}'            # time per job
gh run view <run-id> --json jobs --jq '.jobs[].steps[] | {name, startedAt, completedAt}'    # time per step
```

Locally: `hyperfine 'npm test'`, `pytest --durations=15`, `vitest --reporter=verbose`, `go test -json ./...`, `tsc --extendedDiagnostics`.

## Common waste and fixes

- **Installing dependencies from scratch every run:** cache them (`actions/setup-node` with `cache: npm|pnpm|yarn`, `actions/setup-python` with `cache: pip`, `astral-sh/setup-uv` with `enable-cache: true`, Gradle/Maven caches). Key caches on the lockfile.
- **Everything in one sequential job:** split lint, typecheck, unit tests, and build into parallel jobs; keep only true dependencies (`needs:`).
- **Running every test for every change in a monorepo:** run affected projects only (`turbo run test --filter=...[origin/main]`, `nx affected -t test`), with a full run on the main branch.
- **One long test job:** shard it (`pytest -n auto` with pytest-xdist, `jest --shard=1/4`, `vitest --shard=1/4`, a matrix of shards).
- **Docker builds without layer caching:** order the Dockerfile so the lockfile is copied and dependencies installed before copying the source; use BuildKit cache mounts and `cache-from: type=gha` / `cache-to: type=gha,mode=max` in `docker/build-push-action`.
- **Duplicate runs:** `concurrency: { group: ${{ github.workflow }}-${{ github.ref }}, cancel-in-progress: true }` cancels superseded runs on the same branch; avoid running the same workflow for both `push` and `pull_request` on the same commits.
- **Slow individual tests:** real network calls, `sleep`-based waits, and per-test database setup. Mock external calls, wait on conditions instead of timers, and reuse database fixtures or wrap tests in transactions.
- **Retries hiding flaky tests:** each retry adds minutes; fix or quarantine the flaky test.
- **Heavy steps on every push** (full E2E suites, multi-platform builds): run them on merge to main, nightly, or when relevant paths change (`paths:` filters).

## Measure

Compare the median run time of the workflow over the last 20 runs before and after the change (`gh run list` output), not a single run: CI machines are noisy. See `../measuring.md`.
