# Pages prédéfinies et paroles synchronisées

## Utilisation

Dans l'éditeur Tauri, « Ajouter une page » ouvre une galerie de points de départ :
page vierge, paroles, notifications, fenêtres, OBS et performances.
Chaque choix crée une page ordinaire : titre, icône, tableau de bord, couleur,
boutons et actions restent modifiables. Le modèle n'établit pas de connexion à
OBS et n'active aucune autorisation à la place de l'utilisateur.

La page « Paroles » affiche le titre et les paroles horodatées sur
l'écran supérieur. L'écran tactile conserve ses six commandes ; la fine barre
de progression sous le titre permet d'avancer dans un morceau quand le lecteur
annonce une durée et prend en charge le déplacement. Le nombre de lignes
visibles (2 à 5) et la couleur d'accent sont réglables dans l'inspecteur.
Le passage actif dispose de deux lignes, équilibrées selon leur largeur réelle,
avec des tailles de police natives. Les lignes voisines gardent une position
stable dans la zone de lecture, séparée des métadonnées du morceau.

Les nouvelles configurations comprennent déjà la page Paroles. L'assistant de
premier démarrage propose son activation ; pour une configuration existante,
il ajoute la page si elle manque, sans dupliquer une page déjà présente. À la
limite des 12 pages, il demande de libérer un emplacement dans l'éditeur.
Les configurations existantes ne sont pas réinitialisées. Le parcours initial
peut être rouvert depuis les réglages.

## Provenance et confidentialité

La recherche LRCLIB est **désactivée par défaut**. Il faut activer « Paroles
en ligne » dans les fonctionnalités, ou choisir « Page Paroles » dans
l'assistant initial. Si nécessaire, le modèle Paroles reste disponible dans la
galerie. Les contrôles multimédias doivent être activés pour la recherche.
Le poste envoie à `https://lrclib.net/api/get` le titre, l'artiste et, s'ils
sont connus, l'album et la durée. La 3DS ne contacte jamais LRCLIB. Si la
fonction est désactivée, le cache téléchargé n'est plus affiché.

Un fichier LRC local peut être placé dans le dossier de cache `lyrics/` de
l'application, sous le nom SHA-256 hexadécimal de
`titre_minuscule\0artiste_minuscule\0album_minuscule\0durée_secondes`.
Cette source locale a priorité sur le réglage en ligne et permet un usage hors
réseau. Les paroles non synchronisées et les morceaux instrumentaux sont
signalés comme tels ; aucune parole n'est fabriquée.

La réponse est limitée à 256 Kio, puis à 256 lignes de 120 octets UTF-8.
Une chanson est envoyée en une trame `media.lyrics` de 64 Kio maximum. La
console suit ensuite sa propre horloge locale, recalée par les messages
`state.update` existants. Les requêtes sont annulées lors d'un changement de
chanson ou de configuration, espacées d'au moins 350 ms et respectent
`Retry-After` lors d'une réponse HTTP 429.

## Vérification avant publication

- Sur macOS : autoriser l'automatisation de Spotify et Music, puis vérifier
  titre, artiste, album, durée, position, pause, reprise, piste suivante,
  volume du lecteur et recherche de fenêtre après permission Accessibilité.
- Sur une console et un émulateur : vérifier les paroles LRC UTF-8, une piste
  instrumentale, une absence de résultat, les sauts temporels, la pause, le
  changement rapide de piste et la reconnexion pendant la lecture.
- Sans réseau : vérifier la lecture d'un fichier `.lrc` local et l'absence de
  requête HTTP quand l'option est désactivée.
- Sur Windows et Linux : la galerie et les pages doivent rester éditables ;
  l'affichage des paroles dépend encore d'un fournisseur de métadonnées et
  de déplacement temporel natif à implémenter et tester sur chaque OS.

Le rendu natif de la 3DS doit encore être construit avec devkitPro sur une
machine équipée de `DEVKITARM`; les tests hôte ne remplacent pas cet essai.
