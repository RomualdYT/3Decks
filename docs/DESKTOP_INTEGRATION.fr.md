# Menu système de 3Decks

[Documentation](README.fr.md) · [English](DESKTOP_INTEGRATION.md)

L’installation graphique maintient 3Decks dans la **barre des menus macOS** ou
la **zone de notification Windows**. L’éditeur reste une page locale dans le
navigateur ; le menu est le point d’entrée léger qui permet de contrôler
l’agent sans garder cette page ouverte.

## Expérience utilisateur

L’icône représente les deux écrans de la console. Sa couleur donne un repère
rapide : vert `#66CB10` lorsqu’une console est reliée, gris lorsqu’aucune console
n’est présente ou lorsque les commandes sont suspendues, orange si un composant
demande de l’attention. Le texte du menu suit automatiquement le français ou
l’anglais de l’OS.

Le menu propose :

- l’état de l’agent et le nombre de consoles ;
- l’ouverture de 3Decks ou de l’assistant de connexion ;
- la suspension des commandes pendant 15 minutes, une heure ou sans limite ;
- les réglages rapides pour notifications, médias, fenêtres, performances et OBS ;
- le démarrage à l’ouverture de session ;
- le diagnostic, l’adresse de connexion, le journal et le redémarrage ;
- la recherche de mise à jour et l’arrêt complet.

Suspendre les commandes ne déconnecte pas la console : les écrans continuent à
se mettre à jour, mais les actions tactiles et les valeurs sont refusées avec un
message compréhensible. Les réglages rapides sont persistants et apparaissent
automatiquement dans l’éditeur si celui-ci n’a aucune modification en cours.

Désactiver les médias conserve les choix individuels de lecteurs/pochettes.
Le journal tourne pendant l’exécution (2 Mio actifs et une sauvegarde). Les
opérations système en arrière-plan sont bornées à quatre ; le compte à rebours
seul ne reconstruit pas le menu chaque seconde.

## Architecture pour les mainteneurs

Le dossier `agent/backend/deck3ds/desktop` est volontairement autonome :

| Module | Rôle |
|---|---|
| `models.py` | contrats immuables entre contrôleur et menu |
| `application.py` | cycle de vie, passerelle thread-safe et actions |
| `tray.py` | construction du menu et rendu de l’icône uniquement |
| `autostart.py` | LaunchAgent macOS et raccourci Démarrage Windows |
| `instance.py` | verrou par configuration et réouverture de l’instance |
| `system.py` | navigateur, presse-papiers et ouverture de journal |
| `logging.py` | journal persistant avec rotation bornée |
| `translations.py` | libellés natifs FR/EN |

Pour ajouter une commande, étendre d’abord `TrayActions`, l’implémenter dans
`DesktopController`, puis la rendre dans `PystrayTray`. Une mutation métier doit
appeler un service existant ou nouveau ; elle ne doit pas modifier directement
le JSON, un client TCP ou un composant React. Le menu ne reçoit que des
`DesktopSnapshot`, jamais l’objet runtime mutable.

`pystray` impose la boucle native au thread principal sur macOS. Le runtime
conserve une unique boucle `asyncio` dans un thread non-daemon. Les callbacks du
menu ne doivent donc jamais attendre une opération : `_submit()` sert aux
coroutines et `_background()` aux petites opérations système synchrones.

## Qualification native

### Arrêt depuis un lanceur

`deck3ds --stop` demande l’arrêt de l’instance graphique associée à la
configuration sélectionnée et attend jusqu’à 30 secondes la libération de son
verrou. Utiliser le même `--config` qu’au lancement s’il est personnalisé.
L’absence d’instance est un succès ; un délai dépassé renvoie un code non nul.
Le contrôle utilise un fichier privé et un identifiant aléatoire par lancement,
pas un endpoint HTTP ou la terminaison d’un PID. Les installateurs abandonnent
la mise à jour si l’arrêt ne se termine pas. Une ancienne version sans ce
contrôle doit être quittée manuellement depuis son menu. Le mode sans menu
système conserve son arrêt habituel (Ctrl+C/service).

Avant une publication, vérifier sur macOS et Windows : apparition et mise à jour
de l’icône, menu FR/EN, connexion/déconnexion réelle d’une 3DS, pause temporisée,
persistance de chaque réglage rapide, second lancement, démarrage de session,
redémarrage, journal et arrêt sans processus restant. Sur Windows, tester aussi
le menu depuis le MSIX Store, car l’identité nécessaire aux notifications ne
peut pas être reproduite par le wheel GitHub.

[Installation](INSTALLATION.fr.md) · [Architecture](ARCHITECTURE.fr.md) ·
[Qualification](QUALIFICATION.fr.md)
