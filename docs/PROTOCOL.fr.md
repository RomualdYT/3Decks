# Protocole console 1

[Documentation](README.fr.md) · [English](PROTOCOL.md) · [Extensions](EXTENSIONS.fr.md)

Contrat PC–3DS, implémenté dans `apps/desktop/src-tauri/src/transport/` et
`apps/console/source/protocol/`. Les versions et noms d'hôte des exemples sont illustratifs.

## Transport et découverte

L'ordinateur écoute par défaut sur TCP `0.0.0.0:38123`. Ce canal utilise des
trames TCP sans HTTP, WebSocket ni TLS, sur un réseau local de confiance.

La console diffuse sur UDP **38122** :

```json
{"type":"deck3ds.discover","protocol":1,"nonce":42}
```

L'ordinateur répond à l'adresse source :

```json
{"type":"deck3ds.agent","protocol":1,"name":"3Decks","platform":"macos","port":38123,"version":"1.0.0","pairing_required":true,"nonce":42}
```

La console utilise l'adresse source du datagramme, pas une IP dans le JSON.
La saisie manuelle IPv4/port reste disponible.

## Trames

Un préfixe de **quatre octets big-endian** contient la longueur de la charge
utile, sans l'en-tête. Limite : **65 536 octets**. Une trame trop grande est
refusée ; les lectures/écritures partielles doivent être prises en charge.

La charge est un objet JSON UTF-8 sans retour à la ligne obligatoire. La pochette
binaire est l'exception décrite plus bas. La console utilise des tampons et une
file d'émission bornés, sans attente bloquante.

## Session et appairage

La console envoie `hello` ; l'ordinateur répond `hello.ok`, puis `config.snapshot`
et `state.update`. Les commandes reçoivent des résultats d'action. Des ping/pong
surveillent la liaison ; la reconnexion suit des délais de 2, 4, 8, 15 et 30 secondes.

```json
{"type":"hello","protocol":1,"device":"new3dsxl","language":"fr","token":"identifiant-sauvegarde"}
```

Une nouvelle console transmet `pair_code` avec le code local à six chiffres à
la place du jeton. Un code valide est consommé et fournit un jeton individuel :

```json
{"type":"hello.ok","protocol":1,"agent":"1.0.0","host":"3Decks","platform":"macos","token":"nouvel-identifiant-individuel"}
```

Le champ `token` n'est fourni qu'après appairage. L'ordinateur conserve son
empreinte SHA-256 dans `paired-consoles.json`. La révocation ferme les connexions
correspondantes. Un identifiant invalide reçoit `hello.error` avec
`code:"pairing_required"`, puis la connexion ferme.

Le handshake entier a un délai de cinq secondes, même fragmenté. Limites :
16 clients en attente et huit authentifiés ; une surcharge peut recevoir
`server_busy`. Les échecs de code sont limités à cinq par adresse et 30 au total
sur une minute ; le dépassement reçoit `pairing_rate_limited`.

## Requêtes console

| Type | Champs | Rôle |
| --- | --- | --- |
| `button.press` | `id`, `page`, `button`, `hold` facultatif | Action principale ou secondaire configurée |
| `value.set` | `id`, `target`, `value` | Volume système/lecteur, entier de 0 à 100 |
| `audio.output.select` | `id`, `output` | Sortie annoncée en mode `direct` |
| `config.request` | `id` | Dernière disposition |
| `ping` | `id` | Réponse `pong` corrélée |

```json
{"type":"button.press","id":7,"page":"main","button":"mic-toggle","hold":false}
{"type":"value.set","id":8,"target":"volume","value":50}
{"type":"audio.output.select","id":9,"output":"0123456789abcdef0123456789abcdef"}
```

Les identifiants des mutations augmentent dans une même connexion, toutes
commandes confondues. Un doublon ou identifiant ancien est refusé. Ce contrôle
recommence à chaque connexion ; ce n'est pas une protection cryptographique.
La pause des commandes refuse les mutations et conserve la liaison et les états.

La page réservée `__direct` accepte uniquement `audio_output.cycle`,
`volume.mute_toggle`, `mic.mute_toggle`, `volume.up` et `volume.down`.
Les autres actions sont résolues depuis la configuration ordinateur, sans
commande exécutable fournie par la console. Leur disponibilité et leurs arguments
viennent du catalogue dynamique (`get_catalog` côté Tauri).

## Configuration

```json
{"type":"config.snapshot","revision":4,"pages":[
 {"id":"main","title":"Principal","icon":"star","dashboard":"auto","layout":"grid",
  "buttons":[{"id":"mic-toggle","slot":0,"label":"Micro","icon":"mic","color":"#66CB10","toggle":"mic_muted","hold_label":"Secondaire"}]}
]}
```

L'instantané remplace la disposition. Il transmet des libellés et identifiants,
jamais les chemins, URL ou commandes privées des actions.

| Champ de page | Valeurs |
| --- | --- |
| `id`, `title`, `icon` | Identité et onglet ; traduction résolue par console |
| `dashboard` | `auto`, `media`, `lyrics`, `system`, `apps`, `audio`, `frame`, `notifications`, `stream_chat`, `extension` |
| `layout` | `grid` ou `list` |
| `buttons` | Six positions au maximum, `slot` de 0 à 5 |
| `entries` | Jusqu'à 32 lignes ordonnées |

Un bouton utilise `id`, `slot`, `label`, `icon`, `color` au format `#RRGGBB`,
et éventuellement `toggle` et `hold_label`. Un élément de liste utilise `id`,
`label`, `detail`, `icon`, `color`, `active`. Plusieurs éléments peuvent être actifs.
Les appuis utilisent le même message dans les deux dispositions.

