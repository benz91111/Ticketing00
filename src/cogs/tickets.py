"""
Ticket System Cog
"""
import discord
from discord import app_commands
from discord.ext import commands
import datetime
import re
import json

from ..utils.database import (
    create_ticket, get_ticket, update_ticket, delete_ticket,
    count_user_tickets, check_cooldown, update_cooldown,
    add_message, get_messages, add_log
)
from ..utils.config import load_config, get_text
from ..utils.transcript import generate_transcript_html, save_transcript
from ..utils.backup import create_backup

class TicketReasonModal(discord.ui.Modal, title="Motivo do Ticket"):
    def __init__(self, category_id, category):
        super().__init__()
        self.category_id = category_id
        self.category = category

    reason = discord.ui.TextInput(
        label="Motivo",
        placeholder="Descreva o motivo do seu ticket...",
        style=discord.TextStyle.paragraph,
        max_length=500,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        await create_ticket_channel(interaction, self.category_id, self.reason.value)

class TicketControlView(discord.ui.View):
    def __init__(self, ticket_id, config):
        super().__init__(timeout=None)
        self.ticket_id = ticket_id
        self.config = config
        self.add_buttons()

    def add_buttons(self):
        buttons = self.config["buttons"]

        # Row 1
        if buttons["close"]["enabled"]:
            self.add_item(discord.ui.Button(
                label=buttons["close"]["label"],
                emoji=buttons["close"]["emoji"],
                style=self.get_style(buttons["close"]["style"]),
                custom_id=f"ticket_close_{self.ticket_id}"
            ))
        if buttons["claim"]["enabled"]:
            self.add_item(discord.ui.Button(
                label=buttons["claim"]["label"],
                emoji=buttons["claim"]["emoji"],
                style=self.get_style(buttons["claim"]["style"]),
                custom_id=f"ticket_claim_{self.ticket_id}"
            ))
        if buttons["call_staff"]["enabled"]:
            self.add_item(discord.ui.Button(
                label=buttons["call_staff"]["label"],
                emoji=buttons["call_staff"]["emoji"],
                style=self.get_style(buttons["call_staff"]["style"]),
                custom_id=f"ticket_callstaff_{self.ticket_id}"
            ))
        if buttons["transcript"]["enabled"]:
            self.add_item(discord.ui.Button(
                label=buttons["transcript"]["label"],
                emoji=buttons["transcript"]["emoji"],
                style=self.get_style(buttons["transcript"]["style"]),
                custom_id=f"ticket_transcript_{self.ticket_id}"
            ))

        # Row 2
        if buttons["add_user"]["enabled"]:
            self.add_item(discord.ui.Button(
                label=buttons["add_user"]["label"],
                emoji=buttons["add_user"]["emoji"],
                style=self.get_style(buttons["add_user"]["style"]),
                custom_id=f"ticket_adduser_{self.ticket_id}"
            ))
        if buttons["remove_user"]["enabled"]:
            self.add_item(discord.ui.Button(
                label=buttons["remove_user"]["label"],
                emoji=buttons["remove_user"]["emoji"],
                style=self.get_style(buttons["remove_user"]["style"]),
                custom_id=f"ticket_removeuser_{self.ticket_id}"
            ))
        if buttons["rename"]["enabled"]:
            self.add_item(discord.ui.Button(
                label=buttons["rename"]["label"],
                emoji=buttons["rename"]["emoji"],
                style=self.get_style(buttons["rename"]["style"]),
                custom_id=f"ticket_rename_{self.ticket_id}"
            ))
        if buttons["lock"]["enabled"]:
            self.add_item(discord.ui.Button(
                label=buttons["lock"]["label"],
                emoji=buttons["lock"]["emoji"],
                style=self.get_style(buttons["lock"]["style"]),
                custom_id=f"ticket_lock_{self.ticket_id}"
            ))

    def get_style(self, style_str):
        styles = {
            "primary": discord.ButtonStyle.primary,
            "secondary": discord.ButtonStyle.secondary,
            "success": discord.ButtonStyle.success,
            "danger": discord.ButtonStyle.danger,
            "blurple": discord.ButtonStyle.blurple,
            "grey": discord.ButtonStyle.grey,
            "green": discord.ButtonStyle.green,
            "red": discord.ButtonStyle.red
        }
        return styles.get(style_str, discord.ButtonStyle.primary)

class TicketsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.spam_tracker = {}

    @app_commands.command(name="ticket", description="Abre o painel de tickets")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def ticket_panel(self, interaction: discord.Interaction):
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

        async def select_callback(interaction: discord.Interaction):
            category_id = select.values[0]
            category = next((c for c in config["categories"] if c["id"] == category_id), None)

            if not category:
                return await interaction.response.send_message(get_text("error_occurred", lang), ephemeral=True)

            # Verificar cooldown
            remaining = check_cooldown(interaction.user.id, interaction.guild_id, config["tickets"]["cooldown_seconds"])
            if remaining > 0:
                return await interaction.response.send_message(
                    get_text("cooldown_active", lang, seconds=remaining),
                    ephemeral=True
                )

            # Verificar limite
            user_tickets = count_user_tickets(interaction.user.id, interaction.guild_id, "open")
            if user_tickets >= config["tickets"]["max_open_per_user"]:
                return await interaction.response.send_message(get_text("max_tickets", lang), ephemeral=True)

            # Modal para motivo
            if config["tickets"]["require_reason"]:
                modal = TicketReasonModal(category_id, category)
                await interaction.response.send_modal(modal)
            else:
                await create_ticket_channel(interaction, category_id, "Não especificado")

        select.callback = select_callback

        view = discord.ui.View(timeout=None)
        view.add_item(select)

        # Botão abrir ticket
        btn_config = config["buttons"]["open"]
        if btn_config["enabled"]:
            open_btn = discord.ui.Button(
                label=btn_config["label"],
                emoji=btn_config["emoji"],
                style=discord.ButtonStyle.primary if btn_config["style"] == "primary" else discord.ButtonStyle.success,
                custom_id="ticket_open_btn"
            )

            async def open_btn_callback(interaction: discord.Interaction):
                await interaction.response.send_message("Selecione uma categoria no dropdown acima.", ephemeral=True)

            open_btn.callback = open_btn_callback
            view.add_item(open_btn)

        await interaction.response.send_message(embed=embed, view=view)
        msg = await interaction.original_response()

        config["panel_message_id"] = msg.id
        config["panel_channel_id"] = msg.channel.id
        config["guild_id"] = interaction.guild_id
        from ..utils.config import save_config
        save_config(config)

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.type != discord.InteractionType.component:
            return

        custom_id = interaction.data.get("custom_id", "")

        if custom_id.startswith("ticket_close_"):
            ticket_id = int(custom_id.split("_")[-1])
            await self.handle_close(interaction, ticket_id)
        elif custom_id.startswith("ticket_claim_"):
            ticket_id = int(custom_id.split("_")[-1])
            await self.handle_claim(interaction, ticket_id)
        elif custom_id.startswith("ticket_callstaff_"):
            ticket_id = int(custom_id.split("_")[-1])
            await self.handle_call_staff(interaction, ticket_id)
        elif custom_id.startswith("ticket_transcript_"):
            ticket_id = int(custom_id.split("_")[-1])
            await self.handle_transcript(interaction, ticket_id)
        elif custom_id.startswith("ticket_adduser_"):
            ticket_id = int(custom_id.split("_")[-1])
            await self.handle_add_user(interaction, ticket_id)
        elif custom_id.startswith("ticket_removeuser_"):
            ticket_id = int(custom_id.split("_")[-1])
            await self.handle_remove_user(interaction, ticket_id)
        elif custom_id.startswith("ticket_rename_"):
            ticket_id = int(custom_id.split("_")[-1])
            await self.handle_rename(interaction, ticket_id)
        elif custom_id.startswith("ticket_lock_"):
            ticket_id = int(custom_id.split("_")[-1])
            await self.handle_lock(interaction, ticket_id)
        elif custom_id.startswith("ticket_reopen_"):
            ticket_id = int(custom_id.split("_")[-1])
            await self.handle_reopen(interaction, ticket_id)
        elif custom_id.startswith("ticket_delete_"):
            ticket_id = int(custom_id.split("_")[-1])
            await self.handle_delete(interaction, ticket_id)

    async def has_permission(self, user, guild, perm_type="staff"):
        config = load_config()
        member = guild.get_member(user.id)
        if not member:
            return False

        if member.guild_permissions.administrator:
            return True

        if perm_type == "admin":
            role_ids = config["permissions"]["admin_roles"]
        elif perm_type == "support":
            role_ids = config["permissions"]["support_roles"]
        else:
            role_ids = config["permissions"]["staff_roles"]

        return any(str(r.id) in role_ids for r in member.roles)

    async def handle_close(self, interaction: discord.Interaction, ticket_id):
        config = load_config()
        lang = config["bot"]["language"]

        if not await self.has_permission(interaction.user, interaction.guild, "staff"):
            return await interaction.response.send_message(get_text("no_permission", lang), ephemeral=True)

        ticket = get_ticket(ticket_id=ticket_id)
        if not ticket:
            return await interaction.response.send_message(get_text("ticket_not_found", lang), ephemeral=True)

        channel = interaction.guild.get_channel(int(ticket["channel_id"]))
        if not channel:
            return await interaction.response.send_message(get_text("not_ticket_channel", lang), ephemeral=True)

        # Atualizar status
        update_ticket(ticket_id=ticket_id, status="closed", closed_at=datetime.datetime.now().isoformat(), closed_by=str(interaction.user.id))

        # Criar transcript
        if config["tickets"]["transcript_on_close"]:
            messages = get_messages(ticket_id)
            transcript_html = generate_transcript_html(ticket, messages, interaction.guild.name)
            if transcript_html:
                filepath = save_transcript(ticket_id, transcript_html)
                update_ticket(ticket_id=ticket_id, transcript_url=filepath)
                add_log(interaction.guild_id, "transcript", interaction.user.id, ticket_id, {"file": filepath})

        # Embed fechado
        closed_desc = config["embeds"]["closed_description"]
        closed_desc = closed_desc.replace("{staff}", interaction.user.mention).replace("{user}", f"<@{ticket['user_id']}>")
        closed_desc = closed_desc.replace("{guild}", interaction.guild.name).replace("{date}", datetime.datetime.now().strftime("%d/%m/%Y %H:%M"))
        closed_desc = closed_desc.replace("{id}", str(ticket_id)).replace("{ticket}", channel.mention)

        closed_embed = discord.Embed(
            title=config["embeds"]["closed_title"],
            description=closed_desc,
            color=int(config["embeds"]["closed_color"].replace("#", ""), 16),
            timestamp=datetime.datetime.now()
        )

        # View com reabrir e deletar
        view = discord.ui.View(timeout=None)

        if config["buttons"]["reopen"]["enabled"]:
            reopen_btn = discord.ui.Button(
                label=config["buttons"]["reopen"]["label"],
                emoji=config["buttons"]["reopen"]["emoji"],
                style=discord.ButtonStyle.success,
                custom_id=f"ticket_reopen_{ticket_id}"
            )
            view.add_item(reopen_btn)

        if config["buttons"]["delete"]["enabled"]:
            delete_btn = discord.ui.Button(
                label=config["buttons"]["delete"]["label"],
                emoji=config["buttons"]["delete"]["emoji"],
                style=discord.ButtonStyle.danger,
                custom_id=f"ticket_delete_{ticket_id}"
            )
            view.add_item(delete_btn)

        transcript_btn = discord.ui.Button(
            label=config["buttons"]["transcript"]["label"],
            emoji=config["buttons"]["transcript"]["emoji"],
            style=discord.ButtonStyle.secondary,
            custom_id=f"ticket_transcript_{ticket_id}"
        )
        view.add_item(transcript_btn)

        await channel.send(embed=closed_embed, view=view)
        add_log(interaction.guild_id, "ticket_close", interaction.user.id, ticket["channel_id"], {"ticket_id": ticket_id})

        await interaction.response.send_message(get_text("ticket_closed", lang), ephemeral=True)

    async def handle_claim(self, interaction: discord.Interaction, ticket_id):
        config = load_config()
        lang = config["bot"]["language"]

        if not await self.has_permission(interaction.user, interaction.guild, "staff"):
            return await interaction.response.send_message(get_text("no_permission", lang), ephemeral=True)

        ticket = get_ticket(ticket_id=ticket_id)
        if not ticket:
            return await interaction.response.send_message(get_text("ticket_not_found", lang), ephemeral=True)

        update_ticket(ticket_id=ticket_id, claimed_by=str(interaction.user.id), status="claimed")

        channel = interaction.guild.get_channel(int(ticket["channel_id"]))
        if channel:
            embed = discord.Embed(
                title=get_text("ticket_claimed", lang),
                description=f"Ticket assumido por {interaction.user.mention}",
                color=discord.Color.blue()
            )
            await channel.send(embed=embed)

        add_log(interaction.guild_id, "ticket_claim", interaction.user.id, ticket_id)
        await interaction.response.send_message(get_text("ticket_claimed", lang), ephemeral=True)

    async def handle_call_staff(self, interaction: discord.Interaction, ticket_id):
        config = load_config()
        lang = config["bot"]["language"]

        ticket = get_ticket(ticket_id=ticket_id)
        if not ticket:
            return await interaction.response.send_message(get_text("ticket_not_found", lang), ephemeral=True)

        channel = interaction.guild.get_channel(int(ticket["channel_id"]))
        if channel:
            pings = []
            for role_id in config["permissions"]["staff_roles"]:
                role = interaction.guild.get_role(int(role_id))
                if role:
                    pings.append(role.mention)

            if pings:
                await channel.send(f"🔔 {get_text('staff_called', lang)}: {' '.join(pings)}")
            else:
                await channel.send(f"🔔 {get_text('staff_called', lang)}!")

        add_log(interaction.guild_id, "staff_called", interaction.user.id, ticket_id)
        await interaction.response.send_message(get_text("staff_called", lang), ephemeral=True)

    async def handle_transcript(self, interaction: discord.Interaction, ticket_id):
        config = load_config()
        lang = config["bot"]["language"]

        ticket = get_ticket(ticket_id=ticket_id)
        if not ticket:
            return await interaction.response.send_message(get_text("ticket_not_found", lang), ephemeral=True)

        messages = get_messages(ticket_id)
        transcript_html = generate_transcript_html(ticket, messages, interaction.guild.name)

        if transcript_html:
            filepath = save_transcript(ticket_id, transcript_html)
            update_ticket(ticket_id=ticket_id, transcript_url=filepath)

            # Enviar arquivo
            await interaction.response.send_message(
                file=discord.File(filepath, filename=f"transcript_{ticket_id}.html"),
                ephemeral=True
            )

            add_log(interaction.guild_id, "transcript", interaction.user.id, ticket_id, {"file": filepath})
        else:
            await interaction.response.send_message(get_text("error_occurred", lang), ephemeral=True)

    async def handle_add_user(self, interaction: discord.Interaction, ticket_id):
        config = load_config()
        lang = config["bot"]["language"]

        if not await self.has_permission(interaction.user, interaction.guild, "staff"):
            return await interaction.response.send_message(get_text("no_permission", lang), ephemeral=True)

        ticket = get_ticket(ticket_id=ticket_id)
        if not ticket:
            return await interaction.response.send_message(get_text("ticket_not_found", lang), ephemeral=True)

        # Modal para adicionar usuário
        class AddUserModal(discord.ui.Modal, title="Adicionar Usuário"):
            user_id = discord.ui.TextInput(label="ID do Usuário", placeholder="Digite o ID do usuário", required=True)

            async def on_submit(modal_self, modal_interaction: discord.Interaction):
                try:
                    user = await interaction.guild.fetch_member(int(modal_self.user_id.value))
                    channel = interaction.guild.get_channel(int(ticket["channel_id"]))

                    if channel:
                        await channel.set_permissions(user, read_messages=True, send_messages=True, read_message_history=True)

                        participants = json.loads(ticket["participants"] or "[]")
                        if str(user.id) not in participants:
                            participants.append(str(user.id))
                            update_ticket(ticket_id=ticket_id, participants=json.dumps(participants))

                        embed = discord.Embed(
                            title=get_text("user_added", lang),
                            description=f"{user.mention} foi adicionado ao ticket.",
                            color=discord.Color.green()
                        )
                        await channel.send(embed=embed)

                        add_log(interaction.guild_id, "user_add", interaction.user.id, user.id, {"ticket_id": ticket_id})
                        await modal_interaction.response.send_message(f"✅ {user.mention} adicionado!", ephemeral=True)
                except Exception as e:
                    await modal_interaction.response.send_message(get_text("invalid_user", lang), ephemeral=True)

        modal = AddUserModal()
        await interaction.response.send_modal(modal)

    async def handle_remove_user(self, interaction: discord.Interaction, ticket_id):
        config = load_config()
        lang = config["bot"]["language"]

        if not await self.has_permission(interaction.user, interaction.guild, "staff"):
            return await interaction.response.send_message(get_text("no_permission", lang), ephemeral=True)

        ticket = get_ticket(ticket_id=ticket_id)
        if not ticket:
            return await interaction.response.send_message(get_text("ticket_not_found", lang), ephemeral=True)

        class RemoveUserModal(discord.ui.Modal, title="Remover Usuário"):
            user_id = discord.ui.TextInput(label="ID do Usuário", placeholder="Digite o ID do usuário", required=True)

            async def on_submit(modal_self, modal_interaction: discord.Interaction):
                try:
                    user = await interaction.guild.fetch_member(int(modal_self.user_id.value))
                    channel = interaction.guild.get_channel(int(ticket["channel_id"]))

                    if channel:
                        await channel.set_permissions(user, overwrite=None)

                        participants = json.loads(ticket["participants"] or "[]")
                        if str(user.id) in participants:
                            participants.remove(str(user.id))
                            update_ticket(ticket_id=ticket_id, participants=json.dumps(participants))

                        embed = discord.Embed(
                            title=get_text("user_removed", lang),
                            description=f"{user.mention} foi removido do ticket.",
                            color=discord.Color.red()
                        )
                        await channel.send(embed=embed)

                        add_log(interaction.guild_id, "user_remove", interaction.user.id, user.id, {"ticket_id": ticket_id})
                        await modal_interaction.response.send_message(f"✅ {user.mention} removido!", ephemeral=True)
                except Exception as e:
                    await modal_interaction.response.send_message(get_text("invalid_user", lang), ephemeral=True)

        modal = RemoveUserModal()
        await interaction.response.send_modal(modal)

    async def handle_rename(self, interaction: discord.Interaction, ticket_id):
        config = load_config()
        lang = config["bot"]["language"]

        if not await self.has_permission(interaction.user, interaction.guild, "staff"):
            return await interaction.response.send_message(get_text("no_permission", lang), ephemeral=True)

        ticket = get_ticket(ticket_id=ticket_id)
        if not ticket:
            return await interaction.response.send_message(get_text("ticket_not_found", lang), ephemeral=True)

        class RenameModal(discord.ui.Modal, title="Renomear Ticket"):
            name = discord.ui.TextInput(label="Novo nome", placeholder="Digite o novo nome do canal", required=True, max_length=100)

            async def on_submit(modal_self, modal_interaction: discord.Interaction):
                channel = interaction.guild.get_channel(int(ticket["channel_id"]))
                if channel:
                    new_name = re.sub(r"[^a-zA-Z0-9\-]", "-", modal_self.name.value).lower()[:100]
                    await channel.edit(name=new_name)

                    embed = discord.Embed(
                        title=get_text("ticket_renamed", lang),
                        description=f"Ticket renomeado para: {modal_self.name.value}",
                        color=discord.Color.blue()
                    )
                    await channel.send(embed=embed)

                    add_log(interaction.guild_id, "ticket_rename", interaction.user.id, ticket_id, {"new_name": modal_self.name.value})
                    await modal_interaction.response.send_message("✅ Ticket renomeado!", ephemeral=True)

        modal = RenameModal()
        await interaction.response.send_modal(modal)

    async def handle_lock(self, interaction: discord.Interaction, ticket_id):
        config = load_config()
        lang = config["bot"]["language"]

        if not await self.has_permission(interaction.user, interaction.guild, "staff"):
            return await interaction.response.send_message(get_text("no_permission", lang), ephemeral=True)

        ticket = get_ticket(ticket_id=ticket_id)
        if not ticket:
            return await interaction.response.send_message(get_text("ticket_not_found", lang), ephemeral=True)

        channel = interaction.guild.get_channel(int(ticket["channel_id"]))
        if not channel:
            return await interaction.response.send_message(get_text("not_ticket_channel", lang), ephemeral=True)

        locked = ticket["locked"] == 1

        if not locked:
            # Bloquear - remover permissão de enviar mensagens de todos exceto staff
            for target in channel.overwrites:
                if isinstance(target, discord.Member) and not await self.has_permission(target, interaction.guild, "staff"):
                    await channel.set_permissions(target, send_messages=False)

            update_ticket(ticket_id=ticket_id, locked=1)
            embed = discord.Embed(title=get_text("ticket_locked", lang), color=discord.Color.red())
            await channel.send(embed=embed)
            await interaction.response.send_message(get_text("ticket_locked", lang), ephemeral=True)
        else:
            # Desbloquear
            ticket_user = await interaction.guild.fetch_member(int(ticket["user_id"]))
            if ticket_user:
                await channel.set_permissions(ticket_user, read_messages=True, send_messages=True, read_message_history=True)

            update_ticket(ticket_id=ticket_id, locked=0)
            embed = discord.Embed(title=get_text("ticket_unlocked", lang), color=discord.Color.green())
            await channel.send(embed=embed)
            await interaction.response.send_message(get_text("ticket_unlocked", lang), ephemeral=True)

        add_log(interaction.guild_id, "ticket_lock" if not locked else "ticket_unlock", interaction.user.id, ticket_id)

    async def handle_reopen(self, interaction: discord.Interaction, ticket_id):
        config = load_config()
        lang = config["bot"]["language"]

        if not await self.has_permission(interaction.user, interaction.guild, "staff"):
            return await interaction.response.send_message(get_text("no_permission", lang), ephemeral=True)

        ticket = get_ticket(ticket_id=ticket_id)
        if not ticket:
            return await interaction.response.send_message(get_text("ticket_not_found", lang), ephemeral=True)

        update_ticket(ticket_id=ticket_id, status="open", closed_at=None, closed_by=None)

        channel = interaction.guild.get_channel(int(ticket["channel_id"]))
        if channel:
            # Restaurar permissões
            ticket_user = await interaction.guild.fetch_member(int(ticket["user_id"]))
            if ticket_user:
                await channel.set_permissions(ticket_user, read_messages=True, send_messages=True, read_message_history=True)

            embed = discord.Embed(
                title=get_text("ticket_reopened", lang),
                description=f"Ticket reaberto por {interaction.user.mention}",
                color=discord.Color.green()
            )

            view = TicketControlView(ticket_id, config)
            await channel.send(embed=embed, view=view)

        add_log(interaction.guild_id, "ticket_reopen", interaction.user.id, ticket_id)
        await interaction.response.send_message(get_text("ticket_reopened", lang), ephemeral=True)

    async def handle_delete(self, interaction: discord.Interaction, ticket_id):
        config = load_config()
        lang = config["bot"]["language"]

        if not await self.has_permission(interaction.user, interaction.guild, "admin"):
            return await interaction.response.send_message(get_text("no_permission", lang), ephemeral=True)

        ticket = get_ticket(ticket_id=ticket_id)
        if not ticket:
            return await interaction.response.send_message(get_text("ticket_not_found", lang), ephemeral=True)

        channel = interaction.guild.get_channel(int(ticket["channel_id"]))
        if channel:
            await channel.send(get_text("ticket_deleted_msg", lang))
            await asyncio.sleep(5)
            await channel.delete()

        delete_ticket(ticket_id=ticket_id)
        add_log(interaction.guild_id, "ticket_delete", interaction.user.id, ticket_id)
        await interaction.response.send_message(get_text("ticket_deleted", lang), ephemeral=True)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        # Anti-spam
        config = load_config()
        if config["anti_spam"]["enabled"]:
            await self.check_spam(message)

        # Log mensagens em tickets
        ticket = get_ticket(channel_id=message.channel.id)
        if ticket:
            attachments = [a.url for a in message.attachments]
            add_message(
                ticket["id"], message.id, message.author.id,
                message.author.name, str(message.author.display_avatar.url) if message.author.display_avatar else "",
                message.content, attachments
            )

            # Primeira resposta do staff
            if ticket["status"] == "open" and str(message.author.id) != ticket["user_id"]:
                from ..utils.database import get_connection
                conn = get_connection()
                c = conn.cursor()
                c.execute("UPDATE tickets SET first_response_at = ? WHERE id = ? AND first_response_at IS NULL",
                          (datetime.datetime.now().isoformat(), ticket["id"]))
                conn.commit()
                conn.close()

    async def check_spam(self, message):
        config = load_config()
        user_id = message.author.id
        now = datetime.datetime.now().timestamp()

        if user_id not in self.spam_tracker:
            self.spam_tracker[user_id] = []

        self.spam_tracker[user_id] = [t for t in self.spam_tracker[user_id] 
                                       if now - t < config["anti_spam"]["time_window"]]
        self.spam_tracker[user_id].append(now)

        if len(self.spam_tracker[user_id]) >= config["anti_spam"]["max_messages"]:
            try:
                await message.channel.send(f"⚠️ {message.author.mention} Anti-spam ativado! Aguarde.", delete_after=10)
            except:
                pass

async def create_ticket_channel(interaction, category_id, reason):
    config = load_config()
    lang = config["bot"]["language"]
    guild = interaction.guild
    user = interaction.user

    category = next((c for c in config["categories"] if c["id"] == category_id), None)
    if not category:
        return await interaction.response.send_message(get_text("error_occurred", lang), ephemeral=True)

    # Criar canal
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        user: discord.PermissionOverwrite(read_messages=True, send_messages=True, read_message_history=True),
        guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
    }

    for role_id in config["permissions"]["staff_roles"]:
        role = guild.get_role(int(role_id))
        if role:
            overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True, read_message_history=True)

    discord_category = None
    if category.get("category_channel_id"):
        discord_category = guild.get_channel(int(category["category_channel_id"]))

    channel_name = config["tickets"]["category_format"].replace("{username}", user.name).replace("{id}", str(user.id))
    channel_name = re.sub(r"[^a-zA-Z0-9\-]", "-", channel_name).lower()[:100]

    try:
        ticket_channel = await guild.create_text_channel(
            name=channel_name,
            category=discord_category,
            overwrites=overwrites,
            topic=f"Ticket de {user.name} | Categoria: {category['label']}"
        )
    except Exception as e:
        return await interaction.response.send_message(f"❌ Erro ao criar canal: {str(e)}", ephemeral=True)

    # Salvar no banco
    ticket_db_id = create_ticket(guild.id, ticket_channel.id, user.id, category_id, reason, category.get("priority", "medium"))
    update_cooldown(user.id, guild.id)

    # Embed de boas-vindas
    welcome_desc = config["embeds"]["welcome_description"]
    welcome_desc = welcome_desc.replace("{user}", user.mention).replace("{username}", user.name)
    welcome_desc = welcome_desc.replace("{category}", category["label"]).replace("{reason}", reason)
    welcome_desc = welcome_desc.replace("{guild}", guild.name).replace("{date}", datetime.datetime.now().strftime("%d/%m/%Y %H:%M"))
    welcome_desc = welcome_desc.replace("{id}", str(ticket_db_id)).replace("{staff}", "Nenhum")

    welcome_embed = discord.Embed(
        title=config["embeds"]["welcome_title"],
        description=welcome_desc,
        color=int(config["embeds"]["welcome_color"].replace("#", ""), 16),
        timestamp=datetime.datetime.now()
    )
    welcome_embed.set_author(name=user.name, icon_url=user.display_avatar.url if user.display_avatar else None)
    welcome_embed.set_footer(text=f"ID: {ticket_db_id}")

    view = TicketControlView(ticket_db_id, config)

    await ticket_channel.send(content=f"{user.mention}", embed=welcome_embed, view=view)

    if category.get("ping_roles"):
        pings = " ".join([f"<@&{r}>" for r in category["ping_roles"] if r])
        if pings:
            await ticket_channel.send(pings)

    add_log(guild.id, "ticket_open", user.id, ticket_channel.id, {"category": category_id, "reason": reason})

    await interaction.response.send_message(
        f"✅ {get_text('ticket_opened', lang)}: {ticket_channel.mention}",
        ephemeral=True
    )

async def setup(bot):
    await bot.add_cog(TicketsCog(bot))
