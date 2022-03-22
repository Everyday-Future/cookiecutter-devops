<script>
  import { Meta, Template, Story } from "@storybook/addon-svelte-csf";
  import ToggleButton from "../../../components/Inputs/ToggleButton.svelte";
</script>

<Meta
  title="components/Inputs/ToggleButton"
  component={ToggleButton}
  argTypes={{
    label: { control: "text" },
    onClick: { action: "onClick" },
  }}
/>

<Template let:args>
  <div style="background-color: var(--white); width: 100%; height: 200px; " class="flex-center-row">
  <ToggleButton {...args} on:click={args.onClick} />
  </div>
</Template>

<Story
  name="Toggle Button Default"
  args={{
    label: "Primary",
  }}
/>
