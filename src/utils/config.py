"""
Configuration Manager
"""
import json
import copy
import secrets
import os
from pathlib import Path

if os.environ.get("RAILWAY_ENVIRONMENT") or os.environ.get("RAILWAY_SERVICE_NAME"):
    BASE_DIR = Path("/data")
else:
    BASE_DIR = Path(__file__).parent.parent.parent

DB_DIR = BASE_DIR / "databases"
DB_DIR.mkdir(parents=True, exist_ok=True)

CONFIG_PATH = DB_DIR / "config.json"
LANG_PATH = DB_DIR / "lang.json"

DEFAULT_CONFIG = {
    "bot": {
        "name": "Ticket Pro",
        "status": "online",
        "activity_type": "watching",
        "activity_text": "tickets | /help",
        "prefix": "!",
        "main_color": "#5865F2",
        "language": "pt",
        "avatar_url": "",
        "banner_url": "",
        "bio": "Sistema profissional de tickets para Discord"
    },
    "embeds": {
        "panel_title": "🎫 Central de Atendimento",
        "panel_description": "Bem-vindo à nossa central de atendimento!\nSelecione uma categoria abaixo para abrir um ticket.",
        "panel_color": "#5865F2",
        "panel_footer": "Ticket Pro System",
        "panel_footer_icon": "",
        "panel_author": "",
        "panel_author_icon": "",
        "panel_thumbnail": "",
        "panel_image": "",
        "welcome_title": "🎫 Seu Ticket",
        "welcome_description": "Olá {user}!\nBem-vindo ao seu ticket de **{category}**.\n\nUm membro da nossa equipe será atendê-lo em breve.\n\n**Motivo:** {reason}",
        "welcome_color": "#57F287",
        "closed_title": "🔒 Ticket Fechado",
        "closed_description": "Este ticket foi fechado por {staff}.\n\nClique no botão abaixo para reabrir ou deletar.",
        "closed_color": "#ED4245",
        "transcript_title": "📄 Transcript",
        "transcript_color": "#EB459E",
        "log_color": "#FEE75C"
    },
    "tickets": {
        "cooldown_seconds": 60,
        "max_open_per_user": 3,
        "max_open_guild": 50,
        "auto_close_hours": 48,
        "auto_delete_hours": 72,
        "require_reason": True,
        "allow_reopen": True,
        "transcript_on_close": True,
        "dm_transcript": False,
        "category_format": "ticket-{username}-{id}",
        "private_threads": False,
        "mention_staff_on_create": True,
        "mention_user_on_close": True
    },
    "permissions": {
        "staff_roles": [],
        "admin_roles": [],
        "support_roles": [],
        "bypass_cooldown_roles": [],
        "can_open": ["@everyone"],
        "can_close": ["staff", "admin"],
        "can_delete": ["admin"],
        "can_claim": ["staff", "admin", "support"],
        "can_transcript": ["staff", "admin", "support"],
        "can_add_remove": ["staff", "admin"],
        "can_rename": ["staff", "admin"],
        "can_lock": ["staff", "admin"]
    },
    "categories": [
        {
            "id": "suporte",
            "label": "🛠️ Suporte Técnico",
            "description": "Problemas técnicos e dúvidas",
            "emoji": "🛠️",
            "category_channel_id": None,
            "priority": "medium",
            "allowed_roles": [],
            "welcome_message": "Bem-vindo ao Suporte Técnico! Descreva seu problema.",
            "auto_assign_role": None,
            "ping_roles": []
        },
        {
            "id": "financeiro",
            "label": "💰 Financeiro",
            "description": "Pagamentos, reembolsos e faturas",
            "emoji": "💰",
            "category_channel_id": None,
            "priority": "high",
            "allowed_roles": [],
            "welcome_message": "Bem-vindo ao Financeiro! Como podemos ajudar?",
            "auto_assign_role": None,
            "ping_roles": []
        },
        {
            "id": "denuncia",
            "label": "📢 Denúncia",
            "description": "Reportar usuários ou comportamentos",
            "emoji": "📢",
            "category_channel_id": None,
            "priority": "high",
            "allowed_roles": [],
            "welcome_message": "Sua denúncia será analisada com sigilo.",
            "auto_assign_role": None,
            "ping_roles": []
        },
        {
            "id": "parceria",
            "label": "🤝 Parceria",
            "description": "Propostas de parceria e colaboração",
            "emoji": "🤝",
            "category_channel_id": None,
            "priority": "low",
            "allowed_roles": [],
            "welcome_message": "Obrigado pelo interesse em parceria!",
            "auto_assign_role": None,
            "ping_roles": []
        },
        {
            "id": "vip",
            "label": "👑 VIP",
            "description": "Atendimento exclusivo VIP",
            "emoji": "👑",
            "category_channel_id": None,
            "priority": "urgent",
            "allowed_roles": [],
            "welcome_message": "Bem-vindo ao atendimento VIP!",
            "auto_assign_role": None,
            "ping_roles": []
        }
    ],
    "buttons": {
        "open": {"label": "Abrir Ticket", "emoji": "🎫", "style": "primary", "enabled": True},
        "close": {"label": "Fechar", "emoji": "🔒", "style": "danger", "enabled": True},
        "delete": {"label": "Deletar", "emoji": "🗑️", "style": "danger", "enabled": True},
        "claim": {"label": "Assumir", "emoji": "✋", "style": "success", "enabled": True},
        "call_staff": {"label": "Chamar Staff", "emoji": "🔔", "style": "primary", "enabled": True},
        "transcript": {"label": "Transcript", "emoji": "📄", "style": "secondary", "enabled": True},
        "reopen": {"label": "Reabrir", "emoji": "🔓", "style": "success", "enabled": True},
        "lock": {"label": "Bloquear", "emoji": "🔐", "style": "danger", "enabled": True},
        "unlock": {"label": "Desbloquear", "emoji": "🔓", "style": "success", "enabled": True},
        "add_user": {"label": "Adicionar", "emoji": "➕", "style": "secondary", "enabled": True},
        "remove_user": {"label": "Remover", "emoji": "➖", "style": "secondary", "enabled": True},
        "rename": {"label": "Renomear", "emoji": "🏷️", "style": "secondary", "enabled": True}
    },
    "ratings": {
        "enabled": True,
        "emoji_1": "⭐",
        "emoji_2": "⭐⭐",
        "emoji_3": "⭐⭐⭐",
        "emoji_4": "⭐⭐⭐⭐",
        "emoji_5": "⭐⭐⭐⭐⭐",
        "ask_comment": True,
        "dm_rating": False
    },
    "logs": {
        "enabled": True,
        "log_channel_id": None,
        "log_ticket_open": True,
        "log_ticket_close": True,
        "log_ticket_delete": True,
        "log_ticket_claim": True,
        "log_transcript": True,
        "log_user_add": True,
        "log_user_remove": True,
        "log_settings_change": True,
        "log_backup": True
    },
    "anti_spam": {
        "enabled": True,
        "max_messages": 5,
        "time_window": 10,
        "mute_duration": 300,
        "warn_threshold": 3
    },
    "backup": {
        "enabled": True,
        "auto_backup_hours": 24,
        "max_backups": 10
    },
    "api": {
        "enabled": True,
        "require_auth": True,
        "api_key": secrets.token_hex(16)
    },
    "panel_message_id": None,
    "panel_channel_id": None,
    "guild_id": None
}

