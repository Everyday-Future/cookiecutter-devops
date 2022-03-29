
/**
 * Get all of the customizer details or some data to construct an error message
 * @return {token}
 */
export async function getToken() {
	// if (get(token) === null) {
		const res = await fetch(`${apiURL}/users`, {method: "GET"});
		const response = await res.json();
		if (response.success === true) {
			token.set(response.token);
			return response.token;
		}
	// } else {
	// 	return get(token);
	// }
}
