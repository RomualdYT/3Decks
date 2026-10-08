# Utiliser les extensions

[Documentation](README.fr.md) · [English](EXTENSIONS.md)

Les extensions s'exécutent sur l'ordinateur et peuvent fournir trois contenus :

| Contribution | Emplacement dans l'éditeur |
| --- | --- |
| Action | Ajouter/modifier un bouton → choisir une action dans Extensions |
| Source de boutons | Réglages de page → Contenu des boutons |
| Écran supérieur | Réglages de page → Écran du haut → choisir l'écran de l'extension |

Ces choix sont indépendants. Ajouter une action ne sélectionne pas automatiquement
l'écran supérieur ni les boutons générés de l'extension.

## Installer et activer

1. Dans **Extensions → Importer**, choisissez un `.3deckext` adapté à votre ordinateur.
2. Consultez l'auteur, les accès déclarés et l'empreinte du paquet.
3. Activez le paquet en approuvant son empreinte.
4. Configurez ses réglages nécessaires, puis sélectionnez ses contenus dans l'éditeur.

L'import seul n'exécute rien. Un paquet modifié demande une nouvelle approbation.
Désactiver arrête son processus ; redémarrer le relance avec ses réglages sauvegardés.
Une cible absente, un échec de démarrage ou un dépassement de délai apparaît sur
la carte de l'extension. Consultez la [sécurité](SECURITY.fr.md) avant d'activer du code tiers.

## Exemple : Focus

[Focus](../examples/extensions/focus/README.fr.md) propose un minuteur Pomodoro avec
progression sauvegardée et textes anglais/français. Créez une page en grille,
sélectionnez **Contenu des boutons → Commandes Focus** et **Écran du haut → Suivi
Focus**. Les six commandes apparaissent automatiquement.

Depuis la racine, compilez le paquet de votre ordinateur :

```sh
python3 examples/extensions/focus/package.py
```

Le résultat se trouve dans `examples/extensions/focus/dist/`. La CI compile aussi
Focus sur macOS, Windows et Linux et fournit les paquets comme artefacts du workflow.

## Créer une extension

Le [guide du SDK Rust](../apps/desktop/extension-sdk/README.md) décrit le manifeste,
le protocole stdio, les contributions, les limites et la sauvegarde. Counter est
un exemple minimal ; Focus est un exemple complet. Un écran personnalisé comprend
jusqu'à quatre cartes déclaratives, sans HTML libre ni code exécuté sur la console.
