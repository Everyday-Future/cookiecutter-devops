<script>
  export let qty = 0;
  export let open = true;
  export let label = '';
  export let maxQuantity = 1000; // support for adding a max allowed limit
  import { createEventDispatcher } from 'svelte';
  const dispatch = createEventDispatcher();

  const setQuantity = (updatedQuantity) => {
    if (updatedQuantity < maxQuantity && updatedQuantity >= 0) {
      qty = updatedQuantity;
      dispatch('update', {qty})
    }
  };
</script>

<div class="changer">
  <p class="qty-label" class:open>{label}</p>
  <div class="changer__controls">
    <button class:open on:click|stopPropagation={() => {setQuantity(qty - 1)}}>-</button>
    <input
      on:click|stopPropagation={() => {setQuantity(qty)}}
      style="opacity: 1; width: 2.5rem;"
      type="number"
      bind:value={qty}
      min="1"
      step="1"
      onkeypress="return event.charCode >= 48 && event.charCode <= 57"
    />
    <button class:open on:click|stopPropagation={() => {setQuantity(qty + 1)}}>+</button>
  </div>
</div>

<style scoped>
  button, p {
    opacity: 0;
    pointer-events: none;
    transition: 300ms;
  }

  .open {
    opacity: 1;
    pointer-events: all;
  }

  .changer {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    color: #6d7a83;
    font-size: 0.8rem;
  }

  .changer__controls {
    display: flex;
    flex-direction: row;
    gap: 0.25rem;
  }

  .changer__controls button {
    width: 1.5rem;
    height: 1.5rem;
    padding: 0;
    margin: 0;
    border-radius: 0.3rem;
    background-color: #e9ebec;
    color: #707070;
    font-size: 1.4rem;
    line-height: 0;
    text-decoration: none;
    border: none;
    cursor: pointer;
    transition: background 0.3s linear;
  }

  .changer__controls button:hover {
    background-color: hsl(0, 0%, 80%);
  }

  .changer__controls input {
      width: 1.5rem;
      height: 1.5rem;
    margin: 0;
    border-radius: 0.3rem;
    text-align: center;
    background-color: white;
    color: #6e7c84;
      font-size: 1rem;
    outline: 1px solid #cfd3d5;
    border: none;
  }

  input::-webkit-outer-spin-button,
  input::-webkit-inner-spin-button {
    -webkit-appearance: none;
    margin: 0;
  }

  input[type='number'] {
    -moz-appearance: textfield;
  }

  .qty-label {
    display: none;
  }

  /* Change to Desktop Version */
  @media (min-width: 500px) {
    .changer {
      flex-direction: row;
      align-items: center;
      gap: 1rem;
      font-size: 1rem;
    }

    .changer__controls button,
    .changer__controls input {
    width: 2.2rem;
    height: 2.2rem;
    font-size: 1.3rem;
    }

  .qty-label {
    display: inline;
  }
  }
</style>
