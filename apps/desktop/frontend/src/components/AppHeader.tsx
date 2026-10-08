import type { AgentState, Locale, View } from "../app/types";
import type { CopyKey } from "../i18n/copy";
import { ConsoleStatusBadge } from "./ConsoleStatusBadge";
import { DeckIcon } from "./DeckIcon";
import { DeckyLogo } from "./Decky";
import { WindowControls } from "./WindowControls";

interface Props {
  view: View;
  locale: Locale;
  status: AgentState | null;
  t: (key: CopyKey, values?: Record<string, string | number>) => string;
  onView: (view: View) => void;
  onLocale: (locale: Locale) => void;
}

export function AppHeader({ view, locale, status, t, onView, onLocale }: Props) {
  return (
    <header className="app-header" data-tauri-drag-region="deep">
      <button className="brand" type="button" onClick={() => onView("editor")} aria-label="3Decks">
        <DeckyLogo />
        <span>3Decks</span>
      </button>
      <nav className="main-nav" aria-label={locale === "fr" ? "Navigation principale" : "Main navigation"}>
        {(["editor", "settings", "extensions", "status"] as View[]).map((item) => (
          <button key={item} className={view === item ? "active" : ""} type="button" onClick={() => onView(item)}>
            <DeckIcon name={item === "extensions" ? "extension" : item === "status" ? "status" : item === "settings" ? "gear" : "grid"} size={17} />
            {t(item)}
          </button>
        ))}
      </nav>
      <div className="header-actions">
        <ConsoleStatusBadge status={status} locale={locale} onOpenSettings={() => onView("settings")} />
        <div className="language-switch" aria-label={t("language")}>
          <button type="button" className={locale === "fr" ? "active" : ""} onClick={() => onLocale("fr")}>FR</button>
          <button type="button" className={locale === "en" ? "active" : ""} onClick={() => onLocale("en")}>EN</button>
        </div>
        <WindowControls locale={locale} />
      </div>
    </header>
  );
}
