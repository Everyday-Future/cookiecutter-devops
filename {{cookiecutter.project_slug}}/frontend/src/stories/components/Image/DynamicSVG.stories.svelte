<script>
    import {Meta, Template, Story} from "@storybook/addon-svelte-csf";
    import DynamicSVG from "../../../components/Image/DynamicSVG.svelte";
    import grid from "../../../lib/svg/2dgrid_1x2.svg.json";
    import body from "../../../lib/svg/body-discomfort_2_1x2.svg.json";
    import golf from "../../../lib/svg/exercise_halfpage_golf.svg.json";
    import metrics from "../../../lib/svg/morning_metrics_1x2.svg.json";
    import museSigns from "../../../lib/svg/muse-signs.svg.json";
    import museSpace from "../../../lib/svg/muse-tic_tac_space.svg.json";
    import todos from "../../../lib/svg/organization_qtr.svg.json";
    import sudoku from "../../../lib/svg/sudoku_2x4.svg.json";
    import calendar from "../../../lib/svg/weekly_calendar_left-digest_2x4.svg.json";
    import wine from "../../../lib/svg/wine_tasting_fxf.svg.json";
</script>

<Meta
  title="components/Image/DynamicSVG"
  component={DynamicSVG}
  argTypes={{
    targetSvg: { control: "data" },
    src: {control: "text"},
    visible: { control: "boolean" }
  }}
/>

<Template let:args>
  <div style="margin: 50px">
    <DynamicSVG {...args}/>
  </div>
</Template>

<Story
  name="Grid"
  args={{
    targetSvg: grid,
    src: '2dgrid_1x2.svg',
    visible: true
  }}
/>

<Story
  name="Body Discomfort"
  args={{
    targetSvg: body,
    src: 'body-discomfort_2_1x2.svg',
    visible: true
  }}
/>

<Story
  name="Golf"
  args={{
    targetSvg: golf,
    src: 'exercise_halfpage_golf.svg',
    visible: true
  }}
/>

<Story
  name="Morning Metrics"
  args={{
    targetSvg: metrics,
    src: 'morning_metrics_1x2.svg',
    visible: true
  }}
/>

<Story
  name="Muse - Signs"
  args={{
    targetSvg: museSigns,
    src: 'muse-signs.svg',
    visible: true
  }}
/>

<Story
  name="Muse - Tic Tac Toe in Space"
  args={{
    targetSvg: museSpace,
    src: 'muse-tic_tac_space.svg',
    visible: true
  }}
/>

<Story
  name="Todo List"
  args={{
    targetSvg: todos,
    src: 'organization_qtr.svg',
    visible: true
  }}
/>

<Story
  name="Sudoku"
  args={{
    targetSvg: sudoku,
    src: 'sudoku_2x4.svg',
    visible: true
  }}
/>

<Story
  name="Weekly Calendar"
  args={{
    targetSvg: calendar,
    src: 'weekly_calendar_left-digest_2x4.svg',
    visible: true
  }}
/>

<Story
  name="Wine Tasting"
  args={{
    targetSvg: wine,
    src: 'wine_tasting_fxf.svg',
    visible: true
  }}
/>