DEFAULT_LANG = {
    "pt": {
        "ticket_opened": "🎫 Ticket Aberto",
        "ticket_closed": "🔒 Ticket Fechado",
        "ticket_deleted": "🗑️ Ticket Deletado",
        "ticket_reopened": "🔓 Ticket Reaberto",
        "ticket_claimed": "✅ Ticket Assumido",
        "user_added": "➕ Usuário Adicionado",
        "user_removed": "➖ Usuário Removido",
        "transcript_created": "📄 Transcript Criada",
        "staff_called": "🔔 Staff Chamado",
        "ticket_locked": "🔐 Ticket Bloqueado",
        "ticket_unlocked": "🔓 Ticket Desbloqueado",
        "ticket_renamed": "🏷️ Ticket Renomeado",
        "spam_detected": "⚠️ Anti-Spam: Aguarde {cooldown}s",
        "no_permission": "❌ Você não tem permissão para isso.",
        "ticket_already_open": "❌ Você já tem um ticket aberto.",
        "select_category": "📋 Selecione uma categoria",
        "enter_reason": "📝 Digite o motivo do ticket",
        "rate_ticket": "⭐ Avalie o atendimento",
        "thank_you": "✨ Obrigado pela avaliação!",
        "ticket_created_by": "Criado por",
        "ticket_category": "Categoria",
        "ticket_priority": "Prioridade",
        "ticket_status": "Status",
        "staff_member": "Staff",
        "opened_at": "Aberto em",
        "closed_at": "Fechado em",
        "reason": "Motivo",
        "priority_low": "🟢 Baixa",
        "priority_medium": "🟡 Média",
        "priority_high": "🔴 Alta",
        "priority_urgent": "⚫ Urgente",
        "status_open": "🟢 Aberto",
        "status_closed": "🔴 Fechado",
        "status_claimed": "🔵 Assumido",
        "button_open": "Abrir Ticket",
        "button_close": "Fechar",
        "button_delete": "Deletar",
        "button_claim": "Assumir",
        "button_call_staff": "Chamar Staff",
        "button_transcript": "Transcript",
        "button_reopen": "Reabrir",
        "button_lock": "Bloquear",
        "button_unlock": "Desbloquear",
        "button_add_user": "Adicionar",
        "button_remove_user": "Remover",
        "button_rename": "Renomear",
        "panel_title": "🎫 Sistema de Tickets",
        "panel_description": "Selecione uma categoria abaixo para abrir um ticket.",
        "welcome_ticket": "Bem-vindo ao seu ticket! Um membro da equipe será atendê-lo em breve.",
        "ticket_closed_msg": "Este ticket foi fechado.",
        "ticket_deleted_msg": "Este ticket será deletado em breve.",
        "transcript_saved": "Transcript salva com sucesso!",
        "backup_created": "💾 Backup criado com sucesso!",
        "settings_saved": "✅ Configurações salvas!",
        "error_occurred": "❌ Ocorreu um erro. Tente novamente.",
        "cooldown_active": "⏳ Aguarde {seconds} segundos antes de abrir outro ticket.",
        "max_tickets": "❌ Limite de tickets atingido.",
        "category_required": "❌ Selecione uma categoria.",
        "reason_required": "❌ Digite um motivo.",
        "invalid_user": "❌ Usuário inválido.",
        "user_not_in_ticket": "❌ Usuário não está no ticket.",
        "user_already_in_ticket": "❌ Usuário já está no ticket.",
        "ticket_not_found": "❌ Ticket não encontrado.",
        "not_ticket_channel": "❌ Este não é um canal de ticket.",
        "dashboard": "Dashboard",
        "tickets": "Tickets",
        "settings": "Configurações",
        "logs": "Logs",
        "statistics": "Estatísticas",
        "total_tickets": "Total de Tickets",
        "open_tickets": "Tickets Abertos",
        "closed_tickets": "Tickets Fechados",
        "avg_rating": "Avaliação Média",
        "response_time": "Tempo de Resposta",
        "today": "Hoje",
        "this_week": "Esta Semana",
        "this_month": "Este Mês",
    },
    "en": {
        "ticket_opened": "🎫 Ticket Opened",
        "ticket_closed": "🔒 Ticket Closed",
        "ticket_deleted": "🗑️ Ticket Deleted",
        "ticket_reopened": "🔓 Ticket Reopened",
        "ticket_claimed": "✅ Ticket Claimed",
        "user_added": "➕ User Added",
        "user_removed": "➖ User Removed",
        "transcript_created": "📄 Transcript Created",
        "staff_called": "🔔 Staff Called",
        "ticket_locked": "🔐 Ticket Locked",
        "ticket_unlocked": "🔓 Ticket Unlocked",
        "ticket_renamed": "🏷️ Ticket Renamed",
        "spam_detected": "⚠️ Anti-Spam: Wait {cooldown}s",
        "no_permission": "❌ You don't have permission.",
        "ticket_already_open": "❌ You already have an open ticket.",
        "select_category": "📋 Select a category",
        "enter_reason": "📝 Enter ticket reason",
        "rate_ticket": "⭐ Rate the service",
        "thank_you": "✨ Thank you for rating!",
        "ticket_created_by": "Created by",
        "ticket_category": "Category",
        "ticket_priority": "Priority",
        "ticket_status": "Status",
        "staff_member": "Staff",
        "opened_at": "Opened at",
        "closed_at": "Closed at",
        "reason": "Reason",
        "priority_low": "🟢 Low",
        "priority_medium": "🟡 Medium",
        "priority_high": "🔴 High",
        "priority_urgent": "⚫ Urgent",
        "status_open": "🟢 Open",
        "status_closed": "🔴 Closed",
        "status_claimed": "🔵 Claimed",
        "button_open": "Open Ticket",
        "button_close": "Close",
        "button_delete": "Delete",
        "button_claim": "Claim",
        "button_call_staff": "Call Staff",
        "button_transcript": "Transcript",
        "button_reopen": "Reopen",
        "button_lock": "Lock",
        "button_unlock": "Unlock",
        "button_add_user": "Add User",
        "button_remove_user": "Remove User",
        "button_rename": "Rename",
        "panel_title": "🎫 Ticket System",
        "panel_description": "Select a category below to open a ticket.",
        "welcome_ticket": "Welcome to your ticket! A team member will assist you shortly.",
        "ticket_closed_msg": "This ticket has been closed.",
        "ticket_deleted_msg": "This ticket will be deleted shortly.",
        "transcript_saved": "Transcript saved successfully!",
        "backup_created": "💾 Backup created successfully!",
        "settings_saved": "✅ Settings saved!",
        "error_occurred": "❌ An error occurred. Please try again.",
        "cooldown_active": "⏳ Wait {seconds} seconds before opening another ticket.",
        "max_tickets": "❌ Ticket limit reached.",
        "category_required": "❌ Select a category.",
        "reason_required": "❌ Enter a reason.",
        "invalid_user": "❌ Invalid user.",
        "user_not_in_ticket": "❌ User is not in the ticket.",
        "user_already_in_ticket": "❌ User is already in the ticket.",
        "ticket_not_found": "❌ Ticket not found.",
        "not_ticket_channel": "❌ This is not a ticket channel.",
        "dashboard": "Dashboard",
        "tickets": "Tickets",
        "settings": "Settings",
        "logs": "Logs",
        "statistics": "Statistics",
        "total_tickets": "Total Tickets",
        "open_tickets": "Open Tickets",
        "closed_tickets": "Closed Tickets",
        "avg_rating": "Average Rating",
        "response_time": "Response Time",
        "today": "Today",
        "this_week": "This Week",
        "this_month": "This Month",
    }
}

def load_config():
    DB_DIR.mkdir(parents=True, exist_ok=True)
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            saved = json.load(f)
        config = copy.deepcopy(DEFAULT_CONFIG)

        def deep_update(d, u):
            for k, v in u.items():
                if isinstance(v, dict) and k in d and isinstance(d[k], dict):
                    deep_update(d[k], v)
                else:
                    d[k] = v
            return d

        deep_update(config, saved)
        return config
    return copy.deepcopy(DEFAULT_CONFIG)

def save_config(config):
    DB_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

def load_lang():
    DB_DIR.mkdir(parents=True, exist_ok=True)
    if LANG_PATH.exists():
        with open(LANG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return DEFAULT_LANG

def save_lang(data):
    DB_DIR.mkdir(parents=True, exist_ok=True)
    with open(LANG_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_text(key, lang="pt", **kwargs):
    langs = load_lang()
    text = langs.get(lang, langs.get("pt", {})).get(key, key)
    return text.format(**kwargs) if kwargs else text

def reset_config():
    save_config(DEFAULT_CONFIG)
    return DEFAULT_CONFIG
