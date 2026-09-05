# Architecture de l’agent

[Documentation](README.fr.md) · [English reference](ARCHITECTURE.md)

Cette synthèse française présente les responsabilités. La référence anglaise détaille les capacités des pools et l’ordre exact du cycle de vie.

## Couches

Le paquet réel se trouve dans `agent/backend/deck3ds`. `agent/deck3ds` est un adaptateur d’import depuis les sources ; `config.py` et `server.py` sont des façades de compatibilité.

| Dossier | Responsabilité |
|---|---|
| api | FastAPI, contrats HTTP, sécurité et assets |
| services | Transactions et opérations métier indépendantes de HTTP |
| configuration | Modèles, validation, sérialisation, stockage |
| runtime | Assemblage, supervision, signaux et arrêt |
| desktop | Menu natif, instance unique, ouverture de session, journaux |
| transports | TCP console et découverte UDP |
| platforms | Intégrations et dialogues macOS/Windows |
| extensions | SDK API 1, confiance, processus et contributions |

Les routes reçoivent des services, pas le runtime. Les imports ne démarrent ni sockets, ni collecte, ni extensions. L’export OpenAPI ne construit aucun adaptateur natif.

## État et transactions

Le document utilisateur persisté est distinct de la vue console contenant les fenêtres et contenus générés. Les lectures HTTP copient une fois l’état sortant depuis les instantanés en cache.

Sauvegarde et rechargement partagent un verrou asynchrone : vérification de révision/empreinte, validation, remplacement atomique, installation mémoire, reconstruction et diffusion. Une erreur d’écriture conserve l’ancien état ; une diffusion échouée n’annule pas une écriture réussie. Les écritures engagées restent supervisées même si le navigateur abandonne.

L’éditeur externe ne participe pas au verrou : le remplacement est atomique, pas une transaction universelle entre applications.

## Cycle de vie

Un processus agent, une boucle asyncio. Uvicorn utilise cette boucle sans multi-worker ni reload. Son échec de port n’empêche pas TCP. Le menu garde Cocoa/Win32 sur le thread principal et exécute asyncio dans un thread dédié.

La fermeture arrête les admissions, dialogues et transports, attend les écritures engagées, ferme clients/extensions et vide les pools avant les ressources natives. Une opération en thread reste comptée jusqu’à sa vraie fin. Collecte, actions, fichiers, dialogues et extensions utilisent des capacités séparées.

Le verrou d’instance graphique est associé au fichier de configuration. L’arrêt coopératif emploie un identifiant aléatoire par lancement ; le menu reçoit des instantanés et ses mutations passent par les services existants.

## Sécurité et distribution

Appairage individuel révocable, quotas, échéances et compteurs limitent les abus ; le TCP reste non chiffré sur LAN de confiance. L’HTTP local possède une session distincte et des contrôles Host/Origin.

Un wheel versionné sert les lanceurs GitHub et le packaging Store. Réglages et extensions restent à côté de la configuration, hors environnement de programme. L’identité MSIX, sa signature finale et les permissions OS ne sont pas fournies par FastAPI.

Voir [API](api/README.fr.md), [protocole](PROTOCOL.fr.md), [sécurité](SECURITY.fr.md) et [performances](PERFORMANCE.fr.md).
