import { Button, Modal } from "@heroui/react";
import { useEffect, useRef, useState } from "react";
import type { DeckConfig, Locale } from "../app/types";
import type { CopyKey } from "../i18n/copy";
import { localized } from "../utils/config";
import { DeckIcon } from "./DeckIcon";
import { TextControl } from "./FormControls";

interface Props {
  config: DeckConfig;
  locale: Locale;
  selectedPage: number;
  pageLimit: number;
  t: (key: CopyKey, values?: Record<string, string | number>) => string;
  onSelect: (index: number) => void;
  onAdd: () => void;
  onMove: (from: number, to: number) => void;
  onRename: (index: number, title: string) => void;
  onDelete: (index: number) => void;
}

interface PageDialog {
  kind: "rename" | "delete";
  index: number;
}

export function AppSidebar({ config, locale, selectedPage, pageLimit, t, onSelect, onAdd, onMove, onRename, onDelete }: Props) {
  const [menu, setMenu] = useState<{ index: number; x: number; y: number } | null>(null);
  const [dialog, setDialog] = useState<PageDialog | null>(null);
  const [name, setName] = useState("");
  const menuRef = useRef<HTMLDivElement>(null);
  const fr = locale === "fr";
  useEffect(() => {
    const close = (event: PointerEvent) => { if (!menuRef.current?.contains(event.target as Node)) setMenu(null); };
    const escape = (event: KeyboardEvent) => { if (event.key === "Escape") setMenu(null); };
    document.addEventListener("pointerdown", close);
    document.addEventListener("keydown", escape);
    return () => { document.removeEventListener("pointerdown", close); document.removeEventListener("keydown", escape); };
  }, []);
  const openDialog = (kind: PageDialog["kind"], index: number) => {
    setMenu(null);
    setName(localized(config.pages[index]?.title ?? "", locale));
    setDialog({ kind, index });
  };
  return (
    <aside className="app-sidebar">
      <div className="sidebar-heading">
        <div><span className="eyebrow">3DS</span><h2>{t("pages")}</h2></div>
        <span className="count-pill">{config.pages.length}/{pageLimit}</span>
      </div>
      <div className="page-list">
        {config.pages.map((page, index) => (
          <div
            className={`page-link ${selectedPage === index ? "active" : ""}`}
            key={page.id}
            draggable
            onContextMenu={(event) => { event.preventDefault(); setMenu({ index, x: event.clientX, y: event.clientY }); }}
            onDragStart={(event) => { event.dataTransfer.effectAllowed = "move"; event.dataTransfer.setData("text/deck-page", String(index)); }}
            onDragOver={(event) => { if (event.dataTransfer.types.includes("text/deck-page")) event.preventDefault(); }}
            onDrop={(event) => { event.preventDefault(); const from = Number(event.dataTransfer.getData("text/deck-page")); if (Number.isInteger(from)) onMove(from, index); }}
          >
            <button className="page-select" type="button" onClick={() => onSelect(index)}>
              <span className="drag-handle"><DeckIcon name="grip" size={16} /></span>
              <span className="page-icon"><DeckIcon name={page.icon || "page"} size={18} /></span>
              <span>{localized(page.title, locale) || page.id}</span>
            </button>
            <button className="page-menu-hint" type="button" title={fr ? "Renommer ou supprimer" : "Rename or delete"} aria-label={fr ? "Options de la page" : "Page options"} onClick={(event) => { const rect = event.currentTarget.getBoundingClientRect(); setMenu({ index, x: rect.right, y: rect.bottom }); }}><DeckIcon name="more" size={16} /></button>
          </div>
        ))}
      </div>
      <Button className="sidebar-add" variant="outline" fullWidth isDisabled={config.pages.length >= pageLimit} onPress={onAdd}>
        <DeckIcon name="plus" size={18} />{t("addPage")}
      </Button>
      {menu && <div className="page-context-menu" ref={menuRef} role="menu" style={{ left: Math.min(menu.x, window.innerWidth - 190), top: Math.min(menu.y, window.innerHeight - 120) }}><button type="button" role="menuitem" onClick={() => openDialog("rename", menu.index)}><DeckIcon name="edit" size={16} />{fr ? "Renommer" : "Rename"}</button><button type="button" role="menuitem" className="danger" onClick={() => openDialog("delete", menu.index)}><DeckIcon name="trash" size={16} />{fr ? "Supprimer" : "Delete"}</button></div>}
      <Modal isOpen={Boolean(dialog)} onOpenChange={(open) => { if (!open) setDialog(null); }}>
        <Modal.Backdrop><Modal.Container size="sm"><Modal.Dialog><Modal.CloseTrigger /><Modal.Header><Modal.Icon><DeckIcon name={dialog?.kind === "delete" ? "trash" : "edit"} /></Modal.Icon><Modal.Heading>{dialog?.kind === "delete" ? (fr ? "Supprimer cette page ?" : "Delete this page?") : (fr ? "Renommer la page" : "Rename page")}</Modal.Heading></Modal.Header><Modal.Body>{dialog?.kind === "delete" ? <p>{fr ? "Les actions de cette page seront supprimées. Cette opération n’est appliquée qu’après enregistrement." : "Actions on this page will be removed. This only applies after saving."}</p> : <TextControl label={fr ? "Nom de la page" : "Page name"} value={name} onChange={setName} />}</Modal.Body><Modal.Footer><Button variant="ghost" onPress={() => setDialog(null)}>{fr ? "Annuler" : "Cancel"}</Button><Button variant={dialog?.kind === "delete" ? "danger" : "primary"} onPress={() => { if (!dialog) return; if (dialog.kind === "rename") onRename(dialog.index, name.trim() || localized(config.pages[dialog.index].title, locale)); else onDelete(dialog.index); setDialog(null); }}>{dialog?.kind === "delete" ? (fr ? "Supprimer" : "Delete") : (fr ? "Renommer" : "Rename")}</Button></Modal.Footer></Modal.Dialog></Modal.Container></Modal.Backdrop>
      </Modal>
    </aside>
  );
}
