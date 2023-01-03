export default {
	env: import.meta.env.VITE_ENV || 'production',
	apiURL: import.meta.env.VITE_API_BASE_URL,
	apiVersion: import.meta.env.VITE_API_VERSION,
	baseURL: import.meta.env.VITE_SELF_BASE_URL || 'https://www.domain.com',
	imgCDN: import.meta.env.VITE_IMAGE_CDN || 'https://storage.domain.com',
	auth0domain: import.meta.env.VITE_AUTH0_DOMAIN,
	auth0clientId: import.meta.env.VITE_AUTH0_CLIENT_ID
};
