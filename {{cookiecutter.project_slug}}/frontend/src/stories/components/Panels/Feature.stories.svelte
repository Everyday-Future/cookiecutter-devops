<!-- InfoBlock.stories.svelte -->

<script>
    import {Meta, Template, Story} from "@storybook/addon-svelte-csf";

    import Feature from "../../../components/Panels/Feature.svelte";
    import Image from "../../../components/Image/Image.svelte";
  import Carousel from "../../../components/Carousels/Carousel.svelte";
</script>

<Meta
  title="components/Panels/Feature"
  component={Feature}
  argTypes={{
    heading: { control: "text", required: false },
    subheading: { control: "text", required: false },
    body: { control: "text", required: false },
    btnText: { control: "text", required: false },
    btnLink: { control: "text", required: false },
    isReversed: {control: "boolean", required: false}
  }}
/>

<Template let:args id="Image Template">
  <div style="padding: 20px">
    <Feature {...args}>
      <Image src='5_ways_to_selfcare.jpg' alt="Bill Murray"/>
    </Feature>
  </div>
</Template>

<Template let:args id="Tall Image Template">
  <div style="max-width: 640px; padding: 20px">
    <Feature {...args}>
      <Image src='215958_pexels-photo-3144296_0.4011.jpg' alt="Bill Murray"/>
    </Feature>
  </div>
</Template>

<Template let:args id="Carousel Template">
  <div style="max-width: 640px; padding: 20px">
    <Feature {...args}>
      <!--
      The Carousel needs an explicit width for some reason.
      May need to listen to clientWidth for sizing.
      -->
      <div style="width: 320px">
  <Carousel {...args} on:click={args.onClick} />
<!--          <Image src='https://www.fillmurray.com/640/360' alt="Bill Murray"/>-->
<!--          <Image src='https://www.fillmurray.com/640/360' alt="Bill Murray"/>-->
<!--          <Image src='https://www.fillmurray.com/640/360' alt="Bill Murray"/>-->
      </div>
    </Feature>
  </div>
</Template>

<Story
  name="With CTA Button" template="Image Template"
  args={{
    heading: 'Heading',
    subheading: 'Subheading',
    btnText: 'Get Started',
    btnLink: 'https://www.luminaryhandbook.com/works_cited',
    body: '<strong>You think water moves fast?</strong> You should see ice. It moves like it has a mind.\n'+
'    Like it knows it killed the world once\n'+
'    and got a taste for murder. <em>After the avalanche, it took us a week to climb out.</em>\n'+
'    Now, I don\'t know exactly when we turned on each other,\n'+
'    <code>but I know that seven of us survived the slide...</code> and only five made it out.\n'+
'    Now we took an oath, that I\'m breaking now.\n'+
'    We said we\'d say it was the snow that killed the other two, but it wasn\'t.\n'+
'    Nature is lethal <a href="#">but it doesn\'t hold a candle to man.</a>',
  }}
/>

<Story
  name="No CTA Button" template="Image Template"
  args={{
    heading: 'Heading',
    subheading: 'Subheading',
    body: '<strong>You think water moves fast?</strong> You should see ice. It moves like it has a mind.\n'+
'    Like it knows it killed the world once\n'+
'    and got a taste for murder. <em>After the avalanche, it took us a week to climb out.</em>\n'+
'    Now, I don\'t know exactly when we turned on each other,\n'+
'    <code>but I know that seven of us survived the slide...</code> and only five made it out.\n'+
'    Now we took an oath, that I\'m breaking now.\n'+
'    We said we\'d say it was the snow that killed the other two, but it wasn\'t.\n'+
'    Nature is lethal <a href="#">but it doesn\'t hold a candle to man.</a>',
  }}
/>

<Story
  name="Tall Image" template="Tall Image Template"
  args={{
    heading: 'Heading',
    subheading: 'Subheading',
    btnText: 'Get Started',
    btnLink: 'https://www.luminaryhandbook.com/works_cited',
    body: '<strong>You think water moves fast?</strong> You should see ice. It moves like it has a mind.\n'+
'    Like it knows it killed the world once\n'+
'    and got a taste for murder. <em>After the avalanche, it took us a week to climb out.</em>\n'+
'    Now, I don\'t know exactly when we turned on each other,\n'+
'    <code>but I know that seven of us survived the slide...</code> and only five made it out.\n'+
'    Now we took an oath, that I\'m breaking now.\n'+
'    We said we\'d say it was the snow that killed the other two, but it wasn\'t.\n'+
'    Nature is lethal <a href="#">but it doesn\'t hold a candle to man.</a>',
  }}
/>

<Story
  name="Reversed" template="Image Template"
  args={{
    heading: 'Heading',
    subheading: 'Subheading',
    btnText: 'Get Started',
    btnLink: 'https://www.luminaryhandbook.com/works_cited',
    isReversed: true,
    body: '<strong>You think water moves fast?</strong> You should see ice. It moves like it has a mind.\n'+
'    Like it knows it killed the world once\n'+
'    and got a taste for murder. <em>After the avalanche, it took us a week to climb out.</em>\n'+
'    Now, I don\'t know exactly when we turned on each other,\n'+
'    <code>but I know that seven of us survived the slide...</code> and only five made it out.\n'+
'    Now we took an oath, that I\'m breaking now.\n'+
'    We said we\'d say it was the snow that killed the other two, but it wasn\'t.\n'+
'    Nature is lethal <a href="#">but it doesn\'t hold a candle to man.</a>',
  }}
/>

<Story
  name="Carousel" template="Carousel Template"
  args={{
    heading: 'Heading',
    subheading: 'Subheading',
    btnText: 'Get Started',
    btnLink: 'https://www.luminaryhandbook.com/works_cited',
    isReversed: true,
    body: '<strong>You think water moves fast?</strong> You should see ice. It moves like it has a mind.\n'+
'    Like it knows it killed the world once\n'+
'    and got a taste for murder. <em>After the avalanche, it took us a week to climb out.</em>\n'+
'    Now, I don\'t know exactly when we turned on each other,\n'+
'    <code>but I know that seven of us survived the slide...</code> and only five made it out.\n'+
'    Now we took an oath, that I\'m breaking now.\n'+
'    We said we\'d say it was the snow that killed the other two, but it wasn\'t.\n'+
'    Nature is lethal <a href="#">but it doesn\'t hold a candle to man.</a>',
  }}
/>

