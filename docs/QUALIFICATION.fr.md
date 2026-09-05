# Qualification d’une version

[Documentation](README.fr.md) · [English](QUALIFICATION.md) · [Tests](TESTING.fr.md) · [Publication](PUBLIC_RELEASE.fr.md)

Pour chaque version candidate, notez commit, artefact, OS et interpréteur. Des tests simulés réussis ne prouvent pas les permissions natives ou le matériel.

## Validation automatique

Exécutez les [commandes de test](TESTING.fr.md) et toute la matrice distante Linux/macOS/Windows × Python 3.12–3.14. Exigez couverture, analyse statique, contrats générés, builds frontend/console et installation isolée du wheel.

Le contrôle du paquet teste assets, CLI/HTTP/TCP et extension hors dépôt. Les fournisseurs OS simulés ne doivent pas demander vos permissions ou piloter une vraie console. Gardez rapports CI et artefacts ; indiquez les résultats réels dans les notes de version, plutôt que des compteurs périssables dans le guide utilisateur.

## Vérifications natives

- [ ] Installer l’artefact de livraison sur macOS et Windows.
- [ ] Toutes les vues : polices, image console, responsive et navigation clavier.
- [ ] Créer, trier, sauvegarder/recharger pages/boutons ; capture clavier et conflits.
- [ ] Menu système, état, préférences médias et réglages rapides.
- [ ] Permissions macOS du véritable exécutable : refus puis approbation.
- [ ] Actions/médias/dialogues Windows ; notifications avec identité MSIX prévue.
- [ ] Spotify/Musique compatibles, sélection fichier/dossier et OBS hors diffusion.
- [ ] Vraie 3DS : découverte, manuel, appairage/révocation, FR/EN, actions, veille/réveil.
- [ ] Extension : import, approbation, configuration, redémarrage/retrait, cartes et listes.
- [ ] Arrêt pendant sauvegarde, dialogue ou extension lente ; processus/sockets restants.
- [ ] Second lancement, ouverture de session, restart, mise à jour, désinstallation et retour arrière.
- [ ] Mesurer repos et [endurance adaptée](PERFORMANCE.fr.md).

## Compte rendu

Séparez tests automatiques, essais natifs et contrôles restants. Un Mac ne qualifie pas Windows/MSIX ; le loopback ne mesure pas la 3DS ; un essai court ne prouve pas plusieurs heures.

Expurgez captures et journaux. Rejouez les audits de dépendances pour le candidat. Le packaging Store ne prouve ni acceptation ni disponibilité publique sur le Store.
