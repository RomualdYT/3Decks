<div align="center">

<img src="cover.png" alt="3Decks : une Nintendo 3DS pour piloter son ordinateur" width="100%">

# 3Decks

**Votre Nintendo 3DS devient votre télécommande de bureau.**

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
2. Copiez `deck3ds.3dsx` de la Release dans `sdmc:/3ds/deck3ds.3dsx`, puis lancez-le depuis Homebrew Launcher.
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
