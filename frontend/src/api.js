const baseUrl = (import.meta.env?.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '');

export async function submitRecon(target) {
  let response;
  try {
    response = await fetch(`${baseUrl}/api/v1/recon`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ target }), signal: AbortSignal.timeout(30000),
    });
  } catch {
    throw new Error('Unable to reach the backend. Check that it is running and try again.');
  }
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    const details = data?.error?.details?.map(item => item.message).join('; ');
    throw new Error(details || data?.error?.message || `Request failed (${response.status})`);
  }
  if (!data || typeof data.status !== 'string' || typeof data.message !== 'string') {
    throw new Error('The backend returned an unexpected response.');
  }
  return data;
}

// Proposed AWS contracts; the current Recon AI backend does not implement these.
const cloudBase = (import.meta.env?.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '');
export const connectionPath = import.meta.env?.VITE_AWS_CONNECT_PATH || '';

async function cloudRequest(path, options = {}) {
  let response;
  try {
    response = await fetch(`${cloudBase}${path}`, {
      ...options, credentials: 'include', signal: options.signal || AbortSignal.timeout(30000),
      headers: { 'Content-Type': 'application/json', ...options.headers },
    });
  } catch (error) {
    if (error.name === 'AbortError') throw error;
    throw new Error('Cannot reach the cloud backend. Check the backend URL and connection.');
  }
  if (response.status === 404 || response.status === 501) {
    throw new Error('AWS integration is unavailable. This backend does not yet provide the required cloud API.');
  }
  if (response.status === 401 || response.status === 403) throw new Error('AWS access is not authorized. Connect through your authorized backend integration.');
  const data = await response.json().catch(() => null);
  if (!response.ok) throw new Error(data?.error?.message || `Cloud request failed (${response.status}).`);
  if (!data) throw new Error('The backend returned an empty response.');
  return data;
}

export function getInventory(signal) {
  return cloudRequest(import.meta.env?.VITE_AWS_INVENTORY_PATH || '/api/v1/aws/inventory', { signal });
}

export function getResource(resource, signal) {
  const query = new URLSearchParams(resource);
  return cloudRequest(`${import.meta.env?.VITE_AWS_RESOURCE_PATH || '/api/v1/aws/resource'}?${query}`, { signal });
}

export function askCloud(question, resources, messages) {
  return cloudRequest(import.meta.env?.VITE_CLOUD_CHAT_PATH || '/api/v1/cloud/chat', {
    method: 'POST', body: JSON.stringify({ question, resources, messages }),
  });
}

export async function connectAWS() {
  if (!connectionPath) throw new Error('An authorized AWS connection endpoint has not been configured.');
  const data = await cloudRequest(connectionPath, { method: 'POST' });
  const url = new URL(data.authorization_url);
  if (url.protocol !== 'https:') throw new Error('The backend must return a secure authorization URL.');
  window.location.assign(url.href);
}
