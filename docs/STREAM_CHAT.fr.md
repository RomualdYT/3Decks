# Chat de stream

[Documentation](README.fr.md) · [English](STREAM_CHAT.md)

Lisez le chat Twitch sur l’écran supérieur de la 3DS et gardez les commandes OBS
sur l’écran tactile. Les deux connexions sont indépendantes : OBS n’a pas besoin
d’être ouvert pour lire le chat.

## Connexion

1. Ouvrez **Réglages → Streaming** dans l’application macOS ou Windows.
2. Cliquez sur **Connecter Twitch**. Twitch s’ouvre dans votre navigateur :
   confirmez le code affiché et autorisez la lecture du chat. La connexion active
   également le chat.
3. Votre chaîne est sélectionnée si aucune chaîne n’était configurée. Pour
   afficher un autre chat, saisissez son nom, `@pseudo` ou son lien Twitch, puis
   enregistrez. **Utiliser ma chaîne** rétablit votre chaîne sans changer de compte.
4. Dans l’éditeur, ajoutez le modèle **Streaming**, ou choisissez **Chat de
   stream** comme écran supérieur d’une page. Enregistrez les pages.

Le compte connecté autorise la lecture ; la chaîne du chat choisit les messages
à afficher. La changer n’abonne pas votre compte à un streamer sur Twitch.

Les versions officielles de 3Decks intègrent le Client ID public de Twitch.
Les utilisateurs connectent simplement leur compte Twitch ; aucune inscription
développeur ni aucun Client Secret n’est nécessaire.

Pour distribuer un fork comme une autre application, enregistrez votre propre
application de type **Public** dans la
[console développeur Twitch](https://dev.twitch.tv/console/apps).
Remplacez l’identifiant intégré avec `DECKS_TWITCH_CLIENT_ID` à la compilation ;
le workflow de release lit la variable de dépôt portant ce nom. Les utilisateurs
n’ont pas d’application Twitch à configurer. Une ancienne configuration locale
personnalisée peut être réinitialisée dans les réglages.

## Lecture

- **X :** suspendre ou reprendre le défilement automatique sur la console.
- **Croix haut/bas pendant la pause :** parcourir les messages récents.
- **Y :** revenir aux nouveaux messages.
- L’aperçu PC propose également un bouton pause/reprise.

Le lecteur conserve les 20 derniers messages. Le texte occupe jusqu’à deux lignes
par message sur la console ; les messages longs sont raccourcis. Le texte compact
permet d’en afficher davantage. L’horodatage facultatif utilise UTC ; le filtre
des commandes masque les nouveaux messages commençant par `!`. Les badges Twitch officiels apparaissent à côté des pseudos, y compris les
badges personnalisés d’abonné et de Bits. Jusqu’à trois badges sont affichés
par message ; les images sont chargées en arrière-plan et conservées dans un
cache mémoire borné. Les émotes
apparaissent sous leur nom textuel. Les suppressions de messages et les effacements
du chat s’appliquent aussi pendant la pause du défilement.

Seuls les nouveaux messages reçus après la connexion sont disponibles. Un chat
connecté ne signifie pas que la chaîne diffuse : le chat Twitch reste utilisable
hors diffusion. Changer de chaîne efface l’historique de la précédente.

## Connexion et confidentialité

L’ordinateur utilise l’autorisation Twitch par code avec la permission
`user:read:chat` et EventSub WebSocket. Les identifiants restent dans le Trousseau
macOS ou le Gestionnaire d’identifiants Windows, séparément de la configuration
de l’éditeur. Ils ne sont jamais envoyés à la console. Déconnecter le compte
supprime les identifiants stockés localement.

Les messages restent en mémoire et sont transmis aux consoles appairées par la
connexion locale existante. Ils ne sont pas enregistrés sur disque. Les coupures
déclenchent une reconnexion avec attente progressive ; les jetons expirés sont
renouvelés. Une nouvelle autorisation peut être nécessaire après révocation de
l’accès ou expiration du jeton de renouvellement.

Voir le [guide anglais](STREAM_CHAT.md#implementation) pour l’arborescence technique.
YouTube et l’envoi de messages ne sont pas implémentés.
