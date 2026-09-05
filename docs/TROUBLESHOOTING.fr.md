# Dépannage

[Documentation](README.fr.md) · [English](TROUBLESHOOTING.md)

## Ordinateur introuvable

Vérifiez que l’agent tourne et que les deux appareils sont sur le même LAN de confiance. Réseau invité, isolation Wi-Fi et VPN peuvent empêcher la découverte. Autorisez le trafic local pour le véritable exécutable agent/Python, sans désactiver globalement le pare-feu.

Essayez l’adresse LAN et le TCP **38123** en manuel. Si cela fonctionne, examinez le filtrage de la découverte **UDP 38122**. L’adresse `127.0.0.1:38124` est celle de l’éditeur local, pas celle à saisir sur la console. N’ouvrez pas ces ports sur Internet.

## Appairage ou session expirée

Ouvrez le panneau de connexion pour obtenir un code actuel : les codes expirent, sont à usage unique et les échecs répétés sont limités. Une console révoquée doit être appairée à nouveau.

Une session **navigateur** expirée se corrige en rouvrant l’éditeur depuis le menu, sans changer le secret durable de la console.

## Icône absente

Sous Windows, regardez derrière **^** près de l’horloge. Sur Mac, une barre étroite ou encombrée peut masquer des éléments. Fermer le navigateur ne retire pas l’icône.

`deck3ds --ui` lance un agent terminal ; `deck3ds-ui` ajoute le menu natif. En cas d’échec, consultez le journal ou lancez la CLI avec `--verbose`.

## Médias et notifications

Vérifiez l’interrupteur d’intégration, son état et les permissions. Les raccourcis de l’éditeur ouvrent les réglages mais ne donnent pas eux-mêmes l’autorisation.

- macOS : Spotify/Musique nécessitent les permissions d’automatisation du bon exécutable. Un changement de Python peut les redemander.
- Notifications macOS : lecture seule de la base Notification Center, soumise aux restrictions de confidentialité.
- Notifications Windows : identité MSIX obligatoire ; l’installation directe GitHub ne suffit pas, sans fallback SQLite.
- Médias Windows : le lecteur doit exposer une session média compatible.
- Le volume propre au lecteur n’est pas implémenté par tous les fournisseurs.
- GPU/température peuvent manquer. Le CPU macOS est dérivé de la charge, pas une mesure identique au gestionnaire des tâches.

Accordez uniquement la permission pertinente, puis redémarrez si nécessaire.

## Sélection de fichier, application ou OBS

Un fichier déplacé doit être choisi de nouveau. Les identifiants d’applications ne sont pas portables entre OS.

OBS doit être lancé avec son serveur WebSocket activé ; vérifiez hôte, port (habituellement 4455) et mot de passe, puis testez avant de choisir une scène.

## Sauvegarde ou mise à jour bloquée

En cas de conflit de configuration, conservez vos modifications souhaitées, rechargez puis réconciliez. Réparez un JSON invalide depuis une sauvegarde, sans l’écraser aveuglément.

Quittez l’agent depuis son menu avant de réessayer une mise à jour ayant expiré. `deck3ds --stop` cible l’instance graphique de la configuration sélectionnée ; gardez le même `--config`. Une ancienne version peut nécessiter un arrêt manuel.

## Signaler un problème

Dans les [issues](https://github.com/RomualdYT/3Decks/issues), indiquez OS, version, modèle de console, installation, étapes, résultat attendu/observé et un court extrait expurgé. Précisez si la connexion manuelle fonctionne.

Ne joignez pas de configuration complète, paramètres SD, registre d’appairage, URL de session, secret, mot de passe OBS ou journal non relu. Les captures peuvent aussi révéler des notifications privées.
