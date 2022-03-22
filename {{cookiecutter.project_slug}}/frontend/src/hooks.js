import cookie from 'cookie';
import {getToken} from "$lib/auth";
import { minify } from 'html-minifier';
import { prerendering } from '$app/env';


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
};

export const handle = async ({ event, resolve }) => {
	if (!prerendering) {
		// Once client-side, get the user id
		let cookies = cookie.parse(event.request.headers.get('cookie') || '');
		let userid = cookies.uid;
		if (!userid) {
			// if this is the first time the user has visited this app,
			// set a cookie so that we recognise them when they return
			userid = await getToken();
		}
		event.locals.userid = userid;
	}

	// TODO https://github.com/sveltejs/kit/issues/1046
	if (event.url.searchParams.has('_method')) {
		event.method = event.url.searchParams.get('_method').toUpperCase();
	}

	// Set the uid cookie to a valid user id
	const response = await resolve(event);
	if (!prerendering && event.locals.userid) {
		response.headers.append('set-cookie', `uid=${event.locals.userid}; Path=/; HttpOnly`);
	}

	// minification
	if (prerendering && response.headers.get('content-type') === 'text/html') {
		const body = await response.text();
		return new Response(minify(body, minification_options), response);
	}
	return response;
};

export function getSession(event) {
    return {
        userAgent: event.request.headers['user-agent'],
		userid: event.locals.userid
    }
}
