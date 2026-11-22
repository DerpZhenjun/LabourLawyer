import assert from 'node:assert/strict';
import {createRegionalClient} from '../frontend/src/api/regional.ts';

const contract = {
  schema_version: 1, context: {
    province: 'zhejiang', city: '杭州市', district: '淳安县', region_code: '330127',
    source_id: 'f'.repeat(24), version: 2, template_id: 'fixture-template',
    kind: 'application', mode: 'blank', adapter: 'fixture',
  },
  fields: [], defaults: {}, policy: {}, contract_id: 'c'.repeat(64),
};
const origin = 'official-blank-metadata-sanitized-filled';
const proof = {layoutSha256: '2'.repeat(64), officialSha256: '1'.repeat(64)};
const baseHeaders = {
  'X-Form-Contract-ID': contract.contract_id,
  'X-Guide-Source-ID': contract.context.source_id,
  'X-Guide-Version': String(contract.context.version),
};
const sanitizedHeaders = {
  'X-Document-Origin': origin,
  'X-Document-Layout-Origin': 'official-blank-metadata-sanitized-layout',
  'X-Template-SHA256': proof.layoutSha256,
  'X-Official-Original-SHA256': proof.officialSha256,
};
const client = (headers = sanitizedHeaders) => createRegionalClient('/', async () =>
  new Response(Uint8Array.from([0x50, 0x4b, 3, 4]), {headers: {...baseHeaders, ...headers}}));

assert.equal((await client().generate(contract, {}, undefined, proof)).size, 4);
await assert.rejects(client().generate(contract, {}));
await assert.rejects(client({'X-Document-Origin': 'official-blank-filled'}).generate(contract, {}, undefined, proof));
await assert.rejects(client({...sanitizedHeaders, 'X-Template-SHA256': proof.officialSha256}).generate(contract, {}, undefined, proof));
await assert.rejects(client({...sanitizedHeaders, 'X-Official-Original-SHA256': '0'.repeat(64)}).generate(contract, {}, undefined, proof));
assert.equal((await client({'X-Document-Origin': 'official-blank-filled'}).generate(contract, {})).size, 4);
console.log('PASS: explicit derived generation identity and two SHA bindings, legacy generated origin retained');
