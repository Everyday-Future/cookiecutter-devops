<script>
    import {Meta, Template, Story} from "@storybook/addon-svelte-csf";
    import BlogCard from "../../../components/Cards/BlogCard.svelte";
</script>

<Meta
  title="components/Cards/BlogCard"
  component={BlogCard}
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

<Template let:args>
  <div style="background-color: var(--white); width: 100%; height: 100vh; " class="flex-center-row">
    <div style="width: 300px;">
      <BlogCard {...args} on:click={args.onClick}/>
    </div>
  </div>
</Template>

<Story
  name="Blog Example"
  args={{
    title: "Example Title",
    summary: "This is a blog post summary, which should tell you a little about the post",
    tags: "example tags",
    src: "why_is_dieting_hard.jpg",
    alt: "journaling styles",
    mobileSrc: "learning_to_break_out_of_loops.jpg"
  }}
/>

<Story
  name="Long Blog Tags"
  args={{
    title: "Example Very Very Long and Important Title",
    summary: "This is a blog post summary, which should tell you a little about the post. <br /><br />" +
     "Besides, sometimes there is a lot to talk about here and so it'll need to be able to accomodate that too",
    tags: "even more example tags that overflow",
    src: "why_is_dieting_hard.jpg",
    alt: "journaling styles",
    mobileSrc: "learning_to_break_out_of_loops.jpg"
  }}
/>
