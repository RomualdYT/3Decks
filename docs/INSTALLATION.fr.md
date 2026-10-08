# Installer et appairer

[Documentation](README.fr.md) · [English](INSTALLATION.md)

## Prérequis

- Une Nintendo 3DS/2DS capable de lancer des homebrews.
- Un ordinateur macOS ou Windows ; voir les [limites des plateformes](../apps/desktop/PLATFORM_STATUS.md).
- Un réseau local de confiance commun aux deux appareils. L'ordinateur peut être relié par Ethernet.

## Installation

Téléchargez les paquets ordinateur et console correspondants depuis les
[Releases GitHub](https://github.com/RomualdYT/3Decks/releases), lorsqu'ils sont disponibles.
Pour compiler, suivez le [guide de contribution](CONTRIBUTING.md).
Les téléchargements de Release incluent `SHA256SUMS.txt` pour vérifier les fichiers.

1. **macOS :** ouvrez le DMG et déplacez 3Decks dans Applications. **Windows :** lancez l'installateur.
2. **Homebrew Launcher :** copiez `deck3ds.3dsx` dans `sdmc:/3ds/deck3ds.3dsx`.
   **Menu HOME :** installez `deck3ds.cia` avec FBI sur une console avec firmware personnalisé.
   Voir les [paquets console](CONSOLE_PACKAGING.fr.md).
3. Ouvrez 3Decks sur l'ordinateur et suivez l'assistant. Activez les fonctions utiles.
4. Ouvrez 3Decks sur la console, choisissez l'ordinateur détecté et saisissez son code à six chiffres.

Chaque console reçoit son propre identifiant sauvegardé. Les connexions suivantes
ne demandent plus de code, sauf révocation de l'accès ou perte de l'identifiant.
Fermer l'éditeur conserve la connexion ; utilisez **Quitter** dans le menu système
pour arrêter l'application ordinateur.

## Réseau et permissions

Les ports par défaut sont **UDP 38122** pour la découverte et **TCP 38123** pour
les commandes. Autorisez l'application sur le réseau local dans le pare-feu.
Si la découverte échoue, saisissez l'adresse IPv4 numérique de l'ordinateur et
le port TCP dans les réglages de la console.

macOS peut demander Accessibilité, Automatisation ou Accès complet au disque
selon les fonctions choisies. Accordez les accès correspondant à votre usage.
L'historique des notifications Windows est indisponible dans l'installateur
direct, qui n'a pas l'identité de paquet nécessaire.

L'ordinateur utilise votre choix de langue enregistré, sinon le français pour
un système/navigateur français et l'anglais pour les autres langues. La console
démarre en anglais ; sa langue est modifiable dans ses réglages.

Ensuite : [configurer les pages](USAGE.fr.md) ou [résoudre un problème de connexion](TROUBLESHOOTING.fr.md).
