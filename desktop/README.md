# 3Decks Desktop

Application de bureau Tauri 2 et Rust. Son éditeur React partagé se trouve dans `../frontend/`.

## Périmètre

- Premier démarrage guidé : accueil Decky, choix des fonctions, permissions adaptées au système et appairage 3DS. La progression reprend après fermeture ou relance ;
  les réglages peuvent rouvrir ce parcours.
- Frontend React partagé : éditeur visuel, réglages, état et
  vue Extensions chargés directement depuis `frontend/`. Le client API
  Tauri relie ces vues aux commandes Rust.
- Galerie de pages prédéfinies entièrement éditables. La page musique propose
  les paroles LRC synchronisées sur l'écran supérieur et la navigation
  temporelle sur l'écran tactile. La recherche LRCLIB est facultative et
  désactivée par défaut : [fonctionnement et essais](docs/LYRICS_AND_PAGE_TEMPLATES.md).
- Icône native, icône de zone de notification et illustrations Decky issues du
  SVG de marque existant.
- Menu natif complet : état des consoles, ouverture et connexion, pause/reprise
  des commandes, réglages rapides, démarrage automatique, diagnostic, journal,
  mises à jour et redémarrage.
- Découverte UDP sur 38122 (broadcast et multicast `239.255.77.83`).
- TCP sur 38123, trames big-endian, appairage par code puis jeton persistant.
- Édition visuelle de la configuration existante, avec validation, révision et
  diffusion des pages modifiées aux consoles connectées.
- Actions macOS : volume système et lecteur (plus, moins et valeur), muet sortie
  et micro, sorties audio, Spotify et Apple Music, ouverture et fermeture
  d'applications, liens et chemins, focalisation de fenêtres, raccourcis clavier
  incluant les touches spéciales (navigation, édition et F1–F12).
- Panneaux 3DS : volume, réglages et cadre via les indicateurs `action.result`.
- État `state.update` : volume, mode muet, micro et lecteur actif.
- Notifications macOS : lecture SQLite en lecture seule, liste dédupliquée,
  annonce d'une nouvelle notification et accès aux réglages de confidentialité.
- Pochettes Spotify/Apple Music : conversion en texture RGB565 128×128,
  transfert binaire `ART0` à la console et aperçu dans l'éditeur.
- Sorties audio macOS via CoreAudio : liste et sortie active dans `state.update`,
  sélection explicite depuis la 3DS par jeton opaque, ou dans l'éditeur de
  bureau. Sur Windows, la 3DS affiche la sortie active et renvoie vers les
  réglages Son du PC sans proposer de changement distant.
- Télémétrie CPU, mémoire, disque et débit réseau avec collecte ciblée ;
  l'intervalle et les fonctionnalités activées suivent la configuration.
- Page dynamique des fenêtres macOS via CoreGraphics, rafraîchie sur la 3DS ;
  la sélection d'une fenêtre utilise les autorisations Accessibilité macOS.
- OBS WebSocket 5 : authentification, changement de scène, bascule d'une
  source, de l'enregistrement et du stream. Test de connexion depuis la fenêtre.
- Extensions natives : paquet approuvé par empreinte, exécutable par cible,
  protocole JSON Lines borné, actions/sources/écrans et SDK Rust dans
  [`extension-sdk/`](extension-sdk/README.md).
- Démarrage avec la session, restauration de la fenêtre et vérification des
  mises à jour signées lorsque la clé publique est fournie au build.
- Verrouillage de session macOS via le raccourci système.
- Adaptateurs Windows natifs séparés sous `src-tauri/src/platform/windows/` :
  WASAPI pour volume/micro et volume des sessions du lecteur actif, MMDevice
  pour lister les sorties avec ouverture des réglages Son Windows, GSMTC pour métadonnées, commandes, position et
  miniatures média, `SendInput` pour les raccourcis, `ShellExecuteW` pour ouvrir,
  `EnumWindows`/`SetForegroundWindow` pour les fenêtres et `WM_CLOSE` pour
  demander une fermeture gracieuse. WinRT lit les notifications du centre après
  consentement et conserve localement, six heures au plus, les notifications
  déjà observées (8 entrées maximum). Ces contrôles demandent un essai réel :
  [plan de validation](docs/WINDOWS_TEST_PLAN.md).
- `ping`/`pong`, `config.request`, validation des trames, limites de connexions.

