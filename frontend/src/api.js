const baseUrl = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '');

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
