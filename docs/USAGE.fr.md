# Utiliser 3Decks

[Documentation](README.fr.md) · [English](USAGE.md)

## Premier démarrage

L’assistant permet de choisir les fonctions de la console, de vérifier les accès nécessaires et d’appairer une 3DS ou 2DS. Vous pouvez terminer sans console et l’appairer plus tard. La progression est enregistrée après chaque étape, y compris si macOS demande de quitter et rouvrir l’application. Sur Windows, les médias, l’audio et les raccourcis utilisent les API natives ; le pare-feu peut demander l’accès au réseau local. La lecture de l’historique des notifications d’autres applications exige en plus un paquet compatible et votre consentement : l’installateur direct actuel ne la propose pas. L’assistant se rouvre dans **Réglages → Avancé**.

Les builds publics signés proposent **Réglages → Avancé → Mises à jour → Vérifier**. La recherche se fait lorsque vous appuyez sur le bouton ; elle n’est pas encore lancée en arrière-plan. Un build local non signé ne contient pas la clé de mise à jour et désactive ce contrôle.

## Première page

1. Ouvrez l’éditeur depuis le menu système de 3Decks.
2. Ajoutez une page à gauche et donnez-lui un nom court.
3. Choisissez **Mes propres actions**, puis un emplacement vide.
4. Sélectionnez une action, par exemple lecture/pause, et complétez ses champs.
5. Choisissez une icône et une couleur ; enregistrez avec la barre inférieure.
6. Touchez le bouton sur la console connectée.

L’enregistrement applique et diffuse la configuration sans redémarrage. En cas de conflit avec un autre éditeur, rechargez puis réconciliez vos changements.

## Organisation

Glissez les pages dans la colonne gauche pour les réordonner ; le clic droit ouvre leurs actions contextuelles. Les boutons peuvent aussi être déplacés.

La **grille 3 × 2** propose six emplacements sur toutes les pages. La **liste** convient aux contenus plus longs. **Mes propres actions** désigne vos boutons ; **Fenêtres disponibles** est une liste produite par 3Decks pour afficher une fenêtre de l’ordinateur. Une extension peut aussi fournir du contenu.

Le contenu généré n’est pas une copie éditable de vos boutons. La grille affiche les six premiers éléments ; préférez la liste pour en afficher davantage. Le visualiseur est un aperçu de l’éditeur, pas une retransmission vidéo de la console.

## Écran supérieur

| Mode | Informations |
|---|---|
| Automatique | Médias disponibles, sinon applications |
| Musique en cours | Titre, artiste, pochette, progression |
| Audio | Volumes, sortie et activité musicale |
| Pochette plein écran | Grande image de l’album |
| Applications | Application active et applications ouvertes |
| Système | Mesures de performances disponibles |
| Extension | Cartes produites par une extension activée |

Une mesure GPU/température indisponible n’est pas une valeur zéro. L’animation musicale est un retour visuel, pas une promesse d’analyse spectrale en temps réel.

## Choisir les actions

**Ouvrir un fichier/dossier** : utilisez le bouton de sélection natif. Le champ contient le chemin, pas le contenu du fichier. Annuler n’est pas une erreur ; si l’élément est déplacé, sélectionnez-le à nouveau.

**Ouvrir une application** : utilisez les suggestions lorsqu’elles sont disponibles. Les noms et identifiants diffèrent entre Mac et Windows.

**Raccourci clavier** : activez la capture et pressez la combinaison. Elle agit dans l’application au premier plan ; testez-la dans un contexte sans risque.

**OBS** : activez l’intégration, saisissez les réglages WebSocket et testez la connexion. Utilisez les scènes retournées. Les commandes de streaming/enregistrement peuvent agir sur une session en direct : testez-les hors diffusion.

Les actions d’appui long sont facultatives. Le retour attente/succès/erreur permet de suivre leur traitement par l’ordinateur.

## Touches de la console

| Geste/touche | Effet |
|---|---|
| Toucher | Exécuter le bouton ou l’élément |
| Maintenir un bouton de grille configuré | Action secondaire |
| Sortir du bouton avant relâchement | Annuler |
| Onglets inférieurs ou L/R | Changer de page |
| Croix directionnelle | Déplacer la sélection |
| A | Valider ; sans sélection dans la grille, sélectionner le premier emplacement |
| B | Effacer/revenir sur la sélection |
| X/Y dans la grille | Activer les emplacements 2/3 |
| L + SELECT | Réglages |
| SELECT seul | Demander le dernier agencement |
| START | Quitter |

Les réglages restent accessibles pendant la connexion. Langue, connexion, son et atténuation sont enregistrés dans `sdmc:/3ds/deck3ds/settings.cfg`. Ce fichier peut contenir un secret : ne le publiez pas.

## Le compagnon Decky

Au lancement, Decky se réveille et salue pendant une courte animation de
1,2 seconde, tandis que la recherche/connexion réseau continue. Un bouton ou
un toucher permet de la passer (START quitte toujours l’application). Elle ne
rejoue pas après une reconnexion ou un réveil et est désactivée lorsque Decky
est masqué dans les réglages de la console.

Sur la **3DS**, ouvre les réglages (roue dentée ou L + SELECT), puis sélectionne
**Decky**. Un toucher ou A fait défiler trois choix :

- **Désactivé** : aucune apparition du compagnon.
- **Discret** (par défaut) : accueil et connexion, puis sommeil pendant la veille
  lorsqu’aucun titre musical n’est disponible. La pochette existante reste prioritaire.
- **Veille compagnon** : Decky occupe l’écran supérieur pendant la veille
  automatique. Il écoute avec son casque pendant la lecture et se repose sinon.
  L’écran inférieur conserve ses informations ; un toucher réveille l’application.

La ligne sélectionnée affiche un aperçu des six expressions sur l’écran du haut.
Enregistre pour conserver ton choix sur la SD. Le délai de veille existant
s’applique aussi à Decky ; « Jamais » désactive la veille automatique. Le mode
pochette choisi manuellement ne change pas. Les animations sont décoratives et
silencieuses, sans requête réseau, permission supplémentaire ou pénalité d’absence.
Ce réglage propre à la console n’est pas encore reproduit dans l’aperçu PC.

Sur PC, Decky apparaît dans la fenêtre de connexion, pendant le chargement,
si l’application de bureau est indisponible et dans la page des extensions vide. **Réglages →
Langue & apparence** permet de découvrir ses expressions ou de masquer ces
apparitions. Ce choix est immédiat et propre au navigateur, indépendant de la 3DS.
Le logo reste visible : il cligne brièvement des yeux toutes les huit secondes et
salue une fois au survol ou au focus clavier. Masquer Decky ou activer la réduction
des mouvements du système le laisse immobile.

Le dessin portable se trouve dans `apps/console/source/graphics/decky.c`. L’outil
`tools/render_decky.c` exporte les six poses depuis le même code ; les tests sont
lancés avec `bash tools/test_console.sh`.

## Intégrations

N’activez que ce qui vous sert. Couper le groupe médias conserve les préférences de lecteurs/pochettes. Certaines autorisations nécessitent un redémarrage ; voir le [dépannage](TROUBLESHOOTING.fr.md).

Importez une extension depuis son onglet, puis examinez ses accès et approuvez son empreinte avant activation. L’import seul n’exécute rien. Consultez la [sécurité](SECURITY.fr.md).
