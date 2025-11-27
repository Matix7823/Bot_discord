🤖 Bot Discord

Ce bot Discord offre plusieurs fonctionnalités avancées, notamment :

📜 Historique global et personnel des commandes

🌳 Système de discussion interactif basé sur un arbre décisionnel

🔢 Calculatrice intégrée

🛠 Commandes de modération (warn / ban)

🧾 Sauvegarde automatique des données en JSON

📩 Messages automatiques (DM / bienvenue)

⚙️ Commandes Prefix ! et commandes Slash /

📦 Installation
Prérequis

Python 3.10+

Modules nécessaires :

pip install discord.py python-dotenv

Configuration

Clone ou télécharge le projet :

git clone <url-du-projet>


Crée un fichier .env à la racine du projet :

DISCORD_TOKEN=TON_TOKEN_ICI


Lance le bot :

python bot.py

📁 Structure du projet
📦 Projet Bot Discord
 ┣ 📜 bot.py
 ┣ 📜 bot_data.json     # Sauvegarde automatique
 ┣ 📜 .env
 ┗ 📜 README.md

🧠 Fonctionnalités principales
📜 Historique des commandes
Commande	Description
!lastcmd	Affiche la dernière commande enregistrée
!myhistory	Affiche votre historique complet
!clearhistory	Supprime l’historique (solo / global / user spécifique)

🌳 Arbre de discussion interactif
Commande	Description
!help guide	Lance un questionnaire interactif
!reset	Réinitialise la discussion
!speak <mot>	Cherche un sujet dans l’arbre »

Exemple d’interaction :

!help guide
> Bienvenue dans le guide ! Quel est votre objectif ? (Aide / Fun)

🔢 Calculatrice
!calc 5+3

➡️ Retournera 8

🛠 Commandes Slash
Commande	Fonction
/test	Embed de test
/warnguy @user	Envoie un avertissement
/banguy @user	Bannit un utilisateur
/ynov	Envoie le lien Ynov Paris
💾 Sauvegarde automatique

Le fichier bot_data.json conserve :

Historique global

Historique par utilisateur

Dates formatées en JJ/MM/AAAA - HH:MM:SS

Sauvegarde automatique lors de :

Déconnexion du bot

Interruption avec Ctrl + C