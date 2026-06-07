#!/usr/bin/env bash
# install.sh — make falsify available globally: the /falsify Claude skill + the `falsify` CLI.
#
#   git pull && ./install.sh
#
# Symlinks (so future `git pull`s are picked up live, no re-install):
#   ~/.claude/skills/falsify  -> <repo>/skills/falsify   (the /falsify Claude Code skill)
#   ~/.local/bin/falsify      -> <repo>/bin/falsify       (the standalone CLI, no Claude needed)
#
# Idempotent. Refuses to clobber a REAL directory (only replaces its own symlinks). Never edits
# your shell rc — if ~/.local/bin isn't on PATH, it prints the line for you to add.
set -eu

# Resolve the repo root from this script's own location (works from any CWD).
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$SCRIPT_DIR"

SKILL_SRC="$REPO_ROOT/skills/falsify"
CLI_SRC="$REPO_ROOT/bin/falsify"
SKILL_DST="$HOME/.claude/skills/falsify"
CLI_DST="$HOME/.local/bin/falsify"

say() { printf '%s\n' "$*"; }

# Create or replace a symlink at $2 pointing to $1. Refuse to clobber a real (non-symlink) path.
link() {
  src="$1"; dst="$2"
  if [ -e "$dst" ] && [ ! -L "$dst" ]; then
    say "ERROR: $dst already exists and is NOT a symlink — refusing to clobber it."
    say "       Move it aside and re-run, or remove it yourself."
    return 1
  fi
  [ -L "$dst" ] && rm "$dst"
  mkdir -p "$(dirname "$dst")"
  ln -s "$src" "$dst"
  say "linked $dst -> $src"
}

say "== falsify install =="
say "repo root: $REPO_ROOT"

# Sanity: the sources must exist (catches a broken/partial clone).
[ -f "$SKILL_SRC/SKILL.md" ] || { say "ERROR: $SKILL_SRC/SKILL.md not found — broken clone?"; exit 1; }
[ -f "$CLI_SRC" ] || { say "ERROR: $CLI_SRC not found — broken clone?"; exit 1; }

# 1) the /falsify skill
link "$SKILL_SRC" "$SKILL_DST"

# 2) the falsify CLI
link "$CLI_SRC" "$CLI_DST"
chmod +x "$CLI_SRC" 2>/dev/null || true

# 3) PATH note (do NOT edit rc files — that's the user's call)
case ":${PATH:-}:" in
  *":$HOME/.local/bin:"*) say "ok: ~/.local/bin is already on PATH" ;;
  *)
    say ""
    say "NOTE: ~/.local/bin is not on your PATH. Add this line to your shell rc"
    say "      (~/.zshrc or ~/.bashrc), then reload your shell:"
    say ""
    say "      export PATH=\"\$HOME/.local/bin:\$PATH\""
    say ""
    ;;
esac

# 4) smoke check — run a subcommand through the installed CLI
if command -v python3 >/dev/null 2>&1; then
  if python3 "$CLI_DST" reality --n 100 --target-effect 0.3 >/dev/null 2>&1; then
    say "smoke check: PASS (falsify reality ran)"
  else
    say "smoke check: FAIL — 'falsify reality' did not run; check python3 and the clone."
  fi
else
  say "smoke check: SKIPPED — python3 not found on PATH (the scripts need Python 3.8+)."
fi

say ""
say "Done."
say "  /falsify   — available in Claude Code (restart/new session if it doesn't autocomplete)."
say "  falsify    — CLI on PATH after you reload your shell; try: falsify --help"
