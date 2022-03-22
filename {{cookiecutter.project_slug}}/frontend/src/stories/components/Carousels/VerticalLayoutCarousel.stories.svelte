<script>
    import {Meta, Template, Story} from "@storybook/addon-svelte-csf";
    import VerticalLayoutCarousel from "../../../components/Carousels/VerticalLayoutCarousel.svelte";
    import PrototypeSVG from "../../../components/Temporary/PrototypeSVG.svelte";

    const carouselItems = [
        {
            title: 'Focus your writing',
            description:
                'Lorem ipsum dolor sit amet, consectetuer adipiscing elit, sed diam nonummy nibh euismod ut laoreet dolore magna aliquam erat volutpat. Ut wisi enim ad minim veniam, quis nostrud exerci tation ullamcorper suscipit lobortis nisl ut aliquip ex ea commodo consequat. Duis autem vel eum iriure dolor in hendrerit in vulputate velit esse molestie consequat, vel illum dolore eu feugiat nulla facilisis at vero eros et accumsan et iusto odio dignissim qui blandit praesent luptatum zzril delenit augue duis dolore te feugait nulla facilisi.',
            ctaLinkText: 'Learn more >',
            ctaLinkHref: '#focusYourWriting',
            handbookVectorImgLeft: PrototypeSVG,
            handbookVectorImgRight: PrototypeSVG
        },
        {
            title: 'Develop habits',
            description:
                'Lorem ipsum dolor sit amet, consectetuer adipiscing elit, sed diam nonummy nibh euismod ut laoreet dolore magna aliquam erat volutpat. Ut wisi enim ad minim veniam, quis nostrud exerci tation ullamcorper suscipit lobortis nisl ut aliquip ex ea commodo consequat. Duis autem vel eum iriure dolor in hendrerit in vulputate velit esse molestie consequat, vel illum dolore eu feugiat nulla facilisis at vero eros et accumsan et iusto odio dignissim qui blandit praesent luptatum zzril delenit augue duis dolore te feugait nulla facilisi.',
            ctaLinkText: 'Learn more >',
            ctaLinkHref: '#developOrBreakHabits',
            handbookVectorImgLeft: PrototypeSVG,
            handbookVectorImgRight: PrototypeSVG
        },
        {
            title: 'Write freeform',
            description:
                'Lorem ipsum dolor sit amet, consectetuer adipiscing elit, sed diam nonummy nibh euismod ut laoreet dolore magna aliquam erat volutpat. Ut wisi enim ad minim veniam, quis nostrud exerci tation ullamcorper suscipit lobortis nisl ut aliquip ex ea commodo consequat. Duis autem vel eum iriure dolor in hendrerit in vulputate velit esse molestie consequat, vel illum dolore eu feugiat nulla facilisis at vero eros et accumsan et iusto odio dignissim qui blandit praesent luptatum zzril delenit augue duis dolore te feugait nulla facilisi.',
            ctaLinkText: 'Learn more >',
            ctaLinkHref: '#writeFreeForm',
            handbookVectorImgLeft: PrototypeSVG,
            handbookVectorImgRight: PrototypeSVG
        },
        {
            title: 'Room to doodle',
            description:
                'Lorem ipsum dolor sit amet, consectetuer adipiscing elit, sed diam nonummy nibh euismod ut laoreet dolore magna aliquam erat volutpat. Ut wisi enim ad minim veniam, quis nostrud exerci tation ullamcorper suscipit lobortis nisl ut aliquip ex ea commodo consequat. Duis autem vel eum iriure dolor in hendrerit in vulputate velit esse molestie consequat, vel illum dolore eu feugiat nulla facilisis at vero eros et accumsan et iusto odio dignissim qui blandit praesent luptatum zzril delenit augue duis dolore te feugait nulla facilisi.',
            ctaLinkText: 'Learn more >',
            ctaLinkHref: '#roomToDoodle',
            handbookVectorImgLeft: PrototypeSVG,
            handbookVectorImgRight: PrototypeSVG
        },
        {
            title: 'Get inspired',
            description:
                'Lorem ipsum dolor sit amet, consectetuer adipiscing elit, sed diam nonummy nibh euismod ut laoreet dolore magna aliquam erat volutpat. Ut wisi enim ad minim veniam, quis nostrud exerci tation ullamcorper suscipit lobortis nisl ut aliquip ex ea commodo consequat. Duis autem vel eum iriure dolor in hendrerit in vulputate velit esse molestie consequat, vel illum dolore eu feugiat nulla facilisis at vero eros et accumsan et iusto odio dignissim qui blandit praesent luptatum zzril delenit augue duis dolore te feugait nulla facilisi.',
            ctaLinkText: 'Learn more >',
            ctaLinkHref: '#getInspired',
            handbookVectorImgLeft: PrototypeSVG,
            handbookVectorImgRight: PrototypeSVG
        }
    ]
</script>

<Meta
  title="components/Carousels/VerticalLayoutCarousel"
  component={VerticalLayoutCarousel}
  argTypes={{

    carouselItems: { control: "data", default: carouselItems }
  }}
/>

<Template let:args>
  <div>
    <VerticalLayoutCarousel {...args}/>
  </div>
</Template>

<Story
  name="Home Page Default"
  args={{
    carouselItems: carouselItems
  }}
/>
