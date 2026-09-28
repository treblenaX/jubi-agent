/**
 * Projects store — shared module state for the sidebar project list
 * (safe: app runs with ssr = false). Mirrors sessions.svelte.ts.
 */
import { listProjects, deleteProject, type ProjectInfo } from '$lib/api/projects';

function createProjectsStore() {
  let projects = $state<ProjectInfo[]>([]);

  return {
    get list() {
      return projects;
    },
    async refresh() {
      try {
        projects = await listProjects();
      } catch (err) {
        console.warn('Failed to load projects:', err);
      }
    },
    remove(id: string) {
      projects = projects.filter((p) => p.project_id !== id);
    }
  };
}

export const projects = createProjectsStore();
