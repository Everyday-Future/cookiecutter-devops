<script>
    export let title = '';
    export let isOpen = true;
    export let durationMS = 300;
    import {slide} from 'svelte/transition';
    import Chevron from '../Icons/Chevron.svelte';

    export let styling = 'overmenu';
    let chevronFill = 'var(--navy)';
    let fontColor = 'var(--navy)';
    let textAlign = 'center';

    if (styling === 'navmenu') {
        chevronFill = 'var(--white)';
        fontColor = 'var(--white)';
        textAlign = 'left';
    }
</script>


<div class="submenu-accordion">
  <div class="submenu-bar {styling}" on:click|stopPropagation={() => {isOpen = !isOpen}}>
    <p class="submenu-title" style="color: {fontColor}">{title}</p>
    <div class="submenu-arrow">
      <Chevron fillColor={chevronFill} rotation={isOpen * 180}/>
    </div>
    {#if isOpen}
      <div
        on:click|stopPropagation={() => {}}
        class="submenu-contents"
        style="text-align: {textAlign}"
        transition:slide|local="{{duration: durationMS}}">
        <slot/>
      </div>
    {/if}
  </div>
</div>


<style>
  .submenu-bar {
    margin-bottom: 8px;
    font-size: 16px;
    padding: 8px;
    position: relative;
  }

  .overmenu {
    background: var(--white) 0 0 no-repeat padding-box;
    box-shadow: 0px 3px 6px #00000029;
  }

  .navmenu {
    background: var(--red) 0 0 no-repeat padding-box;
  }

  .submenu-title {
    font-size: 19px;
    left: 21px;
  }

  .submenu-arrow {
    position: absolute;
    right: 20px;
    top: 10px;
    width: 20px;
  }

</style>
