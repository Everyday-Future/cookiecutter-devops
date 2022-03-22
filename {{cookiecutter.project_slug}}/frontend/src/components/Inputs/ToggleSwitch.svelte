<script>
    import {createEventDispatcher} from 'svelte';

    export let falseLabel = '';
    export let trueLabel = '';
    export let falseMessage = '';
    export let trueMessage = '';
    // Checkbox Status
    export let checked;
    export let name = '';
    export let spacerWidth = '1px';
    const dispatch = createEventDispatcher();

    // Propagate updates upward by raising the 'update' event
    function updateToggle() {
        dispatch('update', {'id': name, 'value': checked})
    }
</script>

<input type="checkbox" id="switch_{name}" bind:checked={checked} on:change={() => {updateToggle()}}>
<div class="app">
  <!-- Middle -->
  <div class="content">
    <label for="switch_{name}">
      <div class="toggle"></div>
      <div class="names" style="text-align: center">
        <p class="light">{falseLabel}</p>
        <div style="width: {spacerWidth}"></div>
        <p class="dark">{trueLabel}</p>
      </div>
    </label>
  </div>
</div>

{#if (falseMessage !== '') || (trueMessage !== '')}
  <div style="display: flex; align-items: center; justify-content: center; height: 80px">
  {#if checked === true}
    <p>{trueMessage}</p>
  {:else}
    <p>{falseMessage}</p>
  {/if}
  </div>
{/if}

<style>

  .app {
    max-width: 400px;
  }

  /*!* Middle *!*/
  .content {
    display: flex;
    flex-direction: column;
    margin: auto;
    text-align: center;
    transform: translateY(5%);
    padding: 0 10px;
  }

  label, .toggle {
    height: 60px;
    border-radius: 100px;
  }

  label {
    width: 100%;
    background-color: rgba(0, 0, 0, .1);
    border-radius: 100px;
    position: relative;
    cursor: pointer;
  }

  .toggle {
    position: absolute;
    width: 50%;
    background-color: #fff;
    box-shadow: 0 2px 15px rgba(0, 0, 0, .15);
    transition: transform .3s cubic-bezier(0.25, 0.46, 0.45, 0.94);
  }

  .names {
    padding: 21px 0;
    font-size: 15px;
    font-weight: 600;
    width: 100%;
    position: absolute;
    display: flex;
    justify-content: space-around;
    user-select: none;
  }

  label::after {
    content: '';
  }

  /* -------- Switch Styles ------------*/
  [type="checkbox"] {
    display: none;
  }

  /* Toggle */
  [type="checkbox"]:checked + .app .toggle {
    transform: translateX(100%);
  }

  [type="checkbox"]:checked + .app .dark {
    opacity: 1;
  }

  [type="checkbox"]:checked + .app .light {
    opacity: .7;
  }

  [type="checkbox"]:not(checked) + .app .light {
    opacity: 1;
  }

  [type="checkbox"]:not(checked) + .app .dark {
    opacity: .7;
  }
</style>