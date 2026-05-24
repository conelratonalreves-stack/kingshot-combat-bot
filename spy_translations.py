"""Translation system for Kingshot Spy Bot."""

from typing import Dict, Optional
import discord

# Try to import Deep Translator (uses Google Translate API)
try:
    from deep_translator import GoogleTranslator
    TRANSLATOR_AVAILABLE = True
    print("✓ Deep Translator (Google Translate) available for automatic translations")
except ImportError:
    TRANSLATOR_AVAILABLE = False
    print("⚠ Deep Translator not available - install with: pip install deep-translator")

# Supported languages
SUPPORTED_LANGUAGES = {
    'en': 'English',
    'es': 'Español',
    'fr': 'Français',
    'de': 'Deutsch',
    'it': 'Italiano',
    'pt': 'Português'
}

# Translation dictionary
TRANSLATIONS = {
    # Commands and titles
    'spy_added_title': {
        'en': '✅ Player Added to Spy List',
        'es': '✅ Jugador Agregado a la Lista de Espías',
        'fr': '✅ Joueur Ajouté à la Liste d\'Espions',
        'de': '✅ Spieler zur Spionliste Hinzugefügt',
        'it': '✅ Giocatore Aggiunto alla Lista Spie',
        'pt': '✅ Jogador Adicionado à Lista de Espiões'
    },
    'player': {
        'en': 'Player',
        'es': 'Jugador',
        'fr': 'Joueur',
        'de': 'Spieler',
        'it': 'Giocatore',
        'pt': 'Jogador'
    },
    'alliance': {
        'en': 'Alliance',
        'es': 'Alianza',
        'fr': 'Alliance',
        'de': 'Allianz',
        'it': 'Alleanza',
        'pt': 'Aliança'
    },
    'coordinates': {
        'en': 'Coordinates',
        'es': 'Coordenadas',
        'fr': 'Coordonnées',
        'de': 'Koordinaten',
        'it': 'Coordinate',
        'pt': 'Coordenadas'
    },
    'reason': {
        'en': 'Reason',
        'es': 'Razón',
        'fr': 'Raison',
        'de': 'Grund',
        'it': 'Motivo',
        'pt': 'Razão'
    },
    'added_by': {
        'en': 'Added by',
        'es': 'Agregado por',
        'fr': 'Ajouté par',
        'de': 'Hinzugefügt von',
        'it': 'Aggiunto da',
        'pt': 'Adicionado por'
    },
    'time': {
        'en': 'Time',
        'es': 'Hora',
        'fr': 'Heure',
        'de': 'Zeit',
        'it': 'Ora',
        'pt': 'Hora'
    },
    'shield_added_title': {
        'en': '🛡️ Shield Timer Added',
        'es': '🛡️ Temporizador de Escudo Agregado',
        'fr': '🛡️ Minuteur de Bouclier Ajouté',
        'de': '🛡️ Schildtimer Hinzugefügt',
        'it': '🛡️ Timer Scudo Aggiunto',
        'pt': '🛡️ Temporizador de Escudo Adicionado'
    },
    'shield_start': {
        'en': 'Shield Start',
        'es': 'Inicio del Escudo',
        'fr': 'Début du Bouclier',
        'de': 'Schildbeginn',
        'it': 'Inizio Scudo',
        'pt': 'Início do Escudo'
    },
    'shield_expires': {
        'en': 'Expires',
        'es': 'Expira',
        'fr': 'Expire',
        'de': 'Läuft ab',
        'it': 'Scade',
        'pt': 'Expira'
    },
    'duration': {
        'en': 'Duration',
        'es': 'Duración',
        'fr': 'Durée',
        'de': 'Dauer',
        'it': 'Durata',
        'pt': 'Duração'
    },
    'hours': {
        'en': 'hours',
        'es': 'horas',
        'fr': 'heures',
        'de': 'Stunden',
        'it': 'ore',
        'pt': 'horas'
    },
    'bot_by': {
        'en': 'Bot by KnyCat',
        'es': 'Bot por KnyCat',
        'fr': 'Bot par KnyCat',
        'de': 'Bot von KnyCat',
        'it': 'Bot di KnyCat',
        'pt': 'Bot por KnyCat'
    },
    'notification_footer': {
        'en': 'You\'ll receive 2 DMs: 10 min warning + expiry alert (if notifications enabled)',
        'es': 'Recibirás 2 DMs: aviso de 10 min + alerta de expiración (si las notificaciones están habilitadas)',
        'fr': 'Vous recevrez 2 DMs: alerte 10 min + alerte d\'expiration (si notifications activées)',
        'de': 'Sie erhalten 2 DMs: 10 Min Warnung + Ablaufwarnung (wenn Benachrichtigungen aktiviert)',
        'it': 'Riceverai 2 DM: avviso 10 min + avviso scadenza (se notifiche abilitate)',
        'pt': 'Você receberá 2 DMs: aviso 10 min + alerta de expiração (se notificações ativadas)'
    },
    'shield_expiring_soon': {
        'en': '⏰ Shield Expiring Soon!',
        'es': '⏰ ¡Escudo Expirando Pronto!',
        'fr': '⏰ Bouclier Expire Bientôt!',
        'de': '⏰ Schild Läuft Bald Ab!',
        'it': '⏰ Scudo in Scadenza!',
        'pt': '⏰ Escudo Expirando em Breve!'
    },
    'shield_expired': {
        'en': '🚨 Shield EXPIRED!',
        'es': '🚨 ¡Escudo EXPIRADO!',
        'fr': '🚨 Bouclier EXPIRÉ!',
        'de': '🚨 Schild ABGELAUFEN!',
        'it': '🚨 Scudo SCADUTO!',
        'pt': '🚨 Escudo EXPIRADO!'
    },
    'attack_now': {
        'en': '**⚔️ ATTACK NOW!**',
        'es': '**⚔️ ¡ATACA AHORA!**',
        'fr': '**⚔️ ATTAQUEZ MAINTENANT!**',
        'de': '**⚔️ JETZT ANGREIFEN!**',
        'it': '**⚔️ ATTACCA ORA!**',
        'pt': '**⚔️ ATAQUE AGORA!**'
    },
    'expires_in_10_min': {
        'en': 'Will expire in approximately 10 minutes!',
        'es': '¡Expirará en aproximadamente 10 minutos!',
        'fr': 'Expirera dans environ 10 minutes!',
        'de': 'Läuft in etwa 10 Minuten ab!',
        'it': 'Scadrà tra circa 10 minuti!',
        'pt': 'Expirará em aproximadamente 10 minutos!'
    },
    'language_set_title': {
        'en': '🌐 Language Set',
        'es': '🌐 Idioma Configurado',
        'fr': '🌐 Langue Configurée',
        'de': '🌐 Sprache Eingestellt',
        'it': '🌐 Lingua Impostata',
        'pt': '🌐 Idioma Configurado'
    },
    'language_set_desc': {
        'en': 'Your language has been set to',
        'es': 'Tu idioma ha sido configurado a',
        'fr': 'Votre langue a été définie sur',
        'de': 'Ihre Sprache wurde eingestellt auf',
        'it': 'La tua lingua è stata impostata su',
        'pt': 'Seu idioma foi configurado para'
    },
    'all_responses_in_language': {
        'en': 'All bot responses and notifications will now be in this language.',
        'es': 'Todas las respuestas y notificaciones del bot estarán ahora en este idioma.',
        'fr': 'Toutes les réponses et notifications du bot seront désormais dans cette langue.',
        'de': 'Alle Bot-Antworten und Benachrichtigungen werden jetzt in dieser Sprache sein.',
        'it': 'Tutte le risposte e notifiche del bot saranno ora in questa lingua.',
        'pt': 'Todas as respostas e notificações do bot estarão agora neste idioma.'
    },
    'tracked_players': {
        'en': '🕵️ Tracked Players',
        'es': '🕵️ Jugadores Rastreados',
        'fr': '🕵️ Joueurs Suivis',
        'de': '🕵️ Verfolgte Spieler',
        'it': '🕵️ Giocatori Tracciati',
        'pt': '🕵️ Jogadores Rastreados'
    },
    'showing_players': {
        'en': 'Showing {count} player(s)',
        'es': 'Mostrando {count} jugador(es)',
        'fr': 'Affichage de {count} joueur(s)',
        'de': '{count} Spieler angezeigt',
        'it': 'Mostrando {count} giocatore/i',
        'pt': 'Mostrando {count} jogador(es)'
    },
    'no_tracked_players': {
        'en': '📋 **No Tracked Players**\nUse `/spy` to add players to track.',
        'es': '📋 **Sin Jugadores Rastreados**\nUsa `/spy` para agregar jugadores.',
        'fr': '📋 **Aucun Joueur Suivi**\nUtilisez `/spy` pour ajouter des joueurs.',
        'de': '📋 **Keine Verfolgten Spieler**\nVerwenden Sie `/spy`, um Spieler hinzuzufügen.',
        'it': '📋 **Nessun Giocatore Tracciato**\nUsa `/spy` per aggiungere giocatori.',
        'pt': '📋 **Nenhum Jogador Rastreado**\nUse `/spy` para adicionar jogadores.'
    },
    'player_added_desc': {
        'en': 'Player **{name}** has been added to the spy list.',
        'es': 'El jugador **{name}** ha sido agregado a la lista de espías.',
        'fr': 'Le joueur **{name}** a été ajouté à la liste d\'espions.',
        'de': 'Spieler **{name}** wurde zur Spionliste hinzugefügt.',
        'it': 'Il giocatore **{name}** è stato aggiunto alla lista spie.',
        'pt': 'O jogador **{name}** foi adicionado à lista de espiões.'
    },
    'shield_added_desc': {
        'en': 'Shield timer {action} for **{name}**',
        'es': 'Temporizador de escudo {action} para **{name}**',
        'fr': 'Minuteur de bouclier {action} pour **{name}**',
        'de': 'Schildtimer {action} für **{name}**',
        'it': 'Timer scudo {action} per **{name}**',
        'pt': 'Temporizador de escudo {action} para **{name}**'
    },
    'added': {
        'en': 'added',
        'es': 'agregado',
        'fr': 'ajouté',
        'de': 'hinzugefügt',
        'it': 'aggiunto',
        'pt': 'adicionado'
    },
    'updated': {
        'en': 'updated',
        'es': 'actualizado',
        'fr': 'mis à jour',
        'de': 'aktualisiert',
        'it': 'aggiornato',
        'pt': 'atualizado'
    }
}

