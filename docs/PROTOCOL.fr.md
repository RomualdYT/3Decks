# Protocole 3Decks v1

[Documentation](README.fr.md) · [English](PROTOCOL.md)

Les valeurs de version et les noms d’hôte des exemples sont fictifs.

Contrat de communication entre l'application 3DS (client) et l'agent PC (serveur).

## Transport

TCP, connexion persistante, l'agent écoute (par défaut `0.0.0.0:38123`), la 3DS se connecte.

Pas de HTTP, pas de WebSocket, pas de TLS. Le choix est délibéré : la 3DS n'a
alors besoin d'aucune bibliothèque externe et le framing reste trivial à
implémenter sans allocation dynamique.

### Découverte locale

Avant la connexion TCP, la 3DS diffuse sur UDP `38122` :

```json
{ "type": "deck3ds.discover", "protocol": 1, "nonce": 42 }
```

Chaque agent compatible répond directement à l'adresse source :

```json
{
  "type": "deck3ds.agent",
  "protocol": 1,
  "name": "Mac du bureau",
  "platform": "macos",
  "port": 38123,
  "version": "1.0.0",
  "pairing_required": true,
  "nonce": 42
}
```

L'adresse IP n'est volontairement pas placée dans le JSON : la console utilise
l'adresse source du datagramme, qui correspond à l'interface réellement
joignable. La saisie manuelle reste disponible si les broadcasts sont filtrés.

### Framing

Chaque message est précédé de sa taille sur 4 octets, big-endian (ordre réseau) :

```
+----------------+--------------------------+
| length (4, BE) | payload JSON (UTF-8)     |
+----------------+--------------------------+
```

- `length` ne compte que le payload, pas l'en-tête.
- Taille maximale d'un message : **65536 octets**. Au-delà, le pair doit fermer
  la connexion plutôt que tenter de lire (protection mémoire côté 3DS).
- Le payload est un objet JSON. Aucun retour à la ligne n'est requis.

Le framing par longueur est préféré au JSON Lines parce qu'il évite tout
échappement de `\n` et permet de savoir à l'avance combien d'octets lire, ce qui
simplifie une lecture non bloquante avec un tampon de taille fixe.

## Cycle de vie

```
3DS                                     Agent
 |                                        |
 |------------- hello ------------------->|
 |<------------ hello.ok ---------------- |
 |<------------ config.snapshot --------- |
 |<------------ state.update ------------ |
 |                                        |
 |------------- button.press ------------>|
 |<------------ action.result ----------- |
 |<------------ state.update ------------ |
 |                                        |
 |------------- ping ------------------->|
 |<------------ pong ------------------- |
```

L'agent envoie `config.snapshot` puis `state.update` spontanément après le
handshake, sans que la 3DS ait à les demander.

## Messages 3DS vers agent

### `hello`

Premier message obligatoire après connexion.

```json
{
  "type": "hello",
  "protocol": 1,
  "device": "new3dsxl",
  "token": "optionnel",
  "pair_code": "optionnel, six chiffres"
}
```

Si l'agent est configuré avec un token et que celui fourni ne correspond à
aucune console connue, il accepte à la place le code court visible dans son
interface locale. Un code valide est consommé immédiatement ; `hello.ok`
renvoie alors une seule fois un secret propre à cette console, que celle-ci
stocke sur sa carte SD. L'agent ne conserve que son empreinte SHA-256 dans
`paired-consoles.json`, à côté de la configuration. Chaque console peut ainsi
être révoquée sans déconnecter les autres. Un ancien jeton partagé reste accepté
une fois et est automatiquement remplacé par une identité individuelle. Sinon l'agent répond
`hello.error` avec `code: "pairing_required"` puis ferme la connexion.

Le handshake complet doit parvenir dans les cinq secondes, même si la trame est
fragmentée. L'agent conserve au plus 16 handshakes en attente et huit consoles
authentifiées ; une admission au-delà de ces bornes reçoit `hello.error` avec
`code: "server_busy"`. Les échecs de code court sont limités sur une fenêtre
d'une minute à cinq par adresse source et 30 au total.

### `button.press`

```json
{
  "type": "button.press",
  "id": 7,
  "page": "main",
  "button": "mic-toggle",
  "hold": false
}
```

- `id` : entier croissant choisi par la 3DS, corrélé dans `action.result`.
- `hold` : `true` pour un appui long (action secondaire du bouton).

Pour les messages qui modifient l'état (`button.press`, `value.set` et
`audio.output.select`), un `id`
déjà vu ou inférieur au précédent est refusé dans la même connexion. Cette
protection évite un double effet après duplication d'une trame ; elle redémarre
à chaque nouvelle connexion et ne constitue pas une authentification
cryptographique.

