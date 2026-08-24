# Deck3DS

Transforme une Nintendo 3DS en surface de contrôle sans fil et en tableau de
bord pour votre ordinateur, sous macOS et Windows.

*[English version](../README.md)*

- **Écran tactile** — une grille de boutons personnalisables : volume, micro,
  lancement d'applications, raccourcis clavier, sélection de fenêtre, navigation.
- **Écran supérieur** — un tableau de bord contextuel : heure, fenêtres ouvertes,
  application active, lecture en cours avec pochette, volumes, état du micro,
  charge système.

La console ne contient aucune logique d'intégration. Elle affiche ce que
l'ordinateur lui envoie et transmet les appuis ; toutes les actions sont décidées
et exécutées par l'agent, à partir d'une liste blanche.

## Prérequis

**Console** — une 3DS, 2DS, New 3DS ou New 3DS XL avec le homebrew activé, sur
le même réseau Wi-Fi que l'ordinateur.

**Ordinateur** — **Python 3.9 ou plus récent**, rien à installer. La compilation
de l'application nécessite **Docker**, ou devkitPro installé localement.

## Premiers pas

### 1. Compiler l'application

```bash
./build.sh
```

Le fichier `3ds-app/deck3ds.3dsx` est produit.

### 2. Démarrer l'agent

```bash
cd agent
python3 -m deck3ds
```

L'agent affiche l'adresse à saisir sur la console. Avant cela, il est utile de
vérifier ce que votre machine expose réellement :

```bash
python3 -m deck3ds --probe
```

Cette commande indique les informations lisibles et les autorisations
manquantes, ce qui évite de configurer un bouton qui ne pourrait pas
fonctionner.

### 3. Installer sur la console

Copiez `deck3ds.3dsx` dans `sdmc:/3ds/`, puis lancez Deck3DS depuis le Homebrew
Launcher. **Un assistant vous guide pour choisir la langue et saisir l'adresse
de votre ordinateur**, et vous permet de tester la connexion avant de
commencer. Aucun fichier n'est à modifier à la main.

### Envoi par Wi-Fi pendant le développement

```bash
python3 tools/send3ds.py -a 192.168.1.88
```

Activez d'abord 3dslink sur la console (Homebrew Launcher, touche `Y`).
L'application est envoyée directement en mémoire, et **l'adresse de l'ordinateur
est détectée automatiquement**.

## Commandes de la console

| Commande | Effet |
|---|---|
| Toucher un bouton | Exécute son action |
| Maintenir un bouton | Action secondaire, si elle est définie |
| Glisser hors du bouton | Annule |
| Onglets du bas | Change de page |
| `L` / `R`, croix | Page précédente / suivante |
| `A` `B` `X` `Y` | Emplacements 0 à 3, sans le stylet |
| `L` + `SELECT` | Ouvre les réglages |
| Bouton Réglages pendant la connexion | Corrige l'adresse sans relancer l'application |
| `SELECT` | Recharge la configuration |
| `START` | Quitte |

## Réglages

L'écran de réglages intégré (`L` + `SELECT`, ou un bouton avec l'action
`settings.open`) permet de changer :

- la langue de l'interface
- l'adresse et le port de l'ordinateur, au clavier système
- le retour au toucher
- le délai d'assombrissement de l'écran
- le relancement de l'assistant

Les réglages sont écrits dans `sdmc:/3ds/deck3ds/settings.cfg`, un fichier texte
modifiable depuis un ordinateur.

## Personnalisation

Deux possibilités : l'interface graphique, ou le fichier directement.

### Interface de configuration

```bash
python3 -m deck3ds --ui
```

L'agent ouvre une interface dans votre navigateur, identique sur macOS, Windows
et Linux. Elle est pensée pour un public non technique : touchez un emplacement
vide, choisissez une action selon votre besoin, puis ne renseignez que les
champs utiles. Elle offre un aperçu fidèle des deux écrans, le déplacement par
glisser-déposer, le français et l'anglais, des états vides guidés, des réglages
de connexion et de sécurité plus lisibles, un sélecteur visuel d'icônes, le
choix grille/liste sous forme de cartes, ainsi qu'une vue d'état dédiée. Une
action indisponible est expliquée au lieu d'échouer silencieusement.

L'enregistrement écrit `config.json` ; l'agent le relit dans la seconde et
transmet la nouvelle mise en page aux consoles connectées, sans redémarrage.

L'interface n'écoute que sur `127.0.0.1` et exige le jeton présent dans le lien
affiché au démarrage. La section `scripts` y est volontairement en **lecture
seule** : c'est le seul endroit qui désigne des programmes à exécuter, et
l'accepter depuis un navigateur ferait de cette page un moyen d'exécuter du code.
Elle s'édite dans le fichier.

Utilisez `--ui-port` si le port 38124 est occupé.

### Modification du fichier

Tout se passe dans `agent/config.json`. **Aucune recompilation n'est
nécessaire** : appuyez sur `SELECT` pour recharger.

La liste complète des actions, icônes et modes de tableau de bord figure dans le
[README anglais](../README.md#action-reference), dont la structure est
identique.

Une page alimentée par les fenêtres ouvertes peut utiliser une liste défilante
ou la même grille 3 × 2 que les pages classiques. La grille affiche les six
fenêtres les plus récentes ; la liste permet d'en parcourir davantage.

### OBS Studio

OBS 28 et les versions suivantes intègrent obs-websocket 5.x. Dans l'interface,
ouvrez **Réglages → OBS Studio**, activez l'intégration, saisissez l'hôte, le
port et le mot de passe éventuel, puis utilisez **Tester la connexion**. Les
scènes disponibles sont récupérées automatiquement pour éviter de devoir saisir
leur nom exact.

Quatre actions sont proposées : changer la scène programme, démarrer ou arrêter
le stream, démarrer ou arrêter l'enregistrement, et afficher ou masquer une
source. Le port WebSocket OBS par défaut est `4455`. L'agent n'a besoin d'aucune
dépendance Python supplémentaire.

### Champs d'un bouton

| Champ | Rôle |
|---|---|
| `id` | Identifiant, unique dans la page |
| `slot` | Position 0 à 5 (grille 3 × 2) |
| `label` | Texte affiché, 24 caractères maximum |
| `icon` | Nom d'icône |
| `color` | Couleur d'accent `#RRGGBB` |
| `toggle` | Clé d'état qui allume le bouton |
| `hold_label` | Indice de l'action longue |
| `action` | Action principale |
| `hold_action` | Action d'appui long, facultative |

## Sécurité

- L'agent n'accepte **aucune commande** venant de la console : celle-ci envoie un
  identifiant de bouton, l'agent consulte sa propre configuration.
- Seules les actions de la liste blanche existent.
- Les scripts sont limités à ceux déclarés dans `scripts`.
- Les commandes sont lancées sans interpréteur, ce qui exclut l'injection.
- La configuration envoyée ne contient ni chemins, ni URL, ni commandes.
- Un jeton partagé peut être exigé via `server.token`.

Le protocole n'est pas chiffré : il est destiné à un réseau local de confiance.
N'exposez pas ce port sur Internet.

### Interface de configuration

Elle modifie un fichier qui désigne des programmes à exécuter : ses protections
sont donc distinctes de celles du protocole.

- écoute sur `127.0.0.1` uniquement, jamais sur `server.host` ;
- jeton de session engendré à chaque démarrage, jamais écrit sur le disque. Sans
  lui, n'importe quelle page ouverte dans le navigateur pourrait écrire la
  configuration, puisque le navigateur, lui, peut atteindre `127.0.0.1` ;
- l'en-tête `Host` est vérifié, ce qui ferme la réattribution de nom de domaine ;
- une origine étrangère est refusée en écriture ;
- `scripts` est en lecture seule : aucune commande ne peut entrer par le réseau.

Elle reste désactivée tant que `--ui` n'est pas passé.

## Particularités connues

**Police de la console.** La police système est un bitmap de 30 pixels ; la
réduire aux tailles de cette interface la rend illisible. Une police est donc
générée à la taille d'affichage avec `mkbcfnt` puis embarquée. Régénérez-la avec
`./tools/make-font.sh [taille]`.

**macOS, état du micro.** `input volume` renvoie souvent `missing value` selon la
carte son. Le bouton fonctionne, mais l'écran affiche `Micro ?` jusqu'au premier
basculement.

**macOS, lecture en cours.** Lire le titre exige d'autoriser l'application qui
lance l'agent à piloter Spotify ou Musique, dans Réglages Système →
Confidentialité et sécurité → Automatisation. Les commandes de lecture
fonctionnent malgré tout.

**macOS, Spotify Connect.** Lorsque le son est diffusé sur une enceinte externe,
les touches média du système ne l'atteignent pas. L'agent pilote Spotify
directement et laisse environ deux secondes à l'état pour se stabiliser.

**Windows.** Un processus PowerShell est maintenu ouvert, son démarrage coûtant
près d'une seconde. **Cet adaptateur n'a pas encore été éprouvé sur une machine
réelle** et mérite des tests.

Quatre fonctions ne sont pas encore portées : sélection de fenêtre, bascule de
sortie audio, volume par application et notifications. La pochette est également
absente, l'API média de Windows n'exposant aucune adresse d'image. L'adaptateur
déclare ces manques dans `capabilities()` : `--ui` grise donc les actions et
tableaux de bord concernés au lieu de proposer des boutons sans effet.

**Salons vocaux Discord.** Lire les participants exige une autorisation OAuth
accordée au cas par cas par Discord : ce n'est donc pas implémenté. Couper votre
micro système fonctionne pendant un appel.

## Contribuer

Pour ajouter une action :

1. déclarez son nom dans `KNOWN_ACTIONS` (`agent/deck3ds/config.py`) ;
2. ajoutez une méthode `_do_<nom>` dans `agent/deck3ds/actions.py` ;
3. si elle dépend du système, ajoutez-la à `platforms/base.py` puis
   implémentez-la dans `macos.py` et `windows.py` ;
4. associez-la dans `ACTION_CAPABILITY` et renseignez le drapeau dans chaque
   `capabilities()`.

L'étape 4 est ce qui rend l'action proposée par l'interface, et ce qui l'empêche
de l'être sur une plateforme incapable de l'honorer. Un test vérifie qu'aucune
action ne reste non classée.

Aucune modification de l'application 3DS n'est nécessaire : l'interface déduit
ses choix de ces tables.

Pour ajouter une langue, complétez `StringId` et les deux catalogues de
`3ds-app/source/i18n.c`, ainsi que `agent/deck3ds/messages.py`. Un test vérifie
qu'aucune clé ne reste sans traduction.

## Licence

Copyright (C) 2026 Romuald ([@RomualdYT](https://github.com/RomualdYT)).

**GNU General Public License v3.0** — voir [LICENSE](../LICENSE).

Vous pouvez utiliser, étudier, modifier et redistribuer ce logiciel, y compris
commercialement. En échange, toute version que vous distribuez doit rester un
logiciel libre sous GPL, code source disponible. Le modifier pour votre usage
personnel ne vous impose rien.

### Composants tiers

| Composant | Licence |
|---|---|
| libctru, citro2d, citro3d (devkitPro) | zlib |
| DejaVu Sans, source de la police embarquée | [Bitstream Vera / domaine public](licences/DejaVuFonts-LICENSE.txt) |

L'agent, lui, n'a aucune dépendance.

La police `3ds-app/romfs/deck.bcfnt` est générée depuis DejaVu Sans, dont la
licence autorise la redistribution. Si vous la régénérez depuis une autre police,
vérifiez sa licence : une police système comme Verdana ou Arial est libre
d'*usage* mais pas de *redistribution*, et l'embarquer rendrait le projet
indistribuable sous sa propre licence. `tools/make-font.sh` avertit lorsqu'il
reconnaît une police de ce type.
