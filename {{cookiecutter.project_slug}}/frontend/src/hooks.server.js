import cookie from 'cookie'
import { getToken, buildCookie } from '$lib/api'
import { minify } from 'html-minifier'
import { building } from '$app/environment'

const minification_options = {
	collapseBooleanAttributes: true,
	collapseWhitespace: true,
	conservativeCollapse: true,
	decodeEntities: true,
	html5: true,
	ignoreCustomComments: [/^#/],
	minifyCSS: true,
	minifyJS: true,
	removeAttributeQuotes: true,
	removeComments: true,
	removeOptionalTags: true,
	removeRedundantAttributes: true,
	removeScriptTypeAttributes: true,
	removeStyleLinkTypeAttributes: true,
	sortAttributes: true,
	sortClassName: true
}

export const handle = async ({ event, resolve }) => {
	// Log the request
	const logMap = {
		method: event.request.method,
		url: event.url.href,
		useragent: event.request.headers.get('user-agent'),
		cookie: event.request.headers.get('cookie')
	}
	console.log(JSON.stringify(logMap))
	// Once client-side, get the user id
	if (!building && !event.url.pathname.startsWith('/admin')) {
		let cookies = cookie.parse(event.request.headers.get('cookie') || '')
		let userid = cookies.uid
		if (!userid) {
			// if this is the first time the user has visited this app,
			// set a cookie so that we recognise them when they return
			userid = await getToken(event.request.headers.get('user-agent'))
		}
		event.locals.userid = userid
	}

	// TODO https://github.com/sveltejs/kit/issues/1046
	if (event.url.searchParams.has('_method')) {
		event.method = event.url.searchParams.get('_method').toUpperCase()
	}

	const response = await resolve(event)

	// Set the uid cookie to a valid user id
	if (!building && !event.url.pathname.startsWith('/admin') && event.locals.userid) {
		response.headers.append('set-cookie', buildCookie('uid', event.locals.userid))
	}

	// minification - disabled until svelte-kit stabilizes at 1.0. This keeps changing right now.
	if (building && !event.url.pathname.startsWith('/admin') && response.body) {
		response.body = minify(response.body, minification_options)
	}
	return response
}
