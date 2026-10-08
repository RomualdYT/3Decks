import { AlertDialog, Button } from "@heroui/react";
import { useState, type ReactNode } from "react";
import type { Locale, Localized } from "../app/types";
import { DeckIcon } from "../components/DeckIcon";
import { TextControl } from "../components/FormControls";

export function InspectorSection({ title, icon, children }: { title: string; icon?: string; children: ReactNode }) {
  return <section className="inspector-section" aria-label={title}>
    <h3>{icon && <DeckIcon name={icon} size={16} />}{title}</h3>
    {children}
  </section>;
}

export function LocalizedInspectorField({ value, locale, maxLength, label, onChange }: {
  value: Localized; locale: Locale; maxLength: number; label: string; onChange: (value: string) => void;
}) {
  return <div className="localized-field">
    <span className="language-badge">{locale.toUpperCase()}</span>
    <TextControl label={label} value={typeof value === "string" ? value : value[locale] ?? ""} maxLength={maxLength} onChange={onChange} />
  </div>;
}

export function InspectorDeleteAction({ locale, name, kind, onDelete }: {
  locale: Locale; name: string; kind: "page" | "button"; onDelete: () => void;
}) {
  const [open, setOpen] = useState(false);
  const fr = locale === "fr";
  const page = kind === "page";
  const trigger = fr ? (page ? "Supprimer cette page…" : "Supprimer ce bouton…") : (page ? "Delete this page…" : "Delete this button…");
  const title = fr ? (page ? "Supprimer cette page ?" : "Supprimer ce bouton ?") : (page ? "Delete this page?" : "Delete this button?");
  const description = fr ? (page ? `La page « ${name} » et ses boutons seront supprimés.` : `Le bouton « ${name} » sera supprimé de cette page.`) : (page ? `“${name}” and its buttons will be removed.` : `“${name}” will be removed from this page.`);
  return <>
    <Button className="inspector-delete-trigger" variant="ghost" onPress={() => setOpen(true)}><DeckIcon name="trash" size={16} />{trigger}</Button>
    <AlertDialog isOpen={open} onOpenChange={setOpen}>
      <AlertDialog.Backdrop><AlertDialog.Container size="sm"><AlertDialog.Dialog>
        <AlertDialog.Header><AlertDialog.Heading>{title}</AlertDialog.Heading></AlertDialog.Header>
        <AlertDialog.Body><p>{description}</p></AlertDialog.Body>
        <AlertDialog.Footer>
          <Button variant="outline" onPress={() => setOpen(false)}>{fr ? "Annuler" : "Cancel"}</Button>
          <Button variant="danger" onPress={() => { setOpen(false); onDelete(); }}>{fr ? "Supprimer" : "Delete"}</Button>
        </AlertDialog.Footer>
      </AlertDialog.Dialog></AlertDialog.Container></AlertDialog.Backdrop>
    </AlertDialog>
  </>;
}

export function InspectorPreviewNote({ locale }: { locale: Locale }) {
  return <div className="inspector-footer inspector-preview-note"><DeckIcon name="eye" size={15} />{locale === "fr" ? "L’aperçu se met à jour immédiatement" : "Changes appear in the preview instantly"}</div>;
}
