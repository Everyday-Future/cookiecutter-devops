<script>
    import {Meta, Template, Story} from "@storybook/addon-svelte-csf";
    import Popover from "../../../components/Popover/Popover.svelte";
    import AccountPopover from "../../../components/Popover/AccountPopover.svelte";
</script>

<Meta
  title="components/Popover/PopoverBase"
  component={Popover}
  argTypes={{
    open: { control: "boolean" }
  }}
/>

<Template let:args>
  <div style="background-color: var(--white); width: 100%; height: 200px;" class="flex-center-row">
  <Popover
    arrowColor="#fff"
    action="hover"
    placement="bottom-end"
    overlayColor=""
    padding="0rem"
    closeButton={false}
    open={false}
  >
    <p class="sign-in-link" slot="target">Account Popover Test</p>
    <div slot="content" class="content">
      <AccountPopover username="extralongemailname!" />
    </div>
  </Popover>
  </div>
</Template>

<Story
  name="Account Popover"
  args={{
    open: true
  }}
/>

