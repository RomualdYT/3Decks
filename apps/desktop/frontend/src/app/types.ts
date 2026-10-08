import type { components } from "../api/generated";

// Visual state stays local; wire contracts are generated from the agent API.
export type Locale = "fr" | "en";
export type View = "editor" | "settings" | "status" | "extensions";
export type ButtonConfig = components["schemas"]["ButtonDocument"];
export type PageConfig = components["schemas"]["PageDocument"];
export type ObsConfig = components["schemas"]["ObsSettings"];
export type DeckConfig = components["schemas"]["ConfigDocument"];
export type ActionArgument = components["schemas"]["ActionArgument"];
export type ActionSpec = components["schemas"]["ActionSpec"];
export type FeatureSpec = components["schemas"]["FeatureSpec"];
export type Schema = components["schemas"]["Catalog"];
export type ExtensionManifest = components["schemas"]["ExtensionManifest"];
export type InstalledExtension = components["schemas"]["InstalledExtension"];
export type ExtensionCatalog = components["schemas"]["ExtensionCatalog"];
export type AgentState = components["schemas"]["AgentState"];
export type Localized = PageConfig["title"];
export type ActionValue = ButtonConfig["action"];
