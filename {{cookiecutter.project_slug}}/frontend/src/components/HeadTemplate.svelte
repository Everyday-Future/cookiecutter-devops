<script>
	/*
    Fill out a complete metadata map for the page and mount it to the head of the document
     */
	import envVars from '../lib/variables';

	export let title = '{{ cookiecutter.project_name }}';
	export let description = '{{ cookiecutter.project_short_description }}';
    export let domain = '{{ cookiecutter.project_domain }}'
    export let slug = '{{ cookiecutter.project_slug }}';
	export let baseUrl = 'https://www.{{ cookiecutter.project_domain }}';
	// export let thumbnailImage = 'favicon.png';
</script>

<svelte:head>
	<!--{# Required meta tags #}-->
	<meta charset="utf-8" />
	<meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no" />
	<!--{# Primary Meta Tags #}-->
	<meta name="title" content={title} />
	<meta name="description" content={description} />
	<title>{title}</title>
	<meta
		name="keywords"
		content="keyword,list"
	/>
	<meta name="copyright" content="Copyright 2022 ..." />
<!--  TODO - Add content security policy  -->
	<meta
		http-equiv="Content-Security-Policy"
		content="*"
	/>
	<!--{# Open Graph / Facebook #}-->
	<meta property="og:type" content="website" />
	<meta property="og:url" content={baseUrl} />
	<meta property="og:title" content={title} />
	<meta property="og:description" content={description} />
<!--	<meta property="og:image" content="{envVars.imgCDN}/{thumbnailImage}" />-->
	<meta property="fb:app_id" content="716086475511927" />
	<meta property="og:site_name" content="{title}" />
	<meta name="facebook-domain-verification" content="y67dzw79l19luayfqh3spsiwgvyzyr" />
	<meta property="author" content="{title}" />
	<meta property="article:author" content="{title}" />
	<meta property="article:publisher" content="https://www.facebook.com/{slug}" />
	<!--{# Twitter #}-->
	<meta name="twitter:card" content="summary_large_image" />
	<meta name="twitter:url" content={baseUrl} />
	<meta name="twitter:title" content={title} />
	<meta name="twitter:description" content={description} />
<!--	<meta name="twitter:image" content="{envVars.imgCDN}/{thumbnailImage}" />-->
	<meta name="twitter:site" content="@{slug}" />
	<meta name="twitter:domain" content="{domain}" />
	<!--{# IExplorer and Windows 8.1+ #}-->
	<meta name="msapplication-TileColor" content="#D5695C" />
	<meta
		name="msapplication-TileImage"
		content="https://blog.{domain}/favicon-144.png"
	/>
	<link rel="preconnect" href="https://fonts.googleapis.com" crossorigin />
	<link rel="preconnect" href="https://cdnjs.cloudflare.com" crossorigin />
	<link
		href="https://fonts.googleapis.com/css2?family=Permanent+Marker:wght@400&display=swap"
		rel="stylesheet"
	/>
	<link
		href="https://fonts.googleapis.com/css2?&family=Work+Sans:wght@300;400;500;600&display=swap"
		rel="stylesheet"
	/>
</svelte:head>
