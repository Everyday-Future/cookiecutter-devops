<script>
    import {Meta, Template, Story} from "@storybook/addon-svelte-csf";
    import TestimonialCard from "../../../components/Cards/TestimonialCard.svelte";
</script>

<Meta
  title="components/Cards/TestimonialCard"
  component={TestimonialCard}
  argTypes={{
    rating: { control: "number", default: 4.0 },
    name: { control: "text", default: "Connie M." },
    body: { control: "text", default: "This is a testimonial, which should tell you a little about someone's experience" },
    imgSrc: { control: "text", default: "" }
  }}
/>

<Template let:args>
  <div style="background-color: var(--white); width: 100%; height: 100vh; " class="flex-center-row">
    <div style="width: 300px;">
      <TestimonialCard {...args} on:click={args.onClick}/>
    </div>
  </div>
</Template>

<Story
  name="High-Rating Testimonial"
  args={{
    rating: 4.0,
    name: "Connie M.",
    body: "This is a blog post summary, which should tell you a little about the post",
    imgSrc: ""
  }}
/>

<Story
  name="Long Low-Rating Testimonial"
  args={{
    rating: 1.0,
    name: "Hinkle McKrinkle",
    body: "This is a blog post summary, which should tell you a little about the post. <br /><br />" +
     "Besides, sometimes there is a lot to talk about here and so it'll need to be able to accomodate that too",
    imgSrc: ""
  }}
/>

<Story
  name="Testimonial with picture"
  args={{
    rating: 1.0,
    name: "Hinkle McKrinkle",
    body: "This is a blog post summary, which should tell you a little about the post",
    imgSrc: "learning_to_break_out_of_loops.jpg"
  }}
/>
