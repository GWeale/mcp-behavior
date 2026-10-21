# Docker-backed isolation prototype

This opt-in experiment runs the existing expectations stdio server in a container
through the unchanged `verify(...)` API. It is not a new production runner.

## Prerequisites and execution

Use a Linux host, a running Docker Engine with permission to build/run containers,
Python 3.11+ and the repository's development environment. Docker Desktop/Windows
behavior has not been validated. Image construction downloads the declared project
dependencies; runtime containers have no network access.

```bash
docker build -t mcp-behavior-prototype:local -f prototypes/docker/Dockerfile .
uv run python prototypes/docker/measure.py
```

The JSON report lives under `.mcp-behavior/docker-prototype/`. It records the exact
image ID, a minimal container startup probe in milliseconds, the full MCP run and
cleanup duration, and whether the named container was removed for both a successful
expectations run and a deliberately unresponsive server. The latter must return
`INCONCLUSIVE`, never a verified behavioral difference. Image build/pull time is
excluded from the startup probe. These are single-machine measurements, not a
performance benchmark or portability claim.

The [Docker prototype workflow](../../.github/workflows/docker-prototype.yml)
executes both cases on Linux and uploads the report. Its measured results, rather
than estimates from a host without Docker, are the evidence for this experiment.

## Boundary and cleanup

Only a new temporary workspace is mounted read/write; the application/image
filesystem is read-only. The container runs as the invoking UID/GID, with no added
capabilities, no network, no new privileges, and bounded memory, CPU and process
count. A separate tmpfs provides temporary storage. No Docker socket or host home
directory is mounted. Base-image environment defaults remain; only the explicitly
allowed `PROTOTYPE_MARKER` is forwarded from the host. A host-only sentinel verifies
that the container does not receive the rest of the host environment.

Container names contain a fresh UUID. A `finally` path checks that exact name,
force-removes it if needed, and verifies absence with a successful daemon query.
Workspace removal happens after container cleanup. The JSON records cleanup time
as part of each case. A daemon failure makes the experiment fail rather than claim
that cleanup succeeded. Evidence directories are retained for inspection.

This reduces accidental host access. It is not a hostile-code sandbox: the daemon,
image build, shared kernel and mounted workspace remain trust boundaries. The image
tag is a local experiment convenience; use reviewed digest-pinned images before a
production design. No core runner, contract syntax or runtime dependency changes.

References: [Docker run options](https://docs.docker.com/reference/cli/docker/container/run/)
and [Docker security](https://docs.docker.com/engine/security/).
