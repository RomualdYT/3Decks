import type { Locale } from "../app/types";

export function notificationPermissionError(access: string | undefined, error: string | undefined, locale: Locale): string {
  if (!error || locale !== "fr") return error ?? "";
  if (access === "Unavailable" && error.includes("packaged app identity")) {
    return "Cette fonction nécessite une installation Windows avec identité MSIX.";
  }
  if (access === "Denied") {
    return "Accès refusé. Autorisez 3Decks dans les paramètres de notifications Windows.";
  }
  return error;
}
