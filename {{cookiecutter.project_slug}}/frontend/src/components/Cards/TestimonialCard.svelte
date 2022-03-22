<script>
    import StarRating from "../Inputs/StarRating.svelte";
    import Image from "../Image/Image.svelte";

    export let rating = 4.0;
    export let name = '';
    export let body = '';
    export let imgSrc = '';

</script>

<div class="card">
  <div class="container">
    {#if imgSrc !== ""}
      <Image src={imgSrc} alt={name} />
    {/if}
    <h4><b>{name}</b></h4>
    <p>{@html body}</p>
    <StarRating {rating}/>
  </div>
</div>


<style>
  .card {
    /* Add shadows to create the "card" effect */
    box-shadow: 0 4px 8px 0 rgba(0, 0, 0, 0.2);
    transition: 0.3s;
    border-radius: 5px; /* 5px rounded corners */
    break-inside: avoid;
    margin: 30px 0;
  }

  /* On mouse-over, add a deeper shadow */
  .card:hover {
    box-shadow: 0 8px 16px 0 rgba(0, 0, 0, 0.2);
  }

  /* Add some padding inside the card container */
  .container {
    padding: 2px 16px;
  }

</style>
