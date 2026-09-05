import type { ExtensionRequest } from "../api/client";
import type { InstalledExtension } from "../app/types";

export type ExtensionConfirmation = {
  item: InstalledExtension;
  operation: "enable" | "remove";
};

export function approvalRequest({ item, operation }: ExtensionConfirmation): ExtensionRequest {
  return operation === "remove"
    ? { operation, id: item.manifest.id, confirm: true }
    : { operation, id: item.manifest.id, trust: true, digest: item.digest };
}
