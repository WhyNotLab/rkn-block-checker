from __future__ import annotations

import argparse
import json
import logging
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

from .core import check_url, get_self_info
from .models import CheckResult
from .output import print_header, print_result, print_section, print_summary
from .targets import BLACK_URLS, WHITE_URLS


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="rkn-check",
        description=(
            "Probe a list of sites and decide whether the current network "
            "is in an RKN-blocked zone."
        ),
    )
    p.add_argument("--json", dest="as_json", action="store_true",
                   help="emit machine-readable JSON instead of the colored report")
    p.add_argument("--white", dest="white_only", action="store_true",
                   help="check only the control (whitelist) targets")
    p.add_argument("--black", dest="black_only", action="store_true",
                   help="check only the blacklist targets")
    p.add_argument("--timeout", type=float, default=5.0,
                   help="per-probe timeout in seconds (default: 5.0)")
    p.add_argument("--workers", type=int, default=10,
                   help="thread pool size for parallel checks (default: 10)")
    p.add_argument("-v", "--verbose", action="count", default=0,
                   help="increase log verbosity (-v info, -vv debug)")
    return p


def _setup_logging(verbosity: int) -> None:
    level = logging.WARNING
    if verbosity == 1:
        level = logging.INFO
    elif verbosity >= 2:
        level = logging.DEBUG
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def _run_streaming(
    run_white: bool,
    run_black: bool,
    workers: int,
    timeout: float,
) -> tuple[list[CheckResult], list[CheckResult]]:
    """Run both groups in a single pool, print each result the moment it lands.

    Whitelist results print first (in completion order, under the whitelist
    section), then blacklist results (under the blacklist section). Both
    groups are executing in parallel the whole time, so by the time the
    whitelist section finishes printing, most of the blacklist is already
    done — the blacklist section then drains nearly instantly.
    """
    white_results: list[CheckResult] = []
    black_results: list[CheckResult] = []

    with ThreadPoolExecutor(max_workers=workers) as pool:
        white_futs = {
            pool.submit(check_url, name, url, timeout): name
            for name, url in (WHITE_URLS.items() if run_white else [])
        }
        black_futs = {
            pool.submit(check_url, name, url, timeout): name
            for name, url in (BLACK_URLS.items() if run_black else [])
        }

        if run_white:
            print_section("Whitelist (should always work)")
            for fut in as_completed(white_futs):
                r = fut.result()
                white_results.append(r)
                print_result(r)
                sys.stdout.flush()

        if run_black:
            print_section("Blacklist (RKN-restricted)")
            for fut in as_completed(black_futs):
                r = fut.result()
                black_results.append(r)
                print_result(r)
                sys.stdout.flush()

    return white_results, black_results


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    _setup_logging(args.verbose)

    run_white = not args.black_only
    run_black = not args.white_only

    if args.as_json:
        # JSON mode collects everything before emitting one document — there's
        # no streaming benefit since the consumer is parsing a single object.
        from .core import check_urls_parallel
        white_results = (
            check_urls_parallel(WHITE_URLS, args.workers, args.timeout)
            if run_white else []
        )
        black_results = (
            check_urls_parallel(BLACK_URLS, args.workers, args.timeout)
            if run_black else []
        )
        payload = {
            "self_info": get_self_info(),
            "whitelist": [r.to_dict() for r in white_results],
            "blacklist": [r.to_dict() for r in black_results],
        }
        json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
        return 0

    # Print the header first so the user immediately sees their IP/ISP
    # while the per-target probes run in the background.
    print_header(get_self_info(timeout=args.timeout))
    sys.stdout.flush()

    white_results, black_results = _run_streaming(
        run_white, run_black, args.workers, args.timeout
    )

    if run_white and run_black:
        print_summary(white_results, black_results)

    return 0


if __name__ == "__main__":
    sys.exit(main())
