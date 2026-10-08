import { Button, Label, Radio, RadioGroup, Tooltip, toast } from "@heroui/react";
import { useCallback, useEffect, useRef, useState } from "react";
import type { AudioOutput } from "../app/desktopControls";
import type { Locale } from "../app/types";
import { DeckIcon } from "../components/DeckIcon";

export function AudioOutputSettings({ locale, windows }: { locale: Locale; windows: boolean }) {
  const [outputs, setOutputs] = useState<AudioOutput[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const requestId = useRef(0);
  const fr = locale === "fr";
  const refresh = useCallback(async () => {
    const controls = window.decksDesktopControls;
    if (!controls) return;
    const id = ++requestId.current;
    setLoading(true);
    try {
      const next = await controls.getAudioOutputs();
      if (id === requestId.current) { setOutputs(next); setError(""); }
    } catch (reason) {
      if (id === requestId.current) setError(reason instanceof Error ? reason.message : String(reason));
    } finally {
      if (id === requestId.current) setLoading(false);
    }
  }, []);
  useEffect(() => {
    void refresh();
    const onFocus = () => { void refresh(); };
    window.addEventListener("focus", onFocus);
    return () => { requestId.current++; window.removeEventListener("focus", onFocus); };
  }, [refresh]);
  const openSettings = () => {
    setBusy(true);
    void window.decksDesktopControls?.openAudioSettings()
      .catch((error: Error) => toast.danger(error.message))
      .finally(() => setBusy(false));
  };
  const select = (id: string) => {
    setBusy(true);
    void window.decksDesktopControls?.selectAudioOutput(id)
      .then(async () => { await refresh(); toast.success(fr ? "Sortie audio modifiée" : "Audio output changed"); })
      .catch((error: Error) => toast.danger(error.message))
      .finally(() => setBusy(false));
  };
  const activeOutput = outputs.find((output) => output.is_default);
  return <div className="feature-audio-output">
    <div className="feature-audio-output-heading">
      <strong>{fr ? "Sortie de lecture" : "Playback device"}</strong>
      <div className="feature-audio-output-actions">
        <Tooltip><Button size="sm" variant="ghost" isDisabled={loading || busy} onPress={() => void refresh()} aria-label={fr ? "Actualiser les sorties audio" : "Refresh audio outputs"}><DeckIcon name="refresh" size={16} /></Button><Tooltip.Content>{fr ? "Actualiser" : "Refresh"}</Tooltip.Content></Tooltip>
        {windows && <Button size="sm" variant="outline" isPending={busy} onPress={openSettings}><DeckIcon name="gear" size={14} />{fr ? "Réglages Son" : "Sound settings"}</Button>}
      </div>
    </div>
    {windows && <p className="feature-detail-note">{fr ? "La sortie par défaut se choisit dans les réglages Son de Windows." : "Choose the default output in Windows Sound settings."}</p>}
    {error ? <p className="feature-audio-output-error" role="alert">{error}</p> : loading && !outputs.length ? <p className="feature-detail-note" role="status">{fr ? "Recherche des sorties…" : "Looking for outputs…"}</p> : outputs.length === 0 ? <p className="feature-detail-note">{fr ? "Aucune sortie audio disponible." : "No audio outputs are available."}</p> : windows ? <div className="feature-audio-output-list">
      {outputs.map((output) => <div className={`feature-audio-output-row ${output.is_default ? "is-active" : ""}`} key={output.id}>
        <DeckIcon name="volume-up" size={18} /><span className="audio-output-name">{output.name}</span>
        {output.is_default && <span className="audio-output-active"><DeckIcon name="check" size={13} />Active</span>}
      </div>)}
    </div> : <RadioGroup className="feature-audio-output-list" aria-label={fr ? "Sortie audio de lecture" : "Playback audio output"} value={activeOutput?.id ?? ""} isDisabled={busy || loading} onChange={select}>
      {outputs.map((output) => <Radio value={output.id} key={output.id} className="feature-audio-output-option">
        <Radio.Content><DeckIcon name="volume-up" size={18} /><Label>{output.name}</Label>
          {output.is_default && <span className="audio-output-active">Active</span>}
          <Radio.Control><Radio.Indicator /></Radio.Control>
        </Radio.Content>
      </Radio>)}
    </RadioGroup>}
  </div>;
}
