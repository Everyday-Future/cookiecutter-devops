<script>
    export let label = "";
    export let value = "1";
</script>


<div id="ck-button" class="unselectable">
  <label>
    <input type="checkbox" bind:checked={value}><span id="bg-span">{label}</span>
  </label>
</div>

<style>
  div label input {
    margin-right: 100px;
  }

  label::after {
    content: '';
  }

  #ck-button {
    margin: 6px 4px;
    border-radius: 70px;
    overflow: hidden;
    display: inline;
    height: 70px;
    font-size: 18px;
    font-weight: 700;
    color: var(--navy);
    background-color: var(--white);
  }

  #ck-button label {
    /*float: left;*/
    width: 180px;
    display: inline-block;
  }

  #ck-button label span {
    text-align: center;
    padding: 24px 0;
    display: block;
  }

  #ck-button label input {
    position: absolute;
    top: -200px;
  }

  #bg-span {
    height: 70px;
    border-radius: 60px;
    border:1px solid var(--navy);
    /*margin: 1px;*/
  }

  #ck-button input:checked + span {
    /*background-color: var(--blue);*/
    border:4px solid var(--blue);
    padding: 21px 0;
  }
</style>
