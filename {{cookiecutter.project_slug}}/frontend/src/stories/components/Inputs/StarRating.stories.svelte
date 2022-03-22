<script>
  import { Meta, Template, Story } from "@storybook/addon-svelte-csf";
  import StarRating from "../../../components/Inputs/StarRating.svelte";
</script>

<Meta
  title="components/Inputs/StarRating"
  component={StarRating}
  argTypes={{
    rating: { control: "number", default: 4.5 },
    size: { control: "number", default: 20 },
    onClick: { action: "onClick" },
  }}
/>

<Template let:args>
  <div style="background-color: var(--white); width: 100%; height: 200px; " class="flex-center-row">
  <StarRating {...args} on:click={args.onClick} />
  </div>
</Template>

<Story
  name="Star Rating High"
  args={{
    rating: 5.0,
  }}
/>

<Story
  name="Star Rating Low"
  args={{
    rating: 0.5,
  }}
/>
