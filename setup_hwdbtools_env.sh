#!/usr/bin/env bash
#
# After installation...
# source .venv/bin/activate     # (or conda activate sisyphus_env)
# python -m Sisyphus.Gui.Dashboard
#
# ---------------------------------------------------------------------
# Python HWDB Tools Environment Setup Script
# Compatible with macOS, Linux, and WSL
#
# - This sets up the environment needed to run Python HWDB Tools.
#   Will writes few lines to setup env variables in your ~/.bashrc or .zshrc or .profile.
# - Place this script in the root directory of the source code. E.g., ~//DUNE-HWDB-Python/
# - Then run it; ./setup_hwdbtools_env.sh
# ---------------------------------------------------------------------

set -euo pipefail
IFS=$'\n\t'

echo "=== Python HWDB Tools Environment Setup ==="

# ---------------------------------------------------------------------
# 1. Detect OS type
# ---------------------------------------------------------------------
OS="$(uname -s)"
case "$OS" in
    Darwin*) OS_TYPE="macOS" ;;
    Linux*)
        if grep -qi microsoft /proc/version 2>/dev/null; then
            OS_TYPE="WSL"
        else
            OS_TYPE="Linux"
        fi
        ;;
    *) OS_TYPE="Unknown" ;;
esac
echo "Detected OS: $OS_TYPE"

#----------------------------------------------------------------------
# 2. Verify Python availability
#----------------------------------------------------------------------
if ! command -v python3 &>/dev/null && ! command -v conda &>/dev/null; then
     echo " Python not found."
     echo "Please install Miniconda first:"
     echo "https://docs.conda.io/en/latest/miniconda.html"
     exit 1
fi

# ---------------------------------------------------------------------
# 3. Detect Python + package manager
# ---------------------------------------------------------------------
if command -v conda &>/dev/null; then
    PKG_MGR="conda"

     echo "Accepting Conda Terms of Service (if required)..."
     conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/main || true
     conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/r || true

elif command -v pip &>/dev/null; then
    PKG_MGR="pip"
else
    echo "❌ Neither conda nor pip found. Please install Python first."
    exit 1
fi
echo "Using package manager: $PKG_MGR"

# ---------------------------------------------------------------------
# 4. Define environment name and location
# ---------------------------------------------------------------------
DEFAULT_ENV_NAME="hwdb_env"

echo " "
echo "Please enter a name for the Python environment."
echo "Press Enter to use the  default: [$DEFAULT_ENV_NAME]"
read -r ENV_NAME

ENV_NAME="${ENV_NAME:-$DEFAULT_ENV_NAME}"
echo "Using environment name: $ENV_NAME"
echo " "

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SISYPHUS_HOME="$ROOT_DIR"
REQ_FILE="$ROOT_DIR/requirements.txt"

# ---------------------------------------------------------------------
# 5. Create environment and verify of the active environment
# ---------------------------------------------------------------------
if [ "$PKG_MGR" = "conda" ]; then
    if conda env list | grep -q "$ENV_NAME"; then
        echo "Conda environment '$ENV_NAME' already exists."
    else
        echo "Creating new conda environment '$ENV_NAME'..."
        conda create -y -n "$ENV_NAME" python=3.13
	#conda create -y -n "$ENV_NAME" python=3.12 -y
    fi
    eval "$(conda shell.bash hook)"
    echo "Activating '$ENV_NAME'..."
    conda activate "$ENV_NAME"
else
    if [ ! -d "$ROOT_DIR/.venv" ]; then
        echo "Creating virtual environment (.venv)..."
        python3 -m venv "$ROOT_DIR/.venv"
    fi
    echo "Activating '$ROOT_DIR'/.venv..."
    source "$ROOT_DIR/.venv/bin/activate"
fi

# ---------------------------------------------------------------------
# 6. Generate or update requirements.txt using pip-tools
# ---------------------------------------------------------------------
if ! command -v pip-compile &>/dev/null; then
    echo "Installing pip-tools..."
    python -m pip install --upgrade pip-tools
fi

REQ_IN="$ROOT_DIR/requirements.in"
REQ_OUT="$ROOT_DIR/requirements.txt"

# Create a starter requirements.in if none exists
if [ ! -f "$REQ_IN" ]; then
    echo "Creating default requirements.in..."
    cat > "$REQ_IN" <<'EOF'
dash
dash-bootstrap-components
htgettoken
json5
numpy
pyopenssl
PyQt5
pandas
qdarkstyle
reportlab
EOF
fi

