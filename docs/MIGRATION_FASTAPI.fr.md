# Installer et migrer l’agent FastAPI

[Documentation](README.fr.md). Pour une première installation, préférez le
[guide utilisateur](INSTALLATION.fr.md). Ce document concerne les anciennes
configurations et Python manuel. Depuis un nouveau clone, suivez le
[développement](CONTRIBUTING_AGENT.fr.md) pour compiler l’éditeur et créer une
configuration privée ignorée avant lancement.

[English](MIGRATION_FASTAPI.md) · [Architecture](ARCHITECTURE.fr.md) · [API HTTP](api/README.fr.md) · [Contribuer](CONTRIBUTING_AGENT.fr.md)

## Ce qui change

3Decks 0.2 nécessite **Python 3.12 minimum**, avec une qualification ciblant 3.12, 3.13 et 3.14. FastAPI, Pydantic 2, Uvicorn minimal et platformdirs remplacent le serveur HTTP maison. Aucun compte distant, serveur supplémentaire, base de données, Redis ou Celery n’est nécessaire.

L’éditeur React, le protocole TCP 1, la découverte UDP 38122, les configurations et l’API 1 des extensions restent compatibles. L’ancien serveur HTTP a été supprimé : il n’existe pas de mode de secours historique.

## Depuis les sources

Installez [uv](https://docs.astral.sh/uv/getting-started/installation/), puis :

```sh
cd agent
uv sync --locked
uv run --locked deck3ds --ui
```

Le fichier historique du dépôt est repris s’il existe. Ne réutilisez pas l’ancien environnement Python 3.9 : `uv sync --locked` prépare l’environnement compatible et refuse un verrou incohérent.

Pour choisir votre fichier existant :

```sh
uv run --locked deck3ds --config /chemin/absolu/config.json --ui
```

Pour un premier démarrage avec une configuration distincte :

```sh
uv run --locked deck3ds --config config.local.json --init-config
uv run --locked deck3ds --config config.local.json --ui
```

`--init-config` crée des commandes de démonstration bilingues et un nouveau jeton sécurisé. **Un fichier existant n’est jamais écrasé.** Node.js ne sert qu’au développement et à la compilation du frontend.

## Installer le paquet sans le dépôt

Récupérez un wheel issu d’un build qualifié ou de l’artefact CI `python-distribution`. Ces commandes ne supposent pas de publication sur PyPI.

macOS :

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install /chemin/deck3ds-0.2.0-py3-none-any.whl
.venv/bin/deck3ds --init-config
.venv/bin/deck3ds --ui
```

Windows PowerShell, sans modifier la politique d’exécution des scripts :

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install C:\Downloads\deck3ds-0.2.0-py3-none-any.whl
.venv\Scripts\deck3ds.exe --init-config
.venv\Scripts\deck3ds.exe --ui
```

L’interface, le PNG de la console et les polices sont intégrés. Aucun Node.js ni CDN n’est requis pour l’utilisateur final. Le verrou `uv.lock` fixe les dépendances des sources et de la qualification CI ; une installation pip classique du wheel résout les versions compatibles indiquées dans ses métadonnées.

## Où sont les données ?

L’ordre de sélection est : chemin `--config`, puis `agent/config.json` dans un dépôt qui le contient, puis répertoire utilisateur fourni par platformdirs. Par défaut, il s’agit généralement de `~/Library/Application Support/3Decks/config.json` sur macOS et `%LOCALAPPDATA%\3Decks\config.json` sur Windows.

Dans une installation du paquet, le dossier courant ne sert pas de source implicite. Indiquez `--config` pour reprendre un fichier ancien. Les extensions restent dans le dossier `extensions/` situé **à côté du fichier choisi**. Aucun déplacement automatique n’est réalisé ; conservez ensemble le registre d’approbation, les paquets et leurs données.

Avant une mise à jour, arrêtez l’ancien agent et sauvegardez ce fichier ainsi que son dossier d’extensions. Les jetons durables 3DS, paramètres OBS, scripts et traductions sont conservés. À la première reconnexion, l’ancien jeton partagé est échangé automatiquement contre une identité révocable propre à la console ; sauvegardez ensuite aussi le fichier voisin `paired-consoles.json`. Le lien de l’éditeur, lui, est renouvelé à chaque lancement : rouvrez le nouveau lien affiché dans le terminal.

Les sauvegardes HTTP sont atomiques et appliquées immédiatement. Une sauvegarde concurrente ou une modification externe détectée produit `409 config_conflict` : rechargez avant de poursuivre. Un fichier externe invalide ne remplace pas la configuration en mémoire. Un éditeur externe ne partage pas le verrou de l’agent : évitez les modifications simultanées fichier/UI. Le remplacement final est atomique, mais l’agent ne peut pas imposer une transaction à un autre logiciel.

## Permissions et limites de distribution

Sur macOS, les autorisations dépendent de l’application et de l’interpréteur qui exécutent l’agent. Après un changement de Python, Automatisation, Accessibilité ou Accès complet au disque peuvent nécessiter une nouvelle approbation. Les raccourcis de l’éditeur ouvrent les panneaux utiles ; FastAPI ne contourne pas ces protections.

**Installer Python ou le wheel ne fournit pas l’identité MSIX Windows.** Les notifications nécessitent toujours cette identité, la capacité `userNotificationListener` et l’accord de l’utilisateur. Aucun fallback SQLite n’est réintroduit. Le workflow manuel `Windows Store package` prépare depuis le wheel publié un MSIX non signé à envoyer exclusivement à Partner Center ; Microsoft signe la version Store acceptée.

Linux sert à tester le cœur portable, pas à annoncer de nouvelles intégrations natives.

## Diagnostic et retour arrière

Sans `--ui`, l’agent fonctionne sans serveur HTTP. `--ui-port` ne change que le port local. Un port UI occupé n’empêche pas la console de fonctionner. `--check` valide le fichier choisi ; `--probe` effectue une vraie collecte native et peut nécessiter des autorisations ; `--verbose` détaille les journaux.

Pour revenir en arrière : arrêtez l’agent, réinstallez l’artefact/environnement précédent et reprenez le même chemin de configuration. Aucune migration inverse du format n’est nécessaire. Gardez néanmoins la sauvegarde au cas où une extension aurait modifié son propre format de données.

Le [bilan de qualification](QUALIFICATION.fr.md) distingue les tests automatisés des vérifications natives à réaliser sur macOS et Windows/MSIX.
