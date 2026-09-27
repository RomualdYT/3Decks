# Dépannage

- **L’ordinateur n’apparaît pas :** placez les deux appareils sur le même Wi-Fi de confiance. Le réseau invité, le VPN ou le pare-feu peuvent bloquer la découverte UDP ; essayez l’adresse et le port manuels. Ports par défaut : UDP 38122 et TCP 38123.
- **Un port est déjà occupé :** arrêtez l’ancien agent Python ou une autre instance de 3Decks, puis relancez l’application.
- **Une action demande une permission :** rouvrez l’assistant depuis les réglages avancés. macOS peut exiger de quitter puis relancer 3Decks.
- **Notifications Windows indisponibles :** l’installateur direct actuel ne donne pas d’identité de paquet. Voir le [plan d’essais Windows](../desktop/docs/WINDOWS_TEST_PLAN.md).
- **Pas de mise à jour :** les builds de développement n’embarquent pas la clé de mise à jour. Il faut une Release publiée et signée.
