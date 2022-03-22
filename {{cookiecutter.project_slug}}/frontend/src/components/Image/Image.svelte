
<script>
  // Placeholder for the ultimate image loader
  import envVars from "../../lib/variables";
  export let src = '';
  export let alt = '';
  export let width = '';
  export let height = '';

  if (!src.includes('http')) {
      src = `${envVars.imgCDN}/${src}`
  }
</script>

<img src="{src}" {alt} style="width:100%" />