<script>
    export let open;
    export let duration = 400;
</script>


<button class:open on:click={() => open = !open}
        style="transition: color {duration}ms ease-in-out; color: var(--white);">
  <svg width=32 height=32>
    <line id="top" x1=0 y1=9 x2=32 y2=9
          style="transition: transform {duration}ms ease-in-out, opacity {duration}s ease-in-out;"/>
    <line id="mid" x1=0 y1=18.5 x2=32 y2=18.5
          style="transition: transform {duration}ms ease-in-out, opacity {duration}s ease-in-out;"/>
    <line id="bot" x1=0 y1=28 x2=32 y2=28
          style="transition: transform {duration}ms ease-in-out, opacity {duration}s ease-in-out;"/>
  </svg>
</button>


<style>
  button {
    position: absolute;
    left: 0px;
    top: 0px;
    margin: 5px;
    z-index: 10;
    background-color: Transparent;
    background-repeat: no-repeat;
    border: none;
    cursor: pointer;
    overflow: hidden;
    outline: none;
  }

  button > svg {
    height: 40px;
    width: 40px;
    margin: 0;
  }

  svg line {
    stroke: currentColor;
    stroke-width: 3;
  }

  /* rotate the top line */
  .open #top {
    transform: translate(10px, 0px) rotate(45deg);
  }

  /* hide the middle */
  .open #mid {
    opacity: 0;
    color: transparent;
  }

  /* rotate the bottom line */
  .open #bot {
    transform: translate(-15px, 8px) rotate(-45deg);
  }
</style>