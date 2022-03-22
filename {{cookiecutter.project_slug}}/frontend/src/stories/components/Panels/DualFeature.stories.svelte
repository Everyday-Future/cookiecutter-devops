<script>
    import {Meta, Template, Story} from "@storybook/addon-svelte-csf";
    import DualFeature from "../../../components/Panels/DualFeature.svelte";
    import Image from "../../../components/Image/Image.svelte";
</script>

<Meta
  title="components/Panels/DualFeature"
  component={DualFeature}
  argTypes={{
  }}
/>

<Template let:args id="TwoImages">
  <div style="margin-top: 30px;">
    <DualFeature {...args}>
      <div slot="left">
        <Image src="learning_to_break_out_of_loops.jpg" />
      </div>
      <div slot="right">
        <Image src="why_is_dieting_hard.jpg" />
      </div>
    </DualFeature>
  </div>
</Template>

<Story
  name="Two Images" template="TwoImages"
  args={{
  }}
/>