### `value.set`

Les curseurs envoient une valeur entière de 0 à 100 pour `volume` ou `app_volume` :

```json
{"type":"value.set","id":8,"target":"volume","value":50}
```

Le résultat utilise `action.result`. Les mêmes contrôles de monotonie et de pause que pour les boutons s’appliquent.

### `audio.output.select`

La 3DS choisit une sortie annoncée par l'agent lorsque `audio_output_mode`
vaut `direct` :

```json
{"type":"audio.output.select","id":9,"output":"0123456789abcdef0123456789abcdef"}
```

`output` est un jeton opaque de 32 caractères, pas un nom potentiellement
dupliqué. L'agent vérifie l'identifiant sur la liste actualisée avant de
changer la sortie et répond par `action.result`.

### `config.request`

Demande explicite de renvoi de la configuration.

```json
{ "type": "config.request", "id": 3 }
```

### `ping`

```json
{ "type": "ping", "id": 12 }
```

## Messages agent vers 3DS

### `hello.ok`

```json
{
  "type": "hello.ok",
  "protocol": 1,
  "agent": "1.0.0",
  "host": "MacBook-Pro",
  "platform": "darwin",
  "token": "secret individuel, présent uniquement après appairage ou échange du jeton d’amorçage"
}
```

### `hello.error`

```json
{
  "type": "hello.error",
  "reason": "jeton invalide, appairage requis",
  "code": "pairing_required"
}
```

### `config.snapshot`

Décrit l'intégralité de l'interface. La 3DS reconstruit son UI à sa réception.

```json
{
  "type": "config.snapshot",
  "revision": 4,
  "pages": [
    {
      "id": "main",
      "title": "Principal",
      "dashboard": "auto",
      "buttons": [
        {
          "id": "mic-toggle",
          "slot": 0,
          "label": "Micro",
          "icon": "mic",
          "color": "#3B82F6",
          "toggle": "mic_muted",
          "hold_label": "Périphériques"
        }
      ]
    }
  ]
}
```

Champs d'une page :

| Champ | Type | Rôle |
|---|---|---|
| `id` | string | Identifiant, référencé par `page.open` |
| `title` | string | Affiché sur la barre et le dashboard |
| `icon` | string | Icône de l'onglet |
| `dashboard` | string | `auto`, `media`, `system`, `apps`, `audio` ou `frame` |
| `layout` | string | `grid` (défaut) ou `list` |
| `buttons` | array | 6 maximum, pour `layout: grid` |
| `entries` | array | Jusqu'à 32 éléments, pour `layout: list` |

### Pages en mode liste

La grille convient à des actions fixes, mais pas à un contenu dont la longueur
varie : au-delà de six éléments, le reste devient inaccessible. Une page peut
donc adopter une présentation en liste défilante.

```json
{
  "id": "windows",
  "title": "Windows",
  "icon": "app",
  "layout": "list",
  "entries": [
    {
      "id": "win-0",
      "label": "Safari",
      "detail": "Personnel — Deck3DS",
      "icon": "browser",
      "color": "#3B82F6",
      "active": true
    }
  ]
}
```

Champs d'un élément de liste :

| Champ | Type | Rôle |
|---|---|---|
| `id` | string | Renvoyé dans `button.press` |
| `label` | string | Ligne principale, 24 caractères maximum |
| `detail` | string | Ligne secondaire, 40 caractères maximum |
| `icon` | string | Icône affichée à gauche |
| `color` | string | Accent `#RRGGBB` |
| `active` | bool | Élément mis en évidence, un seul par liste |

L'ordre du tableau est significatif : il est conservé tel quel par la console.
Pour les fenêtres, l'agent le fait correspondre à l'ordre d'empilement, donc à
l'usage le plus récent.

Les appuis sur un élément de liste utilisent le même message `button.press` que
la grille : la console n'a pas à distinguer les deux cas.

Champs d'un bouton :

| Champ | Type | Rôle |
|---|---|---|
| `id` | string | Identifiant, renvoyé dans `button.press` |
| `slot` | int | Position 0..5 dans la grille |
| `label` | string | Texte affiché |
| `icon` | string | Nom d'icône vectorielle (voir liste) |
| `color` | string | Accent `#RRGGBB` |
| `toggle` | string | Clé d'état pilotant l'apparence active |
| `hold_label` | string | Indice d'action longue, optionnel |

Icônes disponibles : `mic`, `mic-off`, `volume-up`, `volume-down`, `volume-mute`,
`play`, `pause`, `next`, `previous`, `app`, `browser`, `terminal`, `folder`,
`music`, `chat`, `video`, `record`, `lock`, `page`, `power`, `gear`, `star`.

