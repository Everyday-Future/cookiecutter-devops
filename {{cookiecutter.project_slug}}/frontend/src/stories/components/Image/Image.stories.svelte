<script>
  import { Meta, Template, Story } from "@storybook/addon-svelte-csf";
  import Image from "../../../components/Image/Image.svelte";
</script>

<Meta
  title="components/Image/Image"
  component={Image}
  argTypes={{
    src: { control: "text" }
  }}
/>

<Template let:args>
  <div style="background-color: var(--white); width: 50%; height: auto; margin: 50px" class="flex-center-row">
  <Image {...args} />
  </div>
</Template>

<Story
  name="No caption"
  args={{
    src: "box-on-mat-1600.jpg"
  }}
/>
