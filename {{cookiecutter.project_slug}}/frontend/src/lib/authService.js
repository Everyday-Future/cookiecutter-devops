import { createAuth0Client } from '@auth0/auth0-spa-js'
import { get } from 'svelte/store'
import { isAuthenticated, authPopupOpen, user, uid, authError, fetchPost } from './api'
import envVars from './variables.js'

async function createClient () {
	return await createAuth0Client({
		domain: envVars.auth0domain,
		clientId: envVars.auth0clientId
	})
}

async function loginWithPopup (client, options) {
	authPopupOpen.set(true)
	try {
		await client.loginWithPopup(options)
		user.set(await client.getUser())
		isAuthenticated.set(true)
		// get the uid for the user by email from the db
		let resp = await fetchPost(fetch, '/auth/email', get(uid),
			{ 'email': get(user).email })
		// overwrite the uid store and uid cookie
		if (resp.success === true) {
			uid.set(resp.token)
		} else {
			throw 'credentials not accepted by the backend'
		}
	} catch (e) {
		// eslint-disable-next-line
		console.error(e)
		authError.set(e)
		isAuthenticated.set(false)
		user.set(null)
	} finally {
		authPopupOpen.set(false)
	}
}

function logout (client) {
	return client.logout()
}

const auth = {
	createClient,
	loginWithPopup,
	logout
}

export default auth
