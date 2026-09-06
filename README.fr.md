<div align="center">

<img src="docs/assets/3decks-banner.fr.svg" alt="3Decks et Decky, son petit compagnon pixel art à deux écrans" width="100%">

# 3Decks

**Votre Nintendo 3DS devient votre télécommande de bureau.**

<p>
<img src="https://img.shields.io/badge/plateforme-macOS%20%7C%20Windows-66CB10?style=flat-square" alt="macOS et Windows">
<img src="https://img.shields.io/badge/console-3DS%20%7C%202DS%20%7C%20New%203DS-66CB10?style=flat-square" alt="3DS, 2DS et New 3DS">
<img src="https://img.shields.io/badge/python-3.12%2B-3776AB?style=flat-square" alt="Python 3.12 minimum">
<img src="https://img.shields.io/badge/licence-GPL--3.0-F59E0B?style=flat-square" alt="Licence GPL-3.0">
</p>

Créez une surface de contrôle pour macOS et Windows, avec un éditeur visuel sur l’ordinateur et des tableaux de bord sur la console.

[Installer](docs/INSTALLATION.fr.md) · [Documentation](docs/README.fr.md) · [Extensions](docs/EXTENSIONS.fr.md) · [English](README.md)

</div>

## Deux écrans au service de votre ordinateur

- Personnalisez les pages, icônes, couleurs et raccourcis.
- Pilotez applications, fichiers, dossiers, fenêtres, volume et sorties audio.
- Contrôlez Spotify, Apple Music sur macOS et OBS ; affichez les pochettes.
- Consultez les performances et les notifications compatibles.
- Ajoutez des intégrations avec les extensions communautaires.
- Ouvrez l’éditeur, suspendez les commandes ou quittez depuis le menu système.

## Commencer

Il vous faut une **3DS, 2DS ou New 3DS avec homebrew**, un **Mac ou PC Windows** et un réseau local de confiance commun.

1. [Installez l’application ordinateur](docs/INSTALLATION.fr.md).
2. [Installez `deck3ds.cia` sur HOME](docs/CONSOLE_PACKAGING.fr.md) avec FBI (firmware personnalisé requis), ou copiez `deck3ds.3dsx` dans `sdmc:/3ds/deck3ds.3dsx` pour Homebrew Launcher.
3. Sélectionnez votre ordinateur et saisissez le code d’appairage affiché dans l’éditeur.
4. [Créez votre première page](docs/USAGE.fr.md) et enregistrez.

Les lanceurs préparent Python : **pas besoin d’installer Git, Node.js ou Python** pour utiliser une Release. Si aucun fichier de Release n’est encore disponible, utilisez le [guide de développement](docs/CONTRIBUTING_AGENT.fr.md).

## À savoir

Les fonctions disponibles dépendent de l’OS et de ses autorisations. La distribution directe GitHub ne peut pas lire les notifications Windows : une identité MSIX est nécessaire. Le packaging Store est préparé, mais aucune disponibilité sur le Store n’est annoncée ici.

Le protocole console n’est pas chiffré : n’exposez pas ses ports sur Internet. Les extensions possèdent les droits de votre compte ; n’activez que du code de confiance.

## Documentation

| Besoin | Guide |
|---|---|
| Installer, mettre à jour, désinstaller | [Installation](docs/INSTALLATION.fr.md) |
| Configurer ses pages et boutons | [Utilisation](docs/USAGE.fr.md) |
| Comprendre les fichiers et sauvegardes | [Configuration](docs/CONFIGURATION.fr.md) |
| Retrouver le menu de l’application | [Menu système](docs/DESKTOP_INTEGRATION.fr.md) |
| Résoudre un problème | [Dépannage](docs/TROUBLESHOOTING.fr.md) |
| Créer une intégration | [Extensions](docs/EXTENSIONS.fr.md) |
| Contribuer | [Développement](docs/CONTRIBUTING_AGENT.fr.md) |

[L’index complet](docs/README.fr.md) sépare les guides utilisateur, les références techniques et la qualification. L’anglais est la langue de référence ; les versions françaises sont dans des fichiers distincts.

## Licence

[GPL-3.0-only](LICENSE). Police Inter sous [SIL Open Font License](docs/licences/Inter-OFL.txt). Projet homebrew indépendant, non affilié à Nintendo.
