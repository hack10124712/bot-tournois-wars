import discord
from discord.ext import commands
from discord import app_commands
import json
from datetime import datetime
import os
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

# Configuration
CONFIG = {
    'INSCRIPTION_CHANNEL_ID': 1442961241328062484,
    'PARTICIPANTS_CHANNEL_ID': 1442961282461466746,
    'WINNER_CHANNEL_ID': 1442961481883979897,
    'TICKET_CHANNEL_ID': 1442961893831606303,
    'WELCOME_CHANNEL_ID': 1443317965419446383,
    'LOGS_CHANNEL_ID': 1445727274547675217,
    'TICKET_CATEGORY_ID': 1444636591984214107,
    'PARTICIPANT_ROLE_ID': 1442962720126406686,
    'VERIFIED_ROLE_ID': 1442963417601151056,
    'ELIMINATED_ROLE_ID': 1442962878763106415,
    'WINNER_ROLE_ID': 1442962932714438738,
    'PRIX_PARTICIPATION': '10€',
    'CASHPRIZE': '100€'
}

# Intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Variables globales
participants_message_id = None
max_participants = 32
current_prix_participation = 10
current_cashprize = 100

# Charger la config
def load_config():
    global participants_message_id
    try:
        with open('config.json', 'r') as f:
            data = json.load(f)
            participants_message_id = data.get('participants_message_id')
    except FileNotFoundError:
        pass

# Sauvegarder la config
def save_config():
    with open('config.json', 'w') as f:
        json.dump({'participants_message_id': participants_message_id}, f)

@bot.event
async def on_ready():
    print(f'Bot connecté: {bot.user}')
    load_config()
    
    bot.add_view(TicketView())
    
    try:
        synced = await bot.tree.sync()
        print(f'{len(synced)} commandes synchronisées')
        print('Commandes disponibles:')
        for cmd in synced:
            print(f'  - /{cmd.name}')
    except Exception as e:
        print(f'Erreur sync: {e}')

@bot.event
async def on_member_join(member):
    welcome_channel_id = CONFIG.get('WELCOME_CHANNEL_ID')
    if not welcome_channel_id:
        return
    
    welcome_channel = bot.get_channel(welcome_channel_id)
    if not welcome_channel:
        return
    
    # Embed principal avec dégradé de couleurs
    embed1 = discord.Embed(
        title='',
        description='',
        color=0x00FF7F
    )
    
    content = f"# BIENVENUE SUR LE SERVEUR\n\n"
    content += f"## {member.mention}\n\n"
    content += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    embed1.description = content
    embed1.timestamp = datetime.now()
    
    # Deuxième embed avec infos
    embed2 = discord.Embed(
        title='',
        description='',
        color=0x9B59B6
    )
    
    info = f"Tu es le **membre n°{member.guild.member_count}**\n\n"
    info += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    info += "**POUR COMMENCER**\n\n"
    info += "Consulte les salons de discussion\n"
    info += "Participe aux tournois gaming\n"
    info += "Gagne des cashprizes\n\n"
    
    embed2.description = info
    embed2.set_thumbnail(url=member.display_avatar.url)
    embed2.set_footer(text=f'{member.guild.name} • Amuse-toi bien')
    embed2.timestamp = datetime.now()
    
    await welcome_channel.send(embeds=[embed1, embed2])

@bot.event
async def on_member_update(before, after):
    # Détecter si le rôle vérifié a été ajouté
    verified_role_id = CONFIG['VERIFIED_ROLE_ID']
    
    # Vérifier si le rôle vérifié a été ajouté
    before_has_role = any(role.id == verified_role_id for role in before.roles)
    after_has_role = any(role.id == verified_role_id for role in after.roles)
    
    # Si le rôle vient d'être ajouté
    if not before_has_role and after_has_role:
        await update_participants_list_auto(after.guild)
    
    # Si le rôle vient d'être retiré
    elif before_has_role and not after_has_role:
        await update_participants_list_auto(after.guild)
    
    # Log des changements de rôles
    await log_role_changes(before, after)

# Fonction pour logger les actions
async def send_log(guild, embed):
    logs_channel = bot.get_channel(CONFIG['LOGS_CHANNEL_ID'])
    if logs_channel:
        try:
            await logs_channel.send(embed=embed)
        except Exception as e:
            print(f'Erreur envoi log: {e}')

