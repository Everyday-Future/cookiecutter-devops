<script context="module">
    export const prerender = true;
</script>

<script>
    import Header from "../components/Panels/Header.svelte";
    import Feature from "../components/Panels/Feature.svelte";
    import Image from "../components/Image/Image.svelte";

</script>

<!-- Highlighted feature carousel -->
<div style="margin: 100px 0 60px 0">
  <Header
    script="Build your site here!"
    subtitle="So much room for activities"
    body="Did you touch my drum set?!"
  />
</div>

<div class="shipping-feature">
<Feature {...{
    isReversed: true,
    heading: '',
    subheading: 'Ships Free',
    body: 'Useful, beautiful and delivered to your doorstep. All orders ship free. ' +
        'Average delivery time is 10 business days.',
}}>
  <Image src='demo.jpg' alt="Ships for free"/>
</Feature>
</div>


<style>

  .shipping-feature {
    margin: -100px 50px 20px 50px;
  }

</style>