La 3DS impose ces limites et rejette proprement ce qui dépasse :

- 12 pages
- 6 boutons par page
- 24 caractères par label
- 32 caractères par identifiant

### `state.update`

Envoyé à chaque changement pertinent. Tous les champs sont optionnels : c'est un
patch, la 3DS conserve les valeurs qu'elle possède déjà.

```json
{
  "type": "state.update",
  "volume": 63,
  "muted": false,
  "mic_muted": true,
  "media": {
    "title": "Nom du morceau",
    "artist": "Artiste",
    "app": "Spotify",
    "playing": true
  },
  "active_app": "Safari",
  "apps": ["Safari", "Spotify", "Terminal"],
  "cpu": 24,
  "memory": 51,
  "memory_used_mb": 8350,
  "memory_total_mb": 16384,
  "disk": 72,
  "disk_free_mb": 138420,
  "disk_total_mb": 500000,
  "network_down_kbps": 18400,
  "network_up_kbps": 1250,
  "top_process": "Blender",
  "top_process_cpu": 38,
  "gpu": 61,
  "temperature": 68,
  "time": "14:32",
  "date": "22 août"
}
```

`time` et `date` viennent du PC pour garantir la cohérence avec l'affichage de
l'ordinateur, mais la 3DS utilise son horloge interne en repli si le champ est
absent ou la connexion perdue.

Pour les sorties audio, l'agent fournit `audio_output` (nom de la sortie
active), `audio_output_mode` (`direct`, `host_only` ou `unavailable`),
`audio_output_count` (nombre total) et `audio_output_options` (jusqu'à 12 objets
`{id,name,active}`). Sur Windows, le mode `host_only` affiche la sortie active
sans proposer une sélection distante : celle-ci se fait dans les réglages Son
du PC.

Les mesures de performances enrichies sont elles aussi facultatives. Les
volumes mémoire et disque sont exprimés en mébioctets ; les débits réseau en
kilobits par seconde ; la température en degrés Celsius. `gpu` et
`temperature` peuvent rester absents lorsque le pilote ou le système ne les
expose pas. La console adapte alors sa quatrième carte au stockage, sans
afficher de valeur inventée.

### `action.result`

```json
{
  "type": "action.result",
  "id": 7,
  "ok": true,
  "message": "Micro coupé"
}
```

En cas d'échec :

```json
{
  "type": "action.result",
  "id": 7,
  "ok": false,
  "message": "Spotify introuvable"
}
```

Le message est affiché en notification sur l'écran supérieur. Un échec doit
toujours être explicite : un bouton ne doit jamais sembler fonctionner sans
effet.

### `pong`

```json
{ "type": "pong", "id": 12 }
```

### `art` — pochette d'album

La pochette est le seul message binaire du protocole. Elle est transmise comme
une trame ordinaire, mais son contenu n'est pas du JSON : la charge utile
commence par la signature ASCII `ART0`, suivie d'un en-tête puis des pixels.

```
+--------+--------+--------+--------+---------------------------+
| "ART0" | width  | height | token  | pixels RGB565 swizzlés    |
| 4 o.   | 2 o.   | 2 o.   | 4 o.   | width*height*2 octets     |
+--------+--------+--------+--------+---------------------------+
```

Les entiers sont en little-endian. La 3DS reconnaît une pochette au préfixe
`ART0` et n'essaie donc jamais de l'analyser comme du JSON.

- `width` et `height` valent 128. La console refuse toute autre dimension.
- `token` identifie la pochette. L'agent ne renvoie l'image que lorsque ce
  jeton change, ce qui évite de retransmettre 32 Ko à chaque rafraîchissement.

Les pixels sont déjà au format attendu par le processeur graphique de la
console : RGB565 little-endian, réorganisés en tuiles de 8 × 8 selon l'ordre de
Morton, l'index dans la tuile valant `interleave(x, y)`. Ce format a été
vérifié en comparant la sortie de `tex3ds` sur une image témoin. La console peut
donc téléverser le bloc tel quel, sans aucune conversion.

Le champ `media.art` de `state.update` contient le jeton de la pochette
courante, ou est absent s'il n'y en a pas. La console peut ainsi savoir qu'une
image va arriver, et afficher un substitut en attendant.

## Actions

Les actions ne sont jamais des commandes shell arbitraires envoyées par la 3DS.
La 3DS envoie un identifiant de bouton ; l'agent seul décide quoi exécuter, en
consultant sa configuration locale.

Le pseudo-identifiant de page `__direct` est réservé aux panneaux natifs codés
dans l'application 3DS. Il n'autorise que `audio_output.cycle`,
`volume.mute_toggle` et `mic.mute_toggle`. Toutes les autres actions, même
connues du catalogue, doivent être résolues depuis un bouton configuré.

