import type { AgentState, DeckConfig, Locale, PageConfig } from "../app/types";
import { translate } from "../i18n/copy";
import { DeckPreview } from "./DeckPreview";

const ignoreInteraction = () => {};

/** The same shell, screen geometry and renderers as the editor, without editing. */
export function PageTemplatePreview({
  page,
  config,
  status,
  locale,
}: {
  page: PageConfig;
  config: DeckConfig;
  status: AgentState | null;
  locale: Locale;
}) {
  return (
    <div className="template-preview" inert aria-hidden="true">
      <DeckPreview
        config={{ ...config, pages: [page] }}
        page={page}
        pageIndex={0}
        locale={locale}
        status={status}
        slots={6}
        selectedSlot={null}
        t={(key, values) => translate(locale, key, values)}
        onSelectPage={ignoreInteraction}
        onSelectSlot={ignoreInteraction}
        onMoveButton={ignoreInteraction}
      />
    </div>
  );
}
