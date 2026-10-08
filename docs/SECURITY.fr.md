# Sécurité et confidentialité

[Documentation](README.fr.md) · [English](SECURITY.md)

## Réseau local

La découverte et les commandes console utilisent UDP/TCP sans chiffrement.
L'appairage fournit un identifiant individuel : l'ordinateur conserve son
empreinte SHA-256, et la console le stocke sur sa carte SD. Révoquez une console
dans les réglages ordinateur pour lui retirer l'accès.

Utilisez un réseau local de confiance. N'exposez pas les ports 38122 et 38123 sur
Internet. Une personne capable d'inspecter le trafic peut observer les codes
d'appairage et les identifiants.

## Données locales et services facultatifs

La configuration peut contenir des chemins de fichiers, des identifiants OBS et
des réglages d'extension. Ne publiez pas votre configuration personnelle,
`paired-consoles.json`, le fichier console `settings.cfg` ou un journal contenant
des informations privées dans un signalement de bug.

Les paroles en ligne sont facultatives et désactivées par défaut. Leur activation
envoie le titre, l'artiste et les métadonnées album/durée disponibles à LRCLIB.
La console ne contacte pas ce service. Les recherches de mise à jour contactent
GitHub lorsqu'une clé publique est configurée. Voir les
[paroles](../apps/desktop/docs/LYRICS_AND_PAGE_TEMPLATES.md) et les [signatures](RELEASE.fr.md).

Le chat de stream est facultatif. L’ordinateur contacte Twitch via HTTPS/WebSocket
TLS ; les jetons restent dans le coffre d’identifiants système. Les messages
récents et les images des badges sont transmis aux consoles appairées par le protocole local.
Les badges officiels sont chargés depuis le CDN de Twitch sans identifiants OAuth. L’historique
reste en mémoire, sans enregistrement sur disque. Voir le [chat de stream](STREAM_CHAT.fr.md).

## Extensions

Importer un paquet ne l'exécute pas. L'activation exige l'approbation de son
empreinte SHA-256 ; modifier le paquet exige une nouvelle approbation.
Les extensions natives s'exécutent avec les droits de votre compte, dans un
processus séparé sans sandbox. Les permissions déclarées décrivent les accès
prévus, sans les restreindre techniquement. N'activez que du code de confiance.

## Signalement

Signalez les bugs ordinaires dans les issues GitHub ou sur
[Discord](https://discord.gg/EmdnneHeus). Pour une faille de sécurité, utilisez le
signalement privé du dépôt s'il est disponible. Ne publiez pas d'identifiants
ni de détails d'exploitation dans un ticket public.
