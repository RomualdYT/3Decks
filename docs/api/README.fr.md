# Guide de l’API HTTP locale

[Documentation](../README.fr.md) · [English reference](README.md) · [OpenAPI](openapi.json)

Cette introduction française accompagne le contrat exhaustif anglais et l’OpenAPI commun. `/api/schema` est le catalogue dynamique de l’éditeur, pas la spécification OpenAPI.

L’agent HTTP écoute uniquement sur `127.0.0.1`, normalement 38124. Utilisez la session du lien UI dans `X-Deck3DS-Token`, distincte du secret durable console. Les routes inconnues dans `/api` sont aussi protégées. Host et origines d’écriture sont contrôlés ; aucune ouverture CORS générale n’est prévue.

## Opérations

- Catalogue/configuration : GET schema, GET/PUT config, POST config/validate.
- État et diagnostic : GET state, health, openapi.json.
- Natif : GET apps ; POST paths/pick, permissions/open, obs/test.
- Connexion : POST pairing/rotate ; DELETE paired-devices/{id}.
- Extensions : GET et POST extensions.

Tous ces chemins sont sous `/api/`. Les requêtes/réponses exactes et variantes sont dans [OpenAPI](openapi.json) et la [table anglaise](README.md#operations).

## Erreurs et mutations

Les erreurs applicatives contiennent error, code, request_id. Les erreurs de parsing Uvicorn peuvent survenir avant cette enveloppe. Limites : corps 512 Kio même fragmenté, en-têtes applicatifs 16 Kio, réception 15 secondes, concurrence Uvicorn 64, keepalive 5 secondes.

Renvoyez la revision obtenue par GET pour éviter une sauvegarde obsolète. Un conflit renvoie 409 ; une configuration invalide à enregistrer renvoie 422. La prévalidation retourne valid:false sans écrire. Annuler un sélecteur natif n’est pas une panne. scripts reste issu du document de confiance et n’est pas modifiable par HTTP.

Seul 403 invalid_session doit effacer la session du navigateur, pas origin_refused. Une requête abandonnée n’annule pas une écriture déjà engagée. Les lectures config authentifiées contiennent des réglages sensibles ; ne les publiez pas.

L’import d’extension ouvre le sélecteur natif et n’accepte pas de commande/chemin exécutable fourni par le navigateur. Activer requiert l’approbation de l’empreinte.

## Génération

Depuis `agent/` :

```sh
uv run --locked python -m deck3ds.api.export ../docs/api/openapi.json
pnpm api:types
uv run --locked python -m deck3ds.api.export --check ../docs/api/openapi.json
pnpm api:check
```

Ces commandes ne démarrent ni adaptateur, ni serveur, ni extension. Les types générés se trouvent dans frontend/src/api/generated.ts ; le client manuel conserve les règles de session.
