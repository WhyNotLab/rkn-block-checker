# RKN Block Checker

[![CI](https://github.com/MayersScott/rkn-block-checker/actions/workflows/ci.yml/badge.svg)](https://github.com/MayersScott/rkn-block-checker/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

A small CLI that figures out whether the connection you're sitting on is in an
RKN/TSPU-blocked zone — and, more usefully, **what kind** of block it is
(DNS poisoning, TCP reset, TLS DPI on SNI, or an ISP stub page).

The point isn't "site X doesn't open." Browsers already tell you that. The
point is to look at each layer of the stack independently and report *where*
it broke. That tells you a lot more about your situation than a generic
"this site can't be reached" page.

## Example output

```text
======================================================================
  RKN Block Checker
======================================================================
  IP:       95.165.xxx.xxx
  ISP:      AS12389 Rostelecom
  Location: Moscow, Moscow, RU
----------------------------------------------------------------------

Whitelist (should always work)
  name          verdict            TCP     TLS     PLT  status
  ------------------------------------------------------------
  gosuslugi     ✓ OK              18ms    42ms   380ms  200
  yandex        ✓ OK               8ms    25ms    95ms  200
  sberbank      ✓ OK              12ms    38ms   250ms  200
  vk            ✓ OK               9ms    28ms   180ms  200
  ...

Blacklist (RKN-restricted)
  name          verdict            TCP     TLS     PLT  status
  ------------------------------------------------------------
  instagram     ✗ TLS BLOCK       22ms       —       —  —
    └ TLS reset — DPI cutting on SNI (typical RKN/TSPU)
  twitter/x     ✗ TLS BLOCK       24ms       —       —  —
    └ TLS timeout — silent drop after ClientHello
  rutracker     ✗ HTTP STUB       18ms    45ms   120ms  200
    └ response body matches an ISP stub-page marker
  protonvpn     ✗ DNS BLOCK          —       —       —  —
    └ system DNS doesn't resolve, DoH does — DNS poisoning
  ...

======================================================================
  Summary
----------------------------------------------------------------------
  Whitelist: 21/21 working
  Blacklist: 3/15 open, 12/15 blocked

  → You ARE in an RKN-blocked zone.

  Block types in the blacklist:
    ✗ TLS BLOCK: 8
    ✗ DNS BLOCK: 2
    ✗ HTTP STUB: 2
======================================================================
```

## Install

Python 3.10+.

```bash
git clone https://github.com/MayersScott/rkn-block-checker.git
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

JSON output pipes nicely into `jq`:

```bash
rkn-check --json | jq '.blacklist[] | select(.verdict != "OK") | .name'
```

## How it works

For each target the tool walks DNS → TCP → TLS → HTTP and stops at the first
thing that fails. Whichever layer broke becomes the verdict.

| layer | probe | what a failure means |
|------:|-------|----------------------|
| DNS  | system resolver vs Cloudflare DoH | if only the system fails, the ISP is poisoning DNS — the cheapest, oldest form of blocking |
| TCP  | plain TCP handshake on :443 | a `RST` is IP-level blackholing. Rare — most ISPs don't bother |
| TLS  | TLS handshake with SNI = target host | reset/timeout *here* (with TCP working fine) is the classic TSPU/DPI signature: the middlebox sees the SNI and tears the connection down |
| HTTP | `GET` after handshake completes | 451, or an ISP stub page returning 200 with a "blocked by RKN" body |

Two probes are worth calling out:

**System DNS vs DoH.** The cheapest way to "block" a site is to make the
ISP's DNS lie. Every host is resolved twice — once via `socket` (which uses
whatever resolver the OS is configured for, usually the ISP's) and once via
Cloudflare's DoH endpoint, which the ISP can't intercept. Disagreement is
the smoking gun.

**TLS handshake with SNI.** Modern TSPU equipment doesn't drop the TCP
connection — it lets you connect, reads the SNI extension out of the
ClientHello, and *then* sends a RST or simply stops responding. So we have
to actually start the TLS handshake to see this. A `TLS_BLOCK` after a clean
`TCP_OK` is the unambiguous fingerprint of DPI-based blocking.

## Layout

```text
rkn_checker/
  __main__.py     # python -m rkn_checker
  cli.py          # argparse + entry point
  core.py         # orchestrates DNS -> TCP -> TLS -> HTTP
  dns.py          # system resolver + Cloudflare DoH
  network.py      # raw TCP and TLS probes
  http.py         # HTTP GET + stub-page detection
  output.py       # colored CLI report
  targets.py      # whitelist, blacklist, stub markers
  models.py       # CheckResult, Verdict
tests/            # pytest, all network calls mocked
```

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

No network calls in the test suite — every probe is mocked, so it runs the
same in CI, on a plane, or behind a corporate proxy.

## Caveats

- IPv4 only. Some Russian ISPs treat IPv6 differently (often less filtered)
  but the v4 path is what users actually experience in practice.
- The target lists are hard-coded (~20 sites per category). That's enough
  for a verdict but won't catch a block that affects only one specific
  resource. To extend — `rkn_checker/targets.py`.
- One-shot snapshot, no retries, no longitudinal tracking. If you want to
  monitor a connection over time, run `rkn-check --json` from cron.
- Stub markers are mostly Russian-language phrases; false positives on
  unrelated sites that happen to contain the same words are theoretically
  possible but I haven't seen one yet.

## License

MIT.
