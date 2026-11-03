const baseUrl = (import.meta.env?.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '');
const sessionKey = 'recon-ai-session';
export function savedSession() {
  try {
    const value = JSON.parse(localStorage.getItem(sessionKey));
    return value && typeof value.token === 'string' && typeof value.username === 'string' ? value : null;
  } catch { return null; }
}
export function authHeaders() {
  const session = savedSession();
  return session ? { Authorization: `Bearer ${session.token}` } : {};
}
async function request(path, options = {}) {
  let response;
  try {
    response = await fetch(`${baseUrl}/api/v1/auth/${path}`, {
      ...options, headers: { 'Content-Type': 'application/json', ...authHeaders() },
      signal: AbortSignal.timeout(15000),
    });
  } catch { throw new Error('Unable to reach the backend. Please try again.'); }
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    const error = new Error(data?.error?.message || `Request failed (${response.status})`);
    error.status = response.status;
    throw error;
  }
  return data;
}
export async function signIn(username, password) {
  const session = await request('login', { method: 'POST', body: JSON.stringify({ username, password }) });
  try { localStorage.setItem(sessionKey, JSON.stringify(session)); }
  catch { throw new Error('Browser storage is unavailable. Enable local storage to stay signed in.'); }
  return session;
}
export function currentUser() { return request('me'); }
export async function signOut() {
  try { await request('logout', { method: 'POST' }); }
  catch (error) { if (error.status !== 401) throw error; }
  localStorage.removeItem(sessionKey);
}