# Log des changements de rôles
async def log_role_changes(before, after):
    added_roles = [role for role in after.roles if role not in before.roles]
    removed_roles = [role for role in before.roles if role not in after.roles]
    
    if added_roles or removed_roles:
        embed = discord.Embed(
            title='CHANGEMENT DE RÔLE',
            color=0x3498DB
        )
        
        embed.add_field(name='Membre', value=after.mention, inline=True)
        embed.add_field(name='ID', value=f'`{after.id}`', inline=True)
        embed.add_field(name='\u200B', value='\u200B', inline=True)
        
        if added_roles:
            roles_text = ', '.join([role.mention for role in added_roles])
            embed.add_field(name='Rôles ajoutés', value=roles_text, inline=False)
        
        if removed_roles:
            roles_text = ', '.join([role.mention for role in removed_roles])
            embed.add_field(name='Rôles retirés', value=roles_text, inline=False)
        
        embed.timestamp = datetime.now()
        await send_log(after.guild, embed)

@bot.event
async def on_member_remove(member):
    embed = discord.Embed(
        title='MEMBRE QUITTÉ / KICK',
        description=f'{member.mention} a quitté le serveur',
        color=0xE74C3C
    )
    
    embed.add_field(name='Utilisateur', value=f'{member.name}#{member.discriminator}', inline=True)
    embed.add_field(name='ID', value=f'`{member.id}`', inline=True)
    embed.add_field(name='Compte créé', value=f'<t:{int(member.created_at.timestamp())}:R>', inline=True)
    
    roles = [role.mention for role in member.roles if role.name != '@everyone']
    if roles:
        embed.add_field(name='Rôles', value=', '.join(roles), inline=False)
    
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.timestamp = datetime.now()
    await send_log(member.guild, embed)

@bot.event
async def on_member_ban(guild, user):
    embed = discord.Embed(
        title='MEMBRE BANNI',
        description=f'{user.mention} a été banni du serveur',
        color=0xC0392B
    )
    
    embed.add_field(name='Utilisateur', value=f'{user.name}#{user.discriminator}', inline=True)
    embed.add_field(name='ID', value=f'`{user.id}`', inline=True)
    
    embed.set_thumbnail(url=user.display_avatar.url)
    embed.timestamp = datetime.now()
    await send_log(guild, embed)

@bot.event
async def on_member_unban(guild, user):
    embed = discord.Embed(
        title='MEMBRE DÉBANNI',
        description=f'{user.mention} a été débanni',
        color=0x27AE60
    )
    
    embed.add_field(name='Utilisateur', value=f'{user.name}#{user.discriminator}', inline=True)
    embed.add_field(name='ID', value=f'`{user.id}`', inline=True)
    
    embed.timestamp = datetime.now()
    await send_log(guild, embed)

@bot.event
async def on_message_delete(message):
    if message.author.bot:
        return
    
    embed = discord.Embed(
        title='MESSAGE SUPPRIMÉ',
        color=0xE67E22
    )
    
    embed.add_field(name='Auteur', value=message.author.mention, inline=True)
    embed.add_field(name='Salon', value=message.channel.mention, inline=True)
    embed.add_field(name='\u200B', value='\u200B', inline=True)
    
    content = message.content[:1000] if message.content else '*Aucun contenu texte*'
    embed.add_field(name='Contenu', value=content, inline=False)
    
    if message.attachments:
        attachments_text = '\n'.join([f'[{att.filename}]({att.url})' for att in message.attachments])
        embed.add_field(name='Pièces jointes', value=attachments_text, inline=False)
    
    embed.timestamp = datetime.now()
    await send_log(message.guild, embed)

@bot.event
async def on_message_edit(before, after):
    if before.author.bot or before.content == after.content:
        return
    
    embed = discord.Embed(
        title='MESSAGE MODIFIÉ',
        color=0xF39C12
    )
    
    embed.add_field(name='Auteur', value=before.author.mention, inline=True)
    embed.add_field(name='Salon', value=before.channel.mention, inline=True)
    embed.add_field(name='Lien', value=f'[Aller au message]({after.jump_url})', inline=True)
    
    before_content = before.content[:500] if before.content else '*Vide*'
    after_content = after.content[:500] if after.content else '*Vide*'
    
    embed.add_field(name='Avant', value=before_content, inline=False)
    embed.add_field(name='Après', value=after_content, inline=False)
    
    embed.timestamp = datetime.now()
    await send_log(before.guild, embed)

