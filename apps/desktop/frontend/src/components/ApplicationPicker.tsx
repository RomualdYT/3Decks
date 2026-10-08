import { Button, toast } from "@heroui/react";
import { useState } from "react";
import { agentApi } from "../api/client";
import type { Locale } from "../app/types";
import { ComboControl } from "./FormControls";
import { DeckIcon } from "./DeckIcon";

export function ApplicationPicker({ value, choices, locale, onChange }: { value: string; choices: string[]; locale: Locale; onChange: (value: string) => void }) {
  const [picking, setPicking] = useState(false);
  const fr = locale === "fr";
  const pick = async () => {
    setPicking(true);
    try {
      const result = await agentApi.pickPath("file");
      if (!result.cancelled && result.path) onChange(result.path);
    } catch (error) {
      toast.danger(fr ? "Sélection impossible" : "Selection failed", { description: error instanceof Error ? error.message : String(error) });
    } finally {
      setPicking(false);
    }
  };
  return <div className="application-picker">
    <ComboControl label={fr ? "Application" : "Application"} value={value} choices={choices} onChange={onChange}
      description={fr ? "Choisissez une application détectée ou saisissez un nom, un chemin ou un protocole." : "Choose a detected app or enter a name, path or protocol."}
      placeholder={fr ? "Nom de l’application ou chemin complet…" : "Application name or full path…"} />
    <Button variant="outline" isDisabled={picking} onPress={() => { void pick(); }}>
      <DeckIcon name="folder" size={17} />
      {picking ? (fr ? "Ouverture…" : "Opening…") : (fr ? "Choisir une application…" : "Choose an application…")}
    </Button>
  </div>;
}
