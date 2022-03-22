<script>
  import { createEventDispatcher } from 'svelte';
  import { fade } from 'svelte/transition';

  const dispatch = createEventDispatcher(); // dispatcher to allow us to open it from a button

  export let open = false; // boolean to determine if modal is showing so we can dispatch it
  export let overlay = false; // specify if you want a backdrop or not
  export let alignment = 'center'; // modal alignment, can be modified in getAlignment function to apply class

  const getAlignment = () => {
    switch (alignment) {
      default:
      case 'center':
      case 'middle':
        return 'justify-center';
      case 'top':
      case 'flex-start':
        return 'justify-start';
    }
  };
</script>

{#if open}
  <div class={`modal ${getAlignment()}`}>
    {#if overlay}
      <div
        class="modal-overlay"
        in:fade={{ duration: 200 }}
        out:fade={{ duration: 200 }}
        on:click={() => dispatch('close')}></div>
    {/if}
    <div
      class="modal-inner"
      style={!overlay ? 'box-shadow: 0 0 14px hsl(0, 0%, 70%);' : ''}
      in:fade={{ duration: 200 }}
      out:fade={{ duration: 100 }}
    >
      <button class="button-close" on:click={() => dispatch('close')}>
        <svg
          xmlns="http://www.w3.org/2000/svg"
          height="24px"
          viewBox="0 0 24 24"
          width="24px"
          fill="#000000"
          ><path d="M0 0h24v24H0V0z" fill="none" /><path
            d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12 19 6.41z"
          /></svg
        >
      </button>
      <slot>
        <div style="width: 200px; height: 200px;">Placeholder Modal</div>
      </slot>
    </div>
  </div>
{/if}

<style scoped>
  .justify-center {
    justify-content: center;
  }

  .justify-start {
    justify-content: flex-start;
  }
  .modal {
    display: flex;
    flex-direction: column;
    align-items: center;
    position: fixed;
    z-index: 1200;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    padding: 1rem;
  }

  .modal-overlay {
    z-index: 1200;
    display: flex;
    align-items: center;
    justify-content: center;
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: hsla(0, 0%, 0%, 0.5);
  }

  .modal-inner {
    z-index: 1201;
    max-width: 600px;
    padding: 2rem;
    display: flex;
    flex-direction: column;
    gap: 1rem;
    align-items: center;
    background-color: white;
    border-radius: 1rem;
    overflow-y: auto;
    /* box-shadow: 0 0 14px hsl(0, 0%, 70%); */
    position: relative;
  }

  .button-close {
    color: hsl(0, 0%, 100%);
    border: none;
    background: none;
    cursor: pointer;
    position: absolute;
    right: 10px;
    top: 10px;
  }

  @media screen and (min-width: 768px) {
    .modal {
      padding: 4rem;
    }
  }
</style>
