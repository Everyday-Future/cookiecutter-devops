
<script>

    // <CardTilingTemplate>
    //   <!-- content -->
    // </CardTilingTemplate>


</script>


<div class="container">
  <div class="card-columns">
    <slot></slot>
  </div>
</div>

<style>

  @media (min-width: 576px) {
    .card-columns {
      -webkit-column-count: 3;
      -moz-column-count: 3;
      column-count: 3;
      -webkit-column-gap: 1.25rem;
      -moz-column-gap: 1.25rem;
      column-gap: 3.25rem;
      orphans: 1;
      widows: 1
    }
  }
</style>


