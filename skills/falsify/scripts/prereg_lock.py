#!/usr/bin/env python3
"""Gate 2 — date-locked pre-registration (falsify skill).

Write the TRUE shape, FALSE shape, and pass/fail thresholds to a dated file
BEFORE any result is looked at, and refuse to overwrite an existing file for the
same date. A changed threshold must become a NEW dated file, so goalpost-moving
is visible. The content is SHA-256 hashed; once the file lives in a committed
repo, git history makes any later change auditable too.

Pure Python standard library only — runs on any Python 3.8+.
"""

import argparse
import datetime as dt
import hashlib
import sys
from pathlib import Path


def parse_thresholds(spec):
    """Parse 'k=v;k=v' into an ordered dict. Loud error on malformed input."""
    out = {}
    for chunk in spec.split(";"):
        chunk = chunk.strip()
        if not chunk:
            continue
        if "=" not in chunk:
            raise ValueError(f"malformed threshold '{chunk}' (expected key=value)")
        k, v = chunk.split("=", 1)
        k = k.strip()
        v = v.strip()
        if not k:
            raise ValueError(f"empty threshold key in '{chunk}'")
        out[k] = v
    if not out:
        raise ValueError("no thresholds parsed; expected 'key=value;key=value'")
    return out


def content_hash(text):
    """SHA-256 hex digest of the locked content."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def render_prereg(slug, true_shape, false_shape, thresholds, today):
    """Render the pre-registration markdown body (deterministic given inputs)."""
    lines = [
        f"# Pre-registration — {slug}",
        "",
        f"**Date locked:** {today.isoformat()}",
        "",
        "## TRUE shape (what the numbers look like if the claim is real)",
        "",
        true_shape.rstrip(),
        "",
        "## FALSE shape (the counterfactual — what you'd see if it's wrong)",
        "",
        false_shape.rstrip(),
        "",
        "## Locked thresholds",
        "",
    ]
    for k, v in thresholds.items():
        lines.append(f"- `{k}` = {v}")
    lines.append("")
    lines.append("> A threshold cannot move after the result is seen without a NEW dated "
                 "file. The date IS the lock.")
    lines.append("")
    return "\n".join(lines)


def write_prereg(slug, true_shape, false_shape, thresholds, out_dir, today=None):
    """Write the dated pre-registration file; refuse to overwrite the same date.

    `today` is injectable for deterministic testing; defaults to date.today().
    Returns {"path": str, "sha256": str}.
    """
    if today is None:
        today = dt.date.today()
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"prereg_{today.isoformat()}.md"
    if path.exists():
        raise FileExistsError(
            f"pre-registration for {today.isoformat()} already exists at {path}; "
            f"a changed threshold must be a NEW dated file (do not overwrite)")
    body = render_prereg(slug, true_shape, false_shape, thresholds, today)
    digest = content_hash(body)
    # Append the hash as a trailer (not part of the hashed body, so the hash is
    # reproducible from the body alone).
    path.write_text(body + f"\n<!-- sha256: {digest} -->\n")
    return {"path": str(path), "sha256": digest}


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

def _resolve_field(inline, file_path, name):
    """Exactly one of inline / file may be set. Loud error otherwise."""
    if inline is not None and file_path is not None:
        raise ValueError(f"pass only one of --{name} or --{name}-file, not both")
    if inline is not None:
        return inline
    if file_path is not None:
        return Path(file_path).read_text()
    raise ValueError(f"missing --{name} (or --{name}-file)")


def build_parser():
    p = argparse.ArgumentParser(description="Date-locked pre-registration (Gate 2).")
    p.add_argument("--slug", required=True, help="kebab-case hypothesis slug")
    p.add_argument("--true-shape")
    p.add_argument("--true-shape-file")
    p.add_argument("--false-shape")
    p.add_argument("--false-shape-file")
    p.add_argument("--thresholds", help="'key=value;key=value'")
    p.add_argument("--thresholds-file")
    p.add_argument("--out-dir", help="output dir (default falsify/<slug>/)")
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        true_shape = _resolve_field(args.true_shape, args.true_shape_file, "true-shape")
        false_shape = _resolve_field(args.false_shape, args.false_shape_file, "false-shape")
        thr_text = _resolve_field(args.thresholds, args.thresholds_file, "thresholds")
        thresholds = parse_thresholds(thr_text)
        out_dir = args.out_dir or (Path("falsify") / args.slug)
        res = write_prereg(args.slug, true_shape, false_shape, thresholds, out_dir)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2
    except FileExistsError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 3
    except OSError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2
    print(f"locked: {res['path']}")
    print(f"sha256: {res['sha256']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
