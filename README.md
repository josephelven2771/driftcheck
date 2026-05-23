# driftcheck

Detects configuration drift between running services and their declared infrastructure definitions.

---

## Installation

```bash
pip install driftcheck
```

Or install from source:

```bash
git clone https://github.com/yourorg/driftcheck.git && cd driftcheck && pip install .
```

---

## Usage

Point `driftcheck` at your infrastructure definition file and a running environment to compare them:

```bash
driftcheck --config infra/services.yaml --env production
```

Example output:

```
[DRIFT DETECTED] service: api-gateway
  expected: replicas=3, memory_limit=512Mi
  actual:   replicas=2, memory_limit=768Mi

[OK] service: auth-service
[OK] service: worker-queue

Summary: 1 drift(s) found across 3 service(s).
```

You can also run it programmatically:

```python
from driftcheck import DriftChecker

checker = DriftChecker(config="infra/services.yaml", env="production")
results = checker.run()

for result in results.drifted:
    print(f"Drift in {result.service}: {result.diff}")
```

Use `--output json` for CI-friendly output or `--fail-on-drift` to exit with a non-zero status when drift is detected.

---

## Configuration

Define your expected service state in a YAML file:

```yaml
services:
  api-gateway:
    replicas: 3
    memory_limit: 512Mi
  auth-service:
    replicas: 2
    memory_limit: 256Mi
```

You can also specify ignored fields that should be excluded from drift comparison:

```yaml
services:
  api-gateway:
    replicas: 3
    memory_limit: 512Mi
    ignore:
      - last_deployed
      - build_sha
```

---

## License

MIT © 2024 Your Name
