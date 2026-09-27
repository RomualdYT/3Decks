# Installation Python manuelle

[Documentation](README.fr.md) · [English](PYTHON_SETUP.md)

Pour une installation normale, préférez les [lanceurs](INSTALLATION.fr.md). Ce guide concerne un wheel déjà construit ; pour les sources, voir [Contribuer](CONTRIBUTING_AGENT.fr.md).

Python 3.12 minimum est nécessaire. Node.js n’est pas requis pour l’éditeur fourni. Ces commandes ne supposent pas une publication PyPI.

## macOS

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install /chemin/deck3ds-0.2.0-py3-none-any.whl
.venv/bin/deck3ds-ui
```

## Windows PowerShell

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install C:\Downloads\deck3ds-0.2.0-py3-none-any.whl
.venv\Scripts\deck3ds-ui.exe
```

Adaptez chemin et version au wheel téléchargé. Le lanceur graphique crée seulement une configuration absente. Pour un agent terminal, utilisez `deck3ds --ui` ; sans `--ui`, aucun serveur HTTP d’édition ne démarre. `python -m deck3ds` fonctionne aussi dans cet environnement.

## Réglages et permissions

`--config CHEMIN` sélectionne votre fichier. `deck3ds --config CHEMIN --init-config` crée explicitement un nouveau profil sans écraser un fichier existant. Réglages et extensions restent hors environnement de programme : voir [configuration et sauvegardes](CONFIGURATION.fr.md).

Les permissions macOS dépendent du véritable exécutable ; un autre Python peut les redemander. Un wheel ne fournit **pas** l’identité MSIX nécessaire aux notifications Windows.

pip résout les dépendances déclarées ; les sources et la CI utilisent `uv.lock` pour la reproductibilité. Assets de l’éditeur, PNG et polices sont inclus.

Arrêtez l’agent et sauvegardez son dossier de configuration avant de remplacer le wheel. Gardez le même `--config`. Retirer l’environnement supprime le programme, pas les données utilisateur séparées.
