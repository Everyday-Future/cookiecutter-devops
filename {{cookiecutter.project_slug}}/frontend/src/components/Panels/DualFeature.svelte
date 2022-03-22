<script>

  // InfoTemplate - Two-column responsive layout
  //
  // <DualFeature>
  //   <div slot="left">
  //
  //   </div>
  //   <div slot="right">
  //
  //   </div>
  // </DualFeature>

    export let isReversed = false;
    let reversedClass = '';

    if (isReversed === true) {
        reversedClass = 'reversed';
    }
</script>

<div class="info-container">
  <div class="left-panel {reversedClass}">
    <slot name="left" style="width: 100%"></slot>
  </div>
  <div class="right-panel {reversedClass}">
    <slot name="right" style="width: 100%"></slot>
  </div>
</div>

<style>

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

@media only screen and (orientation: landscape) {
  .info-container {
    display: flex;
    flex-direction: row;
  }
  .left-panel, .right-panel {
    flex: 1 1 0;
    padding: 0 50px;
  }

  .left-panel.reversed {
    order: 1;
  }

  .right-panel.reversed {
    order: 0;
  }
}

</style>

