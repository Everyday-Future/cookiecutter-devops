<script>
    import {Meta, Template, Story} from "@storybook/addon-svelte-csf";
    import SignInPopover from "../../../components/Popover/SignInPopover.svelte";

    let signInMode = 'create_acct_msg';
</script>

<Meta
  title="components/Popover/SignInPopover"
  component={SignInPopover}
/>

<Template let:args>
  <div style="background-color: var(--cloudblue); width: 100%; height: 57px;" class="flex-center-row">
  <SignInPopover {...args} />
  </div>
</Template>

<Story
  name="Create Account"
  args={{
    signInMode: 'create_acct_msg'
  }}
/>

<Story
  name="Register Form"
  args={{
    signInMode: 'create_acct_form'
  }}
/>

<Story
  name="Sign In"
  args={{
    signInMode: 'sign_in_form'
  }}
/>

<Story
  name="Account Menu"
  args={{
    signInMode: 'acct_menu'
  }}
/>

