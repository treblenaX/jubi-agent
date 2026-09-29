<script lang="ts">
	import { goto } from "$app/navigation";
	import { page } from "$app/state";
	import { HugeiconsIcon } from "@hugeicons/svelte";
	import { PlusSignIcon, Cancel01Icon, PencilEditIcon } from "@hugeicons/core-free-icons";
	import { getProject, updateProject, deleteProject, type ProjectInfo, type ProjectThread } from "$lib/api/projects";
	import { createThread } from "$lib/api/chat";
	import { projects } from "$lib/stores/projects.svelte";
	import { sessions } from "$lib/stores/sessions.svelte";
	import WorkspaceField from "$lib/components/WorkspaceField.svelte";

	// URL is the source of truth: /projects/<id>
	const projectId = $derived(page.params.id ?? '');

	let project = $state<ProjectInfo | null>(null);
	let threads = $state<ProjectThread[]>([]);
	let loading = $state(true);
	let error = $state('');
	let notFound = $state(false);

	// Edit mode
	let editing = $state(false);
	let editTitle = $state('');
	let editDescription = $state('');
	let editWorkspace = $state('');
	let saving = $state(false);

	async function load() {
		loading = true;
		error = '';
		notFound = false;
		try {
			const data = await getProject(projectId);
			project = data.project;
			threads = data.threads;
		} catch (err) {
			notFound = true;
			error = err instanceof Error ? err.message : 'Failed to load project';
		} finally {
			loading = false;
		}
	}

	// Reload whenever the URL project id changes
	$effect(() => {
		void projectId;
		void load();
	});

	function startEdit() {
		if (!project) return;
		editTitle = project.title;
		editDescription = project.description;
		editWorkspace = project.workspace_path ?? '';
		editing = true;
	}

	async function saveEdit() {
		if (!project || saving) return;
		saving = true;
		try {
			await updateProject(project.project_id, {
				title: editTitle.trim(),
				description: editDescription.trim(),
				workspace_path: editWorkspace.trim() || null
			});
			editing = false;
			await load();
			projects.refresh(); // sidebar label updates
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to save project';
		} finally {
			saving = false;
		}
	}

	async function handleDelete() {
		if (!project) return;
		try {
			await deleteProject(project.project_id);
			projects.remove(project.project_id);
			await goto('/');
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to delete project';
		}
	}

	async function newChat() {
		if (!project) return;
		try {
			const tid = await createThread(project.project_id);
			await sessions.refresh(); // sidebar tree picks up the new chat
			await goto(`/?t=${tid}`);
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to create chat';
		}
	}
</script>

