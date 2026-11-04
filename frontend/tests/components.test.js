import test, { before, after } from 'node:test';
import assert from 'node:assert/strict';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { createServer } from 'vite';
import { parseAnswer } from '../src/resources.js';

let server;
before(async () => {
  server = await createServer({ server: { middlewareMode: true, hmr: false, ws: false }, appType: 'custom' });
});
after(async () => { await server?.close(); });
async function render(name, props) {
  const { default: Component } = await server.ssrLoadModule(`/src/components/${name}.jsx`);
  return renderToStaticMarkup(React.createElement(Component, props));
}

test('Markdown renders GFM tables, lists and code; blocks unsafe links and raw HTML', async () => {
  const html = await render('Markdown', { children: '| Resource | Region |\n| --- | --- |\n| `i-test` | us-east-1 |\n\n- **Review** usage\n\n[Docs](https://example.com)\n\n[Bad](javascript:alert%281%29)\n\n<script>alert(1)</script>' });
  assert.match(html, /<table>/);
  assert.match(html, /<th>Resource<\/th>/);
  assert.match(html, /<code>i-test<\/code>/);
  assert.match(html, /<ul>/);
  assert.match(html, /rel="noopener noreferrer"/);
  assert.doesNotMatch(html, /href="javascript:|<script>/);
});

test('backend response adapter integrates with answer renderer and preserves all three sources', async () => {
  const sources = ['s3://bucket/one.json', 's3://bucket/two.json', 's3://bucket/three.json'];
  const answer = parseAnswer({ message: '| Resource | Finding |\n| --- | --- |\n| EC2 | Review CPU |', source: sources[0], sources });
  const html = await render('Answer', { answer, inventory: [], inspect() {} });
  for (const source of sources) assert.ok(html.includes(source));
  assert.match(html, /<table>/);
  assert.match(html, /Review CPU/);
});

test('unverified resource references remain text rather than actionable controls', async () => {
  const answer = { parts: [{ type: 'resource', reference_id: 'r' }], references: [{ id: 'r', label: 'Unknown instance' }] };
  const html = await render('Answer', { answer, inventory: [], inspect() {} });
  assert.match(html, /Unknown instance/);
  assert.match(html, /not in current inventory/);
  assert.doesNotMatch(html, /<button/);
});

test('conversation renders user text safely and exposes pending status', async () => {
  const html = await render('Conversation', { messages: [{ role: 'user', content: '<script>bad()</script>', resources: [] }], setPrompt() {}, composer: { current: null }, inventory: [], setSelected() {}, sending: true, end: { current: null } });
  assert.match(html, /&lt;script&gt;/);
  assert.doesNotMatch(html, /<script>/);
  assert.match(html, /role="status"/);
});

test('composer preserves retry text and disables submission while sending', async () => {
  const html = await render('ChatComposer', { chatError: 'Network failed', send() {}, attachments: [], sending: true, setAttachments() {}, composer: { current: null }, prompt: 'Original question', setPrompt() {}, inventoryReady: false, setSidebar() {} });
  assert.match(html, /role="alert"/);
  assert.match(html, /Network failed/);
  assert.match(html, /Original question/);
  assert.match(html, /disabled="" aria-label="Send question"/);
});
