import { writable, get } from 'svelte/store'

// scroll position store
export const scroll = writable(0)
export const windowWidth = writable(0)
export const windowHeight = writable(0)
export const totalHeight = writable(0)
let prevBodyPosition
let prevBodyOverflow
let prevScroll = 0

export function disableScroll () {
	prevScroll = get(scroll)
	prevBodyPosition = document.body.style.position
	prevBodyOverflow = document.body.style.overflow
	document.body.style.position = 'fixed'
	document.body.style.top = `-${get(scroll)}px`
	document.body.style.overflow = 'hidden'
}

export function enableScroll () {
	document.body.style.position = prevBodyPosition || ''
	document.body.style.top = ''
	document.body.style.overflow = prevBodyOverflow || ''
	scroll.set(prevScroll)
	window.scrollTo(0, prevScroll)
	scroll.set(prevScroll)
}

// Easy delay func using async/await
export const delay = ms => new Promise(res => setTimeout(res, ms))

export function makeUniqueId () {
	// from https://gist.github.com/gordonbrander/2230317
	return '_' + Math.random().toString(36).substr(2, 9)
}

// Check if a variable is a number
export function isNumber (n) {
	return typeof n === 'number' && n === Number(n) && Number.isFinite(n)
}

// Check if a string is a number
export function isNumeric (str) {
	if (typeof str != 'string') return false // we only process strings!
	return (
		!isNaN(str) && // use type coercion to parse the _entirety_ of the string (`parseFloat` alone does not do this)...
		!isNaN(parseFloat(str))
	) // ...and ensure strings of whitespace fail
}

export function validateEmail (email) {
	const re = /\S+@\S+\.\S+/
	return re.test(email)
}

// Build out a link to a citation from just the citation number
export function citation (citation_number) {
	return (
		'<a href="/works-cited/' +
		citation_number +
		'" target="_blank" rel="noopener"><sup>' +
		citation_number +
		'</sup></a>'
	)
}

// Get a random property from an object
export let randomProperty = function (obj) {
	let keys = Object.keys(obj)
	return obj[keys[(keys.length * Math.random()) << 0]]
}

// Convert a sentence to title case for Blogs
export function toTitleCase (str) {
	return str.replace(
		/\w\S*/g,
		function (txt) {
			return txt.charAt(0).toUpperCase() + txt.substr(1).toLowerCase()
		}
	)
}