<script>
    import {tweened} from 'svelte/motion';

    export let animateInterval = 400;
    export let isVertical = false;
    export let width = '200px';
    export let value = 0;
    const progress = tweened(0, {
        duration: animateInterval
    });
    $: {$progress = value}

</script>

<div style="width: {width}" class="progress-container" class:isVertical>
  <div class="progress-background"></div>
  <progress value={$progress}></progress>
</div>


<style>
  .progress-container {
    position: relative;
    height: 5px;
  }

  .isVertical {
    transform: rotate(90deg);
    transform-origin: left;
  }

  .progress-background {
    position: absolute;
    top: 2px;
    width: 100%;
    border-top: solid 1px var(--navy);
    opacity: 0.7;
  }

  /* indeterminate value */
  progress:not([value]) {

  }

  progress[value] {
    /* Reset the default appearance */
    -webkit-appearance: none;
    appearance: none;
    width: 100%;
    height: 5px;
    position: absolute;
  }

  progress[value]::-webkit-progress-bar {
    background-color: transparent;
  }

  progress[value]::-webkit-progress-value {
    background-color: var(--red);
}
</style>
