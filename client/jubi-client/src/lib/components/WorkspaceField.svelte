<script lang="ts">
	/**
	 * WorkspaceField — text input + Browse button that opens a server-side
	 * folder browser. Browser folder pickers can't yield absolute server paths
	 * (and the webkitdirectory fallback enumerates every file, which looks like
	 * an upload), so the server lists directories and the exact path is filled
	 * in directly.
	 */
	import { API_URL } from "$lib/constants";

	let { value = $bindable('') }: { value?: string } = $props();

	interface DirEntry {
		name: string;
		path: string;
	}

	let open = $state(false);
	let cur = $state('');
	let parent = $state<string | null>(null);
	let home = $state('');
	let entries = $state<DirEntry[]>([]);
	let loading = $state(false);
	let error = $state('');

	async function loadDir(path: string) {
		loading = true;
		error = '';
		try {
			const res = await fetch(`${API_URL}/workspace/list?path=${encodeURIComponent(path)}`);
			if (!res.ok) throw new Error((await res.json()).detail ?? `Failed (${res.status})`);
			const data = await res.json();
			cur = data.path;
			parent = data.parent;
			home = data.home;
			entries = data.entries;
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to list directory';
		} finally {
			loading = false;
		}
	}

	function browse() {
		open = true;
		void loadDir(value.trim() || '');
	}

	function pick() {
		value = cur;
		open = false;
	}
</script>

<div>
	<label for="proj-workspace" class="mb-1.5 block text-sm font-medium text-foreground">Workspace (optional)</label>
	<div class="flex gap-2">
		<input
			id="proj-workspace"
			type="text"
			bind:value
			placeholder="/home/ec/projects/my-app"
			spellcheck="false"
			class="w-full rounded-md border border-border bg-background px-3 py-2 font-mono text-sm text-foreground outline-none focus:border-ring focus:ring-1 focus:ring-ring"
		/>
		<button
			type="button"
			onclick={browse}
			class="shrink-0 rounded-md border border-border px-3 py-2 text-sm font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground"
		>
			Browse
		</button>
	</div>
	<p class="mt-1 text-xs text-muted-foreground">
		Absolute path to an existing directory on the server. When set, the agents' file and shell
		tools are locked to this folder — they can't read, write, or run anything outside it.
		Leave empty to use the default sandbox (/tmp/jubi-sandbox).
	</p>

	{#if open}
		<!-- Server-side folder browser: no client filesystem access at all -->
		<div class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" role="dialog" aria-label="Choose workspace folder">
			<div class="flex max-h-[70vh] w-full max-w-lg flex-col rounded-lg border border-border bg-card shadow-lg">
				<div class="flex items-center justify-between gap-2 border-b border-border px-4 py-3">
					<span class="truncate font-mono text-xs text-foreground" title={cur}>{cur}</span>
					<button
						type="button"
						class="shrink-0 rounded p-1 text-muted-foreground hover:bg-accent hover:text-accent-foreground"
						onclick={() => (open = false)}
						aria-label="Close"
					>
						✕
					</button>
				</div>
				<div class="flex gap-2 border-b border-border px-4 py-2">
					<button
						type="button"
						disabled={!parent}
						class="rounded border border-border px-2 py-1 text-xs text-muted-foreground hover:bg-accent hover:text-accent-foreground disabled:opacity-40"
						onclick={() => parent && loadDir(parent)}
					>
						↑ Up
					</button>
					<button
						type="button"
						class="rounded border border-border px-2 py-1 text-xs text-muted-foreground hover:bg-accent hover:text-accent-foreground"
						onclick={() => loadDir(home)}
					>
						Home
					</button>
				</div>
				<div class="min-h-0 flex-1 overflow-y-auto p-2">
					{#if loading}
						<p class="p-2 text-xs text-muted-foreground">Loading…</p>
					{:else if error}
						<p class="p-2 text-xs text-destructive">{error}</p>
					{:else if entries.length === 0}
						<p class="p-2 text-xs text-muted-foreground">No subdirectories.</p>
					{:else}
						{#each entries as e (e.path)}
							<button
								type="button"
								class="block w-full truncate rounded px-2 py-1.5 text-left text-sm text-foreground hover:bg-accent"
								onclick={() => loadDir(e.path)}
							>
								📁 {e.name}
							</button>
						{/each}
					{/if}
				</div>
				<div class="flex justify-end gap-2 border-t border-border px-4 py-3">
					<button
						type="button"
						class="rounded-md border border-border px-3 py-1.5 text-sm text-muted-foreground hover:bg-accent hover:text-accent-foreground"
						onclick={() => (open = false)}
					>
						Cancel
					</button>
					<button
						type="button"
						class="rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground hover:opacity-90"
						onclick={pick}
					>
						Use this folder
					</button>
				</div>
			</div>
		</div>
	{/if}
</div>