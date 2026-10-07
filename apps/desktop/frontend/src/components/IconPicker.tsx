import { Button, Input, Label, Popover, TextField, Tooltip } from "@heroui/react";
import { useMemo, useState } from "react";
import type { Locale } from "../app/types";
import { DeckIcon } from "./DeckIcon";

export function IconPicker({ icons, value, onChange, label, locale = "en" }: { icons: string[]; value: string; onChange: (icon: string) => void; label: string; locale?: Locale }) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const visible = useMemo(() => icons.filter((icon) => icon.toLowerCase().includes(query.toLowerCase())), [icons, query]);
  return (
    <div className="icon-picker">
      <span className="field-label">{label}</span>
      <Popover isOpen={open} onOpenChange={setOpen}>
        <Button className="icon-picker-trigger" variant="outline" fullWidth>
          <span className="icon-preview"><DeckIcon name={value} size={21} /></span><span className="icon-trigger-copy"><strong>{value}</strong><small>{label}</small></span><DeckIcon name="down" size={16} />
        </Button>
        <Popover.Content className="icon-popover-shell" placement="bottom end">
          <Popover.Dialog>
            <Popover.Heading>{label}</Popover.Heading>
            <TextField className="icon-search" value={query} onChange={setQuery} aria-label={label}><Label>{locale === "fr" ? "Rechercher" : "Search icons"}</Label><Input placeholder={locale === "fr" ? "Musique, fenêtre, volume…" : "Music, window, volume…"} /></TextField>
            <div className="icon-popover" role="listbox" aria-label={label}>
              {visible.map((icon) => (
                <Tooltip key={icon} delay={250}>
                  <button type="button" role="option" aria-label={icon} aria-selected={icon === value} className={icon === value ? "selected" : ""} onClick={() => { onChange(icon); setOpen(false); }}><DeckIcon name={icon} size={21} /></button>
                  <Tooltip.Content>{icon}</Tooltip.Content>
                </Tooltip>
              ))}
            </div>
          </Popover.Dialog>
        </Popover.Content>
      </Popover>
    </div>
  );
}
