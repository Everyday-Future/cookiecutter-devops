<script>
	export let username = '';
</script>

<ul>
	<li><b>Welcome, {username}!</b></li>
	<li><a href="#">Saved Layouts</a></li>
	<li><a href="#">Order History</a></li>
	<li><a href="#">Logout</a></li>
</ul>

<style scoped>
	ul {
		list-style: none;
		margin: 1.5rem 0;
		padding: 0;
	}

	li {
		border-bottom: 1px solid var(--navy);
		padding: 0.8rem 2rem;
	}

	a {
		color: var(--navy);
		text-decoration: none;
	}

	a:hover {
		background-color: hsl(0, 0%, 97%);
	}

	b {
		color: var(--navy);
	}
</style>
