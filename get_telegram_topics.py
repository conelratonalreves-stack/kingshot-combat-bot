#!/usr/bin/env python3
"""
Script para obtener los IDs de los temas (topics) en un grupo de Telegram
"""
import sys
from telegram import Bot
from dotenv import load_dotenv
import os

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = -5234180120  # [AOW] Art of War - Kingshot

if not TELEGRAM_TOKEN:
    print("❌ Error: TELEGRAM_BOT_TOKEN no encontrado en .env")
    sys.exit(1)

try:
    bot = Bot(token=TELEGRAM_TOKEN)
    chat = bot.get_chat(CHAT_ID)
    
    print(f"\n📱 Grupo: {chat.title}")
    print(f"🔗 Chat ID: {chat.id}")
    
    if hasattr(chat, 'topics') and chat.topics:
        print(f"\n✅ Temas encontrados ({len(chat.topics)}):\n")
        for topic in chat.topics:
            print(f"  Tema: {topic.name}")
            print(f"  ID: {topic.topic_id}")
            print()
    else:
        print("\n⚠️  No hay temas configurados o el grupo no tiene soporte de temas habilitado.")
        print("Habilita Temas en: Grupo → Menú (⋮) → Editar grupo → Temas\n")
    
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)
