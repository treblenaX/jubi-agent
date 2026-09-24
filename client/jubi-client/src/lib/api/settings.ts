/**
 * Settings API Client — runtime settings + model list for the settings menu.
 */

import { API_URL as BASE_URL } from "$lib/constants";

export interface JubiSettings {
  model: string;
  num_ctx: number;
  compaction_enabled: boolean;
  compaction_mode: 'state_doc' | 'summary';
  compaction_trigger_fraction: number; // 0.1–0.95, % of num_ctx
  compaction_keep_messages: number;
}

export async function getSettings(): Promise<JubiSettings> {
  const res = await fetch(`${BASE_URL}/settings`);
  if (!res.ok) throw new Error(`Failed to load settings: ${res.status}`);
  return res.json();
}

export async function updateSettings(
  patch: Partial<JubiSettings>
): Promise<JubiSettings> {
  const res = await fetch(`${BASE_URL}/settings`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(patch)
  });
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new Error(body?.detail || `Failed to save settings: ${res.status}`);
  }
  return res.json();
}

export async function fetchModels(): Promise<{
  models: string[];
  connected: boolean;
  error?: string;
}> {
  const res = await fetch(`${BASE_URL}/models`);
  if (!res.ok) throw new Error(`Failed to load models: ${res.status}`);
  return res.json();
}