@bot.event
async def on_guild_channel_create(channel):
    embed = discord.Embed(
        title='SALON CRÉÉ',
        description=f'Nouveau salon : {channel.mention}',
        color=0x27AE60
    )
    
    embed.add_field(name='Nom', value=channel.name, inline=True)
    embed.add_field(name='Type', value=str(channel.type), inline=True)
    embed.add_field(name='ID', value=f'`{channel.id}`', inline=True)
    
    embed.timestamp = datetime.now()
    await send_log(channel.guild, embed)

@bot.event
async def on_guild_channel_delete(channel):
    embed = discord.Embed(
        title='SALON SUPPRIMÉ',
        description=f'Salon supprimé : **{channel.name}**',
        color=0xE74C3C
    )
    
    embed.add_field(name='Nom', value=channel.name, inline=True)
    embed.add_field(name='Type', value=str(channel.type), inline=True)
    embed.add_field(name='ID', value=f'`{channel.id}`', inline=True)
    
    embed.timestamp = datetime.now()
    await send_log(channel.guild, embed)

@bot.event
async def on_guild_role_create(role):
    embed = discord.Embed(
        title='RÔLE CRÉÉ',
        description=f'Nouveau rôle : {role.mention}',
        color=0x27AE60
    )
    
    embed.add_field(name='Nom', value=role.name, inline=True)
    embed.add_field(name='Couleur', value=str(role.color), inline=True)
    embed.add_field(name='ID', value=f'`{role.id}`', inline=True)
    
    embed.timestamp = datetime.now()
    await send_log(role.guild, embed)

@bot.event
async def on_guild_role_delete(role):
    embed = discord.Embed(
        title='RÔLE SUPPRIMÉ',
        description=f'Rôle supprimé : **{role.name}**',
        color=0xE74C3C
    )
    
    embed.add_field(name='Nom', value=role.name, inline=True)
    embed.add_field(name='ID', value=f'`{role.id}`', inline=True)
    
    embed.timestamp = datetime.now()
    await send_log(role.guild, embed)

# Commande: /setup-inscription
@bot.tree.command(name="setup-inscription", description="Envoyer le message d'inscription avec bouton (ADMIN)")
@app_commands.describe(
    places="Nombre maximum de participants",
    mode="Mode de jeu du tournoi",
    prix_participation="Prix de participation en euros (ex: 10)",
    cashprize="Montant du cashprize en euros (ex: 100)"
)
@app_commands.choices(mode=[
    app_commands.Choice(name="1v1", value="1v1"),
    app_commands.Choice(name="2v2", value="2v2"),
    app_commands.Choice(name="3v3", value="3v3"),
    app_commands.Choice(name="4v4", value="4v4")
])
async def setup_inscription(
    interaction: discord.Interaction, 
    places: int = 32, 
    prix_participation: int = 10,
    cashprize: int = 100,
    mode: app_commands.Choice[str] = None
):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message('Commande admin uniquement', ephemeral=True)
        return

    global max_participants, current_prix_participation, current_cashprize
    max_participants = places
    current_prix_participation = prix_participation
    current_cashprize = cashprize
    
    mode_text = mode.value if mode else "À définir"

    # Compter les participants actuels
    verified_role = interaction.guild.get_role(CONFIG['VERIFIED_ROLE_ID'])
    current_count = len(verified_role.members) if verified_role else 0

    embed = discord.Embed(
        title='',
        description='',
        color=0xE67E22
    )
    
    content = "# INSCRIPTION AU TOURNOI\n\n"
    content += "Rejoins le tournoi et tente de remporter le cashprize\n\n"
    content += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    content += f"**Mode** : {mode_text}\n"
    content += f"**Participation** : {prix_participation}€\n"
    content += f"**Prize Pool** : {cashprize}€\n"
    content += f"**Places disponibles** : {places - current_count}\n\n"
    content += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    content += "**COMMENT PARTICIPER**\n\n"
    content += "1. Clique sur le bouton ci-dessous\n"
    content += "2. Un salon privé sera créé pour toi\n"
    content += "3. Suis les instructions données\n"
    content += "4. Attends la validation du staff\n\n"
    
    if mode and mode.value != "1v1":
        content += f"**IMPORTANT** : Tournoi {mode.value}, tu devras former une équipe\n\n"
    
    embed.description = content
    embed.set_footer(text='Tournoi Gaming • Bonne chance')
    embed.timestamp = datetime.now()

    button = discord.ui.Button(
        label='S\'INSCRIRE AU TOURNOI',
        style=discord.ButtonStyle.primary,
        custom_id='register_tournament'
    )

    async def button_callback(interaction: discord.Interaction):
        await handle_registration(interaction, prix_participation)

    button.callback = button_callback
    view = discord.ui.View(timeout=None)
    view.add_item(button)

    channel = bot.get_channel(CONFIG['INSCRIPTION_CHANNEL_ID'])
    if not channel:
        await interaction.response.send_message('Salon inscription introuvable', ephemeral=True)
        return

    await channel.send(embed=embed, view=view)
    await interaction.response.send_message(
        f'Message d\'inscription envoyé ({mode_text}, {places} places, {prix_participation}€ participation, {cashprize}€ cashprize)', 
        ephemeral=True
    )

