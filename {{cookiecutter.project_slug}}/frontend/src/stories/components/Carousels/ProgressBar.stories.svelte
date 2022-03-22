<script>
    import {Meta, Template, Story} from "@storybook/addon-svelte-csf";
    import ProgressBar from "../../../components/Carousels/ProgressBar.svelte";
</script>

<Meta
  title="components/Carousels/ProgressBar"
  component={ProgressBar}
  argTypes={{
    value: {control: 'number', default: 0.5},
    isVertical: {control: 'boolean', default: false},
    onClick: { action: "onClick" },
  }}
/>

<Template let:args>
  <div style="margin: 100px 50px">
    <ProgressBar {...args} on:click={args.onClick}/>
  </div>
</Template>

<Story
  name="Progress Half Horiz"
  args={{
    value: 0.5
  }}
/>

<Story
  name="Progress Half Vertical"
  args={{
    value: 0.5,
    isVertical: true
  }}
/>