echo "Compiling dependencies with pip-compile..."
python -m piptools compile "$REQ_IN" --output-file "$REQ_OUT" --quiet

# ---------------------------------------------------------------------
# 7. Install dependencies
# ---------------------------------------------------------------------
echo "Installing required Python packages from $REQ_OUT..."
if [ "$PKG_MGR" = "conda" ]; then
    # Use pip even inside conda env to match exact versions
    python -m pip install --no-cache-dir -r "$REQ_OUT"
else
    python -m pip install --no-cache-dir -r "$REQ_OUT"
fi

# ---------------------------------------------------------------------
# 8. Set environment variables
# ---------------------------------------------------------------------
echo "Setting environment variables..."
export SISYPHUS_HOME="$SISYPHUS_HOME"
export PATH="$SISYPHUS_HOME:$SISYPHUS_HOME/bin:$SISYPHUS_HOME/devtools:$PATH"
export PYTHONPATH="$SISYPHUS_HOME/lib:$PYTHONPATH"
export FLASK_RUN_FROM_CLI="false"

# OS-specific adjustments
case "$OS_TYPE" in
    macOS)
        export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES
        ;;
    WSL)
        export BROWSER="wslview"
        ;;
esac

# Persist to shell profile
if [[ "$SHELL" == *"bash"* ]]; then
    RC_FILE="$HOME/.bashrc"
elif [[ "$SHELL" == *"zsh"* ]]; then
    RC_FILE="$HOME/.zshrc"
else
    RC_FILE="$HOME/.profile"
fi

if ! grep -q "SISYPHUS_HOME" "$RC_FILE" 2>/dev/null; then
    echo "Persisting environment variables in $RC_FILE..."
    {
        echo ""
        echo "# >>> Added by hwdbtools_env.sh >>>"
        echo "export SISYPHUS_HOME=\"$SISYPHUS_HOME\""
	echo "export PATH=\"$SISYPHUS_HOME:$SISYPHUS_HOME/bin:$SISYPHUS_HOME/devtools:\$PATH\""
        echo "export PYTHONPATH=\"\$SISYPHUS_HOME/lib:\$PYTHONPATH\""
        echo "export FLASK_RUN_FROM_CLI=false"
	echo "# <<< Added by setup_hwdbtools_env.sh <<<"
    } >> "$RC_FILE"
fi

# ---------------------------------------------------------------------
# 9. Make sure they are all executable
# ---------------------------------------------------------------------
chmod u+x $SISYPHUS_HOME/hwdb-*
chmod u+x $SISYPHUS_HOME/bin/*
chmod u+x $SISYPHUS_HOME/devtools/*
# ---------------------------------------------------------------------
# 10. Final message
# ---------------------------------------------------------------------
echo ""
echo ""
echo ""
echo "====================================================="
echo "  Python HWDB Tools environment setup complete!"
echo "====================================================="
echo ""

if [ "$PKG_MGR" = "conda" ]; then
    echo "To activate the environment, run:"
    echo "   conda activate $ENV_NAME"
else
    echo "To activate the environment, run:"
    echo "   source .venv/bin/activate"
fi
echo ""
#read -p "Do you want to launch the Dashboard now? (y/n): " RUN_NOW

#if [[  "$RUN_NOW" =~ ^[Yy]$  ]]; then
#   echo "Launching Dashboard..."
#   python -m Sisyphus.Gui.Dashboard
#else 
#   echo ""
#   echo "You can launch it later with:"
#   echo "   python -m Sisyphus.Gui.Dashboard"
#fi
echo "Then launch them with commands such as:"
echo "   hwdb-configure"
echo "   hwdb-dash"
echo "   hwdb-shipping"
echo "   hwdb-labels"
echo "   hwdb-upload"
echo ""
echo "For more details, please refer to the following site:"
echo "General info  : https://dune.github.io/computing-HWDB/07-Using-Python-Upload-Tool/index.html"
echo "hwdb-dash     : https://dune.github.io/computing-HWDB/dashboard/index.html"
echo "hwdb-shipping : https://dune.github.io/computing-HWDB/shippingprocedure/index.html"
echo "hwdb-labels   : https://dune.github.io/computing-HWDB/barqrcode/index.html"
echo "hwdb-upload   : https://dune.github.io/computing-HWDB/07-Using-Python-Upload-Tool/index.html"
echo ""
