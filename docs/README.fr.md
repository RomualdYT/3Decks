# Documentation

[Accueil du projet](../README.fr.md) · [English](README.md)

## Utiliser 3Decks

- [Installation](INSTALLATION.fr.md) : prérequis, connexion, mises à jour et désinstallation.
- [Utilisation](USAGE.fr.md) : pages, boutons, tableaux de bord et touches de la console.
- [Configuration](CONFIGURATION.fr.md) : fichiers, sauvegardes et scripts.
- [Menu système](DESKTOP_INTEGRATION.fr.md) : réglages rapides, pause, démarrage et arrêt.
- [Dépannage](TROUBLESHOOTING.fr.md) : réseau, permissions, médias et notifications.
- [Sécurité](SECURITY.fr.md) : réseau de confiance, secrets et extensions.

## Développer

- [Contribuer](CONTRIBUTING_AGENT.fr.md) : environnement, frontend, tests et compilation.
- [Extensions](EXTENSIONS.fr.md) : démarrage en français ; contrat exhaustif en anglais.
- [Architecture](ARCHITECTURE.fr.md) : synthèse française et référence détaillée anglaise.
- [API HTTP](api/README.fr.md) : guide français, OpenAPI commun aux deux langues.
- [Protocole console](PROTOCOL.fr.md) : découverte UDP, TCP, messages et pochettes.
- [Migration FastAPI](MIGRATION_FASTAPI.fr.md) : configurations existantes et Python 3.12+.

## Maintenir

- [Publication](PUBLIC_RELEASE.fr.md)
- [Qualification et essais restants](QUALIFICATION.fr.md)
- [Qualité du code](CODE_QUALITY.fr.md)
- [Architecture locale et performances](LOCAL_APP.fr.md)

L’anglais est la langue de référence. Les traductions sont séparées dans des fichiers `.fr.md`. Les synthèses sont indiquées comme telles ; les identifiants techniques et l’OpenAPI ne sont pas traduits. Lors d’un changement de comportement, mettre à jour les deux guides concernés et vérifier les liens avec `python3 tools/check_docs.py` depuis la racine.
