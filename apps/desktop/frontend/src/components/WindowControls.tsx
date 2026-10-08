import { useEffect, useState } from "react";
import { Copy, Minus, Square, X } from "lucide-react";
import type { Locale } from "../app/types";
import type {} from "../app/desktopControls";

export function WindowControls({ locale }: { locale: Locale }) {
  const frame = window.decksDesktopControls?.windowFrame;
  const [maximized, setMaximized] = useState(false);
  const [error, setError] = useState("");
  const fr = locale === "fr";
  useEffect(() => {
    if (!frame) return;
    let active = true;
    const refresh = () => { void frame.isMaximized().then(value => { if (active) setMaximized(value); }).catch(() => {}); };
    refresh();
    window.addEventListener("resize", refresh);
    return () => { active = false; window.removeEventListener("resize", refresh); };
  }, [frame]);
  if (!frame) return null;
  const run = (action: () => Promise<void>) => {
    setError("");
    void action().catch(reason => setError(String(reason)));
  };
  const maximizeLabel = maximized ? (fr ? "Restaurer la fenêtre" : "Restore window") : (fr ? "Agrandir la fenêtre" : "Maximize window");
  return <div className="window-controls" role="group" aria-label={fr ? "Contrôles de la fenêtre" : "Window controls"}>
    <button type="button" title={fr ? "Réduire la fenêtre" : "Minimize window"} aria-label={fr ? "Réduire la fenêtre" : "Minimize window"} onClick={() => run(frame.minimize)}><Minus size={16} aria-hidden="true" /></button>
    <button type="button" title={maximizeLabel} aria-label={maximizeLabel} onClick={() => run(frame.toggleMaximize)}>{maximized ? <Copy size={14} aria-hidden="true" /> : <Square size={14} aria-hidden="true" />}</button>
    <button type="button" className="window-close" title={fr ? "Fermer la fenêtre — 3Decks reste actif dans le tray" : "Close window — 3Decks stays active in the tray"} aria-label={fr ? "Fermer la fenêtre" : "Close window"} onClick={() => run(frame.close)}><X size={17} aria-hidden="true" /></button>
    {error && <span className="window-control-error" role="alert">{error}</span>}
  </div>;
}
