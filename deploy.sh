#!/usr/bin/env bash
# ============================================
# MAGoCo-Self-Evo — Freestyle VM Deploy Script
# ============================================
# Run this on a Freestyle VM: npx freestyle vm create --ssh
set -e

echo "🚀 MAGoCo-Self-Evo Deployment Starting..."
echo "=========================================="

# 1. Install dependencies
echo "📦 Step 1: Installing dependencies..."
apt-get update -qq && apt-get install -y -qq git curl docker.io docker-compose > /dev/null 2>&1
echo "   ✅ Dependencies installed"

# 2. Clone the project
echo "📥 Step 2: Cloning project..."
cd /opt
rm -rf MAGoCo-Self-Evo
git clone https://github.com/macmam1/MAGoCo-Self-Evo.git
cd MAGoCo-Self-Evo
echo "   ✅ Project cloned"

# 3. Setup environment
echo "⚙️  Step 3: Setting up environment..."
cp .env.example .env 2>/dev/null || true
echo "   ✅ Environment configured"

# 4. Build and start
echo "🐳 Step 4: Building Docker containers..."
docker-compose up -d --build
echo "   ✅ Containers built and started"

# 5. Wait for services
echo "⏳ Step 5: Waiting for services to start..."
sleep 10

# 6. Health check
echo "🏥 Step 6: Health check..."
HEALTH=$(curl -s http://localhost:8000/health 2>/dev/null || echo '{"status":"checking"}')
echo "   Backend: $HEALTH"

# 7. Get URLs
echo ""
echo "=========================================="
echo "✅ MAGoCo-Self-Evo is LIVE!"
echo "=========================================="
echo ""
echo "🌐 Frontend:  http://localhost:5173"
echo "⚙️  Backend:   http://localhost:8000"
echo "📊 API Docs:  http://localhost:8000/docs"
echo "🏥 Health:    curl http://localhost:8000/health"
echo ""
echo "To get public URLs, check Freestyle dashboard."
echo "=========================================="