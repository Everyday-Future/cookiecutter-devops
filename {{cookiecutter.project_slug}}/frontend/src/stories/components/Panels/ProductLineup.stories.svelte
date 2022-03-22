
<script>
    import {Meta, Template, Story} from "@storybook/addon-svelte-csf";

    import ProductLineup from "../../../components/Panels/ProductLineup.svelte";
</script>

<Meta
  title="components/Panels/ProductLineup"
  component={ProductLineup}
/>

<Template let:args>
  <div style="padding: 20px">
    <ProductLineup {...args}/>
  </div>
</Template>

<Story
  name="Default"
/>
