<!-- CartItem.stories.svelte -->

<script>
  import { Meta, Template, Story } from "@storybook/addon-svelte-csf";
  import { cartContentIDs } from '../../../lib/cart.js';
  import { cartOpen } from '../../../lib/cart';
  import Button from "../../../components/Inputs/Button.svelte";

  import Navbar from "../../../components/Navbar.svelte";

  function toggleCart() {
      if ($cartContentIDs.length === 0) {
          cartContentIDs.set([1])
      } else {
          cartContentIDs.set([])
      }
  }
    $cartOpen = false;

</script>

<Meta
  title="assemblies/Nav/Navbar"
  component={Navbar}
  argTypes={{
    productName: { control: "text" },
    productColor: { control: "color" }
  }}
/>


<Template let:args>
  <div style="background-color: var(--lightblue); width: 100%; height: 200px; " class="flex-center-col">
  <Navbar  {...args} />
    <Button
      label="Toggle cartContents"
      btnSize="large"
      on:click={() => {toggleCart()}}
    />
  </div>
</Template>


<Story
  name="No Product"
  args={{
    productName: "",
    productColor: "#fff"
  }}
/>


<Story
  name="Journal"
  args={{
    productName: "Journal",
    productColor: "var(--lightblue)"
  }}
/>


<Story
  name="Muse"
  args={{
    productName: "Muse",
    productColor: "var(--muse)"
  }}
/>

