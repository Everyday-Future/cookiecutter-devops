<script>
    import Button from "../Inputs/Button.svelte";

    export let heading = '';
    export let subheading = '';
    export let body = '';
    export let btnText = '';
    export let btnLink = '';
    export let isReversed = false;
    export let isVerticalReversed = false;
    let reversedClass = '';

    if (isVerticalReversed === true) {
        reversedClass = 'vert';
    } else if (isReversed === true) {
        reversedClass = 'reversed';
    }
</script>

<div class="info-container">
  <!--  Image slot -->
  <div class="left-panel {reversedClass}">
    <slot></slot>
  </div>
  <!--  Feature content -->
  <div class="right-panel {reversedClass}">
    <h4 class="font-sharpie mb-2">{heading}</h4>
    <h2 class="mb-4">{@html subheading}</h2>
    <p>
      {@html body}
    </p>
    {#if btnText !== ''}
      <div class="btn-container">
        <Button label="{btnText}" on:click={() => {location.href=btnLink}}/>
      </div>
    {/if}
  </div>
</div>

<style>
  p {
    font-size: 24px;
    line-height: 29px;
    max-width: 500px;
  }

  h2 {
    font-size: 35px;
  }

  h4 {
    font-size: 24px;
    line-height: 32px;
  }

  .info-container {
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
  }

  .left-panel, .right-panel {
    flex: 1 1 0;
    padding: 10px 0;
  }

  .btn-container {
    padding-top: 20px;
  }

  .left-panel.vert {
    order: 1;
  }

  .right-panel.vert {
    order: 0;
  }

  @media only screen and (orientation: landscape) {
    .info-container {
      display: flex;
      flex-direction: row;
    }

    .left-panel, .right-panel {
      flex: 1 1 0;
      padding: 0 20px;
    }

    .left-panel.reversed {
      order: 1;
    }

    .right-panel.reversed {
      order: 0;
    }
  }

</style>

