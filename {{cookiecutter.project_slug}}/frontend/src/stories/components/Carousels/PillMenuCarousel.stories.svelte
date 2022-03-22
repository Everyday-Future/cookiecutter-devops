<script>
    import {Meta, Template, Story} from "@storybook/addon-svelte-csf";
    import PillMenuCarousel from "../../../components/Carousels/PillMenuCarousel.svelte";
    import PrototypeSVG from "../../../components/Temporary/PrototypeSVG.svelte";


    const trainer = {
        __typename: 'Product',
        id: 'ckt4z6xg00068m7y4wpe55q2b',
        image: 'https://blog.luminaryhandbook.com/trainer-300.png',
        price: 3500,
        productComparisonDescription:
            'Trainer Lorem ipsum dolor sit amet, consectetuer adipiscing elit, sed diam nonummy nibh euismod tincidunt ut laoreet dolore magna aliquam erat volutpat. Ut wisi enim ad minim veniam, quis nostrud exerci tation ullamcorper suscipit lobortis nisl ut aliquip ex ea commodo consequat. Duis autem vel eum iriure dolor in hendrerit in vulputate velit esse molestie consequat, vel illum dolore eu feugiat nulla facilisis at vero eros et accumsan et iusto odio dignissim qui blandit praesent luptatum zzril delenit augue duis dolore te feugait nulla facilisi. Lorem ipsum dolor sit amet, cons ectetuer adipiscing elit, sed diam nonummy nibh euismod tincidunt ut laoreet dolore magna aliquam erat volutpat. Ut wisi enim ad minim veniam, quis nostrud exerci tation ullamcorper suscipit lobortis nisl ut aliquip ex',
        productPagePath: '/products/trainer',
        title: 'Trainer',
        pathwaysDescription:
            'Pathways-specific copy for Trainer goes here. Lorem ipsum dolor sit amet.',
        pathways: [
            {
                id: '0',
                name: 'Running',
                summary: 'Track distance or interval training<br>Plan and simplify long-term strategies',
                ctaLinkText: 'Learn more >',
                ctaLinkHref: '#placeholder',
                handbookVectorImgLeft: PrototypeSVG,
                handbookVectorImgRight: PrototypeSVG
            },
            {
                id: '1',
                name: 'Gym',
                summary: 'Multi-purpose fitness<br>Strength and/or interval training',
                ctaLinkText: 'Learn more >',
                ctaLinkHref: '#placeholder',
                handbookVectorImgLeft: PrototypeSVG,
                handbookVectorImgRight: PrototypeSVG
            },
            {
                id: '2',
                name: 'Weightlifting',
                summary: 'Plan and maximize gains<br>Track muscle soreness and recovery',
                ctaLinkText: 'Learn more >',
                ctaLinkHref: '#placeholder',
                handbookVectorImgLeft: PrototypeSVG,
                handbookVectorImgRight: PrototypeSVG
            },
            {
                id: '3',
                name: 'Cross-Training',
                summary:
                    'Track weightlifting, cardio, and conditioning<br>Set up short- and long-term training programs',
                ctaLinkText: 'Learn more >',
                ctaLinkHref: '#placeholder',
                handbookVectorImgLeft: PrototypeSVG,
                handbookVectorImgRight: PrototypeSVG
            },
            {
                id: '4',
                name: 'Biking',
                summary: 'Track distance or interval training<br>Plan and simplify long-term strategies',
                ctaLinkText: 'Learn more >',
                ctaLinkHref: '#placeholder',
                handbookVectorImgLeft: PrototypeSVG,
                handbookVectorImgRight: PrototypeSVG
            },
            {
                id: '5',
                name: 'Basketball',
                summary: 'Track shooting workouts<br>Plan solo or team practice sessions',
                ctaLinkText: 'Learn more >',
                ctaLinkHref: '#placeholder',
                handbookVectorImgLeft: PrototypeSVG,
                handbookVectorImgRight: PrototypeSVG
            },
            {
                id: '6',
                name: 'Softball',
                summary: 'Track practice and game performance<br>Create and tune training plan',
                ctaLinkText: 'Learn more >',
                ctaLinkHref: '#placeholder',
                handbookVectorImgLeft: PrototypeSVG,
                handbookVectorImgRight: PrototypeSVG
            },
            {
                id: '7',
                name: 'Baseball',
                summary: 'Track practice and game performance<br>Create and tune training plan',
                ctaLinkText: 'Learn more >',
                ctaLinkHref: '#placeholder',
                handbookVectorImgLeft: PrototypeSVG,
                handbookVectorImgRight: PrototypeSVG
            },
            {
                id: '8',
                name: 'Golf',
                summary:
                    'Track your causal and competitive games<br>Optional details like FIR, GIR, and OB',
                ctaLinkText: 'Learn more >',
                ctaLinkHref: '#placeholder',
                handbookVectorImgLeft: PrototypeSVG,
                handbookVectorImgRight: PrototypeSVG
            },
            {
                id: '9',
                name: 'Disc Golf',
                summary: 'Keep score and watch your game improve<br>Track notes about the game and course',
                ctaLinkText: 'Learn more >',
                ctaLinkHref: '#placeholder',
                handbookVectorImgLeft: PrototypeSVG,
                handbookVectorImgRight: PrototypeSVG
            },
            {
                id: '10',
                name: 'Tennis',
                summary: 'Track drills and performance<br>Find your weak spots on the court',
                ctaLinkText: 'Learn more >',
                ctaLinkHref: '#placeholder',
                handbookVectorImgLeft: PrototypeSVG,
                handbookVectorImgRight: PrototypeSVG
            }
        ]
    }

    const notebook = {
        __typename: 'Product',
        id: 'ckt4z86j20280m7y4icaksoyt',
        image: 'https://blog.luminaryhandbook.com/notebook.jpg',
        price: 3500,
        productComparisonDescription:
            'Notebook Lorem ipsum dolor sit amet, consectetuer adipiscing elit, sed diam nonummy nibh euismod tincidunt ut laoreet dolore magna aliquam erat volutpat. Ut wisi enim ad minim veniam, quis nostrud exerci tation ullamcorper suscipit lobortis nisl ut aliquip ex ea commodo consequat. Duis autem vel eum iriure dolor in hendrerit in vulputate velit esse molestie consequat, vel illum dolore eu feugiat nulla facilisis at vero eros et accumsan et iusto odio dignissim qui blandit praesent luptatum zzril delenit augue duis dolore te feugait nulla facilisi. Lorem ipsum dolor sit amet, cons ectetuer adipiscing elit, sed diam nonummy nibh euismod tincidunt ut laoreet dolore magna aliquam erat volutpat. Ut wisi enim ad minim veniam, quis nostrud exerci tation ullamcorper suscipit lobortis nisl ut aliquip ex',
        productPagePath: '/products/notebook',
        title: 'Notebook',
        pathwaysDescription:
            'Pathways-specific copy for Notebook goes here. Lorem ipsum dolor sit amet.',
        pathways: [
            {
                id: '0',
                name: 'Focus your writing',
                summary: 'Copy for "Focus your writing" goes here. Lorem ipsum dolor sit amet.',
                ctaLinkText: 'Learn more >',
                ctaLinkHref: '#placeholder',
                handbookVectorImgLeft: PrototypeSVG,
                handbookVectorImgRight: PrototypeSVG
            },
            {
                id: '1',
                name: 'Develop or break habits',
                summary: 'Copy for "Develop or break habits" goes here. Lorem ipsum dolor sit amet.',
                ctaLinkText: 'Learn more >',
                ctaLinkHref: '#placeholder',
                handbookVectorImgLeft: PrototypeSVG,
                handbookVectorImgRight: PrototypeSVG
            },
            {
                id: '2',
                name: 'Write freeform',
                summary: 'Copy for "Write freeform" goes here. Lorem ipsum dolor sit amet.',
                ctaLinkText: 'Learn more >',
                ctaLinkHref: '#placeholder',
                handbookVectorImgLeft: PrototypeSVG,
                handbookVectorImgRight: PrototypeSVG
            },
            {
                id: '3',
                name: 'Room to doodle',
                summary: 'Copy for "Room to doodle" goes here. Lorem ipsum dolor sit amet.',
                ctaLinkText: 'Learn more >',
                ctaLinkHref: '#placeholder',
                handbookVectorImgLeft: PrototypeSVG,
                handbookVectorImgRight: PrototypeSVG
            },
            {
                id: '4',
                name: 'Get inspired',
                summary: 'Copy for "Get inspired" goes here. Lorem ipsum dolor sit amet.',
                ctaLinkText: 'Learn more >',
                ctaLinkHref: '#placeholder',
                handbookVectorImgLeft: PrototypeSVG,
                handbookVectorImgRight: PrototypeSVG
            }
        ]
    }

</script>


<Meta
  title="components/Carousels/PillMenuCarousel"
  component={PillMenuCarousel}
  argTypes={{
		product: { control: 'data' }
  }}
/>


<Template let:args>
  <div style="background-color: var(--white); width: 100%;">
      <PillMenuCarousel {...args} on:click={args.onClick}/>
  </div>
</Template>


<Story name="Trainer" args={{ product: trainer }}/>

<Story name="Notebook" args={{ product: notebook }}/>
