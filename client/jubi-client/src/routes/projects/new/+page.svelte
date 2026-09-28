<script lang="ts">
	import { goto } from "$app/navigation";
	import { createProject } from "$lib/api/projects";
	import { projects } from "$lib/stores/projects.svelte";

	let title = $state('');
	let description = $state('');
	let saving = $state(false);
	let error = $state('');

	async function handleSubmit(e: SubmitEvent) {
		e.preventDefault();
		if (!title.trim() || saving) return;
		saving = true;
		error = '';
		try {
			const projectId = await createProject(title.trim(), description.trim());
			await projects.refresh(); // sidebar picks up the new project
			await goto(`/projects/${projectId}`);
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to create project';
			saving = false;
		}
	}
</script>

<div class="mx-auto flex h-full max-w-2xl flex-col justify-center px-6 py-10">
	<h1 class="text-2xl font-bold tracking-tight text-foreground" style="font-family: var(--font-heading)">
		New Project
	</h1>
	<p class="mt-1 text-sm text-muted-foreground">
		Projects group chats and give every agent durable context about what the work is for.
	</p>

	<form class="mt-6 space-y-5" onsubmit={handleSubmit}>
		<div>
			<label for="proj-title" class="mb-1.5 block text-sm font-medium text-foreground">Title</label>
			<input
				id="proj-title"
				type="text"
				bind:value={title}
				placeholder="e.g. Voice assistant for Raspberry Pi"
				class="w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground outline-none focus:border-ring focus:ring-1 focus:ring-ring"
				maxlength="120"
			/>
		</div>
		<div>
			<label for="proj-desc" class="mb-1.5 block text-sm font-medium text-foreground">Description</label>
			<textarea
				id="proj-desc"
				bind:value={description}
				rows="6"
				placeholder="What is this project for? Goals, constraints, current state — anything the AI agents should know before they start."
				class="w-full resize-y rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground outline-none focus:border-ring focus:ring-1 focus:ring-ring"
			></textarea>
			<p class="mt-1 text-xs text-muted-foreground">
				This description is pinned into the agents' system prompts in every chat of this project.
			</p>
		</div>
		{#if error}
			<p class="text-sm text-destructive">{error}</p>
		{/if}
		<div class="flex gap-3">
			<button
				type="submit"
				disabled={saving || !title.trim()}
				class="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
			>
				{saving ? 'Creating…' : 'Create project'}
			</button>
			<button
				type="button"
				class="rounded-md border border-border px-4 py-2 text-sm font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground"
				onclick={() => history.back()}
			>
				Cancel
			</button>
		</div>
	</form>
</div>
