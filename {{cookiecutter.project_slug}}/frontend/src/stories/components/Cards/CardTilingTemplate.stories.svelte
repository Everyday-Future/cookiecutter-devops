<script>
    import {Meta, Template, Story} from "@storybook/addon-svelte-csf";
    import CardTilingTemplate from "../../../components/Cards/CardTilingTemplate.svelte";
    import BlogCard from "../../../components/Cards/BlogCard.svelte";
    import CitationCard from "../../../components/Cards/CitationCard.svelte";
    import TestimonialCard from "../../../components/Cards/TestimonialCard.svelte";
</script>

<Meta
  title="components/Cards/CardTilingTemplate"
  component={CardTilingTemplate}
  argTypes={{
    link: { control: "text", default: "/blog/journaling_styles" },
    src: { control: "text", default: "why_is_dieting_hard.jpg" },
    alt: { control: "text", default: "journaling styles" },
    mobileSrc: { control: "text", default: "learning_to_break_out_of_loops.jpg" },
    title: { control: "text", default: "Example Title" },
    summary: { control: "text", default: "This is a blog post summary, which should tell you a little about the post" },
    tags: { control: "text", default: "example tags" }
  }}
/>

<Template let:args id="Blog">
  <div style="background-color: var(--white); width: 100%; height: 100vh; margin-top: 30px;">
    <div>
      <CardTilingTemplate>
        <BlogCard {...args} />
        <BlogCard {...args} />
        <BlogCard {...args} />
        <BlogCard {...args} />
        <BlogCard {...args} />
        <BlogCard {...args} />
      </CardTilingTemplate>
    </div>
  </div>
</Template>

<Template let:args id="Citation">
  <div style="background-color: var(--white); width: 100%; height: 100vh; margin-top: 30px;">
    <div>
      <CardTilingTemplate>
        <CitationCard {...args} />
        <CitationCard {...args} />
        <CitationCard {...args} />
        <CitationCard {...args} />
        <CitationCard {...args} />
        <CitationCard {...args} />
      </CardTilingTemplate>
    </div>
  </div>
</Template>

<Template let:args id="Testimonial">
  <div style="background-color: var(--white); width: 100%; height: 100vh; margin-top: 30px;">
    <div>
      <CardTilingTemplate>
        <TestimonialCard {...args} />
        <TestimonialCard {...args} />
        <TestimonialCard {...args} />
        <TestimonialCard {...args} />
        <TestimonialCard {...args} />
        <TestimonialCard {...args} />
      </CardTilingTemplate>
    </div>
  </div>
</Template>

<Story
  name="Blog Example" template="Blog"
  args={{
    link: "/blog/journaling_styles",
    src: "why_is_dieting_hard.jpg",
    alt: "journaling styles",
    mobileSrc: "learning_to_break_out_of_loops.jpg",
    title: "Example Title",
    summary: "This is a blog post summary, which should tell you a little about the post",
    tags: "example tags"
  }}
/>

<Story
  name="Citation Example" template="Citation"
  args={{
    idx: 0,
    category: "fitness",
    title: "Example Title",
    description: "This is a blog post summary, which should tell you a little about the post",
    authors: "example tags",
    link: "https://www.luminaryhandbook.com/works_cited",
    source: "https://www.luminaryhandbook.com/works_cited"
  }}
/>

<Story
  name="Testimonial Example" template="Testimonial"
  args={{
    rating: 5.0,
    name: "Hinkle McKrinkle",
    body: "This is a blog post summary, which should tell you a little about the post",
    imgSrc: "learning_to_break_out_of_loops.jpg"
  }}
/>
