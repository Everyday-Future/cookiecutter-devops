<script>
  import { Meta, Template, Story } from "@storybook/addon-svelte-csf";
  import QuantityChanger from "../../../components/Inputs/QuantityChanger.svelte";
</script>

<Meta
  title="components/Inputs/QuantityChanger"
  component={QuantityChanger}
  argTypes={{
    label: { control: "text" },
    onClick: { action: "onClick" },
  }}
/>

<Template let:args>
  <div style="background-color: var(--white); width: 100%; height: 200px; " class="flex-center-row">
  <QuantityChanger {...args} on:click={args.onClick} />
  </div>
</Template>

<Story
  name="Toggle Button No Label"
  args={{
    label: "",
  }}
/>

<Story
  name="Toggle Button With Label"
  args={{
    label: "Primary",
  }}
/>
