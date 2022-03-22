<script>
  import { Meta, Template, Story } from "@storybook/addon-svelte-csf";
  import SaveButton from "../../../components/Inputs/SaveButton.svelte";
</script>

<Meta
  title="components/Inputs/SaveButton"
  component={SaveButton}
  argTypes={{
    isLoggedIn: { control: "boolean" },
    onClick: { action: "onClick" }
  }}
/>

<Template let:args>
  <div style="background-color: var(--slate); width: 100%; height: 200px; " class="flex-center-row">
  <SaveButton {...args} on:click={args.onClick} />
  </div>
</Template>

<Story
  name="Logged In"
  args="{{
      isLoggedIn: true
  }}"
/>

<Story
  name="Logged Out"
  args="{{
      isLoggedIn: false
  }}"
/>
