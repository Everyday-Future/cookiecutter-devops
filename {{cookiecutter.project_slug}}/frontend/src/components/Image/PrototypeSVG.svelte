<script>
	/**
	 * PROPS
	 */

	/**
	 * @type {string} title
	 */
	export let title

	/**
	 * @type {'left'|'right'} pageSide
	 */
	export let pageSide

</script>

<svg viewBox="0 0 240 80" xmlns="http://www.w3.org/2000/svg">
	<text x="20" y="35">{title} ({pageSide})</text>
</svg>
