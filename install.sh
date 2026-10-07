#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="$HOME/.local/bin"

echo "🌙 Installing PDF Dark Mode..."

# 1. Create venv if not present
if [ ! -d "$SCRIPT_DIR/.venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv "$SCRIPT_DIR/.venv"
fi

# 2. Install dependencies
echo "📦 Installing Python dependencies..."
"$SCRIPT_DIR/.venv/bin/pip" install --quiet -r "$SCRIPT_DIR/requirements.txt"

# 3. Create CLI wrapper in ~/.local/bin
mkdir -p "$BIN_DIR"
cat << EOF > "$BIN_DIR/pdf-darkmode"
#!/bin/bash
exec "$SCRIPT_DIR/.venv/bin/python3" "$SCRIPT_DIR/pdf_darkmode.py" "\$@"
EOF
chmod +x "$BIN_DIR/pdf-darkmode"
ln -sf "$BIN_DIR/pdf-darkmode" "$BIN_DIR/pdf-dark"

echo "✅ Installed! You can now run 'pdf-darkmode <file.pdf>' or 'pdf-dark <file.pdf>' in terminal."
