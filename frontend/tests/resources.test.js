import test from 'node:test';
import assert from 'node:assert/strict';
import { contextFor, parseAnswer, parseInventory, resourceKey, verifiedReference } from '../src/resources.js';
import { askCloud, getInventory, getResource } from '../src/api.js';

// Contract fixtures only. These values are never bundled or displayed as live data.
const resource = { resource_id: 'i-test', name: 'Test instance', account_id: '123456789012', region: 'us-east-1', service: 'ec2' };
const answer = { message: 'Review this instance.', parts: [{ type: 'text', text: 'Review ' }, { type: 'resource', reference_id: 'ref-1' }], references: [{ ...resource, id: 'ref-1' }] };

test('inventory accepts only canonical supported resources and real backend categories', () => {
  assert.equal(parseInventory({ resources: [resource], supported_services: ['ec2'] }).resources.length, 1);
  assert.throws(() => parseInventory({ resources: [resource], supported_services: ['s3'] }));
  assert.throws(() => parseInventory({ resources: [{ ...resource, account_id: undefined }], supported_services: ['ec2'] }));
  assert.throws(() => parseInventory({ resources: [resource, resource], supported_services: ['ec2'] }));
  assert.deepEqual(parseInventory({ resources: [], supported_services: [] }).resources, []);
});

test('structured references require exact inventory identity, not display names', () => {
  assert.equal(verifiedReference(answer.references[0], [resource]), resource);
  for (const change of [{ account_id: '999999999999' }, { region: 'eu-west-1' }, { service: 'ebs' }, { resource_id: 'i-other' }]) {
    assert.equal(verifiedReference({ ...resource, ...change }, [resource]), null);
    assert.notEqual(resourceKey({ ...resource, ...change }), resourceKey(resource));
  }
  assert.equal(verifiedReference({ label: resource.name }, [resource]), null);
});

test('chat response preserves explicit tokens and validates evidence and savings', () => {
  assert.deepEqual(parseAnswer(answer).parts, answer.parts);
  assert.throws(() => parseAnswer({ ...answer, parts: [{ type: 'html', text: '<script/>' }] }));
  assert.throws(() => parseAnswer({ ...answer, evidence: [{}] }));
  assert.throws(() => parseAnswer({ ...answer, references: [answer.references[0], answer.references[0]] }));
  assert.throws(() => parseAnswer({ ...answer, savings: [{ amount: '$10' }] }));
  assert.equal(parseAnswer({ ...answer, savings: [{ amount: '$10/month', is_estimate: true, assumptions: ['Stable workload'] }] }).savings[0].is_estimate, true);
});

test('document chat sends the backend question contract', async t => {
  const history = [{ role: 'user', content: 'Earlier question', resources: [contextFor(resource)] }];
  t.mock.method(globalThis, 'fetch', async (url, options) => {
    assert.ok(url.endsWith('/api/v1/chat'));
    assert.equal(options.method, 'POST');
    assert.equal(options.credentials, 'omit');
    assert.deepEqual(JSON.parse(options.body), { question: 'Analyze this' });
    return Response.json(answer);
  });
  assert.deepEqual(await askCloud('Analyze this', [contextFor(resource)], history), answer);
});

test('resource detail query carries complete identity', async t => {
  t.mock.method(globalThis, 'fetch', async url => {
    const query = new URL(url).searchParams;
    for (const [key, value] of Object.entries(contextFor(resource))) assert.equal(query.get(key), value);
    return Response.json(resource);
  });
  assert.deepEqual(await getResource(contextFor(resource)), resource);
});

test('missing APIs produce an explicit integration error, no mock inventory', async t => {
  t.mock.method(globalThis, 'fetch', async () => new Response('', { status: 404 }));
  await assert.rejects(getInventory(), /does not yet provide/);
});

test('unauthorized inventory and invalid responses surface errors', async t => {
  const fetch = t.mock.method(globalThis, 'fetch', async () => new Response('', { status: 403 }));
  await assert.rejects(getInventory(), /not authorized/);
  fetch.mock.mockImplementation(async () => new Response('not JSON', { status: 200 }));
  await assert.rejects(getInventory(), /empty response/);
});


test('S3 chat response is adapted for rendering with its source', () => {
  const parsed = parseAnswer({ message: 'Template analysis', source: 's3://bucket/snapshot.json' });
  assert.deepEqual(parsed.parts, [{ type: 'text', text: 'Template analysis' }]);
  assert.equal(parsed.source, 's3://bucket/snapshot.json');
  assert.deepEqual(parsed.references, []);
  assert.throws(() => parseAnswer({ message: 'Answer', source: 'https://invalid' }));
});

test('chat includes JWT and surfaces backend failures', async t => {
  const originalStorage = globalThis.localStorage;
  globalThis.localStorage = { getItem: () => JSON.stringify({ token: 'test-token', username: 'admin' }) };
  const fetch = t.mock.method(globalThis, 'fetch', async (url, options) => {
    assert.equal(options.headers.Authorization, 'Bearer test-token');
    return Response.json({ message: 'Answer', source: 's3://bucket/key' });
  });
  try {
    assert.equal(parseAnswer(await askCloud('Question')).message, 'Answer');
    fetch.mock.mockImplementation(async () => Response.json({ error: { message: 'Unable to read the configured S3 document' } }, { status: 502 }));
    await assert.rejects(askCloud('Question'), /Unable to read/);
    fetch.mock.mockImplementation(async () => new Response('', { status: 401 }));
    await assert.rejects(askCloud('Question'), /Sign out and sign in/);
  } finally {
    if (originalStorage === undefined) delete globalThis.localStorage;
    else globalThis.localStorage = originalStorage;
  }
});
