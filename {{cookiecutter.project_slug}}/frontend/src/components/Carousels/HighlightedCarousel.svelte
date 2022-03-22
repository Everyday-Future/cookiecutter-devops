<script>
    import DualFeature from "../Panels/DualFeature.svelte";
    import ImageCarousel from "./Carousel.svelte";
    import Button from "../Inputs/Button.svelte";
    import envVars from "../../lib/variables.js";
    import {fly} from 'svelte/transition';

    export let animateInterval = 5000;
    export let index = 0;
    export let carouselItems = [
        {
            "src": "journal_banner_1-1600.jpg",
            "title": "task tracking",
            "subtitle": "",
            "iconSrc": "list-task-tracking.svg",
            "description": "Goal-oriented planners, multi-taskers,<br class=\"lg-only\"> and those looking to simplify their day-to-day."
        },
        {
            "src": "planner_lifestyle_morning_2-1000.jpg",
            "title": "deep thinking",
            "subtitle": "",
            "iconSrc": "Creative Packs-Writer.svg",
            "description": "Deep thinkers—busy brains, diary lovers,<br class=\"lg-only\"> anyone focused on self-growth."
        },
        {
            "src": "notebook_banner_1-1600.jpg",
            "title": "designing and making",
            "subtitle": "",
            "iconSrc": "Creative Packs-Designer.svg",
            "description": "Makers—Engineers, designers,<br class=\"lg-only\"> creators, cooks and more."
        },
        {
            "src": "muse_banner_1-1600.jpg",
            "title": "creativity",
            "subtitle": "",
            "iconSrc": "Creative Packs-Artist.svg",
            "description": "Creative minds—designed for the expression<br class=\"lg-only\"> of creativity without borders."
        },
        {
            "src": "trainer_lifestyle_5-1000.jpg",
            "title": "record-breaking",
            "subtitle": "",
            "iconSrc": "cardio-health-running.svg",
            "description": "Health nuts—athletes, coaches, personal trainers<br class=\"lg-only\"> and those looking to get that extra 1% out of their workout."
        },
    ]

</script>

<DualFeature>
  <div slot="left" class="img-carousel mx-2 mx-lg-0" style="position: relative">
    <ImageCarousel {carouselItems} {animateInterval} showPrevNext={false} bulletOffset="110px" bind:index/>
    <div class="cta-btn">
      <a href="/shop" style="text-decoration: none">
        <Button btnType="white" label="Customize Now"/>
      </a>
    </div>
  </div>
  <div slot="right">
    <!--  Desktop-only icons and descriptions  -->
    <h3 class="lg-only w-100">Great for</h3>
    <div class="great-for-table flex-center-column lg-only" style="justify-content: flex-start">
      {#each carouselItems as item, idx}
        <div class="great-for-item">
          <img class:selected="{index === idx}" src="{envVars.imgCDN}/{item.iconSrc}" alt="{item.title}" width="64px"/>
          <p class:selected="{index === idx}">{@html item.description}</p>
        </div>
      {/each}
    </div>
    <!--  Mobile-only icons and descriptions  -->
    {#key index}
      <div class="sm-only mx-auto" style="position: relative; height: 100px; width: 90vw; margin-top: 5px">
        <div class="great-for-item" in:fly={{x: 300, delay: 150}}>
          <img class="selected" src="{envVars.imgCDN}/{carouselItems[index].iconSrc}"
               alt="{carouselItems[index].title}" width="74px"/>
          <p>{@html carouselItems[index].description}</p>
        </div>
      </div>
    {/key}
  </div>
</DualFeature>


<style>
  .great-for-table {
    flex-grow: 0;
  }

  .img-carousel {
    padding: 0;
  }

  .great-for-item {
    display: grid;
    grid-template-columns: 74px 1fr;
    align-items: center;
    width: 100%;
    height: auto;
    margin: 30px 0;
  }

  .great-for-item p {
    font-weight: 400;
    padding-left: 20px;
    transition: 300ms;
  }

  .great-for-item img {
    opacity: 0.7;
    transition: 300ms;
  }

  .selected {
    font-weight: 600 !important;
    opacity: 1 !important;
  }

  .cta-btn {
    position: absolute;
    bottom: 27px;
    right: 30px;
  }

  :global(.bullet-container) {
    opacity: 0;
  }

  @media screen and (max-width: 768px) {

    .great-for-item {
      margin: 0;
    }

    .img-carousel {
      padding: 0 3vw;
    }

    .great-for-item p {
      font-size: 0.9rem;
      font-weight: 600;
    }

    .cta-btn {
      right: 40px;
    }

    :global(.bullet-container) {
      opacity: 1;
    }

  }
</style>