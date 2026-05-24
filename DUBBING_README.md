# Discord Audio Dubbing Bot

Automatic audio dubbing and translation for Discord voice notes using:
- **OpenAI Whisper** - Audio transcription
- **LibreTranslate** - Free translation
- **ElevenLabs** - Natural voice synthesis

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure API Keys

Add to your `.env` file:

```env
# Discord Bot Token
SPY_BOT_TOKEN=your_discord_token

# OpenAI API Key (for Whisper transcription)
OPENAI_API_KEY=your_openai_key

# ElevenLabs API Key (for voice synthesis)
ELEVENLABS_API_KEY=your_elevenlabs_key
```

### 3. Run the Bot

```bash
python spy_bot_main.py
```

## Commands

### `/dubbing [source_language] [target_language]`
Transcribe, translate, and dub an audio message.

**Usage:**
1. Run `/dubbing auto es` (auto-detect source, translate to Spanish)
2. Upload your audio file (MP3, WAV, OGG, WEBM - max 25MB)
3. Wait for processing (~30-60 seconds)
4. Receive dubbed audio as attachment

**Examples:**
- `/dubbing auto en` - Auto-detect source, dub to English
- `/dubbing es fr` - Spanish to French
- `/dubbing en de` - English to German

### `/voices [language?]`
List available ElevenLabs voices with preview links.

**Usage:**
- `/voices` - Show all voices
- `/voices en` - Show only English voices
- `/voices es` - Show only Spanish voices

Each voice includes:
- Voice ID (for custom selection)
- Language support
- Preview audio link

### `/voice-preview [voice_id] [text?]`
Preview a voice with sample audio.

**Usage:**
- `/voice-preview 21m00Tcm4TlvDq8ikWAM` - Play built-in preview
- `/voice-preview 21m00Tcm4TlvDq8ikWAM Hello world` - Generate custom preview

## Supported Languages

**Common Languages:**
- English (en), Spanish (es), French (fr), German (de)
- Italian (it), Portuguese (pt), Russian (ru)
- Japanese (ja), Korean (ko), Chinese (zh)
- Arabic (ar), Hindi (hi), Dutch (nl)
- Polish (pl), Turkish (tr), Swedish (sv)
- And 160+ more via LibreTranslate

## Costs

- **OpenAI Whisper**: ~$0.006 per minute of audio
- **LibreTranslate**: Free (open-source)
- **ElevenLabs**:
  - Free tier: 10,000 characters/month
  - Starter: $5/month for 30,000 characters
  - Creator: $11/month for 100,000 characters

**Example cost:** 1-minute voice note → ~150 words → ~900 characters
- Transcription: $0.006
- Translation: Free
- Synthesis: ~1-2% of monthly ElevenLabs quota
- **Total: $0.006 + ElevenLabs quota**

## Limitations

- Max audio size: 25MB (Whisper API limit)
- Max audio length: ~25 minutes (25MB at standard bitrate)
- Processing time: 30-60 seconds per audio
- No lip-sync (audio-only dubbing)
- Output format: MP3 (44.1kHz, 128kbps)

## Tips

1. **Use short audio clips** (1-5 minutes) for faster processing
2. **Use clear speech** for better transcription accuracy
3. **Try different voices** with `/voices` and `/voice-preview`
4. **Auto-detect language** works best with clear, single-language audio
5. **Check ElevenLabs quota** regularly on free tier

## Troubleshooting

**"No audio detected"**
- Ensure audio file is valid and contains speech
- Try converting to MP3 or WAV first

**"Transcription failed"**
- Check OPENAI_API_KEY is valid
- Ensure audio is < 25MB
- Verify audio format is supported

**"Translation failed"**
- LibreTranslate may be temporarily unavailable
- Check internet connection
- Try again in a few minutes

**"No voice available"**
- Use `/voices [language]` to see available voices
- Some languages may have limited voice support

## Development

**Project Structure:**
```
Bot Composicion Discord/
├── cogs/
│   └── dubbing.py          # Discord commands
├── utils/
│   ├── elevenlabs_client.py    # ElevenLabs API wrapper
│   ├── audio_transcription.py  # Whisper transcription
│   └── translation.py          # LibreTranslate wrapper
├── spy_bot_main.py         # Main bot file
└── requirements.txt        # Dependencies
```

**Adding Custom Voices:**
Edit `cogs/dubbing.py` and update `default_voices` dict with your preferred voice IDs.

## License

MIT License - See project root for details.
