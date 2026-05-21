#!/usr/bin/env python3
# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                    🎫 TICKET SYSTEM PRO - DISCORD BOT                        ║
# ║                   Sistema Profissional de Tickets                            ║
# ║                         Arquivo Principal                                    ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

import discord
from discord.ext import commands, tasks
import asyncio
import threading
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Adicionar src ao path
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR / "src"))

# Carregar .env
load_dotenv(BASE_DIR / ".env")

# Imports
from utils.database import init_db
from utils.config import load_config, save_config
from utils.backup import create_backup, cleanup_old_backups

# Inicializar banco de dados
init_db()

class TicketBot(commands.Bot):
    def __init__(self):
        config = load_config()
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True

        super().__init__(
            command_prefix=config["bot"]["prefix"],
            intents=intents,
            help_command=None
        )

        self.config = config

    async def setup_hook(self):
        # Carregar cogs
        await self.load_extension("cogs.tickets")
        await self.load_extension("cogs.admin")

        # Sincronizar comandos
        await self.tree.sync()

        # Iniciar tasks
        self.auto_close_task.start()
        self.auto_backup_task.start()
        self.update_presence_task.start()

    async def on_ready(self):
        print(f"✅ Bot conectado como {self.user} ({self.user.id})")
        print(f"🌐 Servidores: {len(self.guilds)}")
        print(f"📊 Comandos sincronizados")
        await self.update_presence()

    async def update_presence(self):
        config = load_config()
        activity_type = config["bot"]["activity_type"]
        activity_text = config["bot"]["activity_text"]
        status = config["bot"]["status"]

        activity_types = {
            "playing": discord.ActivityType.playing,
            "watching": discord.ActivityType.watching,
            "listening": discord.ActivityType.listening,
            "streaming": discord.ActivityType.streaming,
            "competing": discord.ActivityType.competing
        }

        activity = discord.Activity(
            type=activity_types.get(activity_type, discord.ActivityType.watching),
            name=activity_text
        )

        status_map = {
            "online": discord.Status.online,
            "idle": discord.Status.idle,
            "dnd": discord.Status.dnd,
            "invisible": discord.Status.invisible
        }

        await self.change_presence(
            activity=activity,
            status=status_map.get(status, discord.Status.online)
        )

    @tasks.loop(minutes=5)
    async def update_presence_task(self):
        await self.update_presence()

    @tasks.loop(hours=1)
    async def auto_close_task(self):
        config = load_config()
        hours = config["tickets"]["auto_close_hours"]
        if hours <= 0:
            return

        import datetime
        cutoff = datetime.datetime.now() - datetime.timedelta(hours=hours)

        from utils.database import get_connection
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT channel_id FROM tickets WHERE status = 'open' AND last_activity_at < ?", (cutoff.isoformat(),))
        channels = c.fetchall()
        conn.close()

        for row in channels:
            channel = self.get_channel(int(row["channel_id"]))
            if channel:
                try:
                    await channel.send("🔒 Este ticket foi fechado automaticamente por inatividade.")
                    from utils.database import update_ticket
                    update_ticket(channel_id=row["channel_id"], status="closed", closed_at=datetime.datetime.now().isoformat(), closed_by=str(self.user.id))
                except:
                    pass

    @tasks.loop(hours=24)
    async def auto_backup_task(self):
        config = load_config()
        if config["backup"]["enabled"]:
            create_backup()
            cleanup_old_backups(config["backup"]["max_backups"])

    async def on_error(self, event, *args, **kwargs):
        print(f"❌ Erro no evento {event}: {args} {kwargs}")
        import traceback
        traceback.print_exc()

    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandNotFound):
            return
        print(f"❌ Erro no comando: {error}")

# Iniciar bot e Flask
bot = TicketBot()

def run_flask():
    """Run Flask web dashboard in a separate thread"""
    from web.app import app
    import os
    port = int(os.getenv("FLASK_PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

if __name__ == "__main__":
    TOKEN = os.getenv("DISCORD_TOKEN")

    if not TOKEN:
        print("❌ DISCORD_TOKEN não encontrado no .env")
        print("📝 Crie um arquivo .env com: DISCORD_TOKEN=seu_token_aqui")
        sys.exit(1)

    # Iniciar Flask em thread separada
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    print(f"🌐 Painel web iniciado em http://localhost:{os.getenv('FLASK_PORT', '5000')}")

    # Iniciar bot
    try:
        bot.run(TOKEN, reconnect=True)
    except discord.LoginFailure:
        print("❌ Token inválido! Verifique seu DISCORD_TOKEN no .env")
    except Exception as e:
        print(f"❌ Erro ao iniciar bot: {e}")
        import traceback
        traceback.print_exc()
