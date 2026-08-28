import { Spinner, Toast, toast } from "@heroui/react";
import { lazy, Suspense, useCallback, useEffect, useState } from "react";
import type { Locale, View } from "./types";
import { AppHeader } from "../components/AppHeader";
import { SaveBar } from "../components/SaveBar";
import { initialLocale, translate } from "../i18n/copy";
import { useDeckConfig } from "../hooks/useDeckConfig";

const EditorView = lazy(() => import("../editor/EditorView").then(({ EditorView }) => ({ default: EditorView })));
const SettingsView = lazy(() => import("../settings/SettingsView").then(({ SettingsView }) => ({ default: SettingsView })));
const StatusView = lazy(() => import("../status/StatusView").then(({ StatusView }) => ({ default: StatusView })));

export function App() {
  const deck = useDeckConfig();
  const [view, setView] = useState<View>("editor");
  const [locale, setLocaleState] = useState<Locale>(initialLocale);
  const [scenes, setScenes] = useState<string[]>([]);
  const t = useCallback((key: Parameters<typeof translate>[1], values?: Record<string, string | number>) => translate(locale, key, values), [locale]);
  const setLocale = useCallback((next: Locale) => {
    setLocaleState(next);
    document.documentElement.lang = next;
    try { localStorage.setItem("deck3ds.locale", next); } catch { /* temporary preference */ }
  }, []);
  useEffect(() => { document.documentElement.lang = locale; document.title = `3Decks — ${t(view)}`; }, [locale, t, view]);
  useEffect(() => {
    const guard = (event: BeforeUnloadEvent) => { if (deck.dirty) event.preventDefault(); };
    window.addEventListener("beforeunload", guard);
    return () => window.removeEventListener("beforeunload", guard);
  }, [deck.dirty]);
  useEffect(() => {
    if (!deck.notice) return;
    toast.success(locale === "fr" ? "Configuration enregistrée" : "Configuration saved", { description: locale === "fr" ? "La console recevra la nouvelle disposition automatiquement." : "The console will receive the new layout automatically." });
    deck.setNotice("");
  }, [deck.notice, deck.setNotice, locale]);
  useEffect(() => {
    if (!deck.error || deck.loading || !deck.config) return;
    toast.danger(locale === "fr" ? "Impossible d’enregistrer" : "Unable to save", { description: deck.error });
    deck.setError("");
  }, [deck.config, deck.error, deck.loading, deck.setError, locale]);

  if (deck.loading) return <div className="loading-screen"><img src="/3decks-logo.png" alt="3Decks" /><Spinner size="lg" /><p>Préparation de votre console…</p></div>;
  if (!deck.config || !deck.schema) return <div className="loading-screen error"><img src="/3decks-logo.png" alt="3Decks" /><h1>3Decks</h1><p>{t("loadError", { message: deck.error || "Agent indisponible" })}</p><button type="button" onClick={() => void deck.reload()}>Réessayer</button></div>;
  return <div className="app-shell">
    <Toast.Provider placement="bottom end" />
    <AppHeader view={view} locale={locale} status={deck.status} t={t} onView={setView} onLocale={setLocale} />
    <Suspense fallback={<div className="view-loading"><Spinner /><span>{locale === "fr" ? "Chargement de la vue…" : "Loading view…"}</span></div>}>
      {view === "editor" && <EditorView config={deck.config} schema={deck.schema} status={deck.status} apps={deck.apps} locale={locale} scenes={scenes} t={t} update={deck.update} />}
      {view === "settings" && <SettingsView config={deck.config} schema={deck.schema} status={deck.status} locale={locale} scenes={scenes} t={t} update={deck.update} onLocale={setLocale} onScenes={setScenes} />}
      {view === "status" && <StatusView status={deck.status} locale={locale} t={t} />}
    </Suspense>
    <SaveBar dirty={deck.dirty} saving={deck.saving} locale={locale} onSave={() => void deck.save()} onReset={deck.reset} />
  </div>;
}
