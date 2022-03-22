<script>
  import { Meta, Template, Story } from "@storybook/addon-svelte-csf";
  import DropdownPicker from "../../../components/Inputs/DropdownPicker.svelte";
</script>

<Meta
  title="Components/Inputs/DropdownPicker"
  component={DropdownPicker}
  argTypes={{
    title: { control: "text" },
    isOpen: { control: "boolean" },
    durationMS: {control: 'number'},
    onClick: { action: "onClick" },
  }}
/>

<Template let:args id="Empty">
  <div style="padding: 20px;">
    <h1>TODO</h1>
    <DropdownPicker {...args} on:click={args.onClick}>
    </DropdownPicker>
  </div>
</Template>

<Template let:args id="OneItem">
  <div style="padding: 20px;">
    <h1>TODO</h1>
    <DropdownPicker {...args} on:click={args.onClick}>
      <p>item</p>
    </DropdownPicker>
  </div>
</Template>

<Template let:args id="ManyItems">
  <div style="padding: 20px;">
    <h1>TODO</h1>
    <DropdownPicker {...args} on:click={args.onClick}>
      <p>item 1</p>
      <p>item 2</p>
      <p>item 3</p>
    </DropdownPicker>
  </div>
</Template>

<Story
  name="Empty" template="Empty"
  args={{
    title: "Customizer Insert Section",
    isOpen: false
  }}
/>

<Story
  name="OneItem" template="OneItem"
  args={{
    title: "Customizer Insert Section",
    isOpen: false
  }}
/>

<Story
  name="ManyItems" template="ManyItems"
  args={{
    title: "Customizer Insert Section",
    isOpen: false
  }}
/>