Limites : 12 pages ; libellé 24, détail de liste 40 et identifiant 32 **octets
UTF-8**. Les textes d'extension sont tronqués aux frontières des caractères. Les listes
peuvent être réduites pour respecter le budget de trame.

Icônes : `mic`, `mic-off`, `volume-up`, `volume-down`, `volume-mute`, `play`,
`pause`, `next`, `previous`, `app`, `browser`, `terminal`, `folder`, `music`,
`chat`, `video`, `record`, `lock`, `page`, `power`, `gear`, `star`, `bell`, `status`, `artwork`.
Un nom inconnu utilise l'icône d'application générique.

## États et résultats

`state.update` est un patch : un champ absent conserve l'état précédent.
Il comprend audio/micro, applications, métadonnées/progression musicales,
notifications et mesures disponibles.

Les sorties utilisent `audio_output`, `audio_output_mode` (`direct`, `host_only`,
`unavailable`), `audio_output_count` et jusqu'à 12 `audio_output_options` avec
`id`, `name`, `active`. Le jeton opaque de 32 caractères est résolu sur une liste
actualisée avant sélection. Windows utilise `host_only` : le choix se fait dans
les réglages Son de l'ordinateur.

Mesures : `cpu`, `memory`, `memory_used_mb`, `memory_total_mb`, `disk`,
`disk_free_mb`, `disk_total_mb`, `network_down_kbps`, `network_up_kbps`,
`top_process`, `top_process_cpu`, `gpu` et `temperature` facultatifs.
Mémoire/stockage en Mio, réseau en kilobits/seconde, température en °C.
Une mesure absente est indisponible, pas une valeur zéro.

```json
{"type":"action.result","id":7,"ok":true,"message":"Micro coupé"}
{"type":"action.result","id":8,"ok":false,"message":"Lecteur indisponible"}
{"type":"pong","id":10}
```

Les résultats pilotent attente/succès/erreur. Des champs facultatifs peuvent aussi
demander l'ouverture d'une page, d'un panneau ou des réglages console.

## Chat de stream

L’objet facultatif `stream_chat` de `state.update` contient `provider` (`twitch`),
`channel`, `status`, `timestamps`, `compact` et au plus 20 `messages`. Un message
contient `id` (64 octets UTF-8), `user_id` (32), `author` (48), `text` (256),
`color` (`#RRGGBB`), `time` (`HH:MM`, UTC) et `badges` (jusqu’à trois objets : `token` positif sur 31 bits, `title` et URL `image` du CDN officiel). Cet objet
remplace l’historique précédent, y compris ses suppressions. Aucun identifiant
d’authentification n’y figure. Le mode d’écran est `stream_chat`.

### Images des badges Twitch

Une trame binaire `BDG0` utilise le même préfixe de longueur que le JSON et les
pochettes. Son en-tête de 12 octets contient la signature, la largeur et la
hauteur little-endian (16 chacune), puis le jeton du badge (`u32`). Les 1 024
octets suivants contiennent les pixels RGBA8 en tuiles, ordre ABGR du PICA200.
L’ordinateur envoie les images avant les historiques, une seule fois par séjour
dans le cache FIFO de 64 badges de la console. `badge_revision` déclenche leur
envoi après un téléchargement asynchrone. Les images indisponibles sont omises
sans bloquer les messages. Aucun jeton OAuth n’est transmis.


## Paroles synchronisées

```json
{"type":"media.lyrics","status":"ready","track":"Exemple","artist":"Artiste","duration_ms":180000,"lines":[{"t":1200,"text":"Première ligne"}]}
```

`t` et `duration_ms` sont en millisecondes. Le message remplace les paroles ;
`lines:[]` les efface. États : `idle`, `loading`, `ready`, `disabled`,
`unavailable`, `unsynced`, `instrumental`, `error`, `too_large`.
Limites : 256 lignes de 120 octets UTF-8 dans la trame de 64 Kio.
Position et état de lecture viennent de `state.update`.

## Pochette binaire

Une charge préfixée par longueur commence par ASCII `ART0`, puis largeur
(deux octets little-endian), hauteur (deux), jeton (quatre) et pixels.
Largeur/hauteur : 128. Pixels : RGB565 little-endian en tuiles 8 × 8, ordre Morton.
Le jeton est référencé par `media.art` et évite les retransmissions identiques.
La console peut téléverser cette texture sans conversion.

## Affichage des extensions

Les exécutables utilisent le [protocole stdio du SDK](../apps/desktop/extension-sdk/README.md),
pas le socket console. Les boutons utilisent les tableaux habituels ; un écran
d'extension reçoit `dashboard:"extension"`.

```json
{"type":"state.update","extension_panels":[
 {"page":"focus","title":"Focus","status":"ok","cards":[{"label":"Temps restant","value":"24:12","detail":"Session","progress":4}]}
],"extension_buttons":[{"page":"focus","id":"start","active":true,"available":true}]}
```

Ces tableaux remplacent leur contenu précédent ; un tableau vide l'efface.
Limites : 12 panneaux, quatre cartes/panneau, 72 états de boutons ; titre 64,
libellé 24, valeur 40, détail 64 octets UTF-8. La traduction est résolue par
console. Progression facultative de 0 à 100 ; statut `neutral`, `ok`, `warning`,
`error`. Le parseur dispose de 8 192 jetons JSON et de 65 536 octets par trame.
Un ancien client doit être mis à jour pour afficher les nouveaux panneaux.
Aucun code d'extension n'est téléchargé sur la console.

## Réseau de confiance

Un observateur réseau peut lire l'appairage et les identifiants. Les limites,
listes d'actions et identifiants croissants ne sécurisent pas un réseau hostile.
Voir la [sécurité](SECURITY.fr.md).
