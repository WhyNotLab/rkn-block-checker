from __future__ import annotations

import argparse
import json
import logging
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

from .core import check_url, get_self_info
from .lists import ListLoadError, load_targets
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
    p.add_argument("--white-file", dest="white_file", metavar="PATH",
                   help="load whitelist targets from a .txt or .json file "
                        "(replaces the built-in whitelist)")
    p.add_argument("--black-file", dest="black_file", metavar="PATH",
                   help="load blacklist targets from a .txt or .json file "
                        "(replaces the built-in blacklist)")
    p.add_argument("--timeout", type=float, default=5.0,
                   help="per-probe timeout in seconds (default: 5.0)")
    p.add_argument("--workers", type=int, default=10,
                   help="thread pool size for parallel checks (default: 10)")
    p.add_argument("-v", "--verbose", action="count", default=0,
                   help="increase log verbosity (-v info, -vv debug)")
    p.add_argument("--no-self-info", dest="no_self_info", action="store_true",
                   help="skip the external IP self-info lookup")
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


def _resolve_lists(
    white_file: str | None,
    black_file: str | None,
) -> tuple[dict[str, str], dict[str, str]]:
    white = WHITE_URLS
    black = BLACK_URLS
    if white_file:
        white = load_targets(white_file)
    if black_file:
        black = load_targets(black_file)
    return white, black


def _run_streaming(
    run_white: bool,
    run_black: bool,
    white_urls: dict[str, str],
    black_urls: dict[str, str],
    workers: int,
    timeout: float,
) -> tuple[list[CheckResult], list[CheckResult]]:
    white_results: list[CheckResult] = []
    black_results: list[CheckResult] = []

    with ThreadPoolExecutor(max_workers=workers) as pool:
        white_futs = {
            pool.submit(check_url, name, url, timeout): name
            for name, url in (white_urls.items() if run_white else [])
        }
        black_futs = {
            pool.submit(check_url, name, url, timeout): name
            for name, url in (black_urls.items() if run_black else [])
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
    # Принудительно переключаем stdout/stderr на UTF-8 (нужно для Windows cp1252)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    parser = _build_parser()
    args = parser.parse_args(argv)
    _setup_logging(args.verbose)

    if args.white_only and args.black_only:
        parser.error("--white and --black are mutually exclusive")
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    if args.workers <= 0:
        parser.error("--workers must be positive")

    try:
        white_urls, black_urls = _resolve_lists(args.white_file, args.black_file)
    except ListLoadError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    run_white = not args.black_only
    run_black = not args.white_only

    if args.as_json:
        from .core import check_urls_parallel
        white_results = (
            check_urls_parallel(white_urls, args.workers, args.timeout)
            if run_white else []
        )
        black_results = (
            check_urls_parallel(black_urls, args.workers, args.timeout)
            if run_black else []
        )
        self_info = get_self_info(timeout=args.timeout) if not args.no_self_info else None
        payload = {
            "self_info": self_info,
            "whitelist": [r.to_dict() for r in white_results],
            "blacklist": [r.to_dict() for r in black_results],
        }
        json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
        return 0
    
    if not args.no_self_info:
        print_header(get_self_info(timeout=args.timeout))
    else:
        print_header({})
    sys.stdout.flush()

    white_results, black_results = _run_streaming(
        run_white, run_black, white_urls, black_urls, args.workers, args.timeout,
    )

    if run_white and run_black:
        print_summary(white_results, black_results)

    return 0


if __name__ == "__main__":
    sys.exit(main())