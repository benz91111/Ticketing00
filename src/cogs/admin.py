"""
Admin Commands Cog
"""
import discord
from discord import app_commands
from discord.ext import commands
import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.database import get_all_tickets, get_stats, get_logs, add_log
from utils.config import load_config, save_config, get_text
from utils.backup import create_backup, get_backups

class AdminCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="setup", description="Configura o sistema de tickets no servidor")
    @app_commands.checks.has_permissions(administrator=True)
    async def setup_panel(self, interaction: discord.Interaction):
        config = load_config()
        lang = config["bot"]["language"]

        embed = discord.Embed(
            title=config["embeds"]["panel_title"],
            description=config["embeds"]["panel_description"],
            color=int(config["embeds"]["panel_color"].replace("#", ""), 16)
        )

        if config["embeds"]["panel_footer"]:
            embed.set_footer(text=config["embeds"]["panel_footer"], icon_url=config["embeds"]["panel_footer_icon"] or None)
        if config["embeds"]["panel_author"]:
            embed.set_author(name=config["embeds"]["panel_author"], icon_url=config["embeds"]["panel_author_icon"] or None)
        if config["embeds"]["panel_thumbnail"]:
            embed.set_thumbnail(url=config["embeds"]["panel_thumbnail"])
        if config["embeds"]["panel_image"]:
            embed.set_image(url=config["embeds"]["panel_image"])

        # Dropdown de categorias
        options = []
        for cat in config["categories"]:
            options.append(discord.SelectOption(
                label=cat["label"],
                description=cat["description"],
                emoji=cat["emoji"],
                value=cat["id"]
            ))

        select = discord.ui.Select(
            placeholder=get_text("select_category", lang),
            options=options,
            custom_id="ticket_category_select"
        )

        from cogs.tickets import TicketReasonModal, create_ticket_channel

        async def select_callback(interaction: discord.Interaction):
            category_id = select.values[0]
            category = next((c for c in config["categories"] if c["id"] == category_id), None)

            if not category:
                return await interaction.response.send_message(get_text("error_occurred", lang), ephemeral=True)

            from utils.database import check_cooldown, count_user_tickets
            remaining = check_cooldown(interaction.user.id, interaction.guild_id, config["tickets"]["cooldown_seconds"])
            if remaining > 0:
                return await interaction.response.send_message(
                    get_text("cooldown_active", lang, seconds=remaining),
                    ephemeral=True
                )

            user_tickets = count_user_tickets(interaction.user.id, interaction.guild_id, "open")
            if user_tickets >= config["tickets"]["max_open_per_user"]:
                return await interaction.response.send_message(get_text("max_tickets", lang), ephemeral=True)

            if config["tickets"]["require_reason"]:
                modal = TicketReasonModal(category_id, category)
                await interaction.response.send_modal(modal)
            else:
                await create_ticket_channel(interaction, category_id, "Não especificado")

        select.callback = select_callback

        view = discord.ui.View(timeout=None)
        view.add_item(select)

        await interaction.response.send_message(embed=embed, view=view)
        msg = await interaction.original_response()

        config["panel_message_id"] = msg.id
        config["panel_channel_id"] = msg.channel.id
        config["guild_id"] = interaction.guild_id
        from utils.config import save_config
        save_config(config)

    @app_commands.command(name="stats", description="Mostra estatísticas do sistema de tickets")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def stats(self, interaction: discord.Interaction):
        config = load_config()
        lang = config["bot"]["language"]

        stats = get_stats(interaction.guild_id)

        embed = discord.Embed(
            title=f"📊 {get_text('statistics', lang)}",
            color=discord.Color.blue(),
            timestamp=datetime.datetime.now()
        )

        embed.add_field(name=get_text("total_tickets", lang), value=str(stats["total"]), inline=True)
        embed.add_field(name=get_text("open_tickets", lang), value=str(stats["open"]), inline=True)
        embed.add_field(name=get_text("closed_tickets", lang), value=str(stats["closed"]), inline=True)
        embed.add_field(name=get_text("avg_rating", lang), value=f"{stats['avg_rating']} ⭐", inline=True)
        embed.add_field(name=get_text("today", lang), value=str(stats["today"]), inline=True)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="backup", description="Cria um backup do banco de dados")
    @app_commands.checks.has_permissions(administrator=True)
    async def backup(self, interaction: discord.Interaction):
        config = load_config()
        lang = config["bot"]["language"]

        filepath, size = create_backup()
        add_log(interaction.guild_id, "backup", interaction.user.id, None, {"file": filepath, "size": size})

        embed = discord.Embed(
            title=get_text("backup_created", lang),
            description=f"Arquivo: `{filepath}`\nTamanho: {size} bytes",
            color=discord.Color.green()
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="reload", description="Recarrega a configuração do bot")
    @app_commands.checks.has_permissions(administrator=True)
    async def reload_config(self, interaction: discord.Interaction):
        config = load_config()

        # Atualizar presence
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

        await self.bot.change_presence(
            activity=activity,
            status=status_map.get(status, discord.Status.online)
        )

        await interaction.response.send_message("✅ Configuração recarregada!", ephemeral=True)

    @app_commands.command(name="reset", description="Reseta a configuração para padrão")
    @app_commands.checks.has_permissions(administrator=True)
    async def reset_config(self, interaction: discord.Interaction):
        from utils.config import reset_config
        reset_config()
        await interaction.response.send_message("✅ Configuração resetada para padrão!", ephemeral=True)

async def setup(bot):
    await bot.add_cog(AdminCog(bot))
