
<script>

  // <InfoHeader heading="" />

  export let script="";
  export let subtitle="";
  export let body="";
  export let bgColor = "var(--white)";
  export let txtColor="var(--darknavy)";
  export let scriptColor="var(--sharpieblue)";
  export let borderColor="var(--white)";

</script>


<div class="container-fluid flex-center-col p-0"
     style="background-color: {bgColor}; border-top: 1px solid {borderColor};
     border-bottom: 1px solid {borderColor}; text-align: center">
    <div class="mx-auto">
      <p class="sharpie-heading" style="color: {scriptColor}">
        {@html script}
      </p>
      <p class="block-heading" style="color: {txtColor}; max-width: 670px;">
        {@html subtitle}
      </p>
      <p class="block-body" style="color: {txtColor}; max-width: 670px; text-align: left;">
        {@html body}
      </p>
  </div>
</div>


<style>
  p {
    margin: 10px 0;
  }
  .block-body {
    font-size: 22px;
    line-height: 28px;
    font-weight: 400;
  }

</style>
