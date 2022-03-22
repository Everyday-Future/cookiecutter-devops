<!-- InfoBlock.stories.svelte -->

<script>
    import {Meta, Template, Story} from "@storybook/addon-svelte-csf";

    import Product from "../../../components/Panels/Product.svelte";
</script>

<Meta
  title="components/Panels/Product"
  component={Product}
  argTypes={{
    body: { control: "text", required: false },
    bgColor: { control: "text", required: false },
    txtColor: { control: "text", required: false },
    btnText: { control: "text", required: false },
    btnLink: { control: "text", required: false },
    imgSmall: { control: "text", required: false },
    imgLarge: { control: "text", required: false },
    isReversed: {control: "boolean", required: false}
  }}
/>

<Template let:args>
  <div style="padding: 20px">
    <Product {...args}/>
  </div>
</Template>

<Story
  name="With CTA Button"
  args={{
    btnText: 'Get Started',
    btnLink: 'https://www.{{ cookiecutter.project_domain }}.com/works_cited',
    body: '{{ cookiecutter.project_short_description }}',
    imgSmall: 'layout-rotated-journal-01-m.png',
    imgLarge: 'layout-rotated-journal-01-d.png',
  }}
/>

<Story
  name="No CTA Button"
  args={{
    bgColor: 'var(--muse)',
    txtColor: 'var(--darkgrey)',
    body: '"A little nonsense now and then<br/> is relished by the wisest men."<br/><br/> - Willy Wonka',
    imgSmall: 'layout-rotated-journal-01-m.png',
    imgLarge: 'layout-rotated-journal-01-d.png',
  }}
/>
