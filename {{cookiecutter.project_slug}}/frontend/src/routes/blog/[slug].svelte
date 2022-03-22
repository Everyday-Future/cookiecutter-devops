<script context="module">
    // noinspection ES6PreferShortImport
    import {fetchGet} from "../../lib/api";

    export async function load({fetch, params}) {
        try {
            const post = await fetchGet(fetch, `/blog/${params.slug}`, false);
            // eslint-disable-next-line no-unused-vars
            const title = post.title;
            return {
                props: {
                    post,
                },
            }
        } catch (e) {
            return {
                status: 404,
                error: 'Post not found'
            };
        }
    }
</script>

<script>
    export let post
</script>

<svelte:head>
  <title>{post.title}</title>
</svelte:head>

<article class="my-6">
  <h1 style="text-align: center">{post.title}</h1>
  <div class="container">
    {@html post.body}
  </div>
</article>

<style>
  article :global(img) {
    width: 50%!important;
  }

  article :global(h1) {
    margin-bottom: 40px;
  }

  article :global(h2) {
    margin: 50px 0 30px 0;
  }

  article :global(p) {
    margin: 20px 0!important;
  }

  article :global(.col-6) {
    text-align: center;
  }
</style>