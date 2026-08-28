"""Interface de configuration locale de l'agent.

Servie par un second serveur asyncio, sur la boucle d'événements de l'agent :
l'interface accède donc directement à la configuration en cours et aux consoles
connectées, sans communication entre processus.

Le choix d'une interface web répond à trois contraintes du projet :

- une seule mise en œuvre pour macOS, Windows et Linux ;
- aucune dépendance à installer, la bibliothèque standard suffit ;
- un aperçu fidèle des écrans de la console, que produit aisément le HTML.

Elle n'écoute que sur l'interface locale. Voir `http.py` pour le détail du
modèle de sécurité, qui mérite l'attention : la configuration décrit des
commandes exécutables.
"""

# Deck3DS — Copyright (C) 2026 Romuald (@RomualdYT)
# Free software under the GNU GPL v3. See LICENSE for details.

from .http import UiServer

__all__ = ["UiServer"]
