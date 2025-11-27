import discord
from discord.ext import commands
import os 
from dotenv import load_dotenv
import time 
import json
import sys
import asyncio
from collections import deque

if sys.platform == "win32":
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except NotImplementedError:
        pass

# Configuration
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
COMMAND_PREFIX = '!'
DATA_FILE = 'bot_data.json' # Fichier de sauvegarde

print("lancement du bot..")

# Nécessaire pour l'historique, l'arbre et les commandes
intents = discord.Intents.default()
intents.message_content = True 
intents.members = True 

# Désactivation de la commande help par défaut
bot = commands.Bot(command_prefix=COMMAND_PREFIX, intents=intents, help_command=None)

# ----------------------------------------------------------------------

class Maillon:
    """ Représente un maillon de la liste chaînée (une commande spécifique). """
    def __init__(self, commande, utilisateur_nom, timestamp):
        self.commande = commande
        self.utilisateur_nom = utilisateur_nom
        self.timestamp = timestamp
        self.suivant = None

class Historique:
    """ Gère la liste chaînée des commandes. """
    def __init__(self):
        self.tete = None
    def ajouter_commande(self, commande, utilisateur_nom):
        nouveau_maillon = Maillon(commande, utilisateur_nom, time.time())
        nouveau_maillon.suivant = self.tete
        self.tete = nouveau_maillon
    def get_derniere_commande(self):
        if self.tete: return self.tete.commande
        return "Historique vide."
    def vider(self): self.tete = None

    # CORRECTION DU FORMAT TIMESTAMP LISIBLE DANS LA SAUVEGARDE
    def to_list(self):
        commandes = []
        courant = self.tete
        while courant:
            # Conversion du timestamp brut vers le format Jour/Mois/Année - Heure/Minute/Seconde
            date_formattee = time.strftime(
                "%d/%m/%Y - %H:%M:%S",
                time.localtime(courant.timestamp)
            )
            
            commandes.append({
                'commande': courant.commande,
                'utilisateur_nom': courant.utilisateur_nom,
                'timestamp_lisible': date_formattee,
                'timestamp_brut': courant.timestamp
            })
            courant = courant.suivant
        return commandes
    
    @classmethod
    def from_list(cls, liste_commandes):
        nouvel_historique = cls()
        for data in reversed(liste_commandes):
            # Récupère le timestamp brut qui est nécessaire pour reconstruire le Maillon
            timestamp_a_utiliser = data.get('timestamp_brut', data.get('timestamp'))
            
            maillon = Maillon(
                data['commande'],
                data['utilisateur_nom'],
                timestamp_a_utiliser
            )
            maillon.suivant = nouvel_historique.tete
            nouvel_historique.tete = maillon
        return nouvel_historique

# --- Arbre Discussion ---
class QuestionNode:
    """ Représente un nœud dans l'arbre de discussion. """
    def __init__(self, question, conclusion=False):
        self.question = question
        self.conclusion = conclusion
        self.enfants = {}
    def ajouter_enfant(self, reponse_cle, node_enfant):
        self.enfants[reponse_cle.lower()] = node_enfant

