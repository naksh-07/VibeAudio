import { getSignedInUser, persistUserProfile } from './auth.js';

async function bootApp() {
    try {
        if (navigator.onLine) {
            try {
                const user = await getSignedInUser();
                if (user) {
                    persistUserProfile(user);
                }
            } catch (authError) {
                console.warn('Clerk auth verification non-blocking on boot:', authError);
            }
        }
    } catch (error) {
        console.warn('App boot auth initialization non-blocking:', error);
    } finally {
        await import('./ui.js');
    }
}

bootApp();
