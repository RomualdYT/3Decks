# Vérification macOS : menu et raccourcis

Le build local est non signé. Après l'installation, fermer l'ancienne instance
avant de lancer la nouvelle, puis autoriser Accessibilité pour ce bundle si
macOS le demande.

## Raccourcis depuis une 3DS ou l'émulateur

- Tester une lettre et un chiffre avec Cmd, Ctrl, Option et Maj sur AZERTY.
- Tester Échap, Entrée, Tab, Espace et Retour arrière.
- Tester Suppr avant, les quatre flèches, Début, Fin, Page préc./suiv.
- Tester F1 à F12. Sur un clavier Apple, le comportement des touches de fonction
  peut dépendre du réglage système « utiliser F1, F2… comme touches standard ».
- Tester un alias historique (`esc`, `enter`, `delete`) et vérifier qu'une touche
  inconnue produit une erreur visible sans laisser de modificateur enfoncé.

## Menu de barre des menus

- Vérifier le libellé d'état à zéro, une et deux consoles connectées.
- Ouvrir l'éditeur, la connexion et l'onglet État, y compris après fermeture de
  la fenêtre principale.
- Suspendre 15 minutes, 1 heure et sans limite : les appuis 3DS doivent recevoir
  un résultat d'échec sans être exécutés ; la connexion et les états restent
  actifs. Reprendre et vérifier qu'un nouvel appui fonctionne. Tester
  l'expiration d'une pause temporisée.
- Basculer Notifications, Musique et médias, Fenêtres, Performances et OBS ;
  vérifier les coches et la persistance dans les réglages après relance.
- Basculer le démarrage à l'ouverture de session et vérifier l'état après
  déconnexion/reconnexion.
- Copier l'adresse, ouvrir le journal, ouvrir les versions GitHub, redémarrer et
  quitter. Après redémarrage, TCP 38123 et UDP 38122 doivent être repris par une
  seule instance.
