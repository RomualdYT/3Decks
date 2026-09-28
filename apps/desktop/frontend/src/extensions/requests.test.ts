import { describe, expect, it } from "vitest";
import type { InstalledExtension } from "../app/types";
import { approvalRequest } from "./requests";

const item: InstalledExtension = {
  manifest: { id: "org.example.timer", name: "Timer", description: "", author: "Example", version: "1.0.0", api_version: 1, platforms: ["darwin", "win32"], permissions: [], settings: [], actions: [], sources: [], dashboards: [] },
  digest: "approved-hash", enabled: false, status: "untrusted", error: "", updated_at: 0, settings: {}, secret_fields_set: [],
};

describe("strict extension operation contracts", () => {
  it("sends only the fingerprint approval fields when enabling", () => {
    expect(approvalRequest({ item, operation: "enable" })).toEqual({ operation: "enable", id: item.manifest.id, trust: true, digest: item.digest });
  });
  it("never mixes approval fields into removal confirmation", () => {
    expect(approvalRequest({ item, operation: "remove" })).toEqual({ operation: "remove", id: item.manifest.id, confirm: true });
  });
});
