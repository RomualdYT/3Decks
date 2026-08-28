import { Button, Input } from "@heroui/react";
import { useMemo, useState } from "react";
import type { ActionSpec, Locale } from "../app/types";
import type { CopyKey } from "../i18n/copy";
import { DeckIcon } from "../components/DeckIcon";

const CATEGORIES = [
  ["essential", { fr: "Essentiels", en: "Essentials" }],
  ["audio", { fr: "Audio", en: "Audio" }],
  ["media", { fr: "Média", en: "Media" }],
  ["apps", { fr: "Applications", en: "Applications" }],
  ["obs", { fr: "OBS Studio", en: "OBS Studio" }],
  ["navigation", { fr: "Navigation", en: "Navigation" }],
  ["advanced", { fr: "Avancé", en: "Advanced" }],
] as const;

interface Props {
  open: boolean;
  locale: Locale;
  actions: ActionSpec[];
  title: string;
  t: (key: CopyKey, values?: Record<string, string | number>) => string;
  onPick: (action: ActionSpec) => void;
  onClose: () => void;
}

export function ActionPicker({ open, locale, actions, title, t, onPick, onClose }: Props) {
  const [category, setCategory] = useState("essential");
  const [query, setQuery] = useState("");
  const matches = useMemo(() => {
    const needle = query.trim().toLocaleLowerCase(locale);
    return actions.filter((action) => action.kind !== "noop" && (needle
      ? `${action.kind} ${action.title.fr} ${action.title.en} ${action.description.fr} ${action.description.en}`.toLocaleLowerCase(locale).includes(needle)
      : action.category === category));
  }, [actions, category, locale, query]);
  if (!open) return null;
  return (
    <>
      <button className="drawer-backdrop" type="button" aria-label={t("close")} onClick={onClose} />
      <aside className="action-drawer" aria-modal="true" role="dialog" aria-label={title}>
        <div className="drawer-header"><div><span className="eyebrow">3Decks</span><h2>{title}</h2></div><Button isIconOnly variant="ghost" aria-label={t("close")} onPress={onClose}><DeckIcon name="close" /></Button></div>
        <div className="drawer-search"><DeckIcon name="globe" size={18} /><Input autoFocus fullWidth aria-label={t("searchActions")} placeholder={t("searchActions")} value={query} onChange={(event) => setQuery(event.target.value)} /></div>
        <div className="action-browser">
          <nav className="category-nav" aria-label="Catégories">
            {CATEGORIES.map(([id, label]) => <button key={id} type="button" className={!query && category === id ? "active" : ""} onClick={() => { setCategory(id); setQuery(""); }}>{label[locale]}</button>)}
          </nav>
          <div className="action-results">
            {matches.map((action) => (
              <button type="button" className="action-card" key={action.kind} onClick={() => onPick(action)}>
                <span className="action-card-icon" style={{ "--action-color": action.color } as React.CSSProperties}><DeckIcon name={action.icon} /></span>
                <span><strong>{action.title[locale]}</strong><small>{action.description[locale]}</small></span>
                <span className={`availability ${action.supported ? "" : "off"}`}>{t(action.supported ? "available" : "setup")}</span>
              </button>
            ))}
          </div>
        </div>
        <div className="drawer-footer"><DeckIcon name="info" size={18} /><p>{t("actionHelp")}</p></div>
      </aside>
    </>
  );
}
