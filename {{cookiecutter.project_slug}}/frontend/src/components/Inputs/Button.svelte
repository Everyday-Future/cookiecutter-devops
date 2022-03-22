<script>
  import { createEventDispatcher } from 'svelte';
  import envVars from "../../lib/variables";
  /**
   * Is this the principal call to action on the page?
   */
  export let id = undefined;
  export let label = '';
  export let iconLeft = '';
  export let iconRight = '';
  export let width = 'auto';
  export let btnType = 'primary';
  export let btnSize = 'regular';
  let imgSize = `img-${btnSize}`;
  export let transitionMS = 400;
  const dispatch = createEventDispatcher();
  let columns = 'auto';
  if (iconLeft !== '') {
      columns = '30px ' + columns
  }
  if (iconRight !== '') {
      columns = columns + ' 30px'
  }

  /**
   * Optional click handler
   */
  function onClick(event) {
    dispatch('click', event);
  }
</script>

<button
  {id}
  type="button"
  class="btn {btnType} {btnSize}"
  style="transition: {transitionMS}ms; grid-template-columns: {columns}; width: {width}"
  on:click={() => {onClick()}}>
  {#if iconLeft !== ''}
    <img src="{envVars.imgCDN}/{iconLeft}" alt="check out" style="width: 30px" class={imgSize}>
  {/if}
  {label}
  {#if iconRight !== ''}
    <img src="{envVars.imgCDN}/{iconRight}" alt="check out" style="width: 30px" class={imgSize}>
  {/if}
</button>

<style>
  .btn {
    display: inline-grid;
    grid-template-columns: 30px auto 30px;
    grid-template-rows: 35px;
    column-gap: 15px;
    place-items: center;
    border-radius: 200px;
    text-decoration: none;
    -webkit-appearance: none;
    -moz-appearance: none;
    appearance: none;
    border: none;
    cursor: pointer; /* Mouse pointer on hover */
  }

  /*

  Colors

   */

  .primary {
    background-color: var(--red);
    color: var(--white);
    /*border: solid 3px #fff;*/
  }

  .primary:hover {
    background-color: #fff;
    color: #D5695C;
    /*border: solid 3px #D5695C;*/
  }

  .blue {
    background-color: var(--blue);
    color: var(--white);
    border: solid 3px #fff;
  }

  .blue:hover {
    background-color: var(--white);
    color: var(--blue);
    border: solid 3px #fff;
  }

  .blueinvert {
    background-color: var(--white);
    color: var(--blue);
    border: solid 3px #fff;
  }

  .blueinvert:hover {
    background-color: var(--blue);
    color: var(--white);
    border: solid 3px #fff;
  }

  .white {
    background-color: var(--white);
    color: var(--slate);
    border: none;
  }

  .white:hover {
    background-color: var(--slate);
    color: var(--white);
    border: none;
  }

  /*

  Sizes

   */

  .small {
    border-radius: 40px;
    padding: 6px 16px;
    font-size: 17px;
    font-weight: 500;
  }

  .regular {
    border-radius: 40px;
    padding: 13px 20px;
    font-size: 27px;
    font-weight: 500;
  }

  .large {
    border-radius: 40px;
    padding: 16px 24px;
    font-size: 32px;
    font-weight: 400;
  }

  @media screen and (max-width: 768px) {

  .small {
    border-radius: 40px;
    padding: 0 14px;
    font-size: 12px;
  }

  .regular {
    border-radius: 40px;
    padding: 0 14px;
    font-size: 15px;
  }

  .large {
    border-radius: 40px;
    padding: 8px 24px;
    font-size: 21px;
  }

  }


</style>
