<script>
	import { Meta, Template, Story } from '@storybook/addon-svelte-csf'
	import ProductComparison from '../../../components/Panels/ProductComparison.svelte'

	let allProducts = [
		{
			__typename: 'Product',
			id: 'ckt4z86j20280m7y4icaksoyt',
			image: 'https://blog.luminaryhandbook.com/notebook.jpg',
			price: 3500,
			productComparisonDescription:
				'Notebook Lorem ipsum dolor sit amet, consectetuer adipiscing elit, sed diam nonummy nibh euismod tincidunt ut laoreet dolore magna aliquam erat volutpat. Ut wisi enim ad minim veniam, quis nostrud exerci tation ullamcorper suscipit lobortis nisl ut aliquip ex ea commodo consequat. Duis autem vel eum iriure dolor in hendrerit in vulputate velit esse molestie consequat, vel illum dolore eu feugiat nulla facilisis at vero eros et accumsan et iusto odio dignissim qui blandit praesent luptatum zzril delenit augue duis dolore te feugait nulla facilisi. Lorem ipsum dolor sit amet, cons ectetuer adipiscing elit, sed diam nonummy nibh euismod tincidunt ut laoreet dolore magna aliquam erat volutpat. Ut wisi enim ad minim veniam, quis nostrud exerci tation ullamcorper suscipit lobortis nisl ut aliquip ex',
			productPagePath: '/products/notebook',
			title: 'Notebook'
		},
		{
			__typename: 'Product',
			id: 'ckt4z792f0148m7y4p2itqnjh',
			image: 'https://blog.luminaryhandbook.com/planner.jpg',
			price: 3500,
			productComparisonDescription:
				'Planner Lorem ipsum dolor sit amet, consectetuer adipiscing elit, sed diam nonummy nibh euismod tincidunt ut laoreet dolore magna aliquam erat volutpat. Ut wisi enim ad minim veniam, quis nostrud exerci tation ullamcorper suscipit lobortis nisl ut aliquip ex ea commodo consequat. Duis autem vel eum iriure dolor in hendrerit in vulputate velit esse molestie consequat, vel illum dolore eu feugiat nulla facilisis at vero eros et accumsan et iusto odio dignissim qui blandit praesent luptatum zzril delenit augue duis dolore te feugait nulla facilisi. Lorem ipsum dolor sit amet, cons ectetuer adipiscing elit, sed diam nonummy nibh euismod tincidunt ut laoreet dolore magna aliquam erat volutpat. Ut wisi enim ad minim veniam, quis nostrud exerci tation ullamcorper suscipit lobortis nisl ut aliquip ex',
			productPagePath: '/products/planner',
			title: 'Planner'
		},
		{
			__typename: 'Product',
			id: 'ckt4z7uc50192m7y45v1vbzjj',
			image: 'https://blog.luminaryhandbook.com/journal.jpg',
			price: 3500,
			productComparisonDescription:
				'Journal Lorem ipsum dolor sit amet, consectetuer adipiscing elit, sed diam nonummy nibh euismod tincidunt ut laoreet dolore magna aliquam erat volutpat. Ut wisi enim ad minim veniam, quis nostrud exerci tation ullamcorper suscipit lobortis nisl ut aliquip ex ea commodo consequat. Duis autem vel eum iriure dolor in hendrerit in vulputate velit esse molestie consequat, vel illum dolore eu feugiat nulla facilisis at vero eros et accumsan et iusto odio dignissim qui blandit praesent luptatum zzril delenit augue duis dolore te feugait nulla facilisi. Lorem ipsum dolor sit amet, cons ectetuer adipiscing elit, sed diam nonummy nibh euismod tincidunt ut laoreet dolore magna aliquam erat volutpat. Ut wisi enim ad minim veniam, quis nostrud exerci tation ullamcorper suscipit lobortis nisl ut aliquip ex',
			productPagePath: '/products/journal',
			title: 'Journal'
		},
		{
			__typename: 'Product',
			id: 'ckt4z7zzr0236m7y46nkm0jgy',
			image: 'https://blog.luminaryhandbook.com/amuse.jpg',
			price: 3500,
			productComparisonDescription:
				'Amuse Lorem ipsum dolor sit amet, consectetuer adipiscing elit, sed diam nonummy nibh euismod tincidunt ut laoreet dolore magna aliquam erat volutpat. Ut wisi enim ad minim veniam, quis nostrud exerci tation ullamcorper suscipit lobortis nisl ut aliquip ex ea commodo consequat. Duis autem vel eum iriure dolor in hendrerit in vulputate velit esse molestie consequat, vel illum dolore eu feugiat nulla facilisis at vero eros et accumsan et iusto odio dignissim qui blandit praesent luptatum zzril delenit augue duis dolore te feugait nulla facilisi. Lorem ipsum dolor sit amet, cons ectetuer adipiscing elit, sed diam nonummy nibh euismod tincidunt ut laoreet dolore magna aliquam erat volutpat. Ut wisi enim ad minim veniam, quis nostrud exerci tation ullamcorper suscipit lobortis nisl ut aliquip ex',
			productPagePath: '/products/amuse',
			title: 'Amuse'
		},
		{
			__typename: 'Product',
			id: 'ckt4z6xg00068m7y4wpe55q2b',
			image: 'https://blog.luminaryhandbook.com/trainer-300.png',
			price: 3500,
			productComparisonDescription:
				'Athlete Lorem ipsum dolor sit amet, consectetuer adipiscing elit, sed diam nonummy nibh euismod tincidunt ut laoreet dolore magna aliquam erat volutpat. Ut wisi enim ad minim veniam, quis nostrud exerci tation ullamcorper suscipit lobortis nisl ut aliquip ex ea commodo consequat. Duis autem vel eum iriure dolor in hendrerit in vulputate velit esse molestie consequat, vel illum dolore eu feugiat nulla facilisis at vero eros et accumsan et iusto odio dignissim qui blandit praesent luptatum zzril delenit augue duis dolore te feugait nulla facilisi. Lorem ipsum dolor sit amet, cons ectetuer adipiscing elit, sed diam nonummy nibh euismod tincidunt ut laoreet dolore magna aliquam erat volutpat. Ut wisi enim ad minim veniam, quis nostrud exerci tation ullamcorper suscipit lobortis nisl ut aliquip ex',
			productPagePath: '/products/luminary-trainer',
			title: 'Athlete'
		}
	]
</script>

<Meta
	title="components/Panels/ProductComparison"
	component={ProductComparison}
	argTypes={{
		allProducts: { control: 'data' }
	}}
/>

<Template let:args>
	<ProductComparison {...args} />
</Template>

<Story name="Default" args={{ allProducts }} />
