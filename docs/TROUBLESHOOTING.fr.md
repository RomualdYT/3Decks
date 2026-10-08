# Dépannage

[Documentation](README.fr.md) · [English](TROUBLESHOOTING.md)

| Problème | Vérifications |
| --- | --- |
| Ordinateur introuvable | Même réseau local, isolation du réseau invité, VPN et pare-feu. Essayez l'IPv4/port TCP manuels. Ports par défaut : UDP 38122, TCP 38123. |
| Port occupé | Quittez l'autre instance ou le processus utilisant ce port, puis rouvrez 3Decks. |
| Échec de l'appairage | Utilisez le code actuel à six chiffres de l'ordinateur. Un appairage réussi le renouvelle. Révoquez et réappairez si l'identifiant sauvegardé ne fonctionne plus. |
| Action nécessitant une permission indisponible | Consultez la fonction dans les réglages ou rouvrez l'assistant depuis Avancé. macOS peut demander de quitter et rouvrir l'application. |
| Sortie Windows non modifiable à distance | L'application affiche la sortie et ouvre les réglages Son Windows ; le choix se fait sur l'ordinateur. |
| Notifications Windows indisponibles | L'installateur direct n'a pas l'identité de paquet nécessaire au lecteur de notifications. |
| Paroles absentes | Activez les médias et les paroles en ligne, vérifiez titre/artiste et essayez une piste avec paroles synchronisées. Tous les morceaux n'ont pas de résultat. |
| Écran d'extension absent | Activez l'extension et choisissez son écran dans le sélecteur Écran du haut. La source des boutons se choisit séparément. Consultez l'erreur de l'extension. |
| Mise à jour indisponible | Il faut une clé publique intégrée au build et une mise à jour signée publiée. Un build local sans clé ne peut pas utiliser l'updater. |

Pour obtenir de l'aide, utilisez [Discord](https://discord.gg/EmdnneHeus) ou une
issue GitHub. Indiquez version, système, modèle de console, étapes et erreur.
Retirez les chemins privés, identifiants et contenus personnels des captures/journaux.
