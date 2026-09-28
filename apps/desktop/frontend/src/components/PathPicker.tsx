import { Button, Disclosure, toast } from "@heroui/react";
import { useState } from "react";
import { agentApi } from "../api/client";
import type { Locale } from "../app/types";
import { DeckIcon } from "./DeckIcon";
import { TextControl } from "./FormControls";

type PathKind = "file" | "folder";

function itemName(path: string): string {
  const segments = path.split(/[\\/]/).filter(Boolean);
  return segments.at(-1) ?? path;
}

export function PathPicker({ value, locale, onChange }: { value: string; locale: Locale; onChange: (value: string) => void }) {
  const [picking, setPicking] = useState<PathKind | null>(null);
  const fr = locale === "fr";

  const pick = (kind: PathKind) => {
    setPicking(kind);
    void agentApi.pickPath(kind)
      .then((result) => {
        if (!result.cancelled && result.path) onChange(result.path);
      })
      .catch((error: Error) => toast.danger(fr ? "Sélection impossible" : "Selection failed", { description: error.message }))
      .finally(() => setPicking(null));
  };

  return (
    <div className="path-picker">
      <span className="field-label">{fr ? "Élément à ouvrir" : "Item to open"}</span>
      <div className={`path-selection ${value ? "selected" : "empty"}`}>
        <span className="path-selection-icon"><DeckIcon name={value ? "folder" : "plus"} size={20} /></span>
        <div className="path-selection-copy">
          <strong>{value ? itemName(value) : (fr ? "Aucun élément choisi" : "No item selected")}</strong>
          <small title={value}>{value || (fr ? "Choisissez-le directement sur cet ordinateur." : "Choose it directly on this computer.")}</small>
        </div>
        {value ? <Button size="sm" variant="ghost" onPress={() => onChange("")}><DeckIcon name="close" size={14} />{fr ? "Retirer" : "Clear"}</Button> : null}
      </div>

      <div className="path-picker-actions">
        <Button variant="outline" isDisabled={picking !== null} onPress={() => pick("file")}>
          <DeckIcon name="page" size={17} />
          {picking === "file" ? (fr ? "Ouverture…" : "Opening…") : (fr ? "Choisir un fichier" : "Choose a file")}
        </Button>
        <Button variant="outline" isDisabled={picking !== null} onPress={() => pick("folder")}>
          <DeckIcon name="folder" size={17} />
          {picking === "folder" ? (fr ? "Ouverture…" : "Opening…") : (fr ? "Choisir un dossier" : "Choose a folder")}
        </Button>
      </div>
      <p className="path-picker-help"><DeckIcon name="info" size={13} />{fr ? "Une fenêtre macOS ou Windows va s’ouvrir. Vous n’avez aucun chemin à écrire." : "A macOS or Windows window will open. You do not need to type a path."}</p>

      <Disclosure className="advanced-disclosure path-manual">
        <Disclosure.Heading><Disclosure.Trigger><span><DeckIcon name="keyboard" size={15} />{fr ? "Saisir un chemin manuellement" : "Enter a path manually"}</span><Disclosure.Indicator /></Disclosure.Trigger></Disclosure.Heading>
        <Disclosure.Content><Disclosure.Body><TextControl label={fr ? "Chemin complet" : "Full path"} value={value} description={fr ? "Réservé aux chemins réseau ou aux emplacements qui n’apparaissent pas dans le sélecteur." : "For network paths or locations that do not appear in the picker."} placeholder={fr ? "Ex. /Users/moi/Documents/fichier.pdf" : "e.g. C:\\Users\\me\\Documents\\file.pdf"} onChange={onChange} /></Disclosure.Body></Disclosure.Content>
      </Disclosure>
    </div>
  );
}
