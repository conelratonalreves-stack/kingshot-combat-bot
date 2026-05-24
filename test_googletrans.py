try:
    from googletrans import Translator
    print("✓ googletrans imported successfully")
    t = Translator()
    print("✓ Translator created")
    result = t.translate("hello world", dest="es")
    print(f"✓ Translation test: 'hello world' -> '{result.text}'")
except ImportError as e:
    print(f"❌ Import error: {e}")
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
