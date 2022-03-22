<script>
  import { Meta, Template, Story } from "@storybook/addon-svelte-csf";
  import Modal from "../../../components/Panels/Modal.svelte";
  import Header from "../../../components/Panels/Header.svelte";
</script>

<Meta
  title="components/Panels/Modal"
  component={Modal}
  argTypes={{
    open: { control: "boolean", default: true }
  }}
/>

<Template let:args id="header">
  <div>
    <Modal open={true} >
      <Header {...args} />
    </Modal>
  </div>
</Template>

<Story
  name="Header Modal" template="header"
  args={{
    script: "Script heading",
    subtitle: "explanatory subtitle",
    body: "body of the header component<br />Single line break with a simple wraparound<br /><br />" +
     "Should respect break tags and wrap lines on word breaks and not single letter breaks " +
      "and also have a maximum line size to make the wraparound look better",
  }}
/>
