<script>
    import {Meta, Template, Story} from "@storybook/addon-svelte-csf";
    import CitationCard from "../../../components/Cards/CitationCard.svelte";
</script>

<Meta
  title="components/Cards/CitationCard"
  component={CitationCard}
  argTypes={{
    idx: { control: "number", default: 0 },
    category: { control: "text", default: "fitness" },
    title: { control: "text", default: "Example Title" },
    description: { control: "text", default: "This is a blog post summary, which should tell you a little about the post" },
    authors: { control: "text", default: "James Clear" },
    link: { control: "text", default: "https://www.{{ cookiecutter.project_domain }}/works_cited" },
    source: { control: "text", default: "https://www.{{ cookiecutter.project_domain }}/works_cited" }
  }}
/>

<Template let:args>
  <div style="background-color: var(--white); width: 100%; height: 100vh; " class="flex-center-row">
    <div style="width: 300px;">
      <CitationCard {...args} on:click={args.onClick}/>
    </div>
  </div>
</Template>

<Story
  name="Citation Example"
  args={{
    idx: 0,
    category: "fitness",
    title: "Example Title",
    description: "This is a blog post summary, which should tell you a little about the post",
    authors: "example tags",
    link: "https://www.{{ cookiecutter.project_domain }}/works_cited",
    source: "https://www.{{ cookiecutter.project_domain }}/works_cited"
  }}
/>

<Story
  name="Long Citation Example"
  args={{
    idx: 1,
    category: "misc",
    title: "Example Very Very Long and Important Title",
    description: "This is a blog post summary, which should tell you a little about the post.<br /><br /> " +
     "Besides, sometimes there is a lot to talk about here and so it'll need to be able to accomodate that too",
    authors: "example tags",
    link: "https://www.{{ cookiecutter.project_domain }}/works_cited",
    source: "https://www.{{ cookiecutter.project_domain }}/works_cited"
  }}
/>
