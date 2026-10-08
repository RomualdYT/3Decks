import { Button, Input, Modal, TextField } from "@heroui/react";
import { useState } from "react";
import type { Locale } from "../app/types";
import type { Choice } from "../components/FormControls";
import { DeckIcon } from "../components/DeckIcon";

type Props = { value: string; choices: Choice[]; locale: Locale; onChange: (value: string) => void };

export function TopScreenPicker({ value, choices, locale, onChange }: Props) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const fr = locale === "fr";
  const selected = choices.find((choice) => choice.id === value);
  const needle = query.trim().toLocaleLowerCase(locale);
  const matches = choices.filter((choice) => `${choice.label} ${choice.description ?? ""} ${choice.group ?? ""}`.toLocaleLowerCase(locale).includes(needle));
  const groups = Array.from(new Set(matches.map((choice) => choice.group ?? "3Decks")));
  const label = fr ? "Informations affichées en haut" : "Information shown on top";
  const changeOpen = (next: boolean) => { setOpen(next); if (!next) setQuery(""); };

  return <Modal isOpen={open} onOpenChange={changeOpen}>
    <div className="top-screen-picker-field">
      <span>{label}</span>
      <Button variant="outline" className="top-screen-picker-trigger" onPress={() => changeOpen(true)} aria-haspopup="dialog">
        <span className="choice-icon"><DeckIcon name={selected?.icon ?? "monitor"} size={18} /></span>
        <span className="choice-copy"><strong>{selected?.label ?? value}</strong>{selected?.description && <small>{selected.description}</small>}</span>
        <DeckIcon name="down" size={16} />
      </Button>
    </div>
    <Modal.Backdrop>
      <Modal.Container size="lg">
        <Modal.Dialog className="top-screen-picker-modal">
          <Modal.CloseTrigger aria-label={fr ? "Fermer" : "Close"} />
          <Modal.Header>
            <Modal.Icon><DeckIcon name="monitor" size={24} /></Modal.Icon>
            <div><Modal.Heading>{fr ? "Choisir l’écran supérieur" : "Choose a top screen"}</Modal.Heading><p>{fr ? "Choisissez ce que cette page affiche sur l’écran du haut de la console." : "Choose what this page shows on the console’s top screen."}</p></div>
          </Modal.Header>
          <TextField className="ui-field top-screen-picker-search" fullWidth aria-label={fr ? "Rechercher un écran" : "Search screens"} value={query} onChange={setQuery}>
            <Input autoFocus placeholder={fr ? "Rechercher un écran ou une extension…" : "Search screens or extensions…"} />
          </TextField>
          <Modal.Body>
            {!matches.length && <p className="top-screen-picker-empty">{fr ? "Aucun écran ne correspond à votre recherche." : "No screens match your search."}</p>}
            {groups.map((group) => <section className="top-screen-picker-group" key={group}>
              <h3><DeckIcon name={group === "Extensions" ? "extension" : "monitor"} size={16} />{group}</h3>
              <div className="top-screen-picker-options">
                {matches.filter((choice) => (choice.group ?? "3Decks") === group).map((choice) => <Button key={choice.id} variant="outline" className="top-screen-picker-option" aria-pressed={choice.id === value} onPress={() => { onChange(choice.id); changeOpen(false); }}>
                  <span className="choice-icon"><DeckIcon name={choice.icon ?? "monitor"} size={20} /></span>
                  <span className="choice-copy"><strong>{choice.label}</strong>{choice.description && <small>{choice.description}</small>}</span>
                </Button>)}
              </div>
            </section>)}
          </Modal.Body>
          <Modal.Footer><Button variant="ghost" onPress={() => changeOpen(false)}>{fr ? "Fermer" : "Close"}</Button></Modal.Footer>
        </Modal.Dialog>
      </Modal.Container>
    </Modal.Backdrop>
  </Modal>;
}
