import { closestCenter, DndContext, KeyboardSensor, PointerSensor, useSensor, useSensors } from "@dnd-kit/core";
import type { DragEndEvent } from "@dnd-kit/core";
import { rectSortingStrategy, SortableContext, sortableKeyboardCoordinates, useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { Button, Modal } from "@heroui/react";
import type { CSSProperties, MouseEvent as ReactMouseEvent } from "react";
import { useEffect, useRef, useState } from "react";
import type { DeckConfig, Locale, PageConfig } from "../app/types";
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

interface SortablePageProps {
  page: PageConfig;
  index: number;
  locale: Locale;
  selected: boolean;
  onSelect: () => void;
  onContextMenu: (event: ReactMouseEvent) => void;
  onOpenMenu: (event: ReactMouseEvent<HTMLButtonElement>) => void;
}

function SortablePage({ page, index, locale, selected, onSelect, onContextMenu, onOpenMenu }: SortablePageProps) {
  const fr = locale === "fr";
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: page.id });
  const style = { transform: CSS.Transform.toString(transform), transition } as CSSProperties;
  const title = localized(page.title, locale) || page.id;
  return (
    <div ref={setNodeRef} style={style} data-page-id={page.id} className={`page-link ${selected ? "active" : ""} ${isDragging ? "is-dragging" : ""}`} onContextMenu={onContextMenu}>
      <button className="drag-handle" type="button" aria-label={fr ? `Déplacer ${title}` : `Move ${title}`} title={fr ? "Glisser pour réorganiser" : "Drag to reorder"} {...attributes} {...listeners}><DeckIcon name="grip" size={16} /></button>
      <button className="page-select" type="button" onClick={onSelect}>
        <span className="page-icon"><DeckIcon name={page.icon || "page"} size={18} /></span>
        <span>{title}</span>
      </button>
      <button className="page-menu-hint" type="button" title={fr ? "Renommer ou supprimer" : "Rename or delete"} aria-label={fr ? `Options de la page ${index + 1}` : `Page ${index + 1} options`} onClick={onOpenMenu}><DeckIcon name="more" size={16} /></button>
    </div>
  );
}

export function AppSidebar({ config, locale, selectedPage, pageLimit, t, onSelect, onAdd, onMove, onRename, onDelete }: Props) {
  const [menu, setMenu] = useState<{ index: number; x: number; y: number } | null>(null);
  const [dialog, setDialog] = useState<PageDialog | null>(null);
  const [name, setName] = useState("");
  const menuRef = useRef<HTMLDivElement>(null);
  const fr = locale === "fr";
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  );
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
  const finishDrag = ({ active, over }: DragEndEvent) => {
    if (!over || active.id === over.id) return;
    const from = config.pages.findIndex((page) => page.id === active.id);
    const to = config.pages.findIndex((page) => page.id === over.id);
    if (from >= 0 && to >= 0) onMove(from, to);
  };
  return (
    <aside className="app-sidebar">
      <div className="sidebar-heading">
        <div><span className="eyebrow">3DS</span><h2>{t("pages")}</h2></div>
        <span className="count-pill">{config.pages.length}/{pageLimit}</span>
      </div>
      <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={finishDrag}>
        <SortableContext items={config.pages.map((page) => page.id)} strategy={rectSortingStrategy}>
          <div className="page-list">
            {config.pages.map((page, index) => <SortablePage key={page.id} page={page} index={index} locale={locale} selected={selectedPage === index} onSelect={() => onSelect(index)} onContextMenu={(event) => { event.preventDefault(); setMenu({ index, x: event.clientX, y: event.clientY }); }} onOpenMenu={(event) => { const rect = event.currentTarget.getBoundingClientRect(); setMenu({ index, x: rect.right, y: rect.bottom }); }} />)}
          </div>
        </SortableContext>
      </DndContext>
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
