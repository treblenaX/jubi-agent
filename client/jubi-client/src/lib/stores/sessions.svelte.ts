/**
 * Chat sessions store — shared module state (safe: app runs with ssr = false).
 *
 * Holds the sidebar session list fetched from GET /threads.
 * The ACTIVE thread is NOT stored here — the URL (?t=<thread_id>) is the
 * source of truth for that (refresh-safe, deep-linkable).
 */
import { API_URL } from '$lib/constants';

export interface SessionInfo {
	thread_id: string;
	title: string;
	created_at: string;
	updated_at: string;
}

function createSessionsStore() {
	let sessions = $state<SessionInfo[]>([]);

	return {
		get list() {
			return sessions;
		},
		async refresh() {
			try {
				const res = await fetch(`${API_URL}/threads`);
				if (res.ok) {
					const data = await res.json();
					sessions = data.threads ?? [];
				}
			} catch (err) {
				console.warn('Failed to load sessions:', err);
			}
		},
		remove(id: string) {
			sessions = sessions.filter((s) => s.thread_id !== id);
		}
	};
}

export const sessions = createSessionsStore();
