#!/usr/bin/env bash
set -e

echo "=========================================="
echo "    MAGoCo-Self-Evo 1-Click Installer     "
echo "=========================================="

INSTALL_DIR="/opt/magoco"
REPO="macmam1/MAGoCo-Self-Evo"

# 1. Install Docker if missing
if ! command -v docker &> /dev/null; then
    echo "📦 Installing Docker..."
    curl -fsSL https://get.docker.com | sh
fi

# 2. Install docker-compose if missing
if ! command -v docker-compose &> /dev/null; then
    echo "📦 Installing docker-compose..."
    apt-get update -qq && apt-get install -y -qq docker-compose 2>/dev/null || pip3 install docker-compose 2>/dev/null || true
fi

# 3. Download project (try git clone first, fallback to tarball)
mkdir -p "$INSTALL_DIR"
cd "$INSTALL_DIR"

echo "📥 Downloading MAGoCo-Self-Evo..."
if command -v git &> /dev/null; then
    git clone "https://github.com/$REPO.git" . 2>/dev/null || true
fi

# If git clone failed (private repo), download tarball from release
if [ ! -f "docker-compose.yml" ]; then
    echo "📥 Downloading release tarball..."
    curl -fsSL "https://github.com/$REPO/releases/latest/download/magoco-clean.tar.gz" -o /tmp/magoco.tar.gz || {
        echo "❌ Cannot download. Please clone manually or check internet."
        exit 1
    }
    tar -xzf /tmp/magoco.tar.gz -C "$INSTALL_DIR"
    rm /tmp/magoco.tar.gz
fi

# 4. Setup environment
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "✅ .env created (edit $INSTALL_DIR/.env to add API keys)"
fi

# 5. Build and start
echo "🚀 Building & starting services (this may take a few minutes)..."
docker-compose up -d --build

echo ""
echo "=========================================="
echo "✅ MAGoCo-Self-Evo is running!"
echo "   🌐 Frontend: http://localhost:5173"
echo "   ⚙️  Backend:  http://localhost:8000"
echo "   📊 Health:    curl http://localhost:8000/health"
echo ""
echo "   📁 Installed: $INSTALL_DIR"
echo "   ⚙️  Config:    $INSTALL_DIR/.env"
echo "=========================================="
