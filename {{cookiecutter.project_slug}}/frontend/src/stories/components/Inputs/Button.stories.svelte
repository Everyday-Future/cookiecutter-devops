<script>
  import { Meta, Template, Story } from "@storybook/addon-svelte-csf";
  import Button from "../../../components/Inputs/Button.svelte";
</script>

<Meta
  title="components/Inputs/Button"
  component={Button}
  argTypes={{
    label: { control: "text" },
    iconLeft: { control: "text", default: "" },
    iconRight: { control: "text", default: "" },
    btnType: {
      control: { type: 'select' },
      options: ["primary", "blue", "blueinvert", "white"]
    },
    btnSize: {
      control: { type: 'select' },
      options: ['small', 'regular', 'large']
    },
    onClick: { action: "onClick" }
  }}
/>

<Template let:args>
  <div style="background-color: var(--slate); width: 100%; height: 200px; " class="flex-center-row">
  <Button {...args} on:click={args.onClick} />
  </div>
</Template>

<Story
  name="Primary Regular"
  args={{
    label: "Primary",
    btnType: "primary",
    btnSize: "regular",
  }}
/>

<Story
  name="Blue Small"
  args={{
    label: "Blue Small",
    btnType: "blue",
    btnSize: "small",
  }}
/>
<Story
  name="BlueInvert Large"
  args={{
    label: "Blue Invert Large",
    btnType: "blueinvert",
    btnSize: "large",
  }}
/>

<Story
  name="White Regular"
  args={{
    label: "White Regular",
    btnType: "white",
    btnSize: "regular",
  }}
/>

<Story
  name="Checkout Regular"
  args={{
    label: "Checkout",
    iconLeft: "icon-lock-white.svg",
    btnType: "primary",
    btnSize: "regular",
  }}
/>
