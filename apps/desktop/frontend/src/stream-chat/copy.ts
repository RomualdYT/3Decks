import type { Locale } from "../app/types";

const STATUS: Record<string, [string, string]> = {
  disabled: ["Chat disabled", "Chat désactivé"],
  connecting: ["Connecting to Twitch…", "Connexion à Twitch…"],
  connected: ["Connected", "Connecté"],
  token_expired: [
    "Refreshing Twitch connection…",
    "Actualisation de la connexion Twitch…",
  ],
  reconnecting: ["Reconnecting…", "Reconnexion…"],
  awaiting_authorization: [
    "Waiting for Twitch authorization",
    "En attente de l’autorisation Twitch",
  ],
  authorization_required: [
    "Connect your Twitch account",
    "Connectez votre compte Twitch",
  ],
  authorization_denied: ["Authorization was declined", "Autorisation refusée"],
  authorization_expired: [
    "The code expired. Connect again.",
    "Le code a expiré. Reconnectez-vous.",
  ],
  authorization_cancelled: ["Connection cancelled", "Connexion annulée"],
  client_id_required: [
    "Twitch application setup needed",
    "Configuration de l’application Twitch requise",
  ],
  invalid_client_id: [
    "Enter a valid public Client ID",
    "Saisissez un Client ID public valide",
  ],
  invalid_channel: [
    "Enter a Twitch channel name or channel URL",
    "Saisissez le nom ou le lien d’une chaîne Twitch",
  ],
  channel_required: ["Choose a Twitch channel", "Choisissez une chaîne Twitch"],
  channel_not_found: [
    "This Twitch channel was not found",
    "Cette chaîne Twitch est introuvable",
  ],
  rate_limited: [
    "Twitch is busy. Reconnecting shortly…",
    "Twitch est sollicité. Reconnexion dans un instant…",
  ],
  twitch_unavailable: [
    "Twitch is unavailable. Retrying…",
    "Twitch est indisponible. Nouvelle tentative…",
  ],
  invalid_twitch_response: [
    "Unable to read Twitch’s response",
    "Impossible de lire la réponse de Twitch",
  ],
  credential_store_unavailable: [
    "Unable to access the system credential store",
    "Impossible d’accéder au coffre d’identifiants système",
  ],
  invalid_chat_settings: [
    "Chat settings could not be loaded. Save your settings again.",
    "Les réglages du chat n’ont pas pu être lus. Enregistrez-les à nouveau.",
  ],
  chat_settings_unavailable: [
    "Unable to save chat settings",
    "Impossible d’enregistrer les réglages du chat",
  ],
  unsupported_platform: [
    "Available in the macOS and Windows app",
    "Disponible dans l’application macOS et Windows",
  ],
};

export function chatStatus(status: string, locale: Locale): string {
  const text = STATUS[status] ?? ["Chat unavailable", "Chat indisponible"];
  return text[locale === "fr" ? 1 : 0];
}
