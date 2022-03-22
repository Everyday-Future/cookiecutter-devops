<script>
    import Image from "../Image/Image.svelte";
    import {onMount} from "svelte";

    export let link = '';
    export let src = '';
    export let alt = '';
    export let mobileSrc;
    export let title = '';
    export let summary = '';
    export let tags = '';


    onMount(() => {
        if (mobileSrc === '' || mobileSrc === null) {
            mobileSrc = src;
        }
    })

</script>

<div class="card">
  <a href="/blog/{link}">
    <Image {src} {alt}/>
    <div class="card-container">
      <h4 class="my-2"><b>{title}</b></h4>
      <p class="blog-tags">{tags}</p>
      <p class="pb-2">{@html summary}</p>
    </div>
  </a>
</div>


<style>
  a:link {
  text-decoration: none;
}
  .card {
    /* Add shadows to create the "card" effect */
    box-shadow: 0 4px 8px 0 rgba(0, 0, 0, 0.2);
    transition: 0.3s;
    border-radius: 5px; /* 5px rounded corners */
    margin-bottom: 50px;
    break-inside: avoid;
  }

  /* Add rounded corners to the top left and the top right corner of the image */
  img {
    border-radius: 5px 5px 0 0;
  }

  /* On mouse-over, add a deeper shadow */
  .card:hover {
    box-shadow: 0 8px 16px 0 rgba(0, 0, 0, 0.2);
  }

  /* Add some padding inside the card container */
  .card-container {
    padding: 2px 16px;
  }

  .blog-tags {
    color: #D5695C;
    font-weight: 600;
  }

</style>
