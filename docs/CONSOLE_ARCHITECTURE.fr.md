# Architecture de la console

[Documentation](README.fr.md) · [English](CONSOLE_ARCHITECTURE.md) · [Protocole](PROTOCOL.fr.md)

## Arborescence

Les trois parties actives restent distinctes : `desktop/` pour l’application Rust/Tauri,
`frontend/` pour l’éditeur partagé et `3ds-app/` pour la console native.
Les adaptateurs PC, dont CoreAudio, appartiennent à
`desktop/src-tauri/src/platform/`. Les compilations et caches de dépendances
ne sont pas des sources à versionner.

| Dossier console | Responsabilité |
|---|---|
| `source/main.c` | Initialisation SDK, entrées, boucle de rendu et arrêt |
| `source/app/` | État, navigation, retours d’action, connexion et historique des métriques |
| `source/network/` | TCP non bloquant, découpage des messages, découverte et délais |
| `source/protocol/` | JSON, messages, décodage des extensions et modèles bornés |
| `source/ui/` | Écrans, assistant, modales, traductions et géométrie tactile |
| `source/graphics/` | Dessin, texte/cache, icônes, pochettes, stéréo et palette |
| `source/platform/` | Horloge monotone, réglages SD et son |
| `tests/` | Tests C sur ordinateur et substituts limités du SDK |

Le Makefile liste les dossiers explicitement et exclut les tests du binaire
console. Les noms de fichiers doivent rester uniques entre dossiers : les règles
devkitPro utilisent leur nom de base. Après un déplacement de sources, lancez
`./build.sh rebuild` une fois pour renouveler les dépendances générées.

## Responsabilités

Un seul fil principal reçoit les données, décode les messages puis dessine.
Les grosses structures JSON/configuration sont statiques pour préserver la
petite pile de la console.

L’assistant sépare état, interactions, écran supérieur, écran tactile et
géométrie. L’écran tactile sépare grille, liste, attente/veille, retours d’action
et encadrement. Les en-têtes internes partagent les rectangles entre dessin et
détection tactile ; ce ne sont pas des API d’extension.

Le décodage des cartes d’extensions est séparé de leur rendu. Les extensions
fournissent des données déclaratives bornées, jamais du code exécuté sur la 3DS.
Navigation et retours d’action se testent sans GPU.

## Réseau et délais

Le protocole conserve son préfixe de longueur big-endian sur quatre octets et
des charges de 1 à 65 536 octets. La destination réserve un octet supplémentaire
pour terminer la chaîne C ; une destination trop petite entraîne une erreur
explicite, jamais une troncature silencieuse.

Chaque frame autorise huit lectures au maximum, soit au plus 65 540 octets.
Un message complet est extrait avant la lecture suivante ; un tampon plein
contenant un message valide n’est pas une panne. Huit messages au maximum sont
décodés par frame. L’émission conserve huit emplacements ; chaque vidage effectue
au plus huit appels, reprend les écritures partielles et n’attend jamais une
socket saturée. Ces bornes ne promettent pas un temps de frame mesuré.

| Événement | Délai |
|---|---|
| Connexion TCP en cours | Huit secondes |
| Hello envoyé sans réponse | Huit secondes |
| Ping après appairage | Toutes les cinq secondes |
| Absence de trafic entrant décodé | Reconnexion après 15 secondes |
| Tentatives échouées | 2, 4, 8, 15 puis 30 secondes |
| Réveil de la console | Réinitialisation et tentative immédiate |
| Test dans l’assistant | 18 secondes ; une réussite ultérieure actualise le résultat |

Les délais reposent sur les ticks système, pas l’heure civile ni le delta
d’animation. Une frame lente ne repousse donc pas artificiellement les délais.
Le heartbeat détecte une liaison silencieuse ; des états valides prouvent aussi
sa disponibilité lorsqu’un pong tarde.

La découverte conserve les noms humains des ordinateurs. Le mode manuel accepte
une **adresse IPv4 numérique**, pas un nom DNS : aucune résolution synchrone ne
bloque le rendu. Une ancienne configuration utilisant un nom doit être remplacée
via la découverte ou le champ manuel. Les identifiants, ports, annonces et formats
de configuration restent inchangés.

## Texte et ressources

Le cache conserve au maximum 64 mesures et 32 libellés tronqués, pour environ
22 Kio de mémoire statique. Les clés comprennent texte UTF-8, échelle et largeur
disponible pour la troncature. Les longues entrées ne sont pas mises en cache.
Le remplacement est borné et les caches sont réinitialisés au démarrage/à l’arrêt.
Un changement de police doit aussi les réinitialiser. Aucune allocation par frame.

La troncature préserve les caractères UTF-8. Si même les points de suspension ne
tiennent pas, aucun texte n’est dessiné. Les glyphes GPU restent propres à la frame :
le cache ne conserve pas de pointeur GPU. Police, pochette et son conservent leurs
replis facultatifs ; l’échec d’une ressource de rendu obligatoire nettoie puis
arrête l’application. La découverte ferme avant le service réseau.

## Tests et qualification

Depuis la racine, lancez `bash tools/test_console.sh` sur macOS ou Linux avec un
compilateur C. Les sanitizers mémoire, comportements indéfinis et conversions
flottantes sont actifs par défaut. `SANITIZE=0` sert à un compilateur dépourvu
de ces outils, pas à remplacer le contrôle CI.

Les tests compilent le code réel : messages, transport, JSON/protocole,
extensions, navigation, géométrie, retours d’action et disposition du texte.
Le loopback utilise de vraies sockets POSIX ; seuls le SDK, l’horloge et les
effets natifs hors périmètre sont remplacés. Le runner nettoie son dossier
temporaire et le test réseau possède une limite de durée.

Cela ne simule pas les particularités SOC de libctru, le GPU, la diffusion Wi-Fi,
la batterie ni la précision tactile réelle. La compilation 3DS doit également
réussir, puis la [qualification native](QUALIFICATION.fr.md) reste nécessaire.
Consultez les [mesures de performance](PERFORMANCE.fr.md) avant d’annoncer un gain.
