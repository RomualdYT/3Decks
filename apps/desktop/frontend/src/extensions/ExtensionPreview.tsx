import type { AgentState, Locale, Localized } from "../app/types";
import { DeckIcon } from "../components/DeckIcon";
import { localized } from "../utils/config";

interface Panel {
  title: Localized;
  status: string;
  cards: Array<{
    label: Localized;
    value: string;
    detail: Localized;
    progress?: number;
  }>;
}
export interface SourceItem {
  id: string;
  label: Localized;
  detail: Localized;
  icon: string;
  color: string;
  active: boolean;
}

export function extensionSource(
  status: AgentState | null,
  source: string,
): SourceItem[] {
  const sources = status?.snapshot?.extension_sources as
    Record<string, SourceItem[]> | undefined;
  return sources?.[source] ?? [];
}

export function ExtensionPreview({
  dashboard,
  status,
  locale,
}: {
  dashboard: string;
  status: AgentState | null;
  locale: Locale;
}) {
  const panels = status?.snapshot?.extension_previews as
    Record<string, Panel> | undefined;
  const panel = panels?.[dashboard];
  if (!panel)
    return (
      <div className="top-empty">
        <DeckIcon name="extension" size={24} />
        <strong>
          {locale === "fr" ? "Écran d’extension" : "Extension screen"}
        </strong>
        <span>
          {locale === "fr"
            ? "Activez cette intégration dans Extensions pour afficher ses données."
            : "Enable this integration in Extensions to show its data."}
        </span>
      </div>
    );
  return (
    <div className={`top-extension ${panel.status}`}>
      <div className="top-title">
        <DeckIcon name="extension" size={14} />
        <strong>{localized(panel.title, locale)}</strong>
        <i />
      </div>
      <div className="extension-preview-cards">
        {panel.cards.map((card, index) => (
          <div key={index}>
            <small>{localized(card.label, locale)}</small>
            <strong>{card.value}</strong>
            <span>{localized(card.detail, locale)}</span>
            {typeof card.progress === "number" && (
              <progress max={100} value={card.progress} />
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
