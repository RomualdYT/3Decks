"""Bornes de ressources pour le transport TCP de la console."""

# Une connexion qui n'envoie pas rapidement un handshake complet ne doit pas
# conserver indéfiniment une socket et une tâche asyncio.
HANDSHAKE_TIMEOUT = 5.0

# Ces plafonds bornent séparément le travail avant authentification et le
# nombre de consoles actives. Ils restent largement supérieurs à l'usage
# normal (une ou deux consoles) sans laisser le réseau local épuiser l'agent.
MAX_PENDING_CONNECTIONS = 16
MAX_AUTHENTICATED_CLIENTS = 8