# Common reason translations (bidirectional - from any language to any language)
REASON_TRANSLATIONS = {
    'attack': {'en': 'attack', 'es': 'atacar', 'fr': 'attaquer', 'de': 'angreifen', 'it': 'attaccare', 'pt': 'atacar'},
    'atacar': {'en': 'attack', 'es': 'atacar', 'fr': 'attaquer', 'de': 'angreifen', 'it': 'attaccare', 'pt': 'atacar'},
    'attaquer': {'en': 'attack', 'es': 'atacar', 'fr': 'attaquer', 'de': 'angreifen', 'it': 'attaccare', 'pt': 'atacar'},
    'angreifen': {'en': 'attack', 'es': 'atacar', 'fr': 'attaquer', 'de': 'angreifen', 'it': 'attaccare', 'pt': 'atacar'},
    'attaccare': {'en': 'attack', 'es': 'atacar', 'fr': 'attaquer', 'de': 'angreifen', 'it': 'attaccare', 'pt': 'atacar'},
    
    'enemy': {'en': 'enemy', 'es': 'enemigo', 'fr': 'ennemi', 'de': 'feind', 'it': 'nemico', 'pt': 'inimigo'},
    'enemigo': {'en': 'enemy', 'es': 'enemigo', 'fr': 'ennemi', 'de': 'feind', 'it': 'nemico', 'pt': 'inimigo'},
    'ennemi': {'en': 'enemy', 'es': 'enemigo', 'fr': 'ennemi', 'de': 'feind', 'it': 'nemico', 'pt': 'inimigo'},
    'feind': {'en': 'enemy', 'es': 'enemigo', 'fr': 'ennemi', 'de': 'feind', 'it': 'nemico', 'pt': 'inimigo'},
    'nemico': {'en': 'enemy', 'es': 'enemigo', 'fr': 'ennemi', 'de': 'feind', 'it': 'nemico', 'pt': 'inimigo'},
    'inimigo': {'en': 'enemy', 'es': 'enemigo', 'fr': 'ennemi', 'de': 'feind', 'it': 'nemico', 'pt': 'inimigo'},
    
    'hate': {'en': 'hate', 'es': 'odiar', 'fr': 'détester', 'de': 'hassen', 'it': 'odiare', 'pt': 'odiar'},
    'odiar': {'en': 'hate', 'es': 'odiar', 'fr': 'détester', 'de': 'hassen', 'it': 'odiare', 'pt': 'odiar'},
    'détester': {'en': 'hate', 'es': 'odiar', 'fr': 'détester', 'de': 'hassen', 'it': 'odiare', 'pt': 'odiar'},
    'hassen': {'en': 'hate', 'es': 'odiar', 'fr': 'détester', 'de': 'hassen', 'it': 'odiare', 'pt': 'odiar'},
    'odiare': {'en': 'hate', 'es': 'odiar', 'fr': 'détester', 'de': 'hassen', 'it': 'odiare', 'pt': 'odiar'},
    
    'him': {'en': 'him', 'es': 'a él', 'fr': 'lui', 'de': 'ihn', 'it': 'lui', 'pt': 'ele'},
    'her': {'en': 'her', 'es': 'a ella', 'fr': 'elle', 'de': 'sie', 'it': 'lei', 'pt': 'ela'},
    
    'target': {'en': 'target', 'es': 'objetivo', 'fr': 'cible', 'de': 'ziel', 'it': 'obiettivo', 'pt': 'alvo'},
    'objetivo': {'en': 'target', 'es': 'objetivo', 'fr': 'cible', 'de': 'ziel', 'it': 'obiettivo', 'pt': 'alvo'},
    'cible': {'en': 'target', 'es': 'objetivo', 'fr': 'cible', 'de': 'ziel', 'it': 'obiettivo', 'pt': 'alvo'},
    'ziel': {'en': 'target', 'es': 'objetivo', 'fr': 'cible', 'de': 'ziel', 'it': 'obiettivo', 'pt': 'alvo'},
    'obiettivo': {'en': 'target', 'es': 'objetivo', 'fr': 'cible', 'de': 'ziel', 'it': 'obiettivo', 'pt': 'alvo'},
    'alvo': {'en': 'target', 'es': 'objetivo', 'fr': 'cible', 'de': 'ziel', 'it': 'obiettivo', 'pt': 'alvo'},
    
    'ally': {'en': 'ally', 'es': 'aliado', 'fr': 'allié', 'de': 'verbündeter', 'it': 'alleato', 'pt': 'aliado'},
    'aliado': {'en': 'ally', 'es': 'aliado', 'fr': 'allié', 'de': 'verbündeter', 'it': 'alleato', 'pt': 'aliado'},
    'allié': {'en': 'ally', 'es': 'aliado', 'fr': 'allié', 'de': 'verbündeter', 'it': 'alleato', 'pt': 'aliado'},
    'verbündeter': {'en': 'ally', 'es': 'aliado', 'fr': 'allié', 'de': 'verbündeter', 'it': 'alleato', 'pt': 'aliado'},
    'alleato': {'en': 'ally', 'es': 'aliado', 'fr': 'allié', 'de': 'verbündeter', 'it': 'alleato', 'pt': 'aliado'},
    
    'resources': {'en': 'resources', 'es': 'recursos', 'fr': 'ressources', 'de': 'ressourcen', 'it': 'risorse', 'pt': 'recursos'},
    'recursos': {'en': 'resources', 'es': 'recursos', 'fr': 'ressources', 'de': 'ressourcen', 'it': 'risorse', 'pt': 'recursos'},
    'ressources': {'en': 'resources', 'es': 'recursos', 'fr': 'ressources', 'de': 'ressourcen', 'it': 'risorse', 'pt': 'recursos'},
    'ressourcen': {'en': 'resources', 'es': 'recursos', 'fr': 'ressources', 'de': 'ressourcen', 'it': 'risorse', 'pt': 'recursos'},
    'risorse': {'en': 'resources', 'es': 'recursos', 'fr': 'ressources', 'de': 'ressourcen', 'it': 'risorse', 'pt': 'recursos'},
    
    'revenge': {'en': 'revenge', 'es': 'venganza', 'fr': 'vengeance', 'de': 'rache', 'it': 'vendetta', 'pt': 'vingança'},
    'venganza': {'en': 'revenge', 'es': 'venganza', 'fr': 'vengeance', 'de': 'rache', 'it': 'vendetta', 'pt': 'vingança'},
    'vengeance': {'en': 'revenge', 'es': 'venganza', 'fr': 'vengeance', 'de': 'rache', 'it': 'vendetta', 'pt': 'vingança'},
    'rache': {'en': 'revenge', 'es': 'venganza', 'fr': 'vengeance', 'de': 'rache', 'it': 'vendetta', 'pt': 'vingança'},
    'vendetta': {'en': 'revenge', 'es': 'venganza', 'fr': 'vengeance', 'de': 'rache', 'it': 'vendetta', 'pt': 'vingança'},
    'vingança': {'en': 'revenge', 'es': 'venganza', 'fr': 'vengeance', 'de': 'rache', 'it': 'vendetta', 'pt': 'vingança'},
    
    'war': {'en': 'war', 'es': 'guerra', 'fr': 'guerre', 'de': 'krieg', 'it': 'guerra', 'pt': 'guerra'},
    'guerra': {'en': 'war', 'es': 'guerra', 'fr': 'guerre', 'de': 'krieg', 'it': 'guerra', 'pt': 'guerra'},
    'guerre': {'en': 'war', 'es': 'guerra', 'fr': 'guerre', 'de': 'krieg', 'it': 'guerra', 'pt': 'guerra'},
    'krieg': {'en': 'war', 'es': 'guerra', 'fr': 'guerre', 'de': 'krieg', 'it': 'guerra', 'pt': 'guerra'},
    
    'threat': {'en': 'threat', 'es': 'amenaza', 'fr': 'menace', 'de': 'bedrohung', 'it': 'minaccia', 'pt': 'ameaça'},
    'amenaza': {'en': 'threat', 'es': 'amenaza', 'fr': 'menace', 'de': 'bedrohung', 'it': 'minaccia', 'pt': 'ameaça'},
    'menace': {'en': 'threat', 'es': 'amenaza', 'fr': 'menace', 'de': 'bedrohung', 'it': 'minaccia', 'pt': 'ameaça'},
    'bedrohung': {'en': 'threat', 'es': 'amenaza', 'fr': 'menace', 'de': 'bedrohung', 'it': 'minaccia', 'pt': 'ameaça'},
    'minaccia': {'en': 'threat', 'es': 'amenaza', 'fr': 'menace', 'de': 'bedrohung', 'it': 'minaccia', 'pt': 'ameaça'},
    'ameaça': {'en': 'threat', 'es': 'amenaza', 'fr': 'menace', 'de': 'bedrohung', 'it': 'minaccia', 'pt': 'ameaça'},
    
    'weak': {'en': 'weak', 'es': 'débil', 'fr': 'faible', 'de': 'schwach', 'it': 'debole', 'pt': 'fraco'},
    'débil': {'en': 'weak', 'es': 'débil', 'fr': 'faible', 'de': 'schwach', 'it': 'debole', 'pt': 'fraco'},
    'faible': {'en': 'weak', 'es': 'débil', 'fr': 'faible', 'de': 'schwach', 'it': 'debole', 'pt': 'fraco'},
    'schwach': {'en': 'weak', 'es': 'débil', 'fr': 'faible', 'de': 'schwach', 'it': 'debole', 'pt': 'fraco'},
    'debole': {'en': 'weak', 'es': 'débil', 'fr': 'faible', 'de': 'schwach', 'it': 'debole', 'pt': 'fraco'},
    'fraco': {'en': 'weak', 'es': 'débil', 'fr': 'faible', 'de': 'schwach', 'it': 'debole', 'pt': 'fraco'},
    
    'strong': {'en': 'strong', 'es': 'fuerte', 'fr': 'fort', 'de': 'stark', 'it': 'forte', 'pt': 'forte'},
    'fuerte': {'en': 'strong', 'es': 'fuerte', 'fr': 'fort', 'de': 'stark', 'it': 'forte', 'pt': 'forte'},
    'fort': {'en': 'strong', 'es': 'fuerte', 'fr': 'fort', 'de': 'stark', 'it': 'forte', 'pt': 'forte'},
    'stark': {'en': 'strong', 'es': 'fuerte', 'fr': 'fort', 'de': 'stark', 'it': 'forte', 'pt': 'forte'},
    'forte': {'en': 'strong', 'es': 'fuerte', 'fr': 'fort', 'de': 'stark', 'it': 'forte', 'pt': 'forte'},
    
    'spy': {'en': 'spy', 'es': 'espiar', 'fr': 'espionner', 'de': 'ausspionieren', 'it': 'spiare', 'pt': 'espiar'},
    'espiar': {'en': 'spy', 'es': 'espiar', 'fr': 'espionner', 'de': 'ausspionieren', 'it': 'spiare', 'pt': 'espiar'},
    'espionner': {'en': 'spy', 'es': 'espiar', 'fr': 'espionner', 'de': 'ausspionieren', 'it': 'spiare', 'pt': 'espiar'},
    'ausspionieren': {'en': 'spy', 'es': 'espiar', 'fr': 'espionner', 'de': 'ausspionieren', 'it': 'spiare', 'pt': 'espiar'},
    'spiare': {'en': 'spy', 'es': 'espiar', 'fr': 'espionner', 'de': 'ausspionieren', 'it': 'spiare', 'pt': 'espiar'},
    
    'raid': {'en': 'raid', 'es': 'saqueo', 'fr': 'raid', 'de': 'überfall', 'it': 'incursione', 'pt': 'ataque'},
    'saqueo': {'en': 'raid', 'es': 'saqueo', 'fr': 'raid', 'de': 'überfall', 'it': 'incursione', 'pt': 'ataque'},
    'überfall': {'en': 'raid', 'es': 'saqueo', 'fr': 'raid', 'de': 'überfall', 'it': 'incursione', 'pt': 'ataque'},
    'incursione': {'en': 'raid', 'es': 'saqueo', 'fr': 'raid', 'de': 'überfall', 'it': 'incursione', 'pt': 'ataque'},
    'ataque': {'en': 'raid', 'es': 'saqueo', 'fr': 'raid', 'de': 'überfall', 'it': 'incursione', 'pt': 'ataque'},
    
    # Common words
    'still': {'en': 'still', 'es': 'todavía', 'fr': 'encore', 'de': 'noch', 'it': 'ancora', 'pt': 'ainda'},
    'todavía': {'en': 'still', 'es': 'todavía', 'fr': 'encore', 'de': 'noch', 'it': 'ancora', 'pt': 'ainda'},
    'aún': {'en': 'still', 'es': 'todavía', 'fr': 'encore', 'de': 'noch', 'it': 'ancora', 'pt': 'ainda'},
    'encore': {'en': 'still', 'es': 'todavía', 'fr': 'encore', 'de': 'noch', 'it': 'ancora', 'pt': 'ainda'},
    'noch': {'en': 'still', 'es': 'todavía', 'fr': 'encore', 'de': 'noch', 'it': 'ancora', 'pt': 'ainda'},
    'ancora': {'en': 'still', 'es': 'todavía', 'fr': 'encore', 'de': 'noch', 'it': 'ancora', 'pt': 'ainda'},
    'ainda': {'en': 'still', 'es': 'todavía', 'fr': 'encore', 'de': 'noch', 'it': 'ancora', 'pt': 'ainda'},
    
    'the': {'en': 'the', 'es': 'el', 'fr': 'le', 'de': 'der', 'it': 'il', 'pt': 'o'},
    'el': {'en': 'the', 'es': 'el', 'fr': 'le', 'de': 'der', 'it': 'il', 'pt': 'o'},
    'la': {'en': 'the', 'es': 'la', 'fr': 'la', 'de': 'die', 'it': 'la', 'pt': 'a'},
    'le': {'en': 'the', 'es': 'el', 'fr': 'le', 'de': 'der', 'it': 'il', 'pt': 'o'},
    'der': {'en': 'the', 'es': 'el', 'fr': 'le', 'de': 'der', 'it': 'il', 'pt': 'o'},
    'die': {'en': 'the', 'es': 'la', 'fr': 'la', 'de': 'die', 'it': 'la', 'pt': 'a'},
    'il': {'en': 'the', 'es': 'el', 'fr': 'le', 'de': 'der', 'it': 'il', 'pt': 'o'},
    
    'same': {'en': 'same', 'es': 'mismo', 'fr': 'même', 'de': 'gleiche', 'it': 'stesso', 'pt': 'mesmo'},
    'mismo': {'en': 'same', 'es': 'mismo', 'fr': 'même', 'de': 'gleiche', 'it': 'stesso', 'pt': 'mesmo'},
    'misma': {'en': 'same', 'es': 'misma', 'fr': 'même', 'de': 'gleiche', 'it': 'stessa', 'pt': 'mesma'},
    'même': {'en': 'same', 'es': 'mismo', 'fr': 'même', 'de': 'gleiche', 'it': 'stesso', 'pt': 'mesmo'},
    'gleiche': {'en': 'same', 'es': 'mismo', 'fr': 'même', 'de': 'gleiche', 'it': 'stesso', 'pt': 'mesmo'},
    'stesso': {'en': 'same', 'es': 'mismo', 'fr': 'même', 'de': 'gleiche', 'it': 'stesso', 'pt': 'mesmo'},
    'stessa': {'en': 'same', 'es': 'misma', 'fr': 'même', 'de': 'gleiche', 'it': 'stessa', 'pt': 'mesma'},
    'mesmo': {'en': 'same', 'es': 'mismo', 'fr': 'même', 'de': 'gleiche', 'it': 'stesso', 'pt': 'mesmo'},
    'mesma': {'en': 'same', 'es': 'misma', 'fr': 'même', 'de': 'gleiche', 'it': 'stessa', 'pt': 'mesma'}
}


