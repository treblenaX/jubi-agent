<script lang="ts">
  import { Root, Textarea, Addon, Button } from "$lib/components/ui/input-group";
  import { ArrowUp02Icon } from "@hugeicons/core-free-icons";
  import { HugeiconsIcon } from "@hugeicons/svelte";

  // Svelte 5 runes mode - use $props()
  interface Props {
    tokenUsage?: number;   // Context used, percent (0-100); undefined = unknown
    disabled?: boolean;
    placeholder?: string;
    onSend?: (content: string) => void;
  }

  const {
    tokenUsage,
    disabled = false,
    placeholder = "Ask, Search or Chat...",
    onSend = () => {}
  } = $props<Props>();

  let value = $state<string>("");
  let isComposing = $state(false);

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

  // Context bar: fill = used, hover tooltip = left. Color escalates near the limit.
  const pct = $derived(
    tokenUsage === undefined ? null : Math.min(100, Math.max(0, Math.round(tokenUsage)))
  );
  const barColor = $derived(
    pct === null ? "" : pct > 85 ? "bg-destructive" : pct > 65 ? "bg-amber-500" : "bg-primary"
  );
</script>

<Root class="w-full border-transparent">
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
    <!-- Context usage indicator: % shown on hover -->
    {#if pct !== null}
      <div class="group relative ms-auto flex items-center">
        <div class="h-1 w-40 overflow-hidden rounded-full bg-muted">
          <div
            class="h-full rounded-full transition-all duration-500 {barColor}"
            style="width: {pct}%"
          ></div>
        </div>
        <span
          class="pointer-events-none absolute right-0 bottom-full z-50 mb-2 hidden whitespace-nowrap rounded-md border bg-popover px-2 py-1 text-xs tabular-nums text-popover-foreground shadow-md group-hover:block"
        >
          {100 - pct}% left
        </span>
      </div>
    {/if}

    <!-- Send button -->
    <Button
      variant="default"
      size="icon"
      class="ms-auto rounded-full"
      disabled={disabled || !value.trim()}
      onclick={send}
    >
      <HugeiconsIcon icon={ArrowUp02Icon} />
      <span class="sr-only">Send</span>
    </Button>
  </Addon>
</Root>

<style>
  /* No border ever: base + focus + control focus-visible ring */
  :global([data-slot="input-group"]) {
    border-color: transparent;
  }
  :global([data-slot="input-group"]:focus-within) {
    border-color: transparent;
    box-shadow: none;
    background-color: color-mix(in oklab, #7c4dff 7%, transparent);
  }
  :global([data-slot="input-group"]:has([data-slot="input-group-control"]:focus-visible)) {
    border-color: transparent;
    box-shadow: none;
  }
  :global([data-slot="input-group"] [data-slot="input-group-control"]) {
    outline: none !important;
    box-shadow: none !important;
  }
</style>
