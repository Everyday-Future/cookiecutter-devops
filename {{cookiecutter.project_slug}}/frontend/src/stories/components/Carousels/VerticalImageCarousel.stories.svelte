<script>
    import {Meta, Template, Story} from "@storybook/addon-svelte-csf";
    import VerticalImageCarousel from "../../../components/Carousels/VerticalImageCarousel.svelte";

    const carouselItems = [
        {
            title: 'No wasted space',
            description:
                'Make every page count by having full control of your layout. ' +
                'Get started by choosing from our pre-made layouts then customize to make the perfect book for you.',
            ctaLinkText: '',
            ctaLinkHref: '#noWastedSpace',
            src: 'biking_preview_incl.jpg'
        },
        {
            title: '150+ widgets',
            description:
                'Choose from a huge variety of widgets, prompts and much more. Make your book perfect for you.',
            ctaLinkText: '',
            ctaLinkHref: '#150Widgets',
            src: 'customizable-preview.jpg'
        },
        {
            title: 'Easy to use',
            description:
                'Create the perfect journal, notebook, or fitness log for you',
            ctaLinkText: '',
            ctaLinkHref: '#easyToUse',
            src: 'all_books_tiled-1000.jpg'
        },
        {
            title: '180+ pages',
            description:
                'We want to make this notebook perfect for you. If it isn’t, tell us! Click here to suggest new pages or features.',
            ctaLinkText: '',
            ctaLinkHref: '#180Pages',
            src: 'crosstraining_preview_excl.jpg'
        }
    ]
</script>

<Meta
  title="components/Carousels/VerticalImageCarousel"
  component={VerticalImageCarousel}
  argTypes={{
    carouselItems: { control: "data", default: carouselItems }
  }}
/>

<Template let:args>
  <div>
    <VerticalImageCarousel {...args} />
  </div>
</Template>

<Story
  name="Home Page Default"
  args={{
    carouselItems: carouselItems
  }}
/>
