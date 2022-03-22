<script context="module">

    export async function load({url, session}) {
        return {
            props:
                {
                    token: session.userid,
                    path: url.pathname,
                }
        }
    }
</script>


<script>
    // Universal css files
    import '../normalize.css';
    import '../base.css';
    import '../layout.css';
    import '../common.css';
    // The default layout components
    import HeadTemplate from "../components/HeadTemplate.svelte";
    import Navbar from "../components/Navbar.svelte";
    import Footer from "../components/Footer.svelte";
    // User id and page information
    import {browser} from '$app/env';
    import {uid} from "$lib/user";

    export let token;
    export let path;

    // Save the user token to the uid store if it's available
    if ((browser) && (token)) {
        $uid = token;
    }

    let pageData = {
        '': {
            title: 'Custom Books by Luminary Handbook',
            description: 'Custom journals, planners, notebooks and more',
        },
        '/': {
            title: 'Custom Books by Luminary Handbook',
            description: 'Custom journals, planners, notebooks and more',
        },
        '/store': {
            title: 'Custom Books by Luminary Handbook',
            description: 'Custom journals, planners, notebooks and more',
        }
    }

</script>


<HeadTemplate
  title={pageData[path]?.title || 'Custom Books by Luminary Handbook'}
  description={pageData[path]?.description || 'Custom journals, planners, notebooks and more'}
/>
<Navbar page={path}/>
<div style="min-height: 91vh">
  <slot/>
</div>
<Footer/>
