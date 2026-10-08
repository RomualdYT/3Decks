import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { agentApi } from "../api/client";
import type { AgentState, DeckConfig, Schema } from "../app/types";
import { clone, reconcileCommittedConfig } from "../utils/config";

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
  const dirtyRef = useRef(false);
  const revisionRef = useRef<number | null>(null);
  const catalogRevisionRef = useRef<number | null>(null);
  const editEpoch = useRef(0);

  const load = useCallback(async () => {
    const epoch = ++editEpoch.current;
    setLoading(true);
    setError("");
    try {
      const [nextSchema, result, nextStatus, nextApps] = await Promise.all([
        agentApi.schema(), agentApi.config(), agentApi.state().catch(() => null),
        agentApi.apps().catch(() => ({ apps: [] })),
      ]);
      if (epoch !== editEpoch.current) return;
      result.config.features ||= Object.fromEntries(nextSchema.features.map((feature) => [feature.key, feature.enabled]));
      setSchema(nextSchema);
      setConfig(clone(result.config));
      setSaved(clone(result.config));
      revisionRef.current = result.config.revision;
      setStatus(nextStatus);
      catalogRevisionRef.current = nextStatus?.catalog_revision ?? null;
      setApps(nextApps.apps);
    } catch (reason) { setError(reason instanceof Error ? reason.message : String(reason)); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { void load(); }, [load]);
  const dirty = useMemo(() => Boolean(config && saved && JSON.stringify(config) !== JSON.stringify(saved)), [config, saved]);
  useEffect(() => { dirtyRef.current = dirty; }, [dirty]);
  useEffect(() => {
    let refreshing = false;
    let disposed = false;
    const refresh = async () => {
      if (refreshing || disposed || document.hidden) return;
      refreshing = true;
      const epoch = editEpoch.current;
      const revision = revisionRef.current;
      try {
        const nextStatus = await agentApi.state();
        if (disposed) return;
        setStatus(nextStatus);
        const catalogRevision = nextStatus.catalog_revision ?? null;
        const catalogChanged = catalogRevision !== catalogRevisionRef.current;
        const configChanged = !dirtyRef.current && nextStatus.config_revision !== revisionRef.current && epoch === editEpoch.current;
        if (catalogChanged || configChanged) {
          const [nextSchema, result] = await Promise.all([
            agentApi.schema(), configChanged ? agentApi.config() : Promise.resolve(null),
          ]);
          if (disposed) return;
          setSchema(nextSchema);
          catalogRevisionRef.current = catalogRevision;
          if (result && !dirtyRef.current && epoch === editEpoch.current && revision === revisionRef.current) {
            result.config.features ||= Object.fromEntries(nextSchema.features.map((feature) => [feature.key, feature.enabled]));
            revisionRef.current = result.config.revision;
            setConfig(clone(result.config));
            setSaved(clone(result.config));
          }
        }
      } catch {
        if (!disposed) setStatus(null);
      } finally {
        refreshing = false;
      }
    };
    const timer = window.setInterval(() => { void refresh(); }, 4000);
    const onVisibility = () => { if (!document.hidden) void refresh(); };
    document.addEventListener("visibilitychange", onVisibility);
    return () => {
      disposed = true;
      window.clearInterval(timer);
      document.removeEventListener("visibilitychange", onVisibility);
    };
  }, []);
  const update = useCallback((recipe: (draft: DeckConfig) => void) => {
    editEpoch.current += 1;
    dirtyRef.current = true;
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
    editEpoch.current += 1;
    setSaving(true); setError(""); setNotice("");
    try {
      const submitted = clone(config);
      const result = await agentApi.save(submitted);
      setConfig((current) => reconcileCommittedConfig(current, submitted, result.config));
      setSaved(clone(result.config));
      revisionRef.current = result.config.revision;
      setNotice("saved");
      const [nextSchema, nextStatus] = await Promise.all([agentApi.schema(), agentApi.state().catch(() => null)]);
      setSchema(nextSchema); setStatus(nextStatus);
    } catch (reason) { setError(reason instanceof Error ? reason.message : String(reason)); }
    finally { setSaving(false); }
  }, [config, dirty]);

  const reset = useCallback(() => {
    editEpoch.current += 1;
    if (saved) setConfig(clone(saved));
  }, [saved]);
  const refreshSchema = useCallback(async () => { setSchema(await agentApi.schema()); }, []);
  return { schema, config, status, apps, loading, saving, dirty, error, notice, update, save, reset, reload: load, refreshSchema, setError, setNotice };
}
