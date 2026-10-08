import type { Locale } from "../../frontend/src/app/types";
import { DeckIcon } from "../../frontend/src/components/DeckIcon";
import { Decky } from "../../frontend/src/components/Decky";
import { deviceShellStyle } from "../../frontend/src/editor/deviceShell";

type PreviewFeature = { key: string; icon: string; fr: string; en: string };

const previewLabels: Record<string, { fr: string; en: string }> = {
  media: { fr: "Médias", en: "Media" },
  lyrics_online: { fr: "Paroles", en: "Lyrics" },
  windows: { fr: "Applications", en: "Applications" },
  system_stats: { fr: "Système", en: "System" },
  notifications: { fr: "Alertes", en: "Alerts" },
  media_artwork: { fr: "Pochettes", en: "Artwork" },
};

export function ConsoleFeaturePreview({ features, locale }: { features: PreviewFeature[]; locale: Locale }) {
  const fr = locale === "fr";
  return <div className="onboarding-feature-console" style={deviceShellStyle} aria-hidden="true">
    <img src="/device-shell.svg" alt="" draggable={false} />
    <div className="onboarding-feature-console-top">
      <div className="onboarding-feature-console-status"><span>3Decks</span><DeckIcon name="wifi" /></div>
      <Decky mood="idle" size={44} />
      <strong>{fr ? "Votre console, vos choix" : "Your console, your way"}</strong>
      <span>{fr ? "Informations et contrôles à portée de main" : "Information and controls at your fingertips"}</span>
    </div>
    <div className="onboarding-feature-console-bottom">
      <div className="onboarding-feature-console-heading"><strong>{fr ? "Fonctions" : "Features"}</strong><span>•••</span></div>
      {features.length > 0 ? <div className="onboarding-feature-console-grid">
        {features.map((feature) => <div key={feature.key}><DeckIcon name={feature.icon} /><span>{previewLabels[feature.key]?.[locale] ?? (fr ? feature.fr : feature.en)}</span></div>)}
      </div> : <div className="onboarding-feature-console-empty"><DeckIcon name="grid" /><span>{fr ? "Choisissez vos fonctions" : "Choose your features"}</span></div>}
      <div className="onboarding-feature-console-dock"><DeckIcon name="star" /><i /><DeckIcon name="gear" /></div>
    </div>
  </div>;
}
