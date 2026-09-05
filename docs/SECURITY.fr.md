# Sécurité et confidentialité

[Documentation](README.fr.md) · [English](SECURITY.md)

3Decks vise un **LAN de confiance**. Le TCP v1 n’est ni chiffré ni authentifié message par message ; codes et secrets traversent ce canal. Les contrôles d’appairage/rejeu ne protègent pas contre un observateur du réseau. Ne redirigez jamais TCP 38123 ou UDP 38122 sur Internet.

## Console et éditeur

La console envoie normalement des identifiants de page/bouton, pas une commande exécutable. L’agent valide et résout l’action depuis sa configuration. Les contrôles directs possèdent une liste restreinte séparée ; les scripts doivent être déclarés localement.

Chaque console appairée reçoit un secret révocable dont seule l’empreinte SHA-256 est conservée dans le registre. Les anciens jetons sont échangés lors de la migration. Échéances, plafonds, identifiants monotones et quotas limitent certains abus ; ils ne remplacent pas le chiffrement.

L’éditeur écoute uniquement sur `127.0.0.1`, avec une session par démarrage, des contrôles Host/Origin et des limites de requête. L’API de configuration authentifiée expose des réglages sensibles. Gardez le lien initial privé.

Ce lien peut figurer dans l’état privé de transmission du menu système. Ne publiez pas les caches ou sessions. Le navigateur retire le jeton de l’URL après lecture.

## Extensions et permissions

Un processus d’extension et ses accès déclarés **ne sont pas une sandbox**. Il possède les droits de votre compte. N’approuvez que des paquets examinés ; une empreinte modifiée demande une nouvelle approbation. Un champ de type password est masqué dans les catalogues, pas automatiquement chiffré partout.

Les permissions OS restent nécessaires. macOS lit sa base de notifications en lecture seule ; Windows utilise uniquement l’API officielle avec identité MSIX et consentement, sans fallback SQLite.

## Signalement et publication

Ne publiez pas de secret ni de détail d’exploitation dans une issue. Si le signalement privé GitHub est activé, utilisez l’onglet Security ; sinon, contactez le mainteneur par un canal privé disponible. Ce guide ne promet pas un canal qui n’aurait pas été configuré.

Avant de rendre un fork public, auditez ses fichiers **et son historique**. Le contrôleur fourni ne vérifie que certains champs du fichier de démonstration : ce n’est pas un audit exhaustif de secrets. Révoquez tout secret exposé avant d’envisager un nettoyage d’historique.
