import { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";
import "./style.css";

type Status = {
  running: boolean;
  error: string | null;
  tcp_port: number;
  discovery_port: number;
  pairing_code: string;
  connected: number;
  paired: number;
  config_revision: number;
  volume: number | null;
  windows_count: number;
  cpu: number | null;
  memory: number | null;
  last_event: string;
};

type ConfigDocument = { revision: number; pages: unknown[]; [key: string]: unknown };
type AudioOutput = { name: string; is_default: boolean };

function App() {
  const [status, setStatus] = useState<Status | null>(null);
  const [uiError, setUiError] = useState("");
  const [document, setDocument] = useState<ConfigDocument | null>(null);
  const [editorText, setEditorText] = useState("");
  const [saveState, setSaveState] = useState("");
  const [obsStatus, setObsStatus] = useState("");
  const [audioOutputs, setAudioOutputs] = useState<AudioOutput[]>([]);
  const [audioStatus, setAudioStatus] = useState("");
  const obsEnabled = Boolean((document?.integrations as { obs?: { enabled?: boolean } } | undefined)?.obs?.enabled);

  useEffect(() => {
    let active = true;
    const refresh = () => invoke<Status>("get_status")
      .then((value) => { if (active) { setStatus(value); setUiError(""); } })
      .catch((error) => { if (active) setUiError(String(error)); });
    void refresh();
    void invoke<ConfigDocument>("get_config").then((value) => {
      if (active) { setDocument(value); setEditorText(JSON.stringify(value, null, 2)); }
    }).catch((error) => { if (active) setUiError(String(error)); });
    const interval = window.setInterval(refresh, 1500);
    const unlisten = listen<Status>("backend-status", (event) => {
      if (active) setStatus(event.payload);
    });
    return () => {
      active = false;
      window.clearInterval(interval);
      void unlisten.then((off) => off());
    };
  }, []);

  async function saveConfig() {
    try {
      const candidate = JSON.parse(editorText) as ConfigDocument;
      const saved = await invoke<ConfigDocument>("save_config", { document: candidate });
      setDocument(saved);
      setEditorText(JSON.stringify(saved, null, 2));
      setSaveState(`Révision ${saved.revision} enregistrée et envoyée aux consoles.`);
      setUiError("");
    } catch (error) {
      setSaveState("");
      setUiError(String(error));
    }
  }

  async function importConfig(file: File | undefined) {
    if (!file) return;
    try {
      const imported = JSON.parse(await file.text()) as ConfigDocument;
      imported.revision = document?.revision ?? 0;
      setEditorText(JSON.stringify(imported, null, 2));
      setSaveState("Fichier chargé dans l’éditeur. Vérifiez-le avant d’enregistrer.");
      setUiError("");
    } catch (error) { setUiError(`Fichier JSON illisible : ${error}`); }
  }

  async function checkObs() {
    setObsStatus("Connexion à OBS…");
    try {
      const result = await invoke<{ obs_version: string; current_scene: string; scenes: string[] }>("get_obs_status");
      setObsStatus(`OBS ${result.obs_version} connecté · scène : ${result.current_scene || "—"} · ${result.scenes.length} scènes`);
    } catch (error) { setObsStatus(String(error)); }
  }

  async function refreshAudio() {
    try {
      setAudioOutputs(await invoke<AudioOutput[]>("get_audio_outputs"));
      setAudioStatus("");
    } catch (error) { setAudioStatus(String(error)); }
  }

  async function chooseAudio(name: string) {
    try {
      const selected = await invoke<string>("select_audio_output", { name });
      setAudioStatus(`Sortie active : ${selected}`);
      setAudioOutputs(await invoke<AudioOutput[]>("get_audio_outputs"));
    } catch (error) { setAudioStatus(String(error)); }
  }

  return <main>
    <header><span className="mark">3D</span><div><p className="eyebrow">PROTOTYPE NATIF · TAURI 2</p><h1>3Decks</h1></div></header>
    <p className="intro">Connectez votre Nintendo 3DS au serveur Rust expérimental.</p>
    <section className="card"><div className="row"><span>Serveur</span><strong className={status?.running ? "good" : "bad"}>{status?.running ? "Actif" : "Inactif"}</strong></div>
      <div className="row"><span>Découverte</span><code>UDP {status?.discovery_port ?? "—"}</code></div>
      <div className="row"><span>Connexion</span><code>TCP {status?.tcp_port ?? "—"}</code></div>
      <div className="row"><span>Consoles connectées</span><strong>{status?.connected ?? "—"}</strong></div>
      <div className="row"><span>Consoles appairées</span><strong>{status?.paired ?? "—"}</strong></div>
      <div className="row"><span>Configuration</span><strong>révision {status?.config_revision ?? "—"}</strong></div>
      <div className="row"><span>Volume système</span><strong>{status?.volume == null ? "—" : `${status.volume} %`}</strong></div>
      <div className="row"><span>Fenêtres détectées</span><strong>{status?.windows_count ?? "—"}</strong></div>
      <div className="row"><span>CPU</span><strong>{status?.cpu == null ? "—" : `${status.cpu} %`}</strong></div>
      <div className="row"><span>Mémoire</span><strong>{status?.memory == null ? "—" : `${status.memory} %`}</strong></div>
    </section>
    <section className="card pairing"><p className="eyebrow">CODE D’APPAIRAGE</p><p className="code">{status?.pairing_code ?? "······"}</p><p>Saisissez ce code sur la console. Il change après chaque appairage réussi.</p></section>
    <section className="card"><p className="eyebrow">DERNIER ÉVÉNEMENT</p><p>{status?.last_event || "En attente de la console…"}</p></section>
    <section className="card"><p className="eyebrow">INTÉGRATION OBS</p><p>{obsStatus || (obsEnabled ? "Activée dans la configuration" : "Désactivée dans la configuration")}</p><button type="button" onClick={() => void checkObs()}>Tester la connexion</button></section>
    <section className="card"><p className="eyebrow">SORTIES AUDIO</p><p>{audioStatus || "Sélectionnez une sortie audio macOS. La console reçoit aussi la liste et peut passer à la suivante."}</p>
      <button type="button" onClick={() => void refreshAudio()}>Afficher les sorties</button>
      {audioOutputs.map((output) => <div className="row" key={output.name}><span>{output.name}</span><button type="button" disabled={output.is_default} onClick={() => void chooseAudio(output.name)}>{output.is_default ? "Active" : "Choisir"}</button></div>)}
    </section>
    <section className="card editor"><p className="eyebrow">CONFIGURATION 3DS</p>
      <h2>Pages et actions</h2>
      <p>Modifiez le JSON ou importez une configuration 3Decks existante. Les actions non encore portées seront signalées sur la console.</p>
      <label className="import">Importer un fichier JSON<input type="file" accept="application/json,.json" onChange={(event) => { void importConfig(event.target.files?.[0]); event.target.value = ""; }} /></label>
      <textarea aria-label="Configuration JSON" spellCheck={false} value={editorText} onChange={(event) => { setEditorText(event.target.value); setSaveState(""); }} />
      <div className="editor-bottom"><span>{saveState}</span><button type="button" onClick={() => void saveConfig()} disabled={!document}>Enregistrer</button></div>
    </section>
    {status?.error && <p className="error">{status.error}</p>}{uiError && <p className="error">{uiError}</p>}
    <footer>Le serveur reste actif si vous fermez cette fenêtre. Quittez depuis l’icône de la barre des menus.</footer>
  </main>;
}

createRoot(document.getElementById("root")!).render(<App />);
