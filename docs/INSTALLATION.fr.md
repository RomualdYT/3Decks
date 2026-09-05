# Installer 3Decks

[Documentation](README.fr.md) · [English](INSTALLATION.md)

## Prérequis

Une console de la famille 3DS/2DS avec homebrew, un Mac ou PC Windows, Internet pour l’installation et un réseau local de confiance partagé. 3Decks n’installe pas le homebrew.

Téléchargez les fichiers d’une [GitHub Release](https://github.com/RomualdYT/3Decks/releases). Les commandes suivantes nécessitent une Release contenant ces fichiers. S’il n’y en a pas encore, suivez le [guide depuis les sources](CONTRIBUTING_AGENT.fr.md).

Les lanceurs préparent un Python privé avec uv : ni Git, ni Node.js, ni Python préinstallé ne sont nécessaires. Vous pouvez télécharger et lire le script avant de l’exécuter.

## 1. Ordinateur

### macOS

Dans Terminal :

```sh
installer="$(mktemp)" && curl -fL https://github.com/RomualdYT/3Decks/releases/latest/download/install-3decks-macos.sh -o "$installer" && sh "$installer"
```

Ensuite, ouvrez **3Decks.app** dans le dossier Applications de votre compte. L’éditeur s’ouvre dans le navigateur ; l’icône reste dans la barre des menus. Il s’agit d’un lanceur, pas d’un binaire autonome macOS notarié. Les autorisations restent décidées par l’utilisateur.

### Windows

Dans PowerShell :

```powershell
$installer="$env:TEMP\install-3decks.ps1"; Invoke-WebRequest https://github.com/RomualdYT/3Decks/releases/latest/download/install-3decks-windows.ps1 -OutFile $installer; powershell -ExecutionPolicy Bypass -File $installer
```

Les raccourcis sont créés dans le menu Démarrer et sur le Bureau. L’icône peut être derrière **^**, près de l’horloge. L’option de stratégie d’exécution ne concerne que ce processus d’installation ; ne désactivez pas globalement les protections Windows.

**Les notifications Windows ne sont pas disponibles avec l’installation directe GitHub.** Elles nécessitent une identité MSIX, la capacité correspondante et votre accord. Le packaging Store est préparé, sans annoncer ici une version déjà publiée. Aucun fallback SQLite n’existe. Les autres fonctions dépendent aussi des capacités natives.

## 2. Console

Copiez `deck3ds.3dsx` de la même Release dans `sdmc:/3ds/deck3ds.3dsx`. Lancez-le depuis Homebrew Launcher, choisissez une langue et sélectionnez votre ordinateur. Saisissez le code court affiché dans le panneau de connexion de l’éditeur si demandé. Le secret est enregistré automatiquement sur la console.

Si la découverte échoue, utilisez la configuration manuelle avec l’adresse LAN et le port TCP de l’agent, pas `127.0.0.1`. Voir le [dépannage](TROUBLESHOOTING.fr.md).

## 3. Utilisation

Suivez le [guide utilisateur](USAGE.fr.md). Fermer le navigateur ne quitte pas l’agent ; utilisez **Quitter** dans son menu système.

## Mise à jour et désinstallation

Relancez la commande d’installation pour mettre à jour. Le lanceur demande un arrêt propre ; s’il expire, quittez l’ancienne instance depuis son menu et réessayez. Il ne tue pas le processus de force.

Les réglages, consoles appairées et extensions sont conservés. [Sauvegardez-les](CONFIGURATION.fr.md) avant la mise à jour. Remplacez également le `.3dsx` sur la carte SD pour actualiser le homebrew.

Après avoir téléchargé le lanceur, désinstallez avec son chemin :

```sh
sh /chemin/install-3decks-macos.sh --uninstall
```

```powershell
powershell -ExecutionPolicy Bypass -File C:\Downloads\install-3decks-windows.ps1 -Uninstall
```

La désinstallation retire l’application, les raccourcis et le démarrage automatique, pas les données utilisateur. uv peut rester installé.

## Vérification du téléchargement

Le lanceur vérifie l’empreinte SHA-256 du wheel de sa Release. Ce n’est pas un certificat de signature ni une protection indépendante si le compte de publication ou le lanceur est compromis. uv isole l’environnement ; les environnements de développement/CI utilisent aussi le fichier de verrouillage.

Pour Python manuel ou une ancienne installation : [migration](MIGRATION_FASTAPI.fr.md). Pour les mainteneurs : [publication](PUBLIC_RELEASE.fr.md).
