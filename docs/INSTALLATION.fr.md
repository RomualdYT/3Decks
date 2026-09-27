# Installation

Les installateurs publics ne sont pas encore publiés. Les builds de développement sont non signés et destinés aux essais. Lorsqu’une version aura été validée, téléchargez le DMG macOS ou l’installateur Windows et `deck3ds.3dsx`/`.cia` depuis la même [Release GitHub](https://github.com/RomualdYT/3Decks/releases). Un fichier `SHA256SUMS.txt` accompagne les paquets.

1. Installez l’application de bureau : déplacez 3Decks dans Applications sur macOS ou lancez l’installateur Windows.
2. Copiez `deck3ds.3dsx` dans `sdmc:/3ds/deck3ds.3dsx` pour Homebrew Launcher, ou installez le `.cia` avec FBI sur firmware personnalisé.
3. Placez l’ordinateur et la console sur le même réseau Wi-Fi de confiance. Démarrez 3Decks et suivez l’assistant initial.
4. Choisissez l’ordinateur sur la console et saisissez le code à six chiffres affiché dans l’application.

3Decks écoute par défaut sur UDP 38122 et TCP 38123. Arrêtez l’ancien agent Python avant de démarrer Tauri. Si la découverte échoue, utilisez l’adresse et le port manuels sur la console et vérifiez le pare-feu. Certaines fonctions macOS demandent des autorisations. L’historique des notifications Windows exige une identité de paquet et le consentement utilisateur ; l’installateur direct actuel ne la fournit pas.

Voir [Développement](CONTRIBUTING.md) pour construire depuis les sources et [Paquets console](CONSOLE_PACKAGING.fr.md) pour la 3DS.