def get_user_language(interaction: discord.Interaction) -> str:
    """Get user's language from Discord locale.
    
    Args:
        interaction: Discord interaction
        
    Returns:
        Language code (en, es, fr, de, it, pt)
    """
    locale = interaction.locale.value if hasattr(interaction.locale, 'value') else str(interaction.locale)
    
    # Map Discord locales to our supported languages
    locale_map = {
        'en-US': 'en',
        'en-GB': 'en',
        'es-ES': 'es',
        'es-419': 'es',  # Spanish (Latin America)
        'fr': 'fr',
        'de': 'de',
        'it': 'it',
        'pt-BR': 'pt',
        'pt-PT': 'pt'
    }
    
    # Get language code from locale
    lang = locale_map.get(locale, 'en')  # Default to English
    
    # If not found, try to extract base language (e.g., 'es' from 'es-ES')
    if lang == 'en' and '-' in locale:
        base_lang = locale.split('-')[0]
        if base_lang in SUPPORTED_LANGUAGES:
            lang = base_lang
    
    return lang


def translate(key: str, lang: str = 'en') -> str:
    """Get translation for a key.
    
    Args:
        key: Translation key
        lang: Language code
        
    Returns:
        Translated string, or key if not found
    """
    if key in TRANSLATIONS:
        return TRANSLATIONS[key].get(lang, TRANSLATIONS[key].get('en', key))
    return key


