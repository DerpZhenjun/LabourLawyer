/** Fixed public status DTO bridge; stdin is data, never executable code. */
import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
import {parseCollectorStatus} from '../../../packages/client-contracts/src/collector.ts'

const wire=JSON.parse(readFileSync(0,'utf8'))
assert('issue_events' in wire)
assert.deepEqual(parseCollectorStatus(wire).issue_events,wire.issue_events)
console.log('PASS actual collector issue wire')
