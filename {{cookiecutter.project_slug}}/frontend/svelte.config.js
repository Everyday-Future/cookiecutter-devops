
import adapter from '@sveltejs/adapter-node';

/** @type {import('@sveltejs/kit').Config} */
const config = {
	kit: {
		adapter: adapter({
			out: 'build',
			precompress: true
		}),
		browser: {
			router: false,
		},
		vite: {
			server: {
				watch: {
					usePolling: true
				}
			},
			optimizeDeps: {
				include: ['cookie'],
				exclude: ['node-fetch']
			}
		}
	}
};

export default config;
