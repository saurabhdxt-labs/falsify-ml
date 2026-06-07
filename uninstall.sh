#!/usr/bin/env bash
# uninstall.sh — remove the symlinks install.sh created. Only removes its OWN symlinks; never
# deletes a real directory (e.g. if you had a hand-made skill there, it is left untouched).
set -eu

SKILL_DST="$HOME/.claude/skills/falsify"
CLI_DST="$HOME/.local/bin/falsify"

say() { printf '%s\n' "$*"; }
say "== falsify uninstall =="

remove_link() {
  dst="$1"
  if [ -L "$dst" ]; then
    rm "$dst"
    say "removed symlink $dst"
  elif [ -e "$dst" ]; then
    say "left in place (not a symlink we created): $dst"
  else
    say "nothing at $dst"
  fi
}

remove_link "$SKILL_DST"
remove_link "$CLI_DST"
say "Done."
