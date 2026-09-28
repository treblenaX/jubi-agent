/**
 * Projects API Client — project metadata containers that group chat threads.
 * The description is injected into the agents' system prompts as context.
 */

import { API_URL as BASE_URL } from "$lib/constants";

export interface ProjectInfo {
  project_id: string;
  title: string;
  description: string;
  created_at: string;
  updated_at: string;
  thread_count?: number;
}

export interface ProjectThread {
  thread_id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export async function listProjects(): Promise<ProjectInfo[]> {
  const res = await fetch(`${BASE_URL}/projects`);
  if (!res.ok) throw new Error(`Failed to list projects: ${res.status}`);
  return (await res.json()).projects ?? [];
}

export async function createProject(title: string, description: string): Promise<string> {
  const res = await fetch(`${BASE_URL}/projects`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title, description })
  });
  if (!res.ok) throw new Error(`Failed to create project: ${res.status}`);
  return (await res.json()).project_id;
}

export async function getProject(
  projectId: string
): Promise<{ project: ProjectInfo; threads: ProjectThread[] }> {
  const res = await fetch(`${BASE_URL}/projects/${encodeURIComponent(projectId)}`);
  if (!res.ok) throw new Error(`Failed to load project: ${res.status}`);
  return await res.json();
}

export async function updateProject(
  projectId: string,
  patch: { title?: string; description?: string }
): Promise<void> {
  const res = await fetch(`${BASE_URL}/projects/${encodeURIComponent(projectId)}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(patch)
  });
  if (!res.ok) throw new Error(`Failed to update project: ${res.status}`);
}

export async function deleteProject(projectId: string): Promise<void> {
  const res = await fetch(`${BASE_URL}/projects/${encodeURIComponent(projectId)}`, {
    method: 'DELETE'
  });
  if (!res.ok) throw new Error(`Failed to delete project: ${res.status}`);
}