class SystemeDiscussion:
    """ Gère l'arbre de conversation et l'état des utilisateurs. """
    def __init__(self):
        self.racine = self._construire_arbre_initial()
        self.etats_utilisateurs = {}

    def _construire_arbre_initial(self):
        # --- DÉFINITION DE L'ARBRE DE CONVERSATION ---
        racine = QuestionNode("Bienvenue dans le guide ! Quel est votre objectif ? (tapez Aide ou Fun)")
        aide = QuestionNode("S'agit-il d'un problème technique (bug) ou d'une question sur le projet (projet) ? (tapez Bug ou Projet)")
        bug = QuestionNode("Avez-vous redémarré le bot ou vérifié l'erreur ? (tapez Oui ou Non)")
        conclusion_doc = QuestionNode("Conclusion : Veuillez lire la documentation ou ouvrir un ticket.", conclusion=True)
        conclusion_support = QuestionNode("Conclusion : Le support technique va vous contacter dans 24h.", conclusion=True)
        bug.ajouter_enfant("oui", conclusion_doc)
        bug.ajouter_enfant("non", conclusion_support)
        projet = QuestionNode("Le projet est basé sur les structures de données. Bonne chance !", conclusion=True)
        aide.ajouter_enfant("bug", bug)
        aide.ajouter_enfant("projet", projet)
        fun = QuestionNode("Quel sujet préférez-vous ? Les chats (chat) ou le Python (python) ? (tapez Chat ou Python)")
        conclusion_chat = QuestionNode("Conclusion Fun : Un chat est un petit lion dans la maison.", conclusion=True)
        conclusion_python = QuestionNode("Conclusion Fun : Le Python a été choisi. Le chat est triste.", conclusion=True)
        fun.ajouter_enfant("chat", conclusion_chat)
        fun.ajouter_enfant("python", conclusion_python)
        racine.ajouter_enfant("aide", aide)
        racine.ajouter_enfant("fun", fun)
        return racine

    def demarrer_discussion(self, user_id):
        self.etats_utilisateurs[user_id] = self.racine
        return self.racine.question
    def reinitialiser_discussion(self, user_id):
        if user_id in self.etats_utilisateurs: del self.etats_utilisateurs[user_id]
        return self.demarrer_discussion(user_id)
    def parler_de(self, sujet):
        file = deque([self.racine]) 
        while file:
            noeud_courant = file.popleft() 
            if sujet.lower() in noeud_courant.question.lower(): return True
            for enfant in noeud_courant.enfants.values(): file.append(enfant)
        return False

historique_global = Historique()
historiques_utilisateurs = {}
discussion_system = SystemeDiscussion()

# Liste des commandes à exclure de l'enregistrement de l'historique
COMMANDES_HISTORIQUE = ['!lastcmd', '!myhistory', '!clearhistory', '!help'] 

def sauvegarder_donnees():
    try:
        data = {
            'historique_global': historique_global.to_list(),
            'historiques_utilisateurs': {
                str(uid): h.to_list() for uid, h in historiques_utilisateurs.items()
            },
        }
        with open(DATA_FILE, 'w') as f:
            json.dump(data, f, indent=4)
        print("Données sauvegardées.")
    except Exception as e:
        print(f"Erreur lors de la sauvegarde: {e}")

def charger_donnees():
    global historique_global, historiques_utilisateurs
    try:
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)
            historique_global = Historique.from_list(data.get('historique_global', []))
            for uid_str, h_list in data.get('historiques_utilisateurs', {}).items():
                historiques_utilisateurs[int(uid_str)] = Historique.from_list(h_list)
            print("Données chargées avec succès.")
    except FileNotFoundError:
        print("Fichier de sauvegarde non trouvé, initialisation des données.")
    except Exception as e:
        print(f"Erreur lors du chargement des données: {e}")

async def gestion_reponse_arbre(message: discord.Message):
    """ Logique de progression dans l'arbre de discussion. """
    user_id = message.author.id
    reponse = message.content.lower()
    noeud_actuel = discussion_system.etats_utilisateurs.get(user_id)

    if not noeud_actuel: return 

    prochain_noeud = noeud_actuel.enfants.get(reponse)
    
    if prochain_noeud:
        discussion_system.etats_utilisateurs[user_id] = prochain_noeud
        
        # Résultat du questionnaire
        if prochain_noeud.conclusion:
            await message.channel.send(f"**Résultat du questionnaire :** {prochain_noeud.question}")
            del discussion_system.etats_utilisateurs[user_id]
        else:
            await message.channel.send(f"**Question :** {prochain_noeud.question}")
    else:
        reponses_valides = ", ".join(noeud_actuel.enfants.keys())
        await message.channel.send(f"Réponse non reconnue. Veuillez répondre avec une option valide : `{reponses_valides}`.")
# --- ÉVÉNEMENTS DU BOT ---
@bot.event
async def on_ready():
    charger_donnees()
    print("Le bot est prêt")
    try:
        synced = await bot.tree.sync()
        print(f"Commandes slash synchronisées : {len(synced)}")
    except Exception as e:
        print(e)
        
@bot.event
async def on_disconnect():
    sauvegarder_donnees()
    
