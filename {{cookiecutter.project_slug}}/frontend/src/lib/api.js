
import envVars from "./variables";
const { apiURL } = envVars;


export function createAuthHeaders(token) {
  return {
      "Content-Type": "application/json",
      "Authorization": `Bearer ${token}`
  };
}


export async function fetchGet(fetch, url, token) {
	const res = await fetch(`${apiURL}${url}`, {
    method: "GET",
    headers: {...(token) ? createAuthHeaders(token) : {}},
    })
	return await res.json()
}

export async function fetchPost(fetch, url, token, data) {
	const res = await fetch(`${apiURL}${url}`, {
		method: 'POST',
        headers: {...(token) ? createAuthHeaders(token) : {}},
		body: JSON.stringify(data)
	})
	return await res.json()
}
