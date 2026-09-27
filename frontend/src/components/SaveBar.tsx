import { Button, Tooltip } from "@heroui/react";
import type { Locale } from "../app/types";
import { DeckIcon } from "./DeckIcon";

interface Props {
  dirty: boolean;
  saving: boolean;
  locale: Locale;
  onSave: () => void;
  onReset: () => void;
}

export function SaveBar({ dirty, saving, locale, onSave, onReset }: Props) {
  if (!dirty && !saving) return null;
  const fr = locale === "fr";
  return (
    <div className="save-bar" role="status" aria-live="polite">
      <div className="save-bar-copy"><span><DeckIcon name="edit" size={18} /></span><div><strong>{saving ? (fr ? "Enregistrement…" : "Saving…") : (fr ? "Modifications non enregistrées" : "Unsaved changes")}</strong><small>{fr ? "Votre console sera mise à jour automatiquement." : "Your console will update automatically."}</small></div></div>
      <div className="save-bar-actions">
        <Tooltip delay={300}><Button variant="ghost" isDisabled={saving} onPress={onReset}><DeckIcon name="undo" size={17} />{fr ? "Annuler" : "Cancel"}</Button><Tooltip.Content>{fr ? "Revenir à la dernière version enregistrée" : "Restore the last saved version"}</Tooltip.Content></Tooltip>
        <Button className="save-primary" variant="primary" isDisabled={saving} onPress={onSave}>{saving ? <span className="button-loader" /> : <DeckIcon name="save" size={17} />}{fr ? "Enregistrer" : "Save"}</Button>
      </div>
    </div>
  );
}
