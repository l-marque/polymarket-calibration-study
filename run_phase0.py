"""
Phase 0 entrypoint.

Usage:
    python run_phase0.py markets --closed --months 12
    python run_phase0.py prices
    python run_phase0.py macro
    python run_phase0.py explore --output reports/phase0_summary.txt
    python run_phase0.py all                       # markets + prices + macro
"""
from __future__ import annotations
import argparse
import asyncio
import logging
import sys
from pathlib import Path
from rich.logging import RichHandler

from config.settings import LOG_LEVEL, LOG_FILE
from data import storage, collector, macro_collector, explorer


def _setup_logging() -> None:
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=LOG_LEVEL,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[
            RichHandler(rich_tracebacks=True, markup=False),
            logging.FileHandler(LOG_FILE),
        ],
    )


async def cmd_markets(args: argparse.Namespace) -> None:
    storage.init_db()
    async with collector.PolymarketCollector() as c:
        n = await c.collect_markets(
            closed=args.closed if args.closed else None,
            months_lookback=args.months,
            max_pages=args.max_pages,
        )
    print(f"Markets written: {n}")


async def cmd_prices(args: argparse.Namespace) -> None:
    storage.init_db()
    async with collector.PolymarketCollector() as c:
        n = await c.collect_prices_for_all(
            closed_only=True,
            exclude_holdout=True,
            concurrency=args.concurrency,
        )
    print(f"Price points written: {n}")


def cmd_macro(args: argparse.Namespace) -> None:
    storage.init_db()
    n = macro_collector.collect_macro(start_date=args.start)
    print(f"Macro points written: {n}")


def cmd_explore(args: argparse.Namespace) -> None:
    explorer.write_report(args.output)
    print(f"Report: {args.output}")


async def cmd_all(args: argparse.Namespace) -> None:
    await cmd_markets(args)
    await cmd_prices(args)
    cmd_macro(args)
    cmd_explore(args)


def main() -> int:
    _setup_logging()
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)

    pm = sub.add_parser("markets")
    pm.add_argument("--closed", action="store_true", default=True)
    pm.add_argument("--months", type=int, default=12)
    pm.add_argument("--max-pages", type=int, default=200)

    pp = sub.add_parser("prices")
    pp.add_argument("--concurrency", type=int, default=4)

    pma = sub.add_parser("macro")
    pma.add_argument("--start", type=str, default="2020-01-01")

    pe = sub.add_parser("explore")
    pe.add_argument("--output", type=str, default="reports/phase0_summary.txt")

    pa = sub.add_parser("all")
    pa.add_argument("--closed", action="store_true", default=True)
    pa.add_argument("--months", type=int, default=12)
    pa.add_argument("--max-pages", type=int, default=200)
    pa.add_argument("--concurrency", type=int, default=4)
    pa.add_argument("--start", type=str, default="2020-01-01")
    pa.add_argument("--output", type=str, default="reports/phase0_summary.txt")

    args = p.parse_args()
    if args.cmd == "markets":
        asyncio.run(cmd_markets(args))
    elif args.cmd == "prices":
        asyncio.run(cmd_prices(args))
    elif args.cmd == "macro":
        cmd_macro(args)
    elif args.cmd == "explore":
        cmd_explore(args)
    elif args.cmd == "all":
        asyncio.run(cmd_all(args))
    return 0


if __name__ == "__main__":
    sys.exit(main())
