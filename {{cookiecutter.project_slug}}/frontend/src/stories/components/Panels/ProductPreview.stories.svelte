<!-- InfoBlock.stories.svelte -->

<script>
    import {Meta, Template, Story} from "@storybook/addon-svelte-csf";

    import ProductPreview from "../../../components/Panels/ProductPreview.svelte";
</script>

<Meta
  title="components/Panels/ProductPreview"
  component={ProductPreview}
  argTypes={{
    title: { control: "text", required: false },
    description: { control: "text", required: false },
    value: { control: "text", required: false },
    imageUrl: { control: "text", required: false },
    alt: { control: "text", required: false },
    price: { control: "float", required: false },
    discount: { control: "float", required: false }
  }}
/>

<Template let:args>
  <div style="padding: 20px">
    <ProductPreview {...args}/>
  </div>
</Template>

<Story
  name="Luminary Planner"
  args={{
    title: "Luminary Planner",
    description: "Designed for sports and exercise enthusiasts - track nutrition, workouts and record your progress. Choose from a variety of sports and create the perfect outline to achieve your fitness goals!<ul><li>3 months</li><li>Customizable to fit your routine</li><li>Helps you stay focused and dedicated</li><li>Great for athletes, coaches, and personal trainers</li></ul>",
    value: "planner",
    imageUrl: "planner-doodles-1600.png",
    alt: "planner book cover",
    price: 35,
    discount: 0.0
  }}
/>

<Story
  name="Luminary Journal"
  args={{
    title: "Luminary Journal",
    description: "Designed for sports and exercise enthusiasts - track nutrition, workouts and record your progress. Choose from a variety of sports and create the perfect outline to achieve your fitness goals!<ul><li>3 months</li><li>Customizable to fit your routine</li><li>Helps you stay focused and dedicated</li><li>Great for athletes, coaches, and personal trainers</li></ul>",
    value: "journal",
    imageUrl: "journal-doodles-1600.png",
    alt: "journal book cover",
    price: 35,
    discount: 0.0
  }}
/>

<Story
  name="Luminary Trainer"
  args={{
    title: "Luminary Trainer",
    description: "Designed for sports and exercise enthusiasts - track nutrition, workouts and record your progress. Choose from a variety of sports and create the perfect outline to achieve your fitness goals!<ul><li>3 months</li><li>Customizable to fit your routine</li><li>Helps you stay focused and dedicated</li><li>Great for athletes, coaches, and personal trainers</li></ul>",
    value: "trainer",
    imageUrl: "trainer-doodles-1600.png",
    alt: "trainer book cover",
    price: 35,
    discount: 0.0
  }}
/>

<Story
  name="Luminary Notebook"
  args={{
    title: "Luminary Notebook",
    description: "Designed for sports and exercise enthusiasts - track nutrition, workouts and record your progress. Choose from a variety of sports and create the perfect outline to achieve your fitness goals!<ul><li>3 months</li><li>Customizable to fit your routine</li><li>Helps you stay focused and dedicated</li><li>Great for athletes, coaches, and personal trainers</li></ul>",
    value: "notebook",
    imageUrl: "notebook-doodles-1600.png",
    alt: "notebook book cover",
    price: 24,
    discount: 0.0
  }}
/>

<Story
  name="Luminary Muse"
  args={{
    title: "Luminary Muse",
    description: "Designed for sports and exercise enthusiasts - track nutrition, workouts and record your progress. Choose from a variety of sports and create the perfect outline to achieve your fitness goals!<ul><li>3 months</li><li>Customizable to fit your routine</li><li>Helps you stay focused and dedicated</li><li>Great for athletes, coaches, and personal trainers</li></ul>",
    value: "muse",
    imageUrl: "muse-doodles-1600.png",
    alt: "muse book cover",
    price: 28,
    discount: 0.0
  }}
/>
