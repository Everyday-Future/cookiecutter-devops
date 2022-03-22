<script>
    import {slide} from 'svelte/transition';
    import ChevronIcon from "../Icons/Chevron.svelte";

    export let label = '';
    export let selectedText = '';
    export let foregroundColor = '#4c5559';
    export let width = "200px";
    export let isOpen = false;
    export let transitionMS = 400;
    // Picker types include 'border' and 'line'
    export let pickerType = 'line';

</script>

<div id="dropdown-picker unselectable" style="display: inline-block">
  <div class="picker-body" on:click="{() => {isOpen = !isOpen}}">
    <p class="mr-2" style="color: {foregroundColor}; font-size: max(2vw, 11px)">{label}</p>
    <p class="picker-input picker-{pickerType}"
       style="display: inline; width: {width}; border-color: {foregroundColor}">
      {selectedText}
    </p>
    <div class="mx-2" style="width: 20px; display: inline">
      <ChevronIcon fillColor="{foregroundColor}" />
    </div>
  </div>
  <!--  Show the options if the selector is opened-->
  {#if isOpen === true}
    <div class="dropdown-body" transition:slide="{{ duration: 400, y: 150 }}">
      <slot></slot>
    </div>
  {/if}
</div>

<style>

  #dropdown-picker {
    position: relative;
  }

  .picker-body {
    display: flex;
    align-items: center;
    justify-content: center;
    flex-direction: row;
  }

  .picker-input {
    height: 27px;
  }

  .picker-line {
    border-bottom: solid 1px;
  }

  .picker-border {
    border: solid 1px;
  }

  .dropdown-body {
    position: absolute;
    left: 0;
    top: 30px;
  }

</style>