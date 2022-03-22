<script context="module">
    export function load({error, status}) {
        return {
            props: {
                title: `${status}: ${error.message}`
            }
        };
    }
</script>

<script>
    export let title;
</script>

<div class="my-6">
  <h1 style="text-align: center" class="mb-3">{title}</h1>
  <div class="my-2 mx-auto" style="max-width: 600px; text-align: center">
    <img src="https://media.giphy.com/media/S8kS4yKtMlNl27agy4/giphy.gif">
  </div>
</div>