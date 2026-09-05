# Configuration et sauvegardes

[Documentation](README.fr.md) · [English](CONFIGURATION.md)

Utilisez l’éditeur pour les réglages courants. Le JSON manuel s’adresse aux utilisateurs avancés.

## Emplacement

Priorité : `--config CHEMIN`, sinon `agent/config.json` dans les sources s’il existe, sinon le répertoire utilisateur de l’OS.

Emplacements habituels : `~/Library/Application Support/3Decks/config.json` sur macOS et `%LOCALAPPDATA%\3Decks\config.json` sur Windows. Le dossier courant ne sélectionne pas une configuration dans le paquet installé.

À côté du fichier se trouvent `paired-consoles.json` et `extensions/`. Agent arrêté, sauvegardez **tout ce dossier**, avec approbations, paquets et données. Il peut contenir mots de passe OBS, commandes et secrets ; gardez-le privé. Les réglages et le secret de la console restent sur sa SD. Révoquer une console dans l’éditeur ferme aussi ses connexions.

## Depuis les sources

N’enregistrez pas vos données personnelles dans le fichier de démonstration suivi par Git. Depuis `agent/` :

```sh
uv run --locked deck3ds --config config.local.json --init-config
uv run --locked deck3ds-ui --config config.local.json
```

L’initialisation refuse d’écraser un fichier. `config.local.json` est ignoré par Git mais **n’est pas choisi automatiquement** : gardez `--config`. Le lanceur graphique crée seulement un fichier absent, jamais un remplacement d’un fichier invalide.

## Document et écran

Le document contient les choix utilisateur : noms localisés, disposition, écran supérieur, source, boutons, intégrations et scripts. Les fenêtres et éléments générés par les extensions appartiennent à une vue séparée ; ils ne deviennent pas des boutons persistés.

Les noms d’actions abrégés et les libellés bilingues restent acceptés. L’éditeur et `GET /api/schema` authentifié sont la référence des arguments, limites et capacités réellement disponibles.

## Enregistrement

La sauvegarde valide le document, conserve les scripts de confiance, vérifie révision et empreinte disque puis remplace atomiquement le fichier. La mémoire change après réussite de l’écriture. Une console déconnectée n’annule pas l’enregistrement.

Un conflit renvoie `409 config_conflict` : rechargez et réconciliez. Un éditeur externe ne participe pas au verrou de l’agent ; évitez les écritures simultanées. Un JSON externe invalide ne remplace pas l’état valide en mémoire.

## Scripts et sessions

L’UI ne peut pas modifier `scripts`. Dans le fichier local, un utilisateur avancé peut associer un nom à un programme et ses arguments, puis utiliser `script.run`. Ne déclarez que des programmes de confiance.

```sh
uv run --locked deck3ds --config config.local.json --check
```

La session de l’éditeur change à chaque redémarrage et est distincte du secret console. Rouvrez l’éditeur depuis le menu si le lien expire. Le cache privé peut contenir le lien courant : ne le partagez pas.

Voir la [migration](MIGRATION_FASTAPI.fr.md) et le [guide HTTP](api/README.fr.md).
