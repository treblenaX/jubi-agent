<script lang="ts">
  import { render, unmount } from 'svelte/motion';

  interface Props {
    children?: any;
    disabled?: boolean;
    hydrateId?: string;
  }

  let props = $props<Props>();
</script>

{#if !props.disabled}
  <div class="portal-root" data-portal={props.hdrateId}>
    {props.children}
  </div>
{/if}
