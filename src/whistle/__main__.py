"""CLI entry point for whistle."""
import sys
import json
import argparse
from pathlib import Path

from . import parse, compile as whistle_compile, validate
from .compiler import _KNOWN_BREEDS


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="whistle",
        description="Whistle DSL — Intent DSL for Working Animal Architecture",
    )
    sub = parser.add_subparsers(dest="command")

    # validate
    p_val = sub.add_parser("validate", help="Validate a .whistle file")
    p_val.add_argument("file", help="Path to .whistle file")

    # compile
    p_cmp = sub.add_parser("compile", help="Compile a .whistle file to JSON config")
    p_cmp.add_argument("file", help="Path to .whistle file")
    p_cmp.add_argument("-o", "--output", help="Output JSON path (default: stdout)")

    # breeds
    sub.add_parser("breeds", help="List known model breeds")

    args = parser.parse_args(argv)

    if args.command == "validate":
        source = Path(args.file).read_text()
        prog = parse(source)
        result = validate(prog)
        if result.errors:
            for e in result.errors:
                print(f"  ERROR  [{e.whistle}] {e.field}: {e.message}")
        for w in result.warnings:
            print(f"  WARN   [{w.whistle}] {w.field}: {w.message}")
        if result.valid:
            print(f"✓ Valid — {len(prog.statements)} whistle(s)")
            return 0
        else:
            print(f"✗ Invalid — {len(result.errors)} error(s)")
            return 1

    elif args.command == "compile":
        source = Path(args.file).read_text()
        prog = parse(source)
        result = validate(prog)
        if not result.valid:
            print("Validation errors — refusing to compile:", file=sys.stderr)
            for e in result.errors:
                print(f"  [{e.whistle}] {e.field}: {e.message}", file=sys.stderr)
            return 1
        config = whistle_compile(prog)
        output = json.dumps(config, indent=2)
        if args.output:
            Path(args.output).write_text(output)
            print(f"Written to {args.output}")
        else:
            print(output)
        return 0

    elif args.command == "breeds":
        print("Known breeds:")
        for breed, info in sorted(_KNOWN_BREEDS.items()):
            print(f"  {breed:25s}  provider={info['provider']:12s}  ctx={info['context_window']}")
        return 0

    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
