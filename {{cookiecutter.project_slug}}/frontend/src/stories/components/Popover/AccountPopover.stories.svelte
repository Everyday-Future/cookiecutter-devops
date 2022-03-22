<script>
  import { Meta, Template, Story } from "@storybook/addon-svelte-csf";
  import AccountPopover from "../../../components/Popover/AccountPopover.svelte";
</script>

<Meta
  title="components/Popover/AccountPopover"
  component={AccountPopover}
  argTypes={{
    src: { control: "text" }
  }}
/>

<Template let:args>
  <div style="background-color: var(--white); width: 50%; height: auto; margin: 50px" class="flex-center-row">
  <AccountPopover {...args} />
  </div>
</Template>

<Story
  name="No caption"
  args={{
    src: "box-on-mat-1600.jpg"
  }}
/>
