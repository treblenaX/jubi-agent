<script lang="ts">
  import { Root, Textarea, Addon, Button, Text } from "$lib/components/ui/input-group";
  import Separator from "$lib/components/ui/separator/separator.svelte";
  import { ArrowUp02Icon } from "@hugeicons/core-free-icons";
  import { HugeiconsIcon } from "@hugeicons/svelte";

  // Svelte 5 runes mode - use $props()
  interface Props {
    mode?: "auto" | "agent" | "manual";
    tokenUsage?: number;
    disabled?: boolean;
    placeholder?: string;
    onSend?: (content: string) => void;
    onModeChange?: (mode: "auto" | "agent" | "manual") => void;
  }

  const {
    mode = "auto",
    tokenUsage = 52,
    disabled = false,
    placeholder = "Ask, Search or Chat...",
    onSend = () => {},
    onModeChange = () => {}
  } = $props<Props>();

  let value = $state<string>("");
  let isComposing = $state(false);

  const modes = [
    { value: "auto", label: "Auto" },
    { value: "agent", label: "Agent" },
    { value: "manual", label: "Manual" }
  ] as const;

  function handleKeydown(e: KeyboardEvent) {
    if (e.key === "Enter" && !e.shiftKey && !isComposing) {
      e.preventDefault();
      send();
    }
  }

  function handleCompositionStart() {
    isComposing = true;
  }

  function handleCompositionEnd(e: CompositionEvent) {
    isComposing = false;
    if (e.data?.endsWith("\n")) {
      send();
    }
  }

  function send() {
    const content = value.trim();
    if (!content || disabled) return;
    value = "";
    onSend(content);
  }

  function handleModeSelect(m: typeof modes[0]) {
    onModeChange(m.value);
  }
</script>

<Root class="w-full">
  <Textarea
    bind:value
    {placeholder}
    {disabled}
    class="flex-1 min-h-[4rem] resize-none"
    onkeydown={handleKeydown}
    oncompositionstart={handleCompositionStart}
    oncompositionend={handleCompositionEnd}
    rows={3}
  />

  <Addon align="block-end" class="w-full items-end gap-2">
    <!-- Mode selector dropdown (native HTML) -->
    <div class="relative inline-block w-full max-w-[120px]">
      <button
        id="mode-trigger"
        type="button"
        class="px-3 py-1 text-sm font-medium rounded-md border bg-background hover:bg-accent hover:text-accent-foreground w-full text-left"
          onclick={() => {
            const trigger = document.getElementById('mode-trigger') as HTMLButtonElement;
            const content = document.getElementById('mode-content') as HTMLElement;
            const isOpen = content?.classList.contains('hidden') ?? true;

            // Close all open dropdowns
            document.querySelectorAll('[id^="mode-trigger"]').forEach(t => {
              t.classList.add('hidden');
              const parent = t.parentElement as HTMLElement;
              if (parent) parent.classList.remove('flex');
            });

            // Toggle current dropdown
            trigger.classList.toggle('hidden', !isOpen);
            content?.classList.toggle('hidden', isOpen);
          }}
        disabled={disabled}
      >
        {modes.find(m => m.value === mode)?.label}
      </button>

      <div
        id="mode-content"
        class="absolute left-0 right-0 mt-1 bounded-md shadow-lg hidden p-1 z-50 min-w-[120px]"
      >
        {#each modes as m (m.value)}
          <button
            type="button"
            onclick={() => handleModeSelect(m)}
            class="w-full text-left px-3 py-1.5 text-sm hover:bg-accent hover:text-accent-foreground"
            disabled={disabled}
          >
            {m.label}
          </button>
        {/each}
      </div>
    </div>

    <!-- Token usage indicator -->
    <Text class="ms-auto text-xs">{tokenUsage}% used</Text>

    <Separator orientation="vertical" class="!h-4 mx-2" />

    <!-- Send button -->
    <Button
      variant="default"
      size="icon"
      class="rounded-full"
      disabled={disabled || !value.trim()}
      onclick={send}
    >
      <HugeiconsIcon icon={ArrowUp02Icon} />
      <span class="sr-only">Send</span>
    </Button>
  </Addon>
</Root>

<style>
  :global(body.click-close-dropdown) [id^="mode-content"] {
    display: none;
  }
</style>
