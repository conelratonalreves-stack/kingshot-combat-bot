#!/bin/bash
# Setup script for Discord Audio Dubbing Bot

echo "🎙️ Discord Audio Dubbing Bot - Setup"
echo "======================================"
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ .env file not found!"
    echo "Please create a .env file with:"
    echo "  SPY_BOT_TOKEN=your_discord_token"
    echo "  OPENAI_API_KEY=your_openai_key"
    echo "  ELEVENLABS_API_KEY=your_elevenlabs_key"
    exit 1
fi

# Check if ELEVENLABS_API_KEY is set
if ! grep -q "ELEVENLABS_API_KEY=.*[^=]" .env; then
    echo "⚠️  ELEVENLABS_API_KEY not configured in .env"
    echo "Please add your ElevenLabs API key to .env file"
    echo ""
    read -p "Enter your ElevenLabs API key: " api_key
    echo "ELEVENLABS_API_KEY=$api_key" >> .env
    echo "✓ API key added to .env"
fi

# Install dependencies
echo ""
echo "📦 Installing Python dependencies..."
pip install -r requirements.txt

# Check if ffmpeg is available (optional for audio conversion)
if ! command -v ffmpeg &> /dev/null; then
    echo ""
    echo "⚠️  ffmpeg not found (optional for audio format conversion)"
    echo "Install with: sudo apt-get install ffmpeg"
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "To start the bot, run:"
echo "  python spy_bot_main.py"
echo ""
echo "Available commands:"
echo "  /dubbing [source_lang] [target_lang] - Translate and dub audio"
echo "  /voices [language] - List available voices"
echo "  /voice-preview [voice_id] - Preview a voice"
echo ""
