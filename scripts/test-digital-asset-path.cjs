const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const ts=require('../ChatVRM/node_modules/typescript');
const source=fs.readFileSync('ChatVRM/src/utils/buildUrl.ts','utf8');
const output=ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.CommonJS}}).outputText;
for(const prefix of ['', '/digital']){
  const context={exports:{},process:{env:{NEXT_PUBLIC_BASE_PATH:prefix}},require(){throw Error('Asset URLs must use build-time configuration; deprecated runtime config emits a browser warning')}};
  vm.runInNewContext(output,context);
  assert.equal(context.exports.buildUrl('/AvatarSample_B.vrm'),prefix+'/AvatarSample_B.vrm');
}
console.log('PASS local digital asset URLs preserve the build-time root and optional base path without runtime config');
