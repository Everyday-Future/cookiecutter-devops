<script>
  import { Meta, Template, Story } from "@storybook/addon-svelte-csf";
  import ToggleSwitch from "../../../components/Inputs/ToggleSwitch.svelte";
</script>

<Meta
  title="components/Inputs/ToggleSwitch"
  component={ToggleSwitch}
  argTypes={{
    falseLabel: { control: "text" },
    trueLabel: { control: "text" },
    falseMessage: { control: "text" },
    trueMessage: { control: "text" },
    onClick: { action: "onClick" },
  }}
/>

<Template let:args>
  <div style="background-color: var(--white); width: 100%; height: 200px; margin-top: 100px ">
  <ToggleSwitch {...args} on:click={args.onClick} />
  </div>
</Template>

<Story
  name="Toggle Switch Default"
  args={{
      name: "demo",
      falseLabel: "false",
      trueLabel: "true",
      falseMessage: "false message",
      trueMessage: "true message",
  }}
/>
