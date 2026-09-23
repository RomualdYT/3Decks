# 3Decks Desktop PoC

Prototype Tauri 2 autonome, développé à côté de `agent/`. Il ne modifie ni le
backend Python ni l'application 3DS.

## Périmètre

- Premier démarrage guidé : accueil Decky, choix des fonctions, permissions
  macOS et appairage 3DS. La progression reprend après fermeture ou relance ;
  les réglages peuvent rouvrir ce parcours.
- Même frontend React que l’agent Python : éditeur visuel, réglages, état et
  vue Extensions chargés directement depuis `agent/frontend`. Le client API
  Tauri redirige ces vues vers les commandes Rust sans lancer Python.
- Icône native, icône de zone de notification et illustrations Decky issues du
  SVG de marque existant.
- Découverte UDP sur 38122 (broadcast et multicast `239.255.77.83`).
- TCP sur 38123, trames big-endian, appairage par code puis jeton persistant.
- Édition visuelle de la configuration existante, avec validation, révision et
  diffusion des pages modifiées aux consoles connectées.
- Actions macOS : volume système et lecteur (plus, moins et valeur), muet sortie
  et micro, sorties audio, Spotify et Apple Music, ouverture et fermeture
  d'applications, liens et chemins, focalisation de fenêtres, raccourcis clavier.
- Panneaux 3DS : volume, réglages et cadre via les indicateurs `action.result`.
- État `state.update` : volume, mode muet, micro et lecteur actif.
- Notifications macOS : lecture SQLite en lecture seule, liste dédupliquée,
  annonce d'une nouvelle notification et accès aux réglages de confidentialité.
- Pochettes Spotify/Apple Music : conversion en texture RGB565 128×128,
  transfert binaire `ART0` à la console et aperçu dans l'éditeur.
- Sorties audio macOS via CoreAudio : liste et sortie active dans `state.update`,
  actions `audio_output.cycle` et `audio_output.set` depuis la 3DS, sélection
  manuelle dans la fenêtre de diagnostic.
- Télémétrie CPU, mémoire, disque et débit réseau avec collecte ciblée ;
  l'intervalle et les fonctionnalités activées suivent la configuration.
- Page dynamique des fenêtres macOS via CoreGraphics, rafraîchie sur la 3DS ;
  la sélection d'une fenêtre utilise les autorisations Accessibilité macOS.
- OBS WebSocket 5 : authentification, changement de scène, bascule d'une
  source, de l'enregistrement et du stream. Test de connexion depuis la fenêtre.
- Extensions natives : paquet approuvé par empreinte, exécutable par cible,
  protocole JSON Lines borné, actions/sources/écrans et SDK Rust dans
  [`extension-sdk/`](extension-sdk/README.md). Aucun runtime Python dans l'app.
- Démarrage avec la session, restauration de la fenêtre et vérification des
  mises à jour signées lorsque la clé publique est fournie au build.
- Verrouillage de session macOS via le raccourci système.
- Première couche Windows native : volume et micro WASAPI, touches multimédia
  et raccourcis via `SendInput`, ouverture via `ShellExecuteW`, fenêtres via
  `EnumWindows`/`SetForegroundWindow` et verrouillage via `LockWorkStation`.
  Les contrôles Windows demandent encore un essai réel.
- `ping`/`pong`, `config.request`, validation des trames, limites de connexions.

Ce n'est pas encore un remplacement de l'agent Python. CoreAudio pilote
désormais l'audio système macOS et `NSWorkspace` ouvre les liens/fichiers et
gère les applications. Les commandes Spotify/Music, les raccourcis et le
verrouillage macOS utilisent encore AppleScript et peuvent demander une
autorisation Automatisation ou Accessibilité. Windows annonce seulement les
actions intégrées dans son adaptateur ; Linux répond explicitement lorsque
l'action est indisponible. Voir la [matrice des plateformes](PLATFORM_STATUS.md)
avant d'évaluer la parité fonctionnelle.

OBS est désactivé dans la configuration initiale. Pour l'utiliser, activez
`integrations.obs.enabled`, renseignez l'hôte, le port et le mot de passe,
enregistrez puis utilisez « Tester la connexion ». Les actions OBS ne sont
exécutées que lorsque cette intégration est activée.

Le PoC possède son propre fichier de configuration dans le répertoire de
configuration Tauri. Il n'écrit pas dans `agent/config.json`. L’éditeur visuel
enregistre sa configuration dans ce fichier, incrémente la révision et envoie
les nouvelles pages aux consoles connectées. Le secret partagé de l’ancien
agent et le changement à chaud du port sont refusés explicitement ; le PoC
utilise l’appairage individuel par code et jeton.
Fermer l'éditeur détruit sa WebView tout en laissant le serveur actif ; le menu
« Ouvrir 3Decks » recrée la fenêtre. Pour démarrer directement dans la barre des
menus, définir `DECKS_POC_START_TRAY_ONLY=1`.

## Organisation du code Rust

Le backend est découpé entre `app/`, `transport/`, `features/` et `platform/`.
Voir [src-tauri/src/README.md](src-tauri/src/README.md) pour les responsabilités
et la façon d’ajouter un fournisseur Windows ou Linux.

La fenêtre de l’éditeur s’adapte à l’écran (jusqu’à 1440 × 900, minimum
980 × 700), puis retrouve sa taille et sa position après fermeture, y compris lorsqu’elle reste active
dans la barre de menus. Sur macOS, la barre de titre native recouvre l’en-tête
de l’application : les trois boutons de fenêtre restent ceux du système.
Windows et Linux conservent leurs décorations natives.

## Développement

Pré-requis : Rust, Node.js, dépendances système [Tauri 2](https://v2.tauri.app/start/prerequisites/).

```bash
cd desktop-poc
npm install
cd ../agent && pnpm install --frozen-lockfile && cd ../desktop-poc
npm run tauri dev
```

Sur les ports par défaut, l'agent Python doit être arrêté : les deux serveurs
utilisent les mêmes ports.
Pour lancer le PoC en parallèle du serveur Python pendant le développement :

```bash
DECKS_POC_TCP_PORT=48123 DECKS_POC_DISCOVERY_PORT=48122 npm run tauri dev
```

La découverte automatique de la 3DS continue de viser UDP 38122 ; avec ces
ports alternatifs, utilisez son réglage manuel d'adresse et de port, ou un
client de test local.

Pour un test automatisé local du handshake, un build **debug seulement** accepte
`DECKS_POC_TEST_PAIR_CODE=123456`. Cette variable est ignorée par le build
release ; après un appairage réussi, le code est renouvelé aléatoirement.
À l'ouverture, le code à six chiffres apparaît dans la fenêtre. Saisissez-le
sur la 3DS. Après l'appairage, la console reçoit un jeton propre à cette
installation ; seuls son empreinte et son nom sont enregistrés dans le
répertoire de configuration de l'application.

```bash
npm run build
npm run tauri build
```

Le catalogue de l’éditeur dans `desktop-poc/catalog.json` est exporté du
catalogue Python existant. Régénérez-le après une modification du catalogue
pour garder la liste d’actions à jour.

La construction locale ne signe pas une distribution publique. Une version
publiable nécessitera signature/notarisation macOS, tests sur les trois OS,
gestion des mises à jour et migration des données Python.

## Vérification du transport

`cargo test --manifest-path src-tauri/Cargo.toml` vérifie le codec, la
configuration et la validation des raccourcis. Une vraie 3DS doit vérifier la
découverte, le code d'appairage, la reconnexion avec jeton, les pages importées,
les actions, les pings et le maintien de la connexion après fermeture de la
fenêtre.
