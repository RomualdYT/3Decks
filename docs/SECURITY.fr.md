# Sécurité

Chaque console est appairée par code puis reçoit un jeton individuel. La découverte UDP et le protocole TCP sont conçus pour un réseau local de confiance ; ils ne sont pas chiffrés. N’exposez pas les ports 38122 et 38123 sur Internet. Limitez l’accès par pare-feu si le réseau est partagé.

Les extensions natives s’exécutent avec les droits de l’utilisateur après approbation explicite. La mise à jour vérifie les paquets avec une clé publique embarquée ; la clé privée reste dans l’infrastructure de publication. Voir le [guide de publication](RELEASE.fr.md).

## Dépendance amont suivie

La pile GTK 3/WebKit de Tauri 2 pour Linux dépend de `glib` 0.18, concerné par [GHSA-wrw7-89jp-8q8g](https://github.com/advisories/GHSA-wrw7-89jp-8q8g). La version corrigée 0.20 ne peut pas remplacer directement la version imposée par les liaisons GTK de cette pile. Cette dépendance ne figure pas dans les graphes macOS et Windows. Aucun paquet Linux n’est prévu pour la première publication ; il faudra réévaluer l’alerte avant de distribuer sur Linux. L’alerte Dependabot reste ouverte jusqu’à une correction compatible en amont.
