import assert from 'node:assert/strict'
import {normalizeServiceAddress} from '../packages/client-contracts/src/index.ts'
for(const value of ['https://service.example.org','https://service.example.org/','http://192.168.110.81:8088','http://127.0.0.1:8000','http://localhost:8000'])assert.equal(normalizeServiceAddress(value),value.replace(/\/$/,''))
for(const value of ['http://public.example.org','http://172.32.0.1','https://user:pass@example.org','https://host/api','https://host?token=x','https://host/#x','file:///etc/passwd','javascript:alert(1)','https://host\\evil','https://host:99999','https://host\n.evil','http://2130706433','http://127.1'])assert.throws(()=>normalizeServiceAddress(value),value)
assert.equal(normalizeServiceAddress(' http://10.2.3.4:8088/ '),'http://10.2.3.4:8088')
console.log('PASS shared service address: HTTPS/public, private-LAN preview, no credentials/query/path/ambiguous host')
