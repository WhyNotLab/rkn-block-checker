# RKN Block Checker

A small CLI that figures out whether the connection you're sitting on is in an
RKN/TSPU-blocked zone — and, more usefully, **what kind** of block it is
(DNS poisoning, TCP reset, TLS DPI on SNI, or an ISP stub page).

## Install

Python 3.10+.

```bash
git clone https://github.com/yourname/rkn-block-checker.git
cd rkn-block-checker
pip install -r requirements.txt
python -m rkn_checker
```

Or as a package:

```bash
pip install -e .
rkn-check
```

## Usage

```text
rkn-check [-h] [--json] [--white] [--black] [--timeout TIMEOUT]
          [--workers WORKERS] [-v]
```

| flag | what it does |
|------|--------------|
| `--json` | machine-readable JSON instead of the colored report |
| `--white` | only the control (whitelist) targets |
| `--black` | only the blacklist targets |
| `--timeout` | per-probe timeout in seconds (default 5.0) |
| `--workers` | thread pool size for parallel checks (default 10) |
| `-v` / `-vv` | logging at INFO / DEBUG |

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

## License

MIT.
