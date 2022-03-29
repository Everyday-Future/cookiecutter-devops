/*

Stores used for caching user-specific status data.

For example, cart contents and status can be saved here rather than within components.

 */
import {writable, get} from 'svelte/store';

/*

User ID

 */

// Track the user token for API calls
export const uid = writable('');
export const email = writable('');
export const isLoggedIn = writable(false);

// Is the user set up and ready to go?
export function isUserReady() {
    return (get(uid) !== '') & (get(uid) !== undefined) & (get(uid) !== null)
}

/*

User Save / Update

 */

// Track the open/close start of the cart side menu
export function toggleStore() {
    const {subscribe, set, update} = writable(false)

    return {
        subscribe,
        update,
        set,
        toggle: () => update((n) => !n),
        reset: () => set(false)
    }
}
