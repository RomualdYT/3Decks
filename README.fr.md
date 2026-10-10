<div align="center">

<img src="docs/assets/3decks-banner.fr.svg" alt="3Decks et Decky" width="100%">

# 3Decks

**Votre Nintendo 3DS devient votre télécommande de bureau.**

[Démarrer](docs/INSTALLATION.fr.md) · [Documentation](docs/README.fr.md) · [English](README.md)

</div>

3Decks transforme une Nintendo 3DS ou 2DS équipée de homebrew en surface de
contrôle sans fil pour votre ordinateur. Créez vos pages dans l'éditeur, puis
utilisez l'écran tactile pour contrôler les applications, la musique, l'audio et OBS.

[![Voir 3Decks — Meet Decky](docs/assets/meet-decky-preview.png)](docs/assets/meet-decky.mp4)

**[▶ Voir la vidéo — Meet Decky](docs/assets/meet-decky.mp4)**

## Fonctionnalités

- Éditeur visuel avec grilles de six boutons, listes défilantes et aperçu interactif.
- Commandes musicales, pochettes et paroles synchronisées facultatives.
- Applications, raccourcis clavier et listes de fenêtres ouvertes.
- Audio, statistiques de l'ordinateur et intégration OBS WebSocket.
- Extensions natives avec actions, contenu des boutons et écrans personnalisés.
- Appairage individuel, pages sauvegardées et interfaces anglaise/française.

L'application ordinateur utilise Tauri 2, Rust et React/HeroUI ; le client console
est écrit en C. macOS et Windows disposent d'intégrations natives, dont la
disponibilité dépend du système et du lecteur. Les intégrations système Linux
sont incomplètes. Consultez la [matrice des plateformes](apps/desktop/PLATFORM_STATUS.md).

## Démarrer

Il faut une console équipée de homebrew, un ordinateur et un réseau local commun.
Suivez le guide d'[installation et d'appairage](docs/INSTALLATION.fr.md), puis
[créez votre première page](docs/USAGE.fr.md). Les paquets disponibles se trouvent
dans les [Releases GitHub](https://github.com/RomualdYT/3Decks/releases).

Pour obtenir de l'aide, signaler un bug, suivre les nouveautés ou partager des
homebrews, rejoignez [Discord](https://discord.gg/EmdnneHeus). Les deux applications
proposent aussi un QR code vers la communauté.

## Compiler depuis les sources

Installez Rust stable, Node.js 24, pnpm 11 et les dépendances système décrites dans
le [guide de contribution](docs/CONTRIBUTING.md). Depuis la racine :

```sh
cd apps/desktop/frontend
pnpm install --frozen-lockfile
cd ..
npm ci
npm run tauri -- dev
```

Pour la console, lancez `./build.sh all` avec Docker démarré. Les fichiers sont
produits dans `apps/console/deck3ds.3dsx` et `apps/console/deck3ds.cia`.
Voir le [guide de packaging console](docs/CONSOLE_PACKAGING.fr.md).

## Dépôt

| Dossier | Contenu |
| --- | --- |
| [apps/desktop](apps/desktop/README.md) | Application ordinateur et éditeur React partagé |
| [apps/console](apps/console/README.fr.md) | Application native Nintendo 3DS/2DS |
| [examples/extensions/focus](examples/extensions/focus/README.fr.md) | Extension Pomodoro complète et outil de packaging |
| [docs](docs/README.fr.md) | Guides utilisateur et références techniques |
| [resources](resources/README.md) | Sources des ressources partagées et génération |

Utilisez un réseau local de confiance : les échanges console ne sont pas chiffrés.
Les extensions approuvées s'exécutent avec les droits de votre compte.
Voir la [sécurité](docs/SECURITY.fr.md).

[GPL-3.0-or-later](LICENSE). Inter est sous
[SIL Open Font License](docs/licences/Inter-OFL.txt) ; la licence Lucide accompagne
les [icônes console](apps/console/packaging/icons/LUCIDE-LICENSE).
Projet homebrew indépendant, non affilié à Nintendo.
