# Protocole Deck3DS v1

Contrat de communication entre l'application 3DS (client) et l'agent PC (serveur).

## Transport

TCP, connexion persistante, l'agent écoute (par défaut `0.0.0.0:38123`), la 3DS se connecte.

Pas de HTTP, pas de WebSocket, pas de TLS. Le choix est délibéré : la 3DS n'a
alors besoin d'aucune bibliothèque externe et le framing reste trivial à
implémenter sans allocation dynamique.

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
  "token": "optionnel"
}
```

Si l'agent est configuré avec un token et que celui fourni ne correspond pas, il
répond `hello.error` puis ferme la connexion.

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
  "agent": "0.1.0",
  "host": "MacBook-Pro",
  "platform": "darwin"
}
```

### `hello.error`

```json
{ "type": "hello.error", "reason": "bad_token" }
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
  "time": "14:32",
  "date": "22 août"
}
```

`time` et `date` viennent du PC pour garantir la cohérence avec l'affichage de
l'ordinateur, mais la 3DS utilise son horloge interne en repli si le champ est
absent ou la connexion perdue.

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

`page.open` est le seul cas particulier : l'agent le renvoie sous forme de
résultat que la 3DS interprète comme navigation, ce qui évite un aller-retour.

## Robustesse

- Un message JSON invalide entraîne un `action.result` en échec ou est ignoré,
  jamais un plantage.
- La 3DS reconnecte automatiquement toutes les 2 secondes après une coupure,
  sans jamais bloquer le rendu.
- L'agent tolère la disparition brutale d'un client et continue de tourner.
- Plusieurs 3DS peuvent être connectées simultanément ; l'état est diffusé à
  toutes.
