import envVars from './variables'
import { get, writable } from 'svelte/store'

const { apiURL } = envVars

export function consoleLog (content) {
	if (envVars.env !== 'production') {
		console.log(...content)
	}
}

/*

User ID

*/

// Track the user token for API calls
export const uid = writable('')
export const userState = writable(null)
// Sync user between devices with Auth system
export const user = writable(null)
export const isAuthenticated = writable(false)
export const authPopupOpen = writable(false)
export const authError = writable()
export const authPreviewPopoverOpen = writable(false)

/**
 * Get all the customizer details or some data to construct an error message
 * @return {token}
 */
export async function getToken (userAgent) {
	const controller = new AbortController()
	// 15 second timeout:
	const timeoutId = setTimeout(() => controller.abort(), 15000)
	const res = await fetch(
		`${apiURL}/users`,
		{ method: 'POST', body: JSON.stringify({ userAgent }), signal: controller.signal }
	)
	const response = await res.json()
	if (response.success === true) {
		return response.token
	}
}

export function buildCookie (cname, cvalue, days = 90) {
	const d = new Date()
	d.setTime(d.getTime() + (days * 24 * 60 * 60 * 1000))
	let expires = 'expires=' + d.toUTCString()
	return cname + '=' + cvalue + ';' + expires + ';path=/'
}

// Is the user set up and ready to go?
export function isUserReady () {
	return (get(uid) !== '') & (get(uid) !== undefined) & (get(uid) !== null)
}

export function createAuthHeaders (token) {
	return {
		'Content-Type': 'application/json',
		Authorization: `Bearer ${token}`
	}
}

// Wait a number of millis before retrying a fetch
function wait (delay) {
	return new Promise((resolve) => setTimeout(resolve, delay))
}

// Resilient fetch operation with retries and delays between
export function fetchRetry (url, delay, tries, fetchOptions = {}) {
	function onError (err) {
		let triesLeft = tries - 1
		if (!triesLeft) {
			throw err
		}
		return wait(delay).then(() => fetchRetry(url, delay, triesLeft, fetchOptions))
	}

	return fetch(url, fetchOptions).catch(onError)
}

export async function fetchGet (fetch, url, token) {
	const res = await fetchRetry(`${apiURL}${url}`, 300, 3, {
		method: 'GET',
		headers: { ...(token ? createAuthHeaders(token) : {}) }
	})
	return await res.json()
}

export async function fetchPost (fetch, url, token, data) {
	const res = await fetchRetry(`${apiURL}${url}`, 300, 3, {
		method: 'POST',
		headers: { ...(token ? createAuthHeaders(token) : {}) },
		body: JSON.stringify(data)
	})
	return await res.json()
}

/*

User Save / Update

*/

// Toggle a true/false value for the cart side menu etc...
export function toggleStore () {
	const { subscribe, set, update } = writable(false)

	return {
		subscribe,
		update,
		set,
		toggle: () => update((n) => !n),
		reset: () => set(false)
	}
}
