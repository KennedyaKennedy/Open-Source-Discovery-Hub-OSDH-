#!/usr/bin/env bash
set -e

echo "Open-Source Discovery Hub - Installer"
echo "======================================"

check_command() {
    if ! command -v "$1" &> /dev/null; then
        echo "Error: $1 is not installed."
        return 1
    fi
    return 0
}

check_python() {
    if check_command python3; then
        PYTHON=python3
    elif check_command python; then
        PYTHON=python
    else
        echo "Error: Python 3.10+ is required."
        exit 1
    fi

    VERSION=$($PYTHON -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    MAJOR=$(echo "$VERSION" | cut -d. -f1)
    MINOR=$(echo "$VERSION" | cut -d. -f2)

    if [ "$MAJOR" -lt 3 ] || ([ "$MAJOR" -eq 3 ] && [ "$MINOR" -lt 10 ]); then
        echo "Error: Python 3.10+ is required (found $VERSION)."
        exit 1
    fi

    echo "Python $VERSION found."
}

check_ollama() {
    if check_command ollama; then
        echo "Ollama found."
        if ! ollama list 2>/dev/null | grep -q "phi3"; then
            echo "Pulling phi3 model..."
            ollama pull phi3
        fi
    else
        echo "Warning: Ollama not found. AI features will not work."
        echo "Install Ollama: https://ollama.ai"
    fi
}

check_python
check_ollama

echo ""
echo "Setting up virtual environment..."
python3 -m venv .venv 2>/dev/null || python -m venv .venv
source .venv/bin/activate

echo "Installing dependencies..."
pip install -r requirements.txt

echo "Creating directories..."
mkdir -p data data/snapshots data/cache

if [ ! -f .env ]; then
    echo "Creating .env from template..."
    cp .env.example .env
fi

echo ""
echo "Installation complete!"
echo ""
echo "To start the server:"
echo "  source .venv/bin/activate"
echo "  python main.py"
echo ""
echo "Or use Docker:"
echo "  docker compose up -d"
echo ""
echo "CLI usage:"
echo "  python cli.py --help"