Les arguments natifs sont validés depuis le catalogue commun avant installation
de la configuration : aucun champ supplémentaire n'est toléré, les types et
bounds numériques sont stricts et `url.open` n'accepte que HTTP(S).

Actions reconnues dans `config.json` côté agent :

| Action | Arguments | Effet |
|---|---|---|
| `volume.up` | `step` | Augmente le volume |
| `volume.down` | `step` | Diminue le volume |
| `volume.set` | `value` | Fixe le volume |
| `volume.mute_toggle` | — | Bascule la sortie audio |
| `mic.mute_toggle` | — | Bascule le micro |
| `mic.mute` / `mic.unmute` | — | Force l'état du micro |
| `media.play_pause` | — | Lecture/pause |
| `media.next` / `media.previous` | — | Piste suivante/précédente |
| `app.launch` | `target` | Lance/active une application |
| `app.quit` | `target` | Quitte une application |
| `url.open` | `url` | Ouvre une URL |
| `path.open` | `path` | Ouvre un fichier ou dossier |
| `hotkey` | `keys` | Envoie un raccourci clavier |
| `script.run` | `script` | Exécute un script déclaré dans la config |
| `page.open` | `page` | Change de page (traité côté 3DS) |
| `system.lock` | — | Verrouille la session |

Les résultats peuvent également demander une navigation ou l’ouverture des
réglages/panneaux natifs. Les identifiants d’actions et arguments exhaustifs
viennent du catalogue dynamique `/api/schema`, pas de cette liste illustrative.

## Robustesse

### Extensions (champs facultatifs, protocole 1)

Le [guide français des extensions](EXTENSIONS.fr.md) accompagne le
[contrat complet anglais](EXTENSIONS.md).
Ces programmes s'exécutent sur le PC via stdio ; ils ne parlent pas directement
au socket 3DS. Les commandes et paramètres privés ne sont jamais transmis.

Une page utilisant un écran d'extension reçoit `"dashboard":"extension"`.
Les pages alimentées par une extension utilisent les tableaux `buttons`/`entries`
existants. Leurs actions sont exécutées côté agent depuis les identifiants reçus.

`state.update` peut inclure les tableaux suivants (remplacement complet quand
présents ; tableaux vides = effacement ; absents = état inchangé) :

```json
{
  "extension_panels": [{
    "page": "focus", "title": "Focus", "status": "ok",
    "cards": [{"label": "Temps restant", "value": "24:12", "detail": "Session", "progress": 4}]
  }],
  "extension_buttons": [{"page": "focus", "id": "start", "active": true, "available": true}]
}
```

Bornes natives : 12 panneaux, 4 cartes/panneau, 72 états de boutons ; titre64,
libellé24, valeur40 et détail64 octets UTF-8. `progress` est facultatif (0–100).
Les couleurs de statut sont natives (`neutral`, `ok`, `warning`, `error`). La
traduction est résolue par console. La limite de trame reste65536 octets ; les
listes d'extensions volumineuses sont bornées par le budget global du message.
Le parseur accepte8192 jetons JSON dans une allocation statique bornée.
Les anciens clients ignorent les champs inconnus et nécessitent une mise à jour
pour afficher les nouveaux panneaux ; les fonctions natives restent inchangées.

## Limites cryptographiques et réseau de confiance

Le protocole v1 n'est ni chiffré ni authentifié message par message. Le code
d'appairage et le secret individuel traversent le même canal TCP : ajouter un
simple HMAC protégerait certains rejouements mais pas un attaquant capable
d'observer l'appairage, et donnerait une impression de sécurité trompeuse.
3Decks doit donc rester sur un LAN de confiance, derrière un pare-feu, sans
redirection du port TCP.

Un déploiement sur réseau hostile exige une version de protocole négociée et une
construction auditée disponible sur PC **et** 3DS (par exemple un canal Noise à
clé prépartagée), avec identité de session, numéros de séquence authentifiés et
rollback v1 explicite. Aucune cryptographie artisanale n'est introduite tant
qu'une telle primitive n'est pas qualifiée sur devkitARM.

- Un message JSON invalide entraîne un `action.result` en échec ou est ignoré,
  jamais un plantage.
- La 3DS reconnecte avec un délai progressif (2, 4, 8, 15 puis 30 secondes),
  sans bloquer le rendu ; les ping/pong détectent une liaison silencieuse.
- L'agent tolère la disparition brutale d'un client et continue de tourner.
- Plusieurs 3DS peuvent être connectées simultanément ; l'état est diffusé à
  toutes.
