<script>
  import { Meta, Template, Story } from "@storybook/addon-svelte-csf";
  import Header from "../../../components/Panels/Header.svelte";
</script>

<Meta
  title="components/Panels/Header"
  component={Header}
  argTypes={{
    script: { control: "text", default: "Script heading" },
    subtitle: { control: "text", default: "explanatory subtitle" },
    body: { control: "text", default: "body of the header component<br /><br />Should respect break tags" },
    bgColor: { control: "color" },
    txtColor: { control: "color" },
    scriptColor: { control: "color" },
    borderColor: { control: "color" },
  }}
/>

<Template let:args>
  <div style="margin-top: 30px">
  <Header {...args}  />
  </div>
</Template>

<Story
  name="Plain Header"
  args={{
    script: "Script heading",
    subtitle: "explanatory subtitle",
    body: "body of the header component<br />Single line break with a simple wraparound<br /><br />" +
     "Should respect break tags and wrap lines on word breaks and not single letter breaks " +
      "and also have a maximum line size to make the wraparound look better",
  }}
/>

<Story
  name="Color Header"
  args={{
    script: "Script heading",
    subtitle: "explanatory subtitle",
    body: "body of the header component<br />Single line break with a simple wraparound<br /><br />" +
     "Should respect break tags and wrap lines on word breaks and not single letter breaks " +
      "and also have a maximum line size to make the wraparound look better",
    bgColor: "var(--navy)",
    txtColor: "var(--white)"
  }}
/>
<Story
  name="Bordered Header"
  args={{
    label: "Blue Invert Large",
    script: "Script heading",
    subtitle: "explanatory subtitle",
    body: "body of the header component<br />Single line break with a simple wraparound<br /><br />" +
     "Should respect break tags and wrap lines on word breaks and not single letter breaks " +
      "and also have a maximum line size to make the wraparound look better",
    btnType: "blueinvert",
    btnSize: "large",
    borderColor: "var(--navy)"
  }}
/>
