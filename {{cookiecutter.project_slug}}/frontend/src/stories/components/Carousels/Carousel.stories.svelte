<script>
    import {Meta, Template, Story} from "@storybook/addon-svelte-csf";
    import Carousel from "../../../components/Carousels/Carousel.svelte";
</script>

<Meta
  title="components/Carousels/Carousel"
  component={Carousel}
  argTypes={{

    label: { control: "text" },
    iconLeft: { control: "text", default: "" },
    iconRight: { control: "text", default: "" },
    btnType: {
      control: { type: 'select' },
      options: ["primary", "blue", "blueinvert", "white"],
    },
    btnSize: {
      control: { type: 'select' },
      options: ['small', 'regular', 'large'],
    },
    onClick: { action: "onClick" },
  }}
/>

<Template let:args>
  <div style="background-color: var(--slate); width: 100%;">
    <div>
      <Carousel {...args} on:click={args.onClick}/>
    </div>
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