# Gestion de l'inscription - CRÉATION DU SALON TICKET
async def handle_registration(interaction: discord.Interaction, prix_participation: int = 10):
    member = interaction.user
    guild = interaction.guild
    
    # Vérifier si l'utilisateur a déjà un ticket ouvert
    existing_channel = discord.utils.get(guild.text_channels, name=f'inscription-{member.name.lower()}')
    if existing_channel:
        await interaction.response.send_message(f'Tu as déjà un salon d\'inscription ouvert : {existing_channel.mention}', ephemeral=True)
        return

    try:
        await interaction.response.defer(ephemeral=True)
        
        # Utiliser la catégorie spécifiée
        category = interaction.guild.get_channel(CONFIG['TICKET_CATEGORY_ID'])
        if not category:
            await interaction.followup.send('Catégorie introuvable', ephemeral=True)
            return
        
        # Créer le salon privé
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            member: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        
        # Ajouter les permissions pour les admins
        for role in guild.roles:
            if role.permissions.administrator:
                overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
        
        ticket_channel = await guild.create_text_channel(
            name=f'inscription-{member.name}',
            category=category,
            overwrites=overwrites
        )
        
        # Donner le rôle Participant
        role = guild.get_role(CONFIG['PARTICIPANT_ROLE_ID'])
        if role:
            await member.add_roles(role)
        
        # Message d'instructions dans le ticket
        embed = discord.Embed(
            title='',
            description='',
            color=0x9B59B6
        )
        
        content = f"# INSCRIPTION AU TOURNOI\n\n"
        content += f"Bienvenue {member.mention}\n\n"
        content += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        content += "**ÉTAPES À SUIVRE**\n\n"
        content += "1. Un administrateur te donnera les informations de paiement\n"
        content += f"2. Effectue le paiement de {prix_participation}€\n"
        content += "3. Envoie ta preuve de paiement dans ce salon\n"
        content += "4. Attends la validation du staff\n\n"
        content += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        content += "Ce salon est privé entre toi et les administrateurs\n"
        content += "Ton inscription sera validée après vérification\n\n"
        
        embed.description = content
        embed.set_footer(text='Tournoi Gaming • Inscription')
        embed.timestamp = datetime.now()
        
        # Bouton fermer (admin seulement)
        close_button = discord.ui.Button(
            label='Fermer le ticket',
            style=discord.ButtonStyle.danger,
            custom_id=f'close_{ticket_channel.id}'
        )
        
        async def close_callback(button_interaction: discord.Interaction):
            if not button_interaction.user.guild_permissions.administrator:
                await button_interaction.response.send_message('Seuls les admins peuvent fermer', ephemeral=True)
                return
            await button_interaction.response.send_message('Fermeture...', ephemeral=True)
            await ticket_channel.delete()
        
        close_button.callback = close_callback
        view = discord.ui.View(timeout=None)
        view.add_item(close_button)
        
        await ticket_channel.send(f'# {member.mention}', embed=embed, view=view)
        
        # Notifier les admins
        admin_roles = [role.mention for role in guild.roles if role.permissions.administrator]
        if admin_roles:
            await ticket_channel.send(f'{" ".join(admin_roles)} Nouvelle inscription')
        
        await interaction.followup.send(f'Ton salon d\'inscription a été créé : {ticket_channel.mention}', ephemeral=True)
        await update_participants_list_auto(guild)

    except Exception as e:
        print(f'Erreur: {e}')
        await interaction.followup.send('Erreur lors de l\'inscription', ephemeral=True)

# Mettre à jour la liste automatiquement
async def update_participants_list_auto(guild):
    global participants_message_id
    
    channel = bot.get_channel(CONFIG['PARTICIPANTS_CHANNEL_ID'])
    if not channel:
        return

    # Utiliser le rôle VÉRIFIÉ au lieu du rôle participant
    role = guild.get_role(CONFIG['VERIFIED_ROLE_ID'])
    if not role:
        return

    members = role.members
    members_list = '\n'.join([f'{i+1}. {member.mention}' for i, member in enumerate(members)])
    
    if not members_list:
        members_list = '*Aucun participant pour le moment*'

    embed = discord.Embed(
        title='',
        description='',
        color=0x3498DB
    )
    
    content = "# LISTE DES PARTICIPANTS\n\n"
    content += members_list + "\n\n"
    content += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    content += f"**Total** : {len(members)} participants\n"
    
    embed.description = content
    embed.set_footer(text='Tournoi Gaming')
    embed.timestamp = datetime.now()

    try:
        if participants_message_id:
            message = await channel.fetch_message(participants_message_id)
            await message.edit(embed=embed)
        else:
            message = await channel.send(embed=embed)
            participants_message_id = message.id
            save_config()
    except:
        message = await channel.send(embed=embed)
        participants_message_id = message.id
        save_config()

