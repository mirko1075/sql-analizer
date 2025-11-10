#!/bin/bash
# DBPower Base - One-Command Installation Script

set -e  # Exit on error

echo "🧠 DBPower Base - LLaMA Edition"
echo "================================"
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    echo "   Visit: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    echo "   Visit: https://docs.docker.com/compose/install/"
    exit 1
fi

echo "✅ Docker found: $(docker --version)"
echo "✅ Docker Compose found: $(docker compose version)"
echo ""

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "✅ .env file created"
else
    echo "✅ .env file already exists"
fi

echo ""
echo "🚀 Starting DBPower Base..."
echo ""

# Start all services
docker compose up -d

echo ""
echo "⏳ Waiting for services to start..."
sleep 5

# Check service status
echo ""
echo "📊 Service Status:"
docker compose ps

echo ""
echo "✅ Installation complete!"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "⚠️  IMPORTANT: First startup will take 5-10 minutes"
echo "   to download the LLaMA model (~5GB)."
echo ""
echo "📡 Monitor progress:"
echo "   docker compose logs -f ai-llama"
echo "   docker compose logs -f backend"
echo ""
echo "🌐 Access the dashboard:"
echo "   http://localhost:3000"
echo ""
echo "📚 API Documentation:"
echo "   http://localhost:8000/docs"
echo ""
echo "🔍 Check health:"
echo "   curl http://localhost:8000/health"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🎯 Next steps:"
echo "   1. Wait for backend to show '✅ Model ready for analysis'"
echo "   2. Open http://localhost:3000 in your browser"
echo "   3. Click '🔄 Collect Now' to import slow queries"
echo "   4. Click on any query to analyze with AI"
echo ""
echo "📖 For more info, see README.md"
echo ""
