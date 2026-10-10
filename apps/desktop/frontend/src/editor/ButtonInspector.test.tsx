import { renderToStaticMarkup } from "react-dom/server";
import { expect, it } from "vitest";
import catalog from "../../../catalog.json";
import defaults from "../../../default-config.json";
import type { DeckConfig, Schema } from "../app/types";
import { ButtonInspector } from "./ButtonInspector";

function warning(action: string, platform: string, enabled: boolean, available = true) {
  const schema = structuredClone(catalog) as unknown as Schema;
  schema.capabilities.audio_output = enabled;
  schema.features = schema.features.map((feature) => ({ ...feature, available, enabled }));
  schema.actions = schema.actions.map((spec) => ({ ...spec, supported: false }));
  const button = { id: "output", slot: 0, icon: "volume-up", color: "#8B78EA", label: "Output", action };
  return renderToStaticMarkup(<ButtonInspector config={defaults as unknown as DeckConfig} schema={schema}
    button={button} locale="en" platform={platform} scenes={[]} apps={[]} t={(key) => key}
    onUpdateButton={() => {}} onChangeAction={() => {}} onDeleteButton={() => {}} onDeselect={() => {}} />);
}

it("explains Windows audio switching limits even when all features are enabled", () => {
  for (const action of ["audio_output.cycle", "audio_output.set"]) {
    const rendered = warning(action, "win32", true);
    expect(rendered).toContain("Remote audio output switching is not supported on Windows");
    expect(rendered).not.toContain("This action needs a disabled feature");
  }
});

it("keeps the enable-feature guidance for disabled audio output on macOS", () => {
  expect(warning("audio_output.cycle", "darwin", false)).toContain("This action needs a disabled feature");
});

it("does not suggest enabling an unavailable platform feature", () => {
  const rendered = warning("audio_output.cycle", "linux", false, false);
  expect(rendered).toContain("This action is not supported on this computer");
  expect(rendered).not.toContain("This action needs a disabled feature");
});
