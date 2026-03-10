# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ANTA (Arista Network Test Automation) is a Python framework that automates tests for Arista EOS devices. It supports both CLI usage and embedding as a Python library. This is a fork of the upstream `aristanetworks/anta` repository.

## Development Setup

Always use an isolated Python environment — either a `.venv` or a Docker container — rather than installing into the system Python.

```bash
# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install in editable mode with dev dependencies
pip install -e ".[cli]" --group dev

# Install pre-commit hooks
pip install pre-commit
pre-commit install

# Set MYPYPATH when editing both a test and its unit test in the same session
export MYPYPATH=.
```

## Commands

### Linting
```bash
tox -e lint        # Runs ruff check, ruff format --check, pylint on anta/ and tests/
ruff check .       # Run ruff linter only
ruff format .      # Format code
pylint anta        # Run pylint on source
```

### Type Checking
```bash
tox -e type        # mypy on anta/ and tests/
mypy --config-file=pyproject.toml anta
```

### Testing
```bash
tox -e py312       # Run full pytest suite under Python 3.12
pytest             # Run all tests (uses settings in pyproject.toml)
pytest tests/units/anta_tests/test_system.py  # Run a single test file
pytest -k "VerifyUptime"                      # Run tests matching a keyword
pytest tests/units/anta_tests/test_system.py::test[anta.tests.system.VerifyUptime-success]  # Run a specific parametrized case
```

Note: Benchmark tests in `tests/benchmark/` are excluded from normal test runs and only run via Codspeed.

### Documentation
```bash
# Install doc dependencies into the active .venv
pip install -e . --group doc
mkdocs serve                    # Serve docs locally at http://127.0.0.1:8000
mkdocs serve --dev-addr=0.0.0.0:8080  # Expose on all interfaces
```

## Architecture

### Core Abstractions

**`anta/models.py`** — The foundation of the framework:
- `AntaTest` — Abstract base class for all tests. Subclasses define `categories`, `commands` (list of `AntaCommand` or `AntaTemplate`), an inner `Input(AntaTest.Input)` Pydantic model for inputs, and a `test()` method decorated with `@AntaTest.anta_test`. Tests signal outcomes via `self.result.is_success()`, `self.result.is_failure(msg)`, or `self.result.is_skipped(msg)`.
- `AntaCommand` — Pydantic model representing an EOS command to run, with `command`, `ofmt` (json/text), `version`, `revision`, and `output` fields.
- `AntaTemplate` — An f-string command template. Requires a `render()` method on the test class to produce `AntaCommand` instances from test inputs.

**`anta/result_manager/models.py`** — Result types:
- `AntaTestStatus` — Enum: `UNSET`, `SUCCESS`, `FAILURE`, `ERROR`, `SKIPPED`.
- `TestResult` — Holds the test outcome, messages, and optional atomic results.

**`anta/device.py`** — `AntaDevice` (abstract) and `AsyncEOSDevice` (concrete) for communicating with devices via eAPI (httpx) and SSH (asyncssh). Includes `AntaCache` for command-level caching.

**`anta/catalog.py`** — `AntaCatalog` loads YAML/JSON test catalogs mapping Python module paths to lists of test classes with their inputs.

**`anta/inventory/`** — `AntaInventory` manages device collections loaded from YAML inventory files.

**`anta/_runner.py`** — `AntaRunner` orchestrates async execution of tests across all devices. `AntaRunFilters` controls which devices/tests/tags to run.

**`anta/reporter/`** — Output formatters: `CSVReporter`, `MDReporter`. `anta/result_manager/` handles result aggregation.

### Test Modules

All ANTA tests live in `anta/tests/` (one module per feature domain, e.g., `system.py`, `interfaces.py`, `routing/bgp.py`). Complex input models that are reused across tests are factored into `anta/input_models/` (mirroring the `anta/tests/` structure).

### Test Structure Pattern

Each test class follows this pattern:
```python
class VerifyFoo(AntaTest):
    """Docstring with Expected Results section and YAML example."""
    categories: ClassVar[list[str]] = ["category"]
    commands: ClassVar[list[AntaCommand | AntaTemplate]] = [AntaCommand(command="show foo")]

    class Input(AntaTest.Input):
        some_param: int

    @AntaTest.anta_test
    def test(self) -> None:
        self.result.is_success()
        output = self.instance_commands[0].json_output
        if output["value"] != self.inputs.some_param:
            self.result.is_failure(f"Expected {self.inputs.some_param}, got {output['value']}")
```

For `AntaTemplate`, a `render()` method must be defined to produce per-input `AntaCommand` instances. Tests support atomic results (per-item results within one test) using `self.result.atomic_results`.

### Decorators

`anta/decorators.py` provides:
- `@skip_on_platforms(["cEOSLab"])` — Skip a test on specific hardware models.
- `@deprecated_test_class(new_tests=[...], removal_in_version="X.Y.Z")` — Mark a test as deprecated.

### CLI

`anta/cli/` uses Click. Entry point is `anta.cli:cli`. Subcommands: `nrfu`, `check`, `debug`, `exec`, `get`.

## Writing Unit Tests for AntaTest Subclasses

Unit tests for `anta/tests/*.py` go in `tests/units/anta_tests/test_<module>.py`. The test framework uses `pytest_generate_tests` (in `tests/units/anta_tests/conftest.py`) to parametrize a generic `test()` function from a `DATA` constant.

```python
from anta.tests.system import VerifyUptime
from anta.result_manager.models import AntaTestStatus
from tests.units.anta_tests import test  # must import even if unused
from tests.units.anta_tests import AntaUnitTestData

DATA: AntaUnitTestData = {
    (VerifyUptime, "success"): {
        "eos_data": [{"upTime": 1200, "loadAvg": [0.1], "users": 1, "currentTime": 0}],
        "inputs": {"minimum": 600},
        "expected": {"result": AntaTestStatus.SUCCESS},
    },
    (VerifyUptime, "failure"): {
        "eos_data": [{"upTime": 100, "loadAvg": [0.1], "users": 1, "currentTime": 0}],
        "inputs": {"minimum": 600},
        "expected": {"result": AntaTestStatus.FAILURE, "messages": ["Device uptime is incorrect"]},
    },
}
```

Key rules:
- `eos_data` mocks EOS command outputs in the same order as `commands` defined in the test class.
- `messages` in `expected` are substring-matched against actual messages; all messages must be covered.
- If a test uses atomic results, `atomic_results` must be specified in full and in order.
- The `from tests.units.anta_tests import test` import is required for `pytest_generate_tests` to collect the tests.

## Code Style

- Python 3.10+ minimum; use `from __future__ import annotations` at the top of every module.
- Docstrings follow **NumPy convention** (`Parameters`, `Returns`, `Raises` sections).
- Line length: 165 characters (ruff + pylint configured).
- Type annotations are strict — avoid `Any` except in designated areas (`tools.py`, `decorators.py`).
- Pydantic models use `model_config = ConfigDict(extra="forbid")` to reject unknown fields.
- Runtime-evaluated annotations (Pydantic models, `AntaTest.Input` subclasses) must not use `TYPE_CHECKING`-only imports.
- All new Python files require the Apache 2.0 license header (enforced by pre-commit).
