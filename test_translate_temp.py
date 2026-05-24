from spy_translations import TRANSLATOR_AVAILABLE, translate_reason

print(f"Translator Available: {TRANSLATOR_AVAILABLE}")
print("\nTesting translations:")
print(f"'hate him' -> es: {translate_reason('hate him', 'es')}")
print(f"'still the same hate' -> es: {translate_reason('still the same hate', 'es')}")
print(f"'attack resources' -> es: {translate_reason('attack resources', 'es')}")
