<script lang="ts">
  import ChatView from '$lib/components/chat/ChatView.svelte';

  let currentRoute = $state<string>('chat');
  
  export interface PageProps {
    props?: { [key: string]: any };
  }
</script>

<div class="flex min-h-screen flex-col">
  <ChatView />
</div>
