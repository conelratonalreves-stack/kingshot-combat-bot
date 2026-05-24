"""
Quick test script for ElevenLabs API integration.
Tests: API connection, voice listing, and basic synthesis.
"""

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from utils.elevenlabs_client import ElevenLabsClient


def test_connection():
    """Test ElevenLabs API connection."""
    print("🔌 Testing ElevenLabs API connection...")
    
    try:
        client = ElevenLabsClient()
        print("✓ API key loaded")
        return client
    except Exception as e:
        print(f"❌ Failed to initialize client: {e}")
        return None


def test_list_voices(client):
    """Test listing voices."""
    print("\n🎤 Fetching available voices...")
    
    voices = client.list_voices()
    if not voices:
        print("❌ No voices found or API error")
        return False
    
    print(f"✓ Found {len(voices)} voices")
    
    # Show first 5 voices
    print("\nFirst 5 voices:")
    for voice in voices[:5]:
        name = voice.get('name', 'Unknown')
        voice_id = voice.get('voice_id', 'N/A')
        labels = voice.get('labels', {})
        lang = labels.get('language', 'unknown')
        print(f"  • {name} ({voice_id}) - {lang}")
        if 'preview_url' in voice:
            print(f"    Preview: {voice['preview_url']}")
    
    return True


def test_synthesis(client):
    """Test voice synthesis."""
    print("\n🔊 Testing voice synthesis...")
    
    # Get first available voice
    voices = client.list_voices()
    if not voices:
        print("❌ No voices available")
        return False
    
    voice = voices[0]
    voice_id = voice['voice_id']
    voice_name = voice['name']
    
    print(f"Using voice: {voice_name} ({voice_id})")
    
    # Synthesize test text
    text = "Hello! This is a test of the ElevenLabs text to speech API."
    audio_bytes = client.synthesize_speech(text, voice_id)
    
    if not audio_bytes:
        print("❌ Synthesis failed")
        return False
    
    # Save test output
    output_path = "test_output.mp3"
    with open(output_path, 'wb') as f:
        f.write(audio_bytes)
    
    print(f"✓ Generated {len(audio_bytes)} bytes of audio")
    print(f"✓ Saved to: {output_path}")
    print("\nYou can play this file to verify the synthesis worked!")
    
    return True


def test_language_filtering(client):
    """Test language filtering."""
    print("\n🌍 Testing language filtering...")
    
    # Test English voices
    en_voices = client.list_voices('en')
    print(f"English voices: {len(en_voices)}")
    
    # Test Spanish voices
    es_voices = client.list_voices('es')
    print(f"Spanish voices: {len(es_voices)}")
    
    return True


def main():
    """Run all tests."""
    print("=" * 60)
    print("ElevenLabs API Integration Test")
    print("=" * 60)
    
    # Check API key
    if not os.getenv("ELEVENLABS_API_KEY"):
        print("\n❌ ELEVENLABS_API_KEY not set in environment")
        print("Please add it to your .env file:")
        print("  ELEVENLABS_API_KEY=your_key_here")
        return
    
    # Initialize client
    client = test_connection()
    if not client:
        return
    
    # Run tests
    tests = [
        ("List Voices", lambda: test_list_voices(client)),
        ("Language Filtering", lambda: test_language_filtering(client)),
        ("Voice Synthesis", lambda: test_synthesis(client))
    ]
    
    results = {}
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"\n❌ {test_name} failed with error: {e}")
            import traceback
            traceback.print_exc()
            results[test_name] = False
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status} - {test_name}")
    
    all_passed = all(results.values())
    print("\n" + ("✓ All tests passed!" if all_passed else "❌ Some tests failed"))
    
    if all_passed:
        print("\n🎉 ElevenLabs integration is working!")
        print("You can now use the /dubbing, /voices, and /voice-preview commands")


if __name__ == "__main__":
    main()
