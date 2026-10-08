import { useEffect, useState } from "react";
import type { AgentState, ButtonConfig, DeckConfig, Locale, PageConfig, Schema } from "../app/types";
import type { CopyKey } from "../i18n/copy";
import { actionArgs, actionKind, defaultAction, newButton } from "../utils/config";
import { AppSidebar } from "../components/AppSidebar";
import { ActionPicker } from "./ActionPicker";
import { DeckPreview } from "./DeckPreview";
import { Inspector } from "./Inspector";
import { PageTemplateGallery } from "./PageTemplateGallery";
import { pageFromTemplate, type PageTemplateId } from "./pageTemplates";

interface Props {
  config: DeckConfig;
  schema: Schema;
  status: AgentState | null;
  locale: Locale;
  scenes: string[];
  apps: string[];
  t: (key: CopyKey, values?: Record<string, string | number>) => string;
  update: (recipe: (draft: DeckConfig) => void) => void;
}

export function EditorView({ config, schema, status, locale, scenes, apps, t, update }: Props) {
  const [pageIndex, setPageIndex] = useState(0);
  const [selectedSlot, setSelectedSlot] = useState<number | null>(null);
  const [pickerOpen, setPickerOpen] = useState(false);
  const [galleryOpen, setGalleryOpen] = useState(false);
  const page = config.pages[pageIndex];
  const button = page?.buttons.find((item) => item.slot === selectedSlot) ?? null;
  const appChoices = button && actionKind(button.action) === "app.quit"
    ? (Array.isArray(status?.snapshot?.apps) ? status.snapshot.apps.map(String) : [])
    : apps;
  useEffect(() => {
    if (pageIndex >= config.pages.length) setPageIndex(Math.max(0, config.pages.length - 1));
  }, [config.pages.length, pageIndex]);
  const title = button ? t("changeAction") : t("addAction");

  const updatePage = (recipe: (page: PageConfig) => void) => update((draft) => {
    const target = draft.pages[pageIndex];
    if (!target) return;
    const oldId = target.id;
    recipe(target);
    if (oldId !== target.id) {
      for (const candidate of draft.pages.flatMap((item) => item.buttons)) {
        if (actionKind(candidate.action) !== "page.switch") continue;
        const args = actionArgs(candidate.action);
        if (args.page === oldId) candidate.action = { type: "page.switch", ...args, page: target.id };
      }
    }
  });

  const updateButton = (recipe: (button: ButtonConfig) => void) => update((draft) => {
    const target = draft.pages[pageIndex]?.buttons.find((item) => item.slot === selectedSlot);
    if (target) recipe(target);
  });

  const pickAction = (spec: Schema["actions"][number]) => {
    update((draft) => {
      const targetPage = draft.pages[pageIndex];
      if (!targetPage || selectedSlot === null) return;
      const targetButton = targetPage.buttons.find((item) => item.slot === selectedSlot);
      if (targetButton) {
        targetButton.action = defaultAction(spec, draft, scenes);
        targetButton.icon = spec.icon;
        targetButton.color = spec.color;
      } else targetPage.buttons.push(newButton(targetPage, selectedSlot, spec, draft, scenes));
    });
    setPickerOpen(false);
  };

  const addPage = (templateId: PageTemplateId) => {
    if (config.pages.length >= schema.limits.pages) return;
    const nextIndex = config.pages.length;
    update((draft) => { draft.pages.push(pageFromTemplate(draft, schema, templateId, scenes)); });
    setPageIndex(nextIndex);
    setSelectedSlot(null);
    setGalleryOpen(false);
  };

  const deletePageAt = (index: number) => {
    update((draft) => { draft.pages.splice(index, 1); });
    setPageIndex((current) => Math.max(0, current > index ? current - 1 : Math.min(current, config.pages.length - 2)));
    setSelectedSlot(null);
  };

  const renamePage = (index: number, title: string) => update((draft) => {
    const target = draft.pages[index];
    if (!target) return;
    target.title = { ...(typeof target.title === "string" ? { fr: target.title, en: target.title } : target.title), [locale]: title };
  });

  const movePage = (from: number, to: number) => {
    if (from === to || from < 0 || to < 0 || from >= config.pages.length || to >= config.pages.length) return;
    const selectedId = config.pages[pageIndex]?.id;
    const nextOrder = [...config.pages];
    const [movedPage] = nextOrder.splice(from, 1);
    if (!movedPage) return;
    nextOrder.splice(to, 0, movedPage);
    update((draft) => { const [moved] = draft.pages.splice(from, 1); if (moved) draft.pages.splice(to, 0, moved); });
    setPageIndex(Math.max(0, nextOrder.findIndex((candidate) => candidate.id === selectedId)));
  };

  const moveButton = (from: number, to: number) => {
    if (!Number.isInteger(from) || from === to) return;
    update((draft) => {
      const buttons = draft.pages[pageIndex]?.buttons;
      const moved = buttons?.find((item) => item.slot === from);
      const displaced = buttons?.find((item) => item.slot === to);
      if (!moved) return;
      moved.slot = to;
      if (displaced) displaced.slot = from;
    });
    setSelectedSlot(to);
  };

  const preview = page ? (
    <DeckPreview config={config} page={page} pageIndex={pageIndex} locale={locale} status={status} slots={schema.limits.buttons_per_page} selectedSlot={selectedSlot} t={t}
      onSelectPage={(index) => { setPageIndex(index); setSelectedSlot(null); }}
      onSelectSlot={(slot) => { if (page.source) return; setSelectedSlot(slot); if (!page.buttons.some((item) => item.slot === slot)) setPickerOpen(true); }}
      onMoveButton={moveButton}
    />
  ) : <div className="empty-editor"><button type="button" onClick={() => setGalleryOpen(true)}>+ {t("addPage")}</button></div>;

  return (
    <div className="editor-layout">
      <AppSidebar config={config} locale={locale} selectedPage={pageIndex} pageLimit={schema.limits.pages} t={t} onSelect={(index) => { setPageIndex(index); setSelectedSlot(null); }} onAdd={() => setGalleryOpen(true)} onMove={movePage} onRename={renamePage} onDelete={deletePageAt} />
      <main className="editor-workspace">{preview}</main>
      {page && <Inspector config={config} schema={schema} page={page} button={button} locale={locale} scenes={scenes} apps={appChoices} t={t} onUpdatePage={updatePage} onUpdateButton={updateButton}
        onChangeAction={() => setPickerOpen(true)} onDeletePage={() => deletePageAt(pageIndex)}
        onDeleteButton={() => { update((draft) => { const target = draft.pages[pageIndex]; if (target) target.buttons = target.buttons.filter((item) => item.slot !== selectedSlot); }); setSelectedSlot(null); }}
        onDeselect={() => setSelectedSlot(null)} />}
      <ActionPicker open={pickerOpen} locale={locale} actions={schema.actions} title={title} t={t} onPick={pickAction} onClose={() => setPickerOpen(false)} />
      <PageTemplateGallery open={galleryOpen} locale={locale} onChoose={addPage} onClose={() => setGalleryOpen(false)} />
    </div>
  );
}
