import test from 'node:test';
import assert from 'node:assert/strict';
import { authHeaders, currentUser, savedSession, signIn, signOut } from '../src/auth.js';

test('session survives reloads and errors; only sign-out removes it', async () => {
  const originalFetch = globalThis.fetch;
  const originalStorage = globalThis.localStorage;
  const values = new Map();
  globalThis.localStorage = {
    getItem: key => values.get(key) ?? null,
    setItem: (key, value) => values.set(key, value),
    removeItem: key => values.delete(key),
  };
  const calls = [];
  globalThis.fetch = async (url, options) => {
    calls.push({ url, options });
    return { ok: true, json: async () => ({ token: 'opaque-token', username: 'admin' }) };
  };
  try {
    await signIn('admin', 'private-password');
    assert.equal(savedSession().token, 'opaque-token');
    assert.equal([...values.values()].join('').includes('private-password'), false);
    assert.deepEqual(authHeaders(), { Authorization: 'Bearer opaque-token' });
    const reloaded = await import('../src/auth.js?reload');
    assert.equal(reloaded.savedSession().username, 'admin');
    globalThis.fetch = async () => { throw new Error('offline'); };
    await assert.rejects(currentUser());
    await assert.rejects(signOut());
    assert.equal(savedSession().token, 'opaque-token');
    globalThis.fetch = async (url, options) => {
      assert.equal(options.headers.Authorization, 'Bearer opaque-token');
      return { ok: true, json: async () => ({ status: 'signed_out' }) };
    };
    await signOut();
    assert.equal(savedSession(), null);
    assert.deepEqual(authHeaders(), {});
  } finally {
    globalThis.fetch = originalFetch;
    if (originalStorage === undefined) delete globalThis.localStorage;
    else globalThis.localStorage = originalStorage;
  }
});

test('revoked session is retained until explicit sign-out', async () => {
  const originalFetch = globalThis.fetch;
  const originalStorage = globalThis.localStorage;
  let saved = JSON.stringify({ token: 'revoked', username: 'admin' });
  globalThis.localStorage = { getItem: () => saved, removeItem: () => { saved = null; } };
  globalThis.fetch = async () => ({ ok: false, status: 401, json: async () => ({ error: { message: 'Session is no longer valid' } }) });
  try {
    await assert.rejects(currentUser());
    assert.equal(savedSession().token, 'revoked');
    await signOut();
    assert.equal(savedSession(), null);
  } finally {
    globalThis.fetch = originalFetch;
    if (originalStorage === undefined) delete globalThis.localStorage;
    else globalThis.localStorage = originalStorage;
  }
});
