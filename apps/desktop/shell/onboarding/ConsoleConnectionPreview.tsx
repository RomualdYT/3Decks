import type { Locale } from "../../frontend/src/app/types";
import { DeckIcon } from "../../frontend/src/components/DeckIcon";
import { Decky } from "../../frontend/src/components/Decky";
import { deviceShellStyle } from "../../frontend/src/editor/deviceShell";

export function ConsoleConnectionPreview({ connected, locale }: { connected: boolean; locale: Locale }) {
  const fr = locale === "fr";
  return <div className={`onboarding-console-link${connected ? " is-connected" : ""}`} aria-hidden="true">
    <div className="onboarding-console-preview" style={deviceShellStyle}>
      <img src="/device-shell.svg" alt="" draggable={false} />
      <div className="onboarding-console-top">
        <Decky mood={connected ? "wave" : "idle"} size={38} />
        <strong>3Decks</strong>
      </div>
      <div className="onboarding-console-bottom">
        <DeckIcon name={connected ? "check" : "lock"} size={18} />
        <span>{connected ? (fr ? "Connectée" : "Connected") : (fr ? "Code du PC" : "PC pairing code")}</span>
        {!connected && <div className="onboarding-console-code">{Array.from({ length: 6 }, (_, index) => <i key={index}>·</i>)}</div>}
      </div>
    </div>
    <div className="onboarding-console-signal"><i /><i /><i /></div>
    <div className="onboarding-computer-preview">
      <div className="onboarding-computer-display"><Decky mood={connected ? "wave" : "idle"} size={70} /><strong>3Decks</strong></div>
      <span className="onboarding-computer-stand" />
    </div>
  </div>;
}
