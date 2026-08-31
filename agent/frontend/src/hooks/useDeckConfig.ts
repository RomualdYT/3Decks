import { useCallback, useEffect, useMemo, useState } from "react";
import { agentApi } from "../api/client";
import type { AgentState, DeckConfig, Schema } from "../app/types";
import { clone } from "../utils/config";

export function useDeckConfig() {
  const [schema, setSchema] = useState<Schema | null>(null);
  const [config, setConfig] = useState<DeckConfig | null>(null);
  const [saved, setSaved] = useState<DeckConfig | null>(null);
  const [status, setStatus] = useState<AgentState | null>(null);
  const [apps, setApps] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [nextSchema, result, nextStatus, nextApps] = await Promise.all([
        agentApi.schema(), agentApi.config(), agentApi.state().catch(() => null),
        agentApi.apps().catch(() => ({ apps: [] })),
      ]);
      result.config.features ||= Object.fromEntries(nextSchema.features.map((feature) => [feature.key, feature.enabled]));
      setSchema(nextSchema);
      setConfig(clone(result.config));
      setSaved(clone(result.config));
      setStatus(nextStatus);
      setApps(nextApps.apps);
    } catch (reason) { setError(reason instanceof Error ? reason.message : String(reason)); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { void load(); }, [load]);
  useEffect(() => {
    const timer = window.setInterval(() => { void agentApi.state().then(setStatus).catch(() => setStatus(null)); }, 4000);
    return () => window.clearInterval(timer);
  }, []);

  const dirty = useMemo(() => Boolean(config && saved && JSON.stringify(config) !== JSON.stringify(saved)), [config, saved]);
  const update = useCallback((recipe: (draft: DeckConfig) => void) => {
    setConfig((current) => {
      if (!current) return current;
      const next = clone(current);
      recipe(next);
      return next;
    });
    setNotice("");
  }, []);

  const save = useCallback(async () => {
    if (!config || !dirty) return;
    setSaving(true); setError(""); setNotice("");
    try {
      const result = await agentApi.save(config);
      setConfig(clone(result.config));
      setSaved(clone(result.config));
      setNotice("saved");
      const [nextSchema, nextStatus] = await Promise.all([agentApi.schema(), agentApi.state().catch(() => null)]);
      setSchema(nextSchema); setStatus(nextStatus);
    } catch (reason) { setError(reason instanceof Error ? reason.message : String(reason)); }
    finally { setSaving(false); }
  }, [config, dirty]);

  const reset = useCallback(() => { if (saved) setConfig(clone(saved)); }, [saved]);
  const refreshSchema = useCallback(async () => { setSchema(await agentApi.schema()); }, []);
  return { schema, config, status, apps, loading, saving, dirty, error, notice, update, save, reset, reload: load, refreshSchema, setError, setNotice };
}
