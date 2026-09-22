<script lang="ts">
  import "../app.css"; // Your Tailwind/global stylesheet
  import { ModeWatcher } from "mode-watcher";
  import SideView from "../lib/components/SideView.svelte";

  let { children } = $props(); // Svelte 5 syntax
</script>

<!-- Force the default mode to dark -->
<ModeWatcher defaultMode="dark" />

<SideView>
  {@render children?.()}
</SideView>
