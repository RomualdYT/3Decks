# Créer une extension — API 1

[Documentation](README.fr.md) · [English specification](EXTENSIONS.md)

Guide de démarrage français. Le [contrat exhaustif anglais](EXTENSIONS.md) décrit chaque champ de manifeste, type de paramètre, méthode SDK, message stdio et limite. Les identifiants de l’API ne sont pas traduits.

## Première extension

Python 3.12+ ; le SDK est fourni avec le paquet agent. Depuis `agent/`, après `uv sync --locked` :

```sh
uv run --locked python -m deck3ds.extensions init ../my-counter --id com.example.counter
uv run --locked python -m deck3ds.extensions validate ../my-counter
uv run --locked python -m deck3ds.extensions pack ../my-counter -o counter.3deckext
```

Ces commandes n’exécutent pas le code et refusent d’écraser une cible existante. La validation vérifie manifeste, fichiers et empreinte, pas le comportement des handlers.

Importez le paquet dans **Extensions**, examinez sa provenance et ses accès, configurez puis approuvez son empreinte. Ajoutez son action Increment et son écran My counter à une page. Enregistrez et essayez sur la console.

L’[exemple Focus Timer](../examples/extensions/focus-timer) fournit réglages typés, état persistant, boutons, source automatique et cartes.

## Contrat et limites

Une archive ZIP `.3deckext` contient `extension.json` à sa racine, le programme, une documentation et une licence. Les extensions Python utilisent le même interpréteur et SDK que l’agent installé. Pour une autre langue, le runtime command nécessite un exécutable déjà disponible.

L’agent communique par JSON UTF-8, une ligne par message stdio : initialize, action, poll, shutdown. stdout est réservé au protocole ; diagnostics sur stderr. Réponses corrélées par id, requêtes bornées, aucune émission spontanée en API 1.

Les contributions sont déclaratives : états booléens, listes générées et quatre cartes par tableau de bord. La grille affiche six éléments, la liste jusqu’à 32 sous réserve du budget global. Les libellés bilingues sont résolus par console. Le homebrew ne reçoit ni code ni HTML arbitraire.

## Confiance et maintenance

L’extension tourne avec les droits du compte : **le processus séparé n’est pas une sandbox**. Les accès déclarés sont informatifs. Utilisez des réglages password pour les secrets, pas le manifeste ou les arguments publics d’action. Une modification d’empreinte nécessite une nouvelle approbation.

Les paquets, approbations et données vivent dans `extensions/` près du fichier choisi par `--config`. Sauvegardez ce dossier. Une erreur de protocole ou un timeout arrête le worker concerné ; le redémarrage se demande explicitement dans l’UI.

Documentez plateformes et permissions, testez Mac et Windows si vous les annoncez, fournissez licence et dépendances redistribuables. Ne dépendez que du SDK et des contrats publics, jamais des modules internes du manager. Voir [publication et compatibilité](EXTENSIONS.md#8-publishing-checklist-and-compatibility-policy).
