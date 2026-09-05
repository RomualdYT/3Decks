# Publier une version

[Documentation](README.fr.md) · [English](PUBLIC_RELEASE.md) · [Qualification](QUALIFICATION.fr.md)

Ce guide décrit une procédure ; il n’annonce pas une publication GitHub ou Store déjà réalisée.

## Préparer

Relisez le diff complet et les assets générés. Conservez la démonstration neutre ; excluez réglages personnels, registres d’appairage et journaux. Mettez à jour `agent/backend/deck3ds/version.py`, les deux langues et sauvegardez vos données privées séparément.

Depuis la racine : `python3 tools/check_docs.py` puis `./build.sh` pour la console.

Depuis `agent/` :

```sh
uv sync --locked
uv run --locked python tools/audit_public_config.py --history
uv run --locked ruff check backend/deck3ds deck3ds tests tools
uv run --locked mypy
uv run --locked pytest --cov --cov-report=term-missing
uv run --locked python -m deck3ds.api.export --check ../docs/api/openapi.json
pnpm install --frozen-lockfile
pnpm api:check
pnpm typecheck
pnpm test:frontend
pnpm build
uv build
uv run --locked python tools/qualify_wheel.py
```

Le contrôleur de configuration inspecte certains champs et chemins dans un seul fichier et son historique local. Il n’affiche pas les valeurs. Récupérez l’historique complet et auditez séparément le reste du dépôt ; **ce n’est pas un scanner exhaustif**. Révoquez les secrets exposés avant un éventuel nettoyage Git.

## GitHub

Après revue et essais natifs, créez et poussez intentionnellement le tag correspondant au wheel, au format `vMAJOR.MINOR.PATCH`. Une compilation locale ne publie rien.

Le workflow Release attend Quality pour les artefacts agent : frontend, paquet, matrice Linux/macOS/Windows × Python 3.12–3.14, contrats, installation isolée et build console. La publication attend ses jobs requis et refuse un écart tag/wheel.

Vérifiez les assets : wheel, archive source, deux lanceurs, icônes, `.3dsx`, `SHA256SUMS.txt`, ainsi que les URL du README. L’empreinte n’est pas une signature. Les lanceurs préservent les données et demandent l’arrêt propre ; un délai dépassé interrompt la mise à jour. Une ancienne instance peut nécessiter Quitter manuellement.

## Store facultatif

Le packaging est préparé, pas une disponibilité Store annoncée.

Réservez l’identité dans Partner Center, lancez **Windows Store package** sur un tag publié et entrez exactement nom du paquet, Publisher et nom d’affichage. Téléchargez l’artefact non signé `windows-store-submission-*` puis soumettez-le à Partner Center.

**Ne distribuez jamais ce MSIX non signé directement.** La distribution Store acceptée fournit la signature et l’identité ; Python seul ne les fournit pas. Testez sur Windows lancement, mise à jour, retrait, consentement/refus des notifications, dialogues, médias, OBS et extensions. Aucun fallback SQLite n’est prévu.

## Retour arrière

Gardez l’artefact précédent et les sauvegardes. Arrêtez l’agent, réinstallez l’ancienne version qualifiée et sélectionnez le même fichier de configuration. Les données d’extensions peuvent nécessiter leur propre sauvegarde.

Les notes de version doivent indiquer CI réellement exécutée et essais natifs effectués, sans présenter simulations ou benchmarks courts comme une qualification universelle.
