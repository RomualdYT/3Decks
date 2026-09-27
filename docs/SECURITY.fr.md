# Sécurité

Chaque console est appairée par code puis reçoit un jeton individuel. La découverte UDP et le protocole TCP sont conçus pour un réseau local de confiance ; ils ne sont pas chiffrés. N’exposez pas les ports 38122 et 38123 sur Internet. Limitez l’accès par pare-feu si le réseau est partagé.

Les extensions natives s’exécutent avec les droits de l’utilisateur après approbation explicite. La mise à jour vérifie les paquets avec une clé publique embarquée ; la clé privée reste dans l’infrastructure de publication. Voir le [guide de publication](RELEASE.md).