def translate_reason(reason: str, target_lang: str) -> str:
    """Translate a reason text to target language using Google Translate.
    
    Args:
        reason: Original reason text
        target_lang: Target language code
        
    Returns:
        Translated reason text
    """
    if not reason:
        return reason
    
    # If Deep Translator is available, use it for full sentence translation
    if TRANSLATOR_AVAILABLE:
        try:
            # Use auto-detect for source language
            translator = GoogleTranslator(source='auto', target=target_lang)
            translation = translator.translate(reason)
            return translation
            
        except Exception as e:
            print(f"[Translation Error] Failed to translate '{reason}': {e}")
            # Fall back to word-by-word if translation fails
    
    # Fallback: Word-by-word translation using dictionary
    translated_parts = []
    words = reason.split()
    
    for word in words:
        word_lower = word.lower()
        # Remove punctuation for matching
        word_clean = word_lower.strip('.,;:!?')
        
        if word_clean in REASON_TRANSLATIONS:
            # Translate the word
            translated = REASON_TRANSLATIONS[word_clean].get(target_lang, word)
            # Preserve original capitalization
            if word[0].isupper():
                translated = translated.capitalize()
            # Preserve punctuation
            if word != word_clean:
                translated += word[len(word_clean):]
            translated_parts.append(translated)
        else:
            # Keep original word if no translation found
            translated_parts.append(word)
    
    return ' '.join(translated_parts)


def get_translated_embed_field(key: str, value: str, lang: str, inline: bool = True) -> Dict:
    """Create a translated embed field.
    
    Args:
        key: Translation key for field name
        value: Field value
        lang: Language code
        inline: Whether field should be inline
        
    Returns:
        Dictionary with name, value, inline
    """
    return {
        'name': translate(key, lang),
        'value': value,
        'inline': inline
    }
