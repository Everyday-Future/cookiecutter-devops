<script>
    import {onMount} from 'svelte';
    import {fade} from 'svelte/transition';
    import FloatingActionButton from './PrevNextCarouselButton.svelte';
    import ChevronIcon from '../Icons/Chevron.svelte';
    import ProgressBar from './ProgressBar.svelte';
    import envVars from "../../lib/variables";

    export let carouselItems = [
        {'src': 'habits_at_a_glance.jpg', 'title': 'Test 3', 'subtitle': 'dsfsdf'},
        {'src': 'SMART_Goals.jpg', 'title': 'Test 2', 'subtitle': 'dsfsdf'},
        {'src': 'AccountabilityAgreement.jpg', 'title': 'Test 1', 'subtitle': 'dsfsdf'}
    ]

    export let animateInterval = 5000;
    export let index = 0;
    export let titleColor = 'var(--navy)';
    export let subtitleColor = titleColor;
    export let captioned = false;
    export let showPrevNext = true;
    export let showBullets = true;
    export let showProgress = true;
    export let bulletOffset = "20px"


    const prev = () => {
        index = (index - 1) % carouselItems.length
        if (index < 0)
            index = carouselItems.length - 1
    }

    const next = () => {
        index = (index + 1) % carouselItems.length
    }

    onMount(() => {
        const interval = setInterval(() => {
            next()
        }, animateInterval);

        return () => {
            clearInterval(interval);
        };
    });
</script>


<div style="position: relative; width: 100%; height: auto">
  <img src="{envVars.imgCDN}/{carouselItems[0].src}" alt="anchor image"
       style="position: relative; opacity: 0; width: 100%"/>
  {#each [carouselItems[index]] as eachImg (index)}
    <div class="img-container">
      <div class="img-inner-container">
        <img class="py-auto" transition:fade={{delay: 300}}
             src="{envVars.imgCDN}/{eachImg.src}"
             alt="{eachImg.title}"/>
      </div>
    </div>
  {/each}
  {#if showPrevNext}
    <div class="carousel-buttons">
      <div>
        <FloatingActionButton Icon={ChevronIcon} iconRotation={90} on:click={prev}/>
      </div>
      <div>
        <FloatingActionButton Icon={ChevronIcon} iconRotation={-90} on:click={next}/>
      </div>
    </div>
  {/if}
  {#if showProgress}
    <div class="progress-container">
      <div class="mx-auto w-75">
        {#key index}
          <ProgressBar {animateInterval}/>
        {/key}
      </div>
    </div>
  {/if}
  {#if showBullets}
    <div class="bullet-container">
      <div class="mx-auto" style="margin-top: {bulletOffset}">
        {#each carouselItems as eachImg, idx}
          <span class="bullet" class:selected="{index === idx}" on:click={() => {index = idx;}}>
          </span>
        {/each}
      </div>
    </div>
  {/if}
  <p class='img-title' style="color: {titleColor}" class:captioned>
    {carouselItems[index].title}
  </p>
  <p class='img-subtitle' style="color: {subtitleColor}" class:captioned>
    {carouselItems[index].subtitle}
  </p>
</div>


<style>
  .img-container {
    top: 0;
    left: 0;
    position: absolute;
    width: 100%;
    height: 100%;
    text-align: center;
  }

  .img-inner-container {
    display: flex;
    align-items: center;
    height: 100%;
  }

  img {
    max-width: 100%;
    width: 100%;
    height: auto;
    max-height: 100%;
  }

  .img-title {
    position: absolute;
    bottom: -20%;
    left: 0;
    margin: 0;
    width: 100%;
    text-align: center;
    font-size: 2.5vw;
    display: none;
  }

  .img-subtitle {
    position: absolute;
    bottom: -10%;
    left: 0;
    margin: 0;
    width: 100%;
    text-align: center;
    font-size: 2.0vw;
    display: none;
  }

  .captioned {
    display: inline-block;
  }

  .carousel-buttons {
    position: absolute;
    top: 0;
    width: calc(100% - 66px);
    left: 33px;
    height: 100%;
    display: flex;
    justify-content: space-between;
    align-items: center;
    z-index: 10;
  }

  .bullet-container {
    position: absolute;
    display: flex;
    top: 100%;
    width: 100%;
    z-index: 99;
  }

  .bullet {
    height: 10px;
    width: 10px;
    margin: 5px 10px;
    background-color: var(--white);
    border-radius: 50%;
    border: var(--red) solid 1px;
    display: inline-block;
    transition: 1s;
  }

  .bullet.selected {
    background-color: var(--red);
  }

  .progress-container {
    position: absolute;
    display: flex;
    width: 100%;
    top: calc(100% + 12px);
  }
</style>