@bot.event
async def on_message(message: discord.Message):
    if message.author.bot : return

    user_id = message.author.id
    # Récupère le nom d'affichage de l'utilisateur
    user_name = message.author.display_name
    
    # Traitement des commandes préfixées et enregistrement de l'historique
    if message.content.startswith(bot.command_prefix):
        cmd_entree = message.content.split()[0]
        
        # Traite les commandes Discord (!help, !calc)
        await bot.process_commands(message) 
        
        # Enregistre la commande seulement si elle n'est pas dans la liste d'exclusion
        if cmd_entree not in COMMANDES_HISTORIQUE:
            
            historique_global.ajouter_commande(cmd_entree, user_name)
            
            if user_id not in historiques_utilisateurs:
                historiques_utilisateurs[user_id] = Historique()
            historiques_utilisateurs[user_id].ajouter_commande(cmd_entree, user_name)
    
    # GESTION DE L'ARBRE
    elif user_id in discussion_system.etats_utilisateurs:
        await gestion_reponse_arbre(message)

    if message.content.lower() == "bonjour":
        await message.author.send("salut, comment tu vas ?")
    if message.content.lower() == "bienvenue":
        welcome_channel = bot.get_channel(1441343551114969128) 
        if welcome_channel: await welcome_channel.send(f"Bienvenue {message.author.mention} sur le serveur !")

# --- Liste des commandes ---

@bot.command(name='help', description="Affiche toutes les commandes du bot ou lance le guide de conversation.")
async def help_command(ctx, target: str = None):
    # Lancement du système de discussion
    if target and target.lower() == 'guide':
        question = discussion_system.demarrer_discussion(ctx.author.id)
        return await ctx.send(f"{ctx.author.mention}, Guide de conversation lancé. {question}")

    # Affichage de la liste complète des commandes
    embed = discord.Embed(
        title="Liste des Commandes du Bot",
        description="Utilisez `!help guide` pour lancer le questionnaire.\n\nVoici toutes les commandes que vous pouvez utiliser :",
        color=0x3498db
    )
    
    cmds_prefix = ""
    for command in bot.commands:
        if command.name not in ['help']:
            cmds_prefix += f"`!{command.name}`: {command.description}\n"
    
    embed.add_field(name="Commandes Préfixées", value=cmds_prefix, inline=False)
    
    slash_cmds = ""
    slash_cmds += "` /test `: Commande de test embeds.\n"
    slash_cmds += "` /warnguy `: Avertir un utilisateur.\n"
    slash_cmds += "` /banguy `: Bannir un utilisateur.\n"
    slash_cmds += "` /ynov `: Lien Ynov Campus Paris.\n"
    
    embed.add_field(name= "Commandes Slash", value=slash_cmds, inline=False)
    
    await ctx.send(embed=embed)

# --- COMMANDES HISTORIQUE ---
@bot.command(name='lastcmd', description="Affiche la dernière commande ! rentrée (globale ou d'un utilisateur).")
async def last_command(ctx, user: discord.User = None):
    
    if user:
        user_id = user.id
        historique = historiques_utilisateurs.get(user_id)
        
        if not historique:
            return await ctx.send(f"L'utilisateur **{user.display_name}** n'a pas encore de commandes enregistrées.")
            
        cmd = historique.get_derniere_commande()
        await ctx.send(f"La dernière commande enregistrée pour **{user.display_name}** est : `{cmd}`")
        
    else:
        cmd = historique_global.get_derniere_commande()
        await ctx.send(f"La dernière commande **globale** enregistrée est : `{cmd}`")

@bot.command(name='myhistory', description="Affiche toutes les commandes ! rentrées par l'utilisateur.")
async def my_history(ctx):
    user_id = ctx.author.id
    historique_user = historiques_utilisateurs.get(user_id)
    if not historique_user or not historique_user.tete: return await ctx.send("Vous n'avez pas encore envoyé de commandes.")
    messages = ["Votre historique de commandes :"]
    courant = historique_user.tete
    while courant:
        dt_object = time.strftime("%d/%m/%Y - %H:%M:%S", time.localtime(courant.timestamp))
        messages.append(f"• `{courant.commande}` (le {dt_object})")
        courant = courant.suivant
    await ctx.send('\n'.join(messages[:11]))

