#!/usr/bin/env bash

# If sourced, warn and stop (so we don't apply 'set -euo pipefail' to the user's shell)
if [[ "${BASH_SOURCE[0]}" != "$0" ]]; then
  echo "⚠️  Don't source this script. Run it as:  bash ./setup_path.sh"
  return 0 2>/dev/null || exit 0
fi

set -euo pipefail

HWDBTOOLS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

fs_type="$(stat -f -c %T "$HWDBTOOLS_DIR" 2>/dev/null || true)"
if [[ "$fs_type" == "drvfs" || "$HWDBTOOLS_DIR" == /mnt/* ]]; then
  echo "⚠️  This folder appears to be on a Windows mount (DrvFS): $HWDBTOOLS_DIR"
  echo "    Executing Linux binaries from /mnt/c is often problematic."
  echo "    Please copy HWDBTools into your Linux home directory (e.g., ~/HWDBTools_lnx_x8664) and rerun."
fi

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

# Make sure the installer script itself is runnable too
chmod a+rx "$HWDBTOOLS_DIR/setup_path.sh" 2>/dev/null || true

# Make all hwdb-* runnable (for everyone)
if chmod a+rx "$HWDBTOOLS_DIR"/hwdb-* 2>/dev/null; then
  echo "✅ chmod ok"
else
  echo "⚠️  chmod failed. Showing permissions:"
  ls -l "$HWDBTOOLS_DIR"/hwdb-* "$HWDBTOOLS_DIR/setup_path.sh" 2>/dev/null || true
fi

# quick sanity test (helps catch noexec mounts immediately)
if [[ -x "$HWDBTOOLS_DIR/hwdb-htgettoken" ]]; then
  if ! "$HWDBTOOLS_DIR/hwdb-htgettoken" --help >/tmp/hwdb_ht_help.out 2>/tmp/hwdb_ht_help.err; then
    echo "⚠️  hwdb-htgettoken failed to execute cleanly."
    echo "    This can be caused by:"
    echo "      - filesystem mounted with 'noexec' (common on /mnt/c in WSL)"
    echo "      - missing/too-old shared libraries (Linux/WSL compatibility issue)"
    echo ""
    echo "---- stderr (last 50 lines) ----"
    tail -n 50 /tmp/hwdb_ht_help.err || true
    echo "--------------------------------"
    echo ""
    echo "Hints:"
    echo "  • If you're on WSL, ensure HWDBTools is under /home (not /mnt/c)."
    echo "  • If you see 'undefined symbol' or 'not found', it's a shared-lib mismatch."
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
