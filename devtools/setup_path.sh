#!/usr/bin/env bash
set -euo pipefail

HWDBTOOLS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_DIR="$HOME/.config/hwdbtools"
ENV_FILE="$ENV_DIR/env.sh"

mkdir -p "$ENV_DIR"

# ---------------------------------------
# 1) macOS: remove quarantine (recursive)
# ---------------------------------------
if [[ "$(uname -s)" == "Darwin" ]]; then
  if command -v xattr >/dev/null 2>&1; then
    echo "!!!️  macOS detected: removing quarantine attribute from HWDBTools folder..."
    # Use -r for recursive, ignore errors if some files don't have the attribute
    xattr -dr com.apple.quarantine "$HWDBTOOLS_DIR" 2>/dev/null || true
  else
    echo "⚠️  xattr not found; skipping quarantine removal."
  fi
fi

# ---------------------------------------
# 2) All OS: ensure executables are +x
# ---------------------------------------
echo "!!! Setting executable bit on hwdb-* ..."
chmod -R a+rX "$HWDBTOOLS_DIR" || true

if chmod a+x "$HWDBTOOLS_DIR"/hwdb-* 2>/dev/null; then
  echo "✅ chmod ok"
else
  echo "⚠️  chmod failed. Showing permissions:"
  ls -l "$HWDBTOOLS_DIR"/hwdb-* || true
fi

# quick sanity test (helps catch noexec mounts immediately)
if [[ -x "$HWDBTOOLS_DIR/hwdb-htgettoken" ]]; then
  if ! "$HWDBTOOLS_DIR/hwdb-htgettoken" --help >/dev/null 2>&1; then
    echo "⚠️  hwdb-htgettoken exists and is executable, but did not run."
    echo "    This often means the filesystem is mounted with 'noexec'."
    echo "    If you're on WSL, avoid /mnt/c (Windows mounts)."
    echo "    Move HWDBTools to your Linux home dir (e.g., ~/HWDBTools_lnx)."
  fi
else
  echo "⚠️  hwdb-htgettoken is not executable:"
  ls -l "$HWDBTOOLS_DIR/hwdb-htgettoken" 2>/dev/null || true
fi

# ---------------------------------------
# Write env snippet to add HWDBTools to PATH
# ---------------------------------------
cat > "$ENV_FILE" <<EOF
# Auto-generated HWDBTools PATH setup
export PATH="$HWDBTOOLS_DIR:\$PATH"
EOF

# Pick startup file based on current shell
if [[ "${SHELL:-}" == *zsh ]]; then
  RC="$HOME/.zshrc"
elif [[ "${SHELL:-}" == *bash ]]; then
  # prefer .bashrc; if mac + only .bash_profile exists, use that
  if [[ "$(uname -s)" == "Darwin" && -f "$HOME/.bash_profile" && ! -f "$HOME/.bashrc" ]]; then
    RC="$HOME/.bash_profile"
  else
    RC="$HOME/.bashrc"
  fi
else
  RC="$HOME/.profile"
fi

LINE='[ -f "$HOME/.config/hwdbtools/env.sh" ] && source "$HOME/.config/hwdbtools/env.sh"'

touch "$RC"
grep -Fqs "$LINE" "$RC" || printf "\n# HWDBTools\n%s\n" "$LINE" >> "$RC"

echo "✅ HWDBTools PATH enabled."
echo "   HWDBTools dir: $HWDBTOOLS_DIR"
echo "   Startup file:  $RC"
echo ""
echo "Open a new terminal, or run:"
echo "  source \"$ENV_FILE\""
