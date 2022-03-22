<script>
	import { Meta, Template, Story } from '@storybook/addon-svelte-csf';
	import SignInPopover from '../../../components/Popover/SignInPopover.svelte';
	import AuthPopover from '../../../components/Popover/AuthPopover.svelte';
</script>

<Meta title="components/Popover/SignInPopover/Component" component={SignInPopover} />

<Template let:args>
	<AuthPopover {...args} />
</Template>

<Story
	name="Sign In"
	args={{
		state: 'signin'
	}}
/>

<Story
	name="Create Account"
	args={{
		state: 'register'
	}}
/>
