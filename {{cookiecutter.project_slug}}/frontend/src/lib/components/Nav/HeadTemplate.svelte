<script>
	/*
    Fill out a complete metadata map for the page and mount it to the head of the document
     */
	export let title = ''
	export let description = ''
</script>

<svelte:head>
	<!--{# Required meta tags #}-->
	<meta charset="utf-8"/>
  	<link rel="icon" type="image/x-icon" href="/favicon.ico">
	<meta
		name="viewport"
		content="width=device-width, initial-scale=1, shrink-to-fit=no maximum-scale=1.0, user-scalable=no"
	/>
	<!--{# Primary Meta Tags #}-->
	<meta name="title" content="{title}"/>
	<meta name="description" content="{description}"/>
	<title>{title}</title>
	<meta
		name="keywords"
		content=""
	/>
	<meta name="copyright" content=""/>
	<meta
		http-equiv="Content-Security-Policy"
		content="default-src *;"
	/>
	<!-- Fonts -->
	<link
		href="https://fonts.googleapis.com/css2?&family=Work+Sans:wght@400;500;600&display=swap"
		rel="stylesheet"
	/>
</svelte:head>