<div class="mx-auto h-full max-w-3xl px-6 py-10">
	{#if loading}
		<p class="text-sm text-muted-foreground">Loading project…</p>
	{:else if notFound || !project}
		<h1 class="text-xl font-bold text-foreground">Project not found</h1>
		<button
			class="mt-3 rounded-md border border-border px-4 py-2 text-sm text-muted-foreground hover:bg-accent hover:text-accent-foreground"
			onclick={() => goto('/')}
		>
			Back to chats
		</button>
	{:else}
		<div class="flex items-start justify-between gap-4">
			<div class="min-w-0">
				<h1 class="truncate text-2xl font-bold tracking-tight text-foreground" style="font-family: var(--font-heading)">
					{project.title}
				</h1>
				<p class="mt-0.5 text-xs text-muted-foreground">
					Created {new Date(project.created_at).toLocaleDateString()}
				</p>
			</div>
			<div class="flex shrink-0 gap-2">
				<button
					class="flex items-center gap-1.5 rounded-md border border-border px-3 py-1.5 text-sm text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground"
					onclick={startEdit}
				>
					<HugeiconsIcon icon={PencilEditIcon} size={14} strokeWidth={1.5} />
					Edit
				</button>
				<button
					class="flex items-center gap-1.5 rounded-md border border-border px-3 py-1.5 text-sm text-muted-foreground transition-colors hover:border-destructive hover:text-destructive"
					onclick={handleDelete}
				>
					<HugeiconsIcon icon={Cancel01Icon} size={14} strokeWidth={1.5} />
					Delete
				</button>
			</div>
		</div>

		{#if error}
			<p class="mt-3 text-sm text-destructive">{error}</p>
		{/if}

		{#if editing}
			<!-- Edit form: same fields as creation -->
			<form
				class="mt-6 space-y-4 rounded-lg border border-border p-4"
				onsubmit={(e) => { e.preventDefault(); saveEdit(); }}
			>
				<div>
					<label for="edit-title" class="mb-1 block text-sm font-medium text-foreground">Title</label>
					<input
						id="edit-title"
						type="text"
						bind:value={editTitle}
						maxlength="120"
						class="w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground outline-none focus:border-ring focus:ring-1 focus:ring-ring"
					/>
				</div>
				<div>
					<label for="edit-desc" class="mb-1 block text-sm font-medium text-foreground">Description</label>
					<textarea
						id="edit-desc"
						bind:value={editDescription}
						rows="6"
						class="w-full resize-y rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground outline-none focus:border-ring focus:ring-1 focus:ring-ring"
					></textarea>
				</div>
				<WorkspaceField bind:value={editWorkspace} />
				<div class="flex gap-2">
					<button
						type="submit"
						disabled={saving || !editTitle.trim()}
						class="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:opacity-90 disabled:opacity-50"
					>
						{saving ? 'Saving…' : 'Save'}
					</button>
					<button
						type="button"
						class="rounded-md border border-border px-4 py-2 text-sm text-muted-foreground hover:bg-accent hover:text-accent-foreground"
						onclick={() => (editing = false)}
					>
						Cancel
					</button>
				</div>
			</form>
		{:else}
			<!-- Agent context: the description as the agents see it -->
			<div class="mt-5 rounded-lg border border-border bg-card p-4">
				<div class="text-[0.65rem] uppercase tracking-[0.06em] text-muted-foreground">
					Agent context · pinned into every chat's system prompt
				</div>
				<p class="mt-2 whitespace-pre-wrap text-sm leading-relaxed text-foreground">
					{project.description || 'No description yet — click Edit to add one so the agents know what this project is for.'}
				</p>
				{#if project.workspace_path}
					<div class="mt-3 border-t border-border pt-3">
						<div class="text-[0.65rem] uppercase tracking-[0.06em] text-muted-foreground">Workspace · tool actions jailed to</div>
						<p class="mt-1 font-mono text-xs text-foreground">{project.workspace_path}</p>
					</div>
				{/if}
			</div>
		{/if}

		<!-- Chats in this project -->
		<div class="mt-8 flex items-center justify-between">
			<h2 class="text-sm font-semibold uppercase tracking-[0.06em] text-muted-foreground">
				Chats ({threads.length})
			</h2>
			<button
				class="flex items-center gap-1.5 rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90"
				onclick={newChat}
			>
				<HugeiconsIcon icon={PlusSignIcon} size={14} strokeWidth={1.5} />
				New chat
			</button>
		</div>
		<div class="mt-3 space-y-1">
			{#each threads as t (t.thread_id)}
				<button
					class="flex w-full items-center justify-between rounded-md border border-border px-4 py-2.5 text-left text-sm transition-colors hover:bg-accent/50"
					onclick={() => goto(`/?t=${t.thread_id}`)}
				>
					<span class="truncate font-medium text-foreground">{t.title || 'New chat'}</span>
					<span class="shrink-0 text-xs text-muted-foreground">
						{new Date(t.updated_at).toLocaleDateString()}
					</span>
				</button>
			{:else}
				<p class="px-1 py-2 text-xs text-muted-foreground">
					No chats yet — start one and the agents will get this project's context automatically.
				</p>
			{/each}
		</div>
	{/if}
</div>