@bot.command(name='clearhistory', description="Vide l'historique (global, personnel ou d'un utilisateur spécifié).")
async def clear_history(ctx, target: str = None):
    
    if target is None:
        if ctx.author.id in historiques_utilisateurs:
            historiques_utilisateurs[ctx.author.id].vider()
            return await ctx.send("Votre historique personnel a été **vidé**.")
        return await ctx.send("Votre historique personnel était déjà vide.")

    if target.lower() == 'global':
        historique_global.vider()
        return await ctx.send("L'historique **global** des commandes a été **vidé**.")

    try:
        user_converter = commands.UserConverter()
        user = await user_converter.convert(ctx, target)
        user_id = user.id
        
        if ctx.author.id != user_id and not ctx.author.guild_permissions.manage_messages:
             return await ctx.send("Vous n'avez pas la permission de vider l'historique d'un autre utilisateur.")

        if user_id in historiques_utilisateurs:
            historiques_utilisateurs[user_id].vider()
            return await ctx.send(f"L'historique personnel de **{user.display_name}** a été **vidé**.")
        else:
            return await ctx.send(f"L'utilisateur **{user.display_name}** n'avait pas d'historique à vider.")

    except commands.BadArgument:
        return await ctx.send("Argument non valide. **Usage :** `!clearhistory`, `!clearhistory global`, ou `!clearhistory @utilisateur`.")


# --- COMMANDES ARBRE DE DISCUSSION ---

@bot.command(name='reset', description="Recommence la discussion depuis la racine de l'arbre.")
async def reset_guide(ctx):
    question = discussion_system.reinitialiser_discussion(ctx.author.id)
    await ctx.send(f"{ctx.author.mention}, Discussion réinitialisée. {question}")

@bot.command(name='speak', description="Vérifie si le sujet X est présent dans l'arbre (!speak projet).")
async def speak_about_x(ctx, *, sujet: str):
    if discussion_system.parler_de(sujet):
        await ctx.send(f"Oui, le sujet **'{sujet}'** est abordé dans le guide.")
    else:
        await ctx.send(f"Non, le sujet **'{sujet}'** n'a pas été trouvé dans le guide.")
        
# --- Calculatrice ---

@bot.command(name='calc', description="Effectue une opération mathématique simple (ex: !calc 5+3).")
async def calculate(ctx, *, expression: str):
    try:
        resultat = eval(expression) 
        await ctx.send(f"Le résultat de `{expression}` = **{resultat}**.")
    except Exception:
        await ctx.send("Opération mathématique non valide. Veuillez utiliser des nombres et des opérateurs simples (+, -, *, /).")
    
# --- Commandes Slash ---

@bot.tree.command(name="test", description="commande de test embeds") 
async def test(interaction: discord.Interaction):
    embed = discord.Embed(title="Commande de test", description="Ceci est un embed de test", color= 0x008000)
    embed.add_field(name="Champ 1", value="Valeur du champ 1", inline=False)
    embed.add_field(name="Python", value="apprendre le python en bien", inline=False)
    embed.set_image(url="https://www.python.org/static/community_logos/python-logo.png")
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="warnguy", description="warn un utilisateur")
async def warnguy(interaction: discord.Interaction, user: discord.User):
   await interaction.response.send_message("Alerte envoyée")
   await user.send ("Vous avez été warn par un modérateur.")

@bot.tree.command(name="banguy", description="ban un utilisateur")
async def banguy(interaction: discord.Interaction, user: discord.User):
   await interaction.response.send_message("Ban envoyée")
   await user.ban(reason="Violation des règles du serveur")
   await user.send ("Vous avez été banni. Merci et à jamais.")
    
@bot.tree.command(name="ynov", description="site de paris ynov campus")
async def ynov(interaction: discord.Interaction):
    await interaction.response.send_message("bienvenue sur le campus ynov paris : https://www.ynov.com/campus/paris")


# --- LANCEMENT ---
if TOKEN:
    try:
        # Tente de lancer le bot
        print("Lancement de la boucle principale...")
        bot.run(TOKEN)
        
    except KeyboardInterrupt:
        # Attrape Ctrl+C (KeyboardInterrupt)
        print("\nInterruption du bot (Ctrl+C) détectée.")
        
    finally:
        # Force la sauvegarde avant l'arrêt total du script.
        sauvegarder_donnees()
        print("Arrêt sécurisé terminé.")

else:
    print("ATTENTION : Le Token n'a pas été trouvé. Assurez-vous que DISCORD_TOKEN est défini dans votre fichier .env.")