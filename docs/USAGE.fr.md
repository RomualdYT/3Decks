# Utiliser 3Decks

[Documentation](README.fr.md) · [English](USAGE.md)

## Premier démarrage

L'assistant permet de choisir les fonctions, consulter leurs permissions et
appairer la console. Vous pouvez terminer sans console et la connecter ensuite.
La progression est sauvegardée. Rouvrez l'assistant dans **Réglages → Avancé**.

L'ordinateur utilise votre choix de langue enregistré, sinon la langue du
système/navigateur : français pour un système français, anglais sinon. La langue
console est indépendante et commence en anglais. Chaque application conserve
votre choix.

Fermer l'éditeur laisse l'application active dans le menu système. Ce menu
permet de rouvrir l'éditeur, suspendre les commandes ou quitter l'application.

## Créer une page

1. Dans **Éditeur**, choisissez **Ajouter une page**, puis une page vierge ou un modèle.
2. Donnez-lui un nom court et une icône ; choisissez **Grille** ou **Liste**.
3. Dans **Contenu des boutons**, choisissez **Mes propres actions** pour des boutons éditables.
4. Sélectionnez un emplacement vide, choisissez une action et remplissez ses champs.
5. Réglez son libellé, son icône et sa couleur ; enregistrez avec la barre inférieure.
6. Touchez le bouton sur la console connectée.

L'enregistrement applique et diffuse la configuration sans redémarrage. Les
modifications non enregistrées apparaissent d'abord dans l'aperçu. Si un autre
éditeur a enregistré une révision plus récente, rechargez puis réconciliez les
changements avant d'enregistrer.

Glissez les pages ou les boutons pour les réordonner. Le menu contextuel d'une
page propose d'autres opérations. Un modèle crée une page éditable ; il n'active
pas de service et n'accorde pas de permission.

## Boutons générés

**Fenêtres disponibles** affiche les fenêtres de l'ordinateur. Une source
d'extension affiche les éléments fournis par celle-ci. Ces éléments ne sont pas
édités individuellement. La grille montre les six premiers ; une liste peut en
contenir jusqu'à 32. L'aperçu ordinateur est interactif, pas une vidéo de la console.

## Écran du haut

Cliquez sur le choix actuel pour ouvrir le sélecteur avec recherche. Les écrans
d'extension sont regroupés séparément des écrans intégrés.

| Écran | Contenu |
| --- | --- |
| Automatique | Média disponible, sinon applications ouvertes |
| Musique en cours | Titre, artiste, pochette et progression |
| Paroles synchronisées | Paroles horodatées, avec un repli si elles sont absentes |
| Pochette plein écran | Grande image de l'album |
| Applications ouvertes | Application active et applications ouvertes |
| Sorties audio | Sortie actuelle et volume |
| État de l'ordinateur | CPU, mémoire, réseau et stockage disponibles |
| Notifications | Notifications récentes lorsque la source est active et disponible |
| Chat de stream | Messages Twitch configurés dans Réglages → Streaming ; voir la [configuration](STREAM_CHAT.fr.md) |
| Écran d'extension | Tableau de bord fourni par une extension activée |

**Paroles :** activez les médias et les paroles en ligne dans les réglages ou
choisissez cette fonction pendant l'assistant. Les nouvelles configurations
comprennent une page musique/paroles. La recherche en ligne reste désactivée
jusqu'à votre choix et transmet les métadonnées du morceau à LRCLIB. Les fichiers
LRC locaux fonctionnent hors ligne ; voir les [détails](../apps/desktop/docs/LYRICS_AND_PAGE_TEMPLATES.md).

## Actions et intégrations

- **Fichiers/dossiers :** utilisez le sélecteur natif ; sélectionnez de nouveau un élément déplacé.
- **Applications :** utilisez les suggestions disponibles ; noms et chemins dépendent du système.
- **Raccourcis clavier :** utilisez la capture. Le raccourci agit dans l'application au premier plan.
- **OBS :** activez son serveur WebSocket, recopiez hôte/port/mot de passe dans les
  réglages, activez l'intégration et testez la connexion. L'aide intégrée explique
  les étapes. Connexion par défaut : `127.0.0.1:4455`. Choisissez ensuite les scènes retournées.
- **Appui long :** un bouton de grille peut proposer une action secondaire.

N'activez que les fonctions utiles. Une mesure absente est indiquée indisponible.
L'animation musicale est décorative, pas une analyse spectrale mesurée.

## Commandes console

| Geste/touche | Effet |
| --- | --- |
| Toucher / maintenir | Action principale / secondaire configurée |
| Sortir avant relâchement | Annuler le toucher |
| Dock inférieur ou L/R | Changer de page |
| Croix directionnelle | Déplacer la sélection dans la grille ou la liste |
| A | Valider ; sans sélection de grille, sélectionner le premier emplacement |
| B | Effacer/revenir sur la sélection |
| X/Y dans la grille | Activer les emplacements 2/3 |
| Roue dentée ou L + SELECT | Réglages |
| SELECT seul | Demander le dernier agencement |
| START | Quitter |

Les réglages console couvrent langue, connexion, son, délai de veille et Decky.
Decky peut être désactivé, discret ou affiché pendant la veille. Le choix
ordinateur est indépendant. Les préférences et l'appairage sont sauvegardés dans
`sdmc:/3ds/deck3ds/settings.cfg` : gardez ce fichier privé.

## Extensions, mises à jour et aide

[Importez et activez les extensions](EXTENSIONS.fr.md), puis choisissez leurs
actions, sources de boutons et écrans dans l'éditeur.
[Focus](../examples/extensions/focus/README.fr.md) fournit un exemple Pomodoro complet.

Avec une clé publique intégrée au build, l'éditeur recherche une mise à jour après
son ouverture. **Réglages → Avancé → Mises à jour → Vérifier** permet aussi une
recherche manuelle. L'installation nécessite un clic et redémarre l'application.
Un build sans clé désactive l'updater.

**Communauté & aide** dans les réglages ouvre Discord ou son QR code. La console
propose aussi un bouton Communauté. Consultez le [dépannage](TROUBLESHOOTING.fr.md)
pour les problèmes de connexion, de permissions et de fonctions.
