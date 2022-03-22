<script context="module">
    // noinspection ES6PreferShortImport
    import {fetchGet} from "../../lib/api";


    let defaultPosts = [];

    export async function load({fetch}) {
        try {
            const posts = await fetchGet(fetch, '/blog', false);
            const postsList = Object.values(posts);
            return {
                props: {
                    posts: postsList,
                },
            }
        } catch (e) {
            return {
                props: {
                    posts: defaultPosts,
                },
            };
        }
    }
</script>


<script>
    import BlogCard from "../../components/Cards/BlogCard.svelte";

    export let posts;

</script>


<div class="container">
  <div class="blog-menu-header">
    <h1 class="header-title">Blog</h1>
  </div>
  <div class="card-columns">
    {#each posts as post}
      <div class="card">
        <BlogCard {...post}/>
      </div>
    {/each}
  </div>
</div>

<style>

  .blog-menu-header {
    text-align: left;
    height: 80px;
    width: 100%;
    margin-left: 3px;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .header-title {
    color: var(--darknavy);
    flex: 1 1 0;
  }

  .card-columns .card {
    display: inline-block;
    width: 100%;
    margin: -6px 0;
  }

  @media (min-width: 576px) {
    .card-columns {
      -webkit-column-count: 3;
      -moz-column-count: 3;
      column-count: 3;
      -webkit-column-gap: 1.25rem;
      -moz-column-gap: 1.25rem;
      column-gap: 2.25rem;
      orphans: 1;
      widows: 1
    }
  }
</style>


