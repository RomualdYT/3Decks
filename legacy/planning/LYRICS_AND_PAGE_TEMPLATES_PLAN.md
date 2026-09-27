# Pages prédéfinies et paroles synchronisées

## Expérience proposée

Dans « Ajouter une page », présenter une galerie avec aperçu des deux écrans :

- Page vierge (grille personnalisable).
- Musique et paroles (écran supérieur : paroles ou pochette ; écran inférieur : commandes).
- Notifications (historique récent et actions disponibles).
- Fenêtres (applications et fenêtres ouvertes).
- OBS Studio (scènes, sources et état de connexion).
- Performances (CPU, mémoire et réseau).

Chaque modèle crée une **instance éditable** de page. Le modèle apporte un titre, une disposition, des commandes et des options par défaut ; l'utilisateur peut ensuite changer couleurs, fond, taille du texte, nombre de lignes visibles, commandes et comportement en l'absence de données. L'éditeur doit signaler clairement les fonctionnalités désactivées et les permissions manquantes. Un modèle n'est jamais une seconde copie figée de la configuration : le schéma de page et les composants dynamiques sont communs à l'éditeur, à l'agent et à la 3DS.

La page « Musique et paroles » ne doit pas interrompre la page active à chaque changement de piste. Une option explicite peut permettre son ouverture automatique. L'écran inférieur conserve les commandes de lecture et peut proposer un bouton « Paroles / Pochette ». Une barre de recherche dans la piste n'apparaît que si le connecteur du lecteur sait modifier sa position.

## Contrat technique envisagé

Le connecteur multimédia fournit un instantané normalisé : lecteur, titre, artiste, album, durée, position, lecture/pause, identifiant stable de piste et horodatage monotone de l'instantané. Ce contrat doit précéder l'intégration de LRCLIB : la lecture actuelle de Spotify et Music via AppleScript expose certaines valeurs, mais le contrôle de position et les autres lecteurs ne sont pas encore uniformes.

L'agent Rust recherche les paroles lors d'un changement de piste, avec cache local et requête annulable. LRCLIB demande un `User-Agent` identifiable, recommande album et durée pour la correspondance, et impose de respecter `429`/`Retry-After`. L'accès distant doit être une option explicite : le titre et l'artiste quittent le PC. Un fichier LRC local peut être choisi pour corriger une correspondance ou fonctionner hors ligne.

Le message initial vers la console contient un identifiant de session de piste, la durée, l'état de lecture, la position et les lignes horodatées. La console garde les lignes et anime localement. Des messages compacts de recalage apportent l'identifiant de session, la nouvelle position, l'état de lecture et l'instant de référence. Une nouvelle piste invalide l'ancienne session. Pause, reprise et saut exigent un recalage immédiat ; un recalage périodique plus lent compense la dérive d'horloge. Le rendu travaille avec une horloge monotone, pas avec l'heure système.

Les trames actuelles sont limitées à 65 536 octets côté Rust et côté 3DS. La console analyse aussi le JSON avec un nombre maximal de jetons et des structures statiques. Il faut donc plafonner lignes et taille UTF-8, prévoir une transmission en fragments si nécessaire et mesurer la mémoire réelle avant de promettre qu'une chanson entière tient dans un paquet. Une chanson instrumentale, un résultat sans synchronisation, un `404`, un accès hors ligne ou un temps de chargement long ont chacun un état visuel distinct.

## Ordre de réalisation

1. Introduire le schéma de modèles de pages et la galerie dans l'éditeur, avec une page « Musique » utilisant les données déjà disponibles.
2. Normaliser la position musicale et la durée dans les connecteurs ; vérifier les capacités réelles de chaque lecteur (lecture, piste suivante, recherche dans la piste).
3. Ajouter le fournisseur de paroles Rust (LRCLIB, cache, LRC local, annulation, limites et option de confidentialité).
4. Étendre le protocole et l'interface 3DS pour les paroles, puis tester sur émulateur **et matériel** : longues chansons, accents, lignes longues, pause, recherche, reconnexion et perte de Wi-Fi.
5. Mesurer les performances, la mémoire et la qualité visuelle sur une 3DS et une 2DS avant d'activer le modèle par défaut.

Le code du serveur LRCLIB est sous MIT, mais cette licence ne garantit pas les droits de redistribution des textes des chansons. Vérifier les conditions et droits applicables avant une diffusion publique de la fonctionnalité.