# Commande: /update-participants
@bot.tree.command(name="update-participants", description="Mettre à jour la liste des participants (ADMIN)")
async def update_participants(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message('Commande admin uniquement', ephemeral=True)
        return

    await update_participants_list_auto(interaction.guild)
    await interaction.response.send_message('Liste mise à jour', ephemeral=True)

# Commande: /reset-inscriptions
@bot.tree.command(name="reset-inscriptions", description="Retirer les rôles à tous (ADMIN)")
async def reset_inscriptions(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message('Commande admin uniquement', ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)

    verified_role = interaction.guild.get_role(CONFIG['VERIFIED_ROLE_ID'])
    participant_role = interaction.guild.get_role(CONFIG['PARTICIPANT_ROLE_ID'])
    eliminated_role = interaction.guild.get_role(CONFIG['ELIMINATED_ROLE_ID'])
    
    count = 0
    
    # Retirer le rôle vérifié
    if verified_role:
        for member in verified_role.members:
            try:
                await member.remove_roles(verified_role)
                count += 1
            except Exception as e:
                print(f'Erreur: {e}')
    
    # Retirer le rôle participant
    if participant_role:
        for member in participant_role.members:
            try:
                await member.remove_roles(participant_role)
            except Exception as e:
                print(f'Erreur: {e}')
    
    # Retirer le rôle éliminé
    if eliminated_role:
        for member in eliminated_role.members:
            try:
                await member.remove_roles(eliminated_role)
            except Exception as e:
                print(f'Erreur: {e}')

    await update_participants_list_auto(interaction.guild)
    await interaction.followup.send(f'Rôles retirés à {count} membres')

# Commande: /stats
@bot.tree.command(name="stats", description="Voir le nombre de participants")
async def stats(interaction: discord.Interaction):
    # Utiliser le rôle vérifié pour compter les vrais participants
    role = interaction.guild.get_role(CONFIG['VERIFIED_ROLE_ID'])
    count = len(role.members) if role else 0
    
    # Utiliser les valeurs globales actuelles
    global current_prix_participation, current_cashprize

    embed = discord.Embed(
        title='',
        description='',
        color=0xE74C3C
    )
    
    content = "# STATISTIQUES DU TOURNOI\n\n"
    content += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    content += f"**Participants vérifiés** : {count}\n"
    content += f"**Prix par participant** : {current_prix_participation}€\n"
    content += f"**Cagnotte collectée** : {count * current_prix_participation}€\n"
    content += f"**Cashprize à gagner** : {current_cashprize}€\n\n"
    
    embed.description = content
    embed.set_footer(text='Tournoi Gaming')
    embed.timestamp = datetime.now()

    await interaction.response.send_message(embed=embed, ephemeral=True)

# Commande: /setup-ticket
@bot.tree.command(name="setup-ticket", description="Envoyer le système de tickets (ADMIN)")
async def setup_ticket(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message('Commande admin uniquement', ephemeral=True)
        return

    embed = discord.Embed(
        title='',
        description='',
        color=0x2B2D31
    )
    
    content = "# SYSTÈME DE TICKETS\n\n"
    content += "Besoin d'aide ? Ouvre un ticket\n\n"
    content += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    content += "**CATÉGORIES**\n\n"
    content += "**Insulte** - Signaler un comportement inapproprié\n"
    content += "**Question** - Poser une question au staff\n"
    content += "**Paiement** - Problème lié à ton inscription\n\n"
    content += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    content += "Un salon privé sera créé pour toi\n\n"
    
    embed.description = content
    embed.set_footer(text='Tournoi Gaming • Support')
    embed.timestamp = datetime.now()
    
    view = TicketView()
    
    ticket_channel = bot.get_channel(CONFIG['TICKET_CHANNEL_ID'])
    if not ticket_channel:
        await interaction.response.send_message('Salon de tickets introuvable', ephemeral=True)
        return
    
    await ticket_channel.send(embed=embed, view=view)
    await interaction.response.send_message('Système de tickets envoyé', ephemeral=True)

# Vue pour les boutons de tickets
class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        
        # Bouton Insulte
        insulte_btn = discord.ui.Button(
            label='INSULTE',
            style=discord.ButtonStyle.danger,
            custom_id='ticket_insulte'
        )
        insulte_btn.callback = lambda i: self.create_ticket(i, 'insulte')
        
        # Bouton Question
        question_btn = discord.ui.Button(
            label='QUESTION',
            style=discord.ButtonStyle.primary,
            custom_id='ticket_question'
        )
        question_btn.callback = lambda i: self.create_ticket(i, 'question')
        
        # Bouton Paiement
        paiement_btn = discord.ui.Button(
            label='PAIEMENT',
            style=discord.ButtonStyle.success,
            custom_id='ticket_paiement'
        )
        paiement_btn.callback = lambda i: self.create_ticket(i, 'paiement')
        
        self.add_item(insulte_btn)
        self.add_item(question_btn)
        self.add_item(paiement_btn)
    
    async def create_ticket(self, interaction: discord.Interaction, ticket_type: str):
        member = interaction.user
        guild = interaction.guild
        
        # Vérifier si l'utilisateur a déjà un ticket ouvert de ce type
        existing_channel = discord.utils.get(guild.text_channels, name=f'{ticket_type}-{member.name.lower()}')
        if existing_channel:
            await interaction.response.send_message(
                f'Tu as déjà un ticket {ticket_type} ouvert : {existing_channel.mention}',
                ephemeral=True
            )
            return
        
        try:
            await interaction.response.defer(ephemeral=True)
            
            # Utiliser la catégorie spécifiée
            category = guild.get_channel(CONFIG['TICKET_CATEGORY_ID'])
            if not category:
                await interaction.followup.send('Catégorie introuvable', ephemeral=True)
                return
            
            # Créer le salon privé
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                member: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
            }
            
            # Ajouter les permissions pour les admins
            for role in guild.roles:
                if role.permissions.administrator:
                    overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
            
            ticket_channel = await guild.create_text_channel(
                name=f'{ticket_type}-{member.name}',
                category=category,
                overwrites=overwrites
            )
            
            # Messages personnalisés selon le type
            if ticket_type == 'insulte':
                embed = discord.Embed(
                    title='',
                    description='',
                    color=0xC0392B
                )
                
                content = f"# TICKET INSULTE\n\n"
                content += f"{member.mention}\n\n"
                content += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                content += "**INFORMATIONS À FOURNIR**\n\n"
                content += "1. Qui t'a insulté ? (mention ou nom)\n"
                content += "2. Dans quel salon ?\n"
                content += "3. Capture d'écran si possible\n"
                content += "4. Description de la situation\n\n"
                content += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                content += "Un modérateur va examiner ton signalement\n\n"
                
                embed.description = content
                embed.set_footer(text='Tournoi Gaming • Modération')
            
            elif ticket_type == 'question':
                embed = discord.Embed(
                    title='',
                    description='',
                    color=0x2980B9
                )
                
                content = f"# TICKET QUESTION\n\n"
                content += f"{member.mention}\n\n"
                content += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                content += "Pose ta question ici\n"
                content += "Un membre du staff te répondra rapidement\n\n"
                content += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                content += "Décris ta question en détail\n\n"
                
                embed.description = content
                embed.set_footer(text='Tournoi Gaming • Support')
            
            else:  # paiement
                embed = discord.Embed(
                    title='',
                    description='',
                    color=0x16A085
                )
                
                content = f"# TICKET PAIEMENT\n\n"
                content += f"{member.mention}\n\n"
                content += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                content += "**INFORMATIONS À FOURNIR**\n\n"
                content += "1. Preuve de paiement (screenshot)\n"
                content += "2. Montant et date du paiement\n"
                content += "3. Précise ton problème\n\n"
                content += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                content += "Un admin va vérifier et valider ton inscription\n\n"
                
                embed.description = content
                embed.set_footer(text='Tournoi Gaming • Paiement')
            
            embed.timestamp = datetime.now()
            
            # Bouton fermer
            close_button = discord.ui.Button(
                label='FERMER LE TICKET',
                style=discord.ButtonStyle.danger,
                custom_id=f'close_ticket_{ticket_channel.id}'
            )
            
            async def close_callback(button_interaction: discord.Interaction):
                if not button_interaction.user.guild_permissions.administrator and button_interaction.user.id != member.id:
                    await button_interaction.response.send_message('Seuls les admins ou le créateur peuvent fermer', ephemeral=True)
                    return
                await button_interaction.response.send_message('Fermeture du ticket...', ephemeral=True)
                await ticket_channel.delete()
            
            close_button.callback = close_callback
            close_view = discord.ui.View(timeout=None)
            close_view.add_item(close_button)
            
            await ticket_channel.send(f'# {member.mention}', embed=embed, view=close_view)
            
            # Notifier les admins
            admin_roles = [role.mention for role in guild.roles if role.permissions.administrator]
            if admin_roles:
                await ticket_channel.send(f'{" ".join(admin_roles)} Nouveau ticket {ticket_type}')
            
            await interaction.followup.send(
                f'Ton ticket {ticket_type} a été créé : {ticket_channel.mention}',
                ephemeral=True
            )
        
        except Exception as e:
            print(f'Erreur: {e}')
            await interaction.followup.send('Erreur lors de la création du ticket', ephemeral=True)

# Commande: /declare-winner
@bot.tree.command(name="declare-winner", description="Déclarer le gagnant du tournoi (ADMIN)")
@app_commands.describe(membre="Le membre qui a gagné le tournoi")
async def declare_winner(interaction: discord.Interaction, membre: discord.Member):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message('Commande admin uniquement', ephemeral=True)
        return
    
    await interaction.response.defer(ephemeral=True)
    
    # Donner le rôle gagnant
    winner_role = interaction.guild.get_role(CONFIG['WINNER_ROLE_ID'])
    if winner_role:
        await membre.add_roles(winner_role)
    
    # Retirer les rôles vérifié et participant
    verified_role = interaction.guild.get_role(CONFIG['VERIFIED_ROLE_ID'])
    participant_role = interaction.guild.get_role(CONFIG['PARTICIPANT_ROLE_ID'])
    
    if verified_role and verified_role in membre.roles:
        await membre.remove_roles(verified_role)
    if participant_role and participant_role in membre.roles:
        await membre.remove_roles(participant_role)
    
    # Créer le salon privé pour le paiement
    category = interaction.guild.get_channel(CONFIG['TICKET_CATEGORY_ID'])
    if not category:
        await interaction.followup.send('Catégorie introuvable', ephemeral=True)
        return
    
    overwrites = {
        interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
        membre: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        interaction.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
    }
    
    # Ajouter les permissions pour les admins
    for role in interaction.guild.roles:
        if role.permissions.administrator:
            overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
    
    winner_channel = await interaction.guild.create_text_channel(
        name=f'gagnant-{membre.name}',
        category=category,
        overwrites=overwrites
    )
    
    # Message avec les instructions
    embed = discord.Embed(
        title='',
        description='',
        color=0xF39C12
    )
    
    global current_cashprize
    
    content = f"# FÉLICITATIONS {membre.mention} 🏆\n\n"
    content += f"Tu as remporté le tournoi et gagné **{current_cashprize}€** !\n\n"
    content += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    content += "**POUR RECEVOIR TON CASHPRIZE**\n\n"
    content += "Envoie les informations suivantes dans ce salon :\n\n"
    content += "1. **Ton email PayPal**\n"
    content += "2. **Ton nom complet**\n"
    content += "3. **Ta preuve de victoire** (screenshot si nécessaire)\n\n"
    content += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    content += "**IMPORTANT**\n\n"
    content += "Vérifie bien que ton email PayPal est correct\n"
    content += "Le paiement sera effectué sous 24-48h\n"
    content += "Ce salon est privé entre toi et les administrateurs\n\n"
    
    embed.description = content
    embed.set_footer(text='Tournoi Gaming • Félicitations')
    embed.timestamp = datetime.now()
    
    # Bouton fermer
    close_button = discord.ui.Button(
        label='FERMER LE SALON',
        style=discord.ButtonStyle.danger,
        custom_id=f'close_winner_{winner_channel.id}'
    )
    
    async def close_callback(button_interaction: discord.Interaction):
        if not button_interaction.user.guild_permissions.administrator:
            await button_interaction.response.send_message('Seuls les admins peuvent fermer', ephemeral=True)
            return
        await button_interaction.response.send_message('Fermeture du salon...', ephemeral=True)
        await winner_channel.delete()
    
    close_button.callback = close_callback
    close_view = discord.ui.View(timeout=None)
    close_view.add_item(close_button)
    
    await winner_channel.send(f'# {membre.mention}', embed=embed, view=close_view)
    
    # Notifier les admins
    admin_roles = [role.mention for role in interaction.guild.roles if role.permissions.administrator]
    if admin_roles:
        await winner_channel.send(f'{" ".join(admin_roles)} Nouveau gagnant à payer')
    
    # Annonce publique dans le salon des gagnants
    winner_announce_channel = interaction.guild.get_channel(CONFIG['WINNER_CHANNEL_ID'])
    if winner_announce_channel:
        announce_embed = discord.Embed(
            title='',
            description='',
            color=0xF39C12
        )
        
        announce_content = "# 🏆 NOUVEAU GAGNANT 🏆\n\n"
        announce_content += f"## {membre.mention}\n\n"
        announce_content += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        announce_content += f"**Cashprize remporté** : {current_cashprize}€\n\n"
        announce_content += "Félicitations au champion du tournoi !\n\n"
        
        announce_embed.description = announce_content
        announce_embed.set_thumbnail(url=membre.display_avatar.url)
        announce_embed.set_footer(text='Tournoi Gaming • Vainqueur')
        announce_embed.timestamp = datetime.now()
        
        await winner_announce_channel.send(content='@everyone', embed=announce_embed)
    
    # Log
    log_embed = discord.Embed(
        title='GAGNANT DÉCLARÉ',
        color=0xF39C12
    )
    log_embed.add_field(name='Gagnant', value=membre.mention, inline=True)
    log_embed.add_field(name='Déclaré par', value=interaction.user.mention, inline=True)
    log_embed.add_field(name='Cashprize', value=f'{current_cashprize}€', inline=True)
    log_embed.timestamp = datetime.now()
    await send_log(interaction.guild, log_embed)
    
    await interaction.followup.send(
        f'{membre.mention} a été déclaré gagnant ! Salon privé créé : {winner_channel.mention}',
        ephemeral=True
    )

# Commande: /announce
@bot.tree.command(name="announce", description="Envoyer une annonce en MP à tous les membres (ADMIN)")
@app_commands.describe(message="Le contenu de l'annonce")
async def announce(interaction: discord.Interaction, message: str):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message('Commande admin uniquement', ephemeral=True)
        return
    
    await interaction.response.defer(ephemeral=True)
    
    # Créer l'embed de l'annonce
    embed = discord.Embed(
        title='',
        description='',
        color=0xE74C3C
    )
    
    content = f"# ANNONCE DU SERVEUR\n\n"
    content += f"{message}\n\n"
    content += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    content += f"Message envoyé par {interaction.user.mention}\n"
    
    embed.description = content
    embed.set_footer(text=f'{interaction.guild.name} • Annonce')
    embed.set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else None)
    embed.timestamp = datetime.now()
    
    # Envoyer à tous les membres
    success = 0
    failed = 0
    
    for member in interaction.guild.members:
        if member.bot:
            continue
        
        try:
            await member.send(embed=embed)
            success += 1
        except discord.Forbidden:
            failed += 1
        except Exception as e:
            print(f'Erreur envoi MP à {member.name}: {e}')
            failed += 1
    
    # Log de l'annonce
    logs_embed = discord.Embed(
        title='ANNONCE ENVOYÉE',
        color=0xF39C12
    )
    
    logs_embed.add_field(name='Envoyé par', value=interaction.user.mention, inline=True)
    logs_embed.add_field(name='Succès', value=str(success), inline=True)
    logs_embed.add_field(name='Échecs', value=str(failed), inline=True)
    logs_embed.add_field(name='Message', value=message[:1000], inline=False)
    logs_embed.timestamp = datetime.now()
    
    await send_log(interaction.guild, logs_embed)
    
    await interaction.followup.send(
        f'Annonce envoyée à {success} membres ({failed} échecs - MPs fermés)',
        ephemeral=True
    )

# Lancer le bot
TOKEN = os.getenv('DISCORD_TOKEN')
if not TOKEN:
    print('DISCORD_TOKEN non trouvé dans le fichier .env')
else:
    bot.run(TOKEN)