CoreAudio pilote l'audio système macOS et `NSWorkspace` ouvre les liens et fichiers. Les commandes Spotify/Music, leurs métadonnées et pochettes s'appuient sur les adaptateurs Apple Events ; les raccourcis passent par Quartz. Ces fonctions peuvent demander les autorisations Automatisation ou Accessibilité. Windows a ses propres adaptateurs natifs, mais attend une validation sur une machine Windows. Linux répond explicitement lorsque l'action est indisponible. Voir la [matrice des plateformes](PLATFORM_STATUS.md).

Windows ne documente pas d'API publique pour imposer la sortie audio globale,
donc 3Decks ouvre les paramètres Son pour ce choix. L'écoute des notifications
nécessite MSIX ou un paquetage avec identité et manifeste `userNotificationListener` ;
les installateurs MSI/NSIS actuels ne fournissent pas cette identité. Son
historique local est borné à huit entrées et six heures, et effacé si la
fonction ou son autorisation est désactivée ; les alertes émises pendant que
3Decks est fermé ne peuvent pas être récupérées après coup.

OBS est désactivé dans la configuration initiale. Pour l'utiliser, activez
`integrations.obs.enabled`, renseignez l'hôte, le port et le mot de passe,
enregistrez puis utilisez « Tester la connexion ». Les actions OBS ne sont
exécutées que lorsque cette intégration est activée.

L’application stocke sa configuration dans le répertoire de configuration Tauri. L’éditeur visuel
enregistre sa configuration dans ce fichier, incrémente la révision et envoie
les nouvelles pages aux consoles connectées. Le changement à chaud du port
est refusé explicitement ; 3Decks utilise l’appairage individuel par code et jeton.
Fermer l'éditeur détruit sa WebView tout en laissant le serveur actif ; le menu
« Ouvrir 3Decks » recrée la fenêtre. Pour démarrer directement dans la barre des
menus, définir `DECKS_START_TRAY_ONLY=1`.

## Organisation du code Rust

Le backend est découpé entre `app/`, `transport/`, `features/` et `platform/`.
Le dossier `platform/` isole les fournisseurs macOS, Windows et Linux ;
`features/` porte les services transversaux (paroles, OBS, extensions,
notifications) et `transport/` contient le protocole 3DS.
Les notifications séparent la lecture macOS, l'accès WinRT et l'historique
SQLite Windows dans `features/notifications/` et `platform/windows/`.

La fenêtre de l’éditeur s’adapte à l’écran (jusqu’à 1440 × 900, minimum
980 × 700), puis retrouve sa taille et sa position après fermeture, y compris lorsqu’elle reste active
dans la barre de menus. Sur macOS, la barre de titre native recouvre l’en-tête
de l’application : les trois boutons de fenêtre restent ceux du système.
Windows et Linux conservent leurs décorations natives.

## Développement

Pré-requis : Rust, Node.js, dépendances système [Tauri 2](https://v2.tauri.app/start/prerequisites/).

```bash
cd frontend && pnpm install --frozen-lockfile
cd ../desktop && npm ci
npm run tauri -- dev
```

Une seule instance du serveur peut utiliser les ports par défaut à la fois.
Pour utiliser des ports de développement distincts :

```bash
DECKS_TCP_PORT=48123 DECKS_DISCOVERY_PORT=48122 npm run tauri -- dev
```

La découverte automatique de la 3DS continue de viser UDP 38122 ; avec ces
ports alternatifs, utilisez son réglage manuel d'adresse et de port, ou un
client de test local.

Pour un test automatisé local du handshake, un build **debug seulement** accepte
`DECKS_TEST_PAIR_CODE=123456`. Cette variable est ignorée par le build
release ; après un appairage réussi, le code est renouvelé aléatoirement.
À l'ouverture, le code à six chiffres apparaît dans la fenêtre. Saisissez-le
sur la 3DS. Après l'appairage, la console reçoit un jeton propre à cette
installation ; seuls son empreinte et son nom sont enregistrés dans le
répertoire de configuration de l'application.

```bash
npm run build
npm run tauri -- build
```

Le catalogue d’actions embarqué se trouve dans `desktop/catalog.json`. Modifiez-le avec les actions natives correspondantes et vérifiez la cohérence de l’éditeur.

La construction locale ne signe pas une distribution publique. La [chaîne de release](../docs/RELEASE.md) exige des signatures et une qualification sur les OS distribués.

## Vérification du transport

`cargo test --manifest-path src-tauri/Cargo.toml` vérifie le codec, la
configuration et la validation des raccourcis. Une vraie 3DS doit vérifier la
découverte, le code d'appairage, la reconnexion avec jeton, les pages importées,
les actions, les pings et le maintien de la connexion après fermeture de la
fenêtre.
