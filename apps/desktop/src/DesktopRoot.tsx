import { invoke } from "@tauri-apps/api/core";
import { useCallback, useEffect, useState } from "react";
import { App as EditorApp } from "../frontend/src/app/App";
import { Decky } from "../frontend/src/components/Decky";
import { Onboarding } from "./onboarding/Onboarding";
import "./onboarding/onboarding.css";

if (navigator.userAgent.includes("Macintosh")) {
  document.documentElement.classList.add("desktop-macos");
}

window.decksDesktopControls = {
  openCommunity: () => invoke<void>("open_community"),
  getAutostart: () => invoke<boolean>("get_autostart"),
  setAutostart: (enabled) => invoke<boolean>("set_autostart", { enabled }),
  getUpdateCapability: () => invoke<{ configured: boolean; version: string }>("get_update_capability"),
  checkForUpdates: () => invoke<{ available: boolean; version: string; notes?: string }>("check_for_updates"),
  installUpdate: () => invoke<void>("install_update"),
  getAudioOutputs: () => invoke("get_audio_outputs"),
  selectAudioOutput: (id) => invoke<string>("select_audio_output", { id }),
  openAudioSettings: () => invoke<void>("open_audio_settings"),
  requestNotificationAccess: () => invoke("request_notification_access"),
};

export type OnboardingProgress = { step: number; completed: boolean };

export function App() {
  const [progress, setProgress] = useState<OnboardingProgress | null>(null);
  const [error, setError] = useState("");
  const load = useCallback(() => {
    void invoke<OnboardingProgress>("get_onboarding")
      .then((value) => { setProgress(value); setError(""); })
      .catch((reason) => setError(String(reason)));
  }, []);
  useEffect(load, [load]);
  useEffect(() => {
    const restart = () => {
      void invoke<OnboardingProgress>("save_onboarding", { step: 0, completed: false })
        .then((value) => { setProgress(value); setError(""); })
        .catch((reason) => setError(String(reason)));
    };
    window.addEventListener("decks-open-onboarding", restart);
    return () => window.removeEventListener("decks-open-onboarding", restart);
  }, []);
  if (error) return <div className="onboarding-load"><Decky mood="confused" size={96} /><strong>3Decks</strong><p>{error}</p><button type="button" onClick={load}>Réessayer</button></div>;
  if (!progress) return <div className="onboarding-load"><Decky mood="search" size={96} /><strong>3Decks</strong><p>Préparation de 3Decks…</p></div>;
  return progress.completed ? <><EditorApp /><UpdateNotice /></> : <Onboarding initialStep={progress.step} onComplete={setProgress} />;
}

function UpdateNotice() {
  const [version, setVersion] = useState("");
  const [installing, setInstalling] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    const timer = window.setTimeout(() => {
      void window.decksDesktopControls?.getUpdateCapability()
        .then((capability) => capability.configured ? window.decksDesktopControls?.checkForUpdates() : null)
        .then((update) => { if (active && update?.available) setVersion(update.version); })
        .catch(() => {});
    }, 12000);
    return () => { active = false; window.clearTimeout(timer); };
  }, []);
  if (!version) return null;
  return <div className="desktop-update-notice" role="status"><div><strong>3Decks {version} est disponible</strong><p>{error || "Une mise à jour signée est prête à être installée."}</p></div><button type="button" disabled={installing} onClick={() => { setInstalling(true); setError(""); void window.decksDesktopControls?.installUpdate().catch((reason) => { setError(String(reason)); setInstalling(false); }); }}>{installing ? "Installation…" : "Installer"}</button><button type="button" aria-label="Plus tard" onClick={() => setVersion("")}>×</button></div>;
}
