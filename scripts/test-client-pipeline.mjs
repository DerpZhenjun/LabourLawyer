import assert from 'node:assert/strict'
import { mkdtempSync, mkdirSync, readFileSync, writeFileSync, existsSync, utimesSync, symlinkSync, rmSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { test } from 'node:test'

// The injected process boundary avoids builds, SDKs and network; receipts and files are real.
let api
try { api = await import('./client-pipeline.mjs') } catch {}
test('pipeline module supplies the orchestrator', () => assert.equal(typeof api?.runPipeline, 'function', 'client pipeline is not implemented'))

if (api) {
  function fixture(t) {
    const root = mkdtempSync(join(tmpdir(), 'client-pipeline-'))
    t.after(() => rmSync(root, { recursive: true, force: true }))
    mkdirSync(join(root, 'src'))
    writeFileSync(join(root, 'src/input.txt'), 'input v1')
    const graph = {
      shared: { deps: [], command: { bin: 'node', args: ['shared'], cwd: '.' } },
      'web:build': { deps: ['shared'], command: { bin: 'node', args: ['web'], cwd: '.' }, artifacts: [{ path: 'out/web', fresh: true }] },
      'mini:build': { deps: ['shared'], command: { bin: 'node', args: ['mini'], cwd: '.' }, artifacts: [{ path: 'out/mini', fresh: true }] },
    }
    const writeArtifact = (name, body = name) => {
      mkdirSync(join(root, 'out', name), { recursive: true })
      writeFileSync(join(root, 'out', name, 'index.js'), body)
    }
    return { root, graph, writeArtifact, inputs: ['src'], targets: ['web', 'mini'], action: 'build' }
  }

  test('shared dependency executes once, manifests hash actual bytes, and artifact stage prepares an exact allowlist', async t => {
    const f = fixture(t), calls = []
    const result = await api.runPipeline({ ...f, runner: async command => {
      calls.push(command.args[0])
      if (command.args[0] !== 'shared') f.writeArtifact(command.args[0])
      return { status: 0 }
    } })
    assert.deepEqual(calls, ['shared', 'web', 'mini'])
    assert.equal(result.receipt.status, 'passed')
    assert.equal(result.receipt.steps.length, 3)
    assert.equal(result.receipt.artifacts.length, 2)
    assert.equal(result.receipt.artifacts.find(x => x.path === 'out/web/index.js').sha256, '4b5e57f6eb2f42b9039b3d1e13929295f231749c510cbe341cd68036d9af97e2')
    const staged = await api.prepareArtifacts({ root: f.root, receiptPath: result.receiptPath, graph: f.graph, inputs: f.inputs })
    assert.deepEqual(staged.files.map(x => x.path), ['out/mini/index.js', 'out/web/index.js'])
    assert.equal(staged.published, false)
    assert(existsSync(staged.allowlistPath))
  })

  test('a failed process stops dependents and records non-passing steps', async t => {
    const f = fixture(t), calls = []
    const result = await api.runPipeline({ ...f, runner: async command => { calls.push(command.args[0]); return { status: 7 } } })
    assert.deepEqual(calls, ['shared'])
    assert.equal(result.receipt.status, 'failed')
    assert.equal(result.receipt.steps[0].exitCode, 7)
    assert.deepEqual(result.receipt.steps.slice(1).map(x => x.status), ['blocked', 'blocked'])
    await assert.rejects(api.prepareArtifacts({ root: f.root, receiptPath: result.receiptPath, graph: f.graph, inputs: f.inputs }), /successful build/)
  })

  test('dry-run executes zero commands and cannot serve as release evidence', async t => {
    const f = fixture(t)
    const result = await api.runPipeline({ ...f, dryRun: true, runner: () => assert.fail('dry-run executed a command') })
    assert.equal(result.receipt.status, 'planned')
    assert.equal(result.receipt.artifacts.length, 0)
    assert(result.receipt.steps.every(x => x.status === 'planned'))
    await assert.rejects(api.prepareArtifacts({ root: f.root, receiptPath: result.receiptPath, graph: f.graph, inputs: f.inputs }), /successful build/)
  })

  test('a successful command cannot attest an old, missing, or empty output', async t => {
    for (const state of ['old', 'missing', 'empty', 'empty-file']) {
      const f = fixture(t)
      f.targets = ['web']
      if (state === 'old') { f.writeArtifact('web'); utimesSync(join(f.root, 'out/web/index.js'), new Date(0), new Date(0)) }
      if (state === 'empty') mkdirSync(join(f.root, 'out/web'), { recursive: true })
      if (state === 'empty-file') f.writeArtifact('web', '')
      const result = await api.runPipeline({ ...f, runner: async () => ({ status: 0 }) })
      assert.equal(result.receipt.status, 'failed', state)
      assert.match(result.receipt.steps.at(-1).error, /artifact|output/i)
    }
  })

  test('changed source, modified artifacts, expired receipt, or forged passing step is refused', async t => {
    for (const tamper of ['source', 'artifact', 'age', 'step', 'omit']) {
      const f = fixture(t)
      const result = await api.runPipeline({ ...f, runner: async command => {
        if (command.args[0] !== 'shared') f.writeArtifact(command.args[0])
        return { status: 0 }
      } })
      if (tamper === 'source') writeFileSync(join(f.root, 'src/input.txt'), 'changed')
      if (tamper === 'artifact') f.writeArtifact('web', 'changed')
      if (tamper === 'age') result.receipt.finishedAt = new Date(0).toISOString()
      if (tamper === 'step') result.receipt.steps[0].exitCode = 9
      if (tamper === 'omit') result.receipt.steps.pop()
      writeFileSync(result.receiptPath, JSON.stringify(result.receipt))
      await assert.rejects(api.prepareArtifacts({ root: f.root, receiptPath: result.receiptPath, graph: f.graph, inputs: f.inputs }), /source|artifact|expired|step|plan/)
    }
  })

  test('output and working-directory traversal is rejected before execution', async t => {
    for (const field of ['artifact', 'cwd']) {
      const f = fixture(t)
      if (field === 'artifact') f.graph['web:build'].artifacts[0].path = '../outside'
      else f.graph.shared.command.cwd = '../outside'
      await assert.rejects(api.runPipeline({ ...f, runner: () => assert.fail('unsafe graph executed') }), /outside|relative|bounds/)
    }
  })

  test('artifact symlinks cannot escape workspace bounds', async t => {
    const f = fixture(t)
    const outside = mkdtempSync(join(tmpdir(), 'client-pipeline-outside-'))
    t.after(() => rmSync(outside, { recursive: true, force: true }))
    mkdirSync(join(f.root, 'out'))
    writeFileSync(join(outside, 'index.js'), 'outside')
    symlinkSync(outside, join(f.root, 'out/web'), process.platform === 'win32' ? 'junction' : 'dir')
    await assert.rejects(api.runPipeline({ ...f, targets: ['web'], runner: () => assert.fail('junction executed') }), /Symlink|outside|bounds/)
  })

  test('web and Android plan reuse the APK script frontend build and never execute commands', async t => {
    const f = fixture(t)
    const result = await api.runPipeline({ root: f.root, action: 'plan', targets: ['web', 'android'], runner: () => assert.fail('plan executed') })
    const builds = result.receipt.steps.filter(x => x.command?.args.includes('android:apk'))
    assert.equal(builds.length, 1)
    assert.equal(result.receipt.steps.find(x => x.id === 'web:build').command, null)
    assert(builds[0].command.args.includes('--ignore-scripts'), 'nested frontend lifecycle generation must not repeat shared contract dependencies')
  })

  test('old outputs can only be reused with a verified prior receipt for identical inputs and checksum', async t => {
    const f = fixture(t)
    const first = await api.runPipeline({ ...f, runner: async command => {
      if (command.args[0] !== 'shared') f.writeArtifact(command.args[0])
      return { status: 0 }
    } })
    // The clock advances; unchanged output now predates this incremental build.
    const past = new Date(Date.now() - 10_000)
    for (const name of ['web', 'mini']) utimesSync(join(f.root, `out/${name}/index.js`), past, past)
    const next = await api.runPipeline({ ...f, reuseReceiptPath: first.receiptPath, runner: async () => ({ status: 0 }) })
    assert.equal(next.receipt.status, 'passed')
    assert(next.receipt.artifacts.every(x => x.reused === true))
    assert.equal(next.receipt.reusedFrom, `.runtime/client-pipeline/${first.receipt.runId}/receipt.json`)
    const staged = await api.prepareArtifacts({ root: f.root, receiptPath: next.receiptPath, graph: f.graph, inputs: f.inputs })
    assert(staged.files.every(x => x.reused === true))
    f.writeArtifact('web', 'wrong artifact')
    const rejected = await api.runPipeline({ ...f, reuseReceiptPath: first.receiptPath, runner: () => assert.fail('invalid prior artifacts executed') })
    assert.equal(rejected.receipt.status, 'failed')
    assert.match(rejected.receipt.error, /artifact/)
  })

  test('process errors and absent exit status cannot become successful receipts', async t => {
    for (const outcome of [undefined, { status: null, signal: 'SIGTERM' }, { status: 0, signal: 'SIGTERM' }, { status: 0, error: new Error('spawn failed') }]) {
      const f = fixture(t)
      const result = await api.runPipeline({ ...f, runner: async () => outcome })
      assert.equal(result.receipt.status, 'failed')
      assert.equal(result.receipt.steps[0].status, 'failed')
      assert(result.receipt.steps.slice(1).every(x => x.status === 'blocked'))
    }
  })

  test('production runner preserves a real child-process failure exit code', async t => {
    const f = fixture(t)
    f.graph.shared.command = { bin: 'node', args: ['-e', 'process.exit(23)'], cwd: '.' }
    const result = await api.runPipeline(f)
    assert.equal(result.receipt.status, 'failed')
    assert.equal(result.receipt.steps[0].exitCode, 23)
    assert(result.receipt.steps.slice(1).every(x => x.status === 'blocked'))
  })

  test('private backend runtime and SQLite files never affect snapshots or artifact allowlists, while app code does', async t => {
    const f = fixture(t)
    f.inputs = ['src', 'backend', 'data/public-regions']
    const privateFiles = ['backend/data/user-case.json', 'backend/uploads/private-upload.pdf', 'backend/runtime/session.sqlite', 'backend/runtime/session.sqlite-wal', 'backend/runtime/session.sqlite3', 'backend/runtime/session.sqlite3-shm']
    for (const file of [...privateFiles, 'backend/service.py', 'data/public-regions/guides.json']) {
      mkdirSync(join(f.root, file, '..'), { recursive: true })
      writeFileSync(join(f.root, file), file === 'backend/service.py' ? 'app_code = 1' : 'fixture data')
    }
    const result = await api.runPipeline({ ...f, runner: async command => {
      if (command.args[0] !== 'shared') {
        f.writeArtifact(command.args[0])
        for (const extension of ['db', 'db-wal', 'sqlite', 'sqlite-shm', 'sqlite3', 'sqlite3-wal']) writeFileSync(join(f.root, `out/${command.args[0]}/private.${extension}`), 'private database')
      }
      return { status: 0 }
    } })
    assert.equal(result.receipt.status, 'passed')
    for (const file of privateFiles) writeFileSync(join(f.root, file), 'private data changed')
    const staged = await api.prepareArtifacts({ root: f.root, receiptPath: result.receiptPath, graph: f.graph, inputs: f.inputs })
    assert.deepEqual(staged.files.map(x => x.path), ['out/mini/index.js', 'out/web/index.js'])
    writeFileSync(join(f.root, 'backend/service.py'), 'app_code = 2')
    await assert.rejects(api.prepareArtifacts({ root: f.root, receiptPath: result.receiptPath, graph: f.graph, inputs: f.inputs }), /source/)
  })

  test('Kotlin compiler cache writes do not stale Android receipts while Gradle source remains fingerprinted', async t => {
    const f=fixture(t)
    mkdirSync(join(f.root,'mobile/android/.kotlin/sessions'),{recursive:true})
    const cache=join(f.root,'mobile/android/.kotlin/sessions/compiler.json'),gradle=join(f.root,'mobile/android/build.gradle')
    writeFileSync(cache,'initial compiler session');writeFileSync(gradle,'real Gradle source v1')
    const graph={shared:f.graph.shared,'android:build':{deps:['shared'],command:{bin:'node',args:['android'],cwd:'.'},artifacts:[{path:'out/android',fresh:true}]}}
    const result=await api.runPipeline({...f,graph,inputs:['mobile'],targets:['android'],runner:async command=>{
      if(command.args[0]==='android'){writeFileSync(cache,'compiler cache changed during build');f.writeArtifact('android')}
      return{status:0}
    }})
    assert.equal(result.receipt.status,'passed','Generated Kotlin cache must not count as changed source')
    writeFileSync(cache,'another transient compiler session')
    await api.prepareArtifacts({root:f.root,receiptPath:result.receiptPath,graph,inputs:['mobile']})
    writeFileSync(gradle,'real Gradle source v2')
    await assert.rejects(api.prepareArtifacts({root:f.root,receiptPath:result.receiptPath,graph,inputs:['mobile']}),/source/)
  })

  test('editing an executed shared test or release metadata check invalidates build evidence', async t => {
    for (const changed of ['scripts/test-public-draft-scope.mjs', 'scripts/test-client-ai-contracts.mjs', 'scripts/test-regional-contracts.mjs', 'scripts/test-official-collector.mjs', 'scripts/test-digital-service-config.mjs', 'scripts/test-regional-online-link.mjs', 'scripts/sync-client-release.mjs', 'desktop/start.html', 'desktop/preload.cjs', 'scripts/test-digital-chat-privacy.cjs', 'scripts/react-mount-fixture/package-lock.json', 'ChatVRM/src/pages/index.tsx']) {
      const f = fixture(t)
      for (const directory of ['scripts', 'packages', 'backend', 'config', 'data/public-regions', 'frontend', 'miniprogram', 'desktop', 'scripts/react-mount-fixture', 'ChatVRM/src/pages']) mkdirSync(join(f.root, directory), { recursive: true })
      writeFileSync(join(f.root,'desktop/start.html'),'<p>initial desktop start page</p>')
      writeFileSync(join(f.root,'desktop/preload.cjs'),'// initial actual desktop bridge')
      for (const name of ['scripts/react-mount-fixture/package.json', 'scripts/react-mount-fixture/package-lock.json', 'ChatVRM/src/pages/index.tsx']) writeFileSync(join(f.root,name),'{}')
      writeFileSync(join(f.root,'scripts/test-digital-chat-privacy.cjs'),'// initial digital privacy check')
      for (const file of ['test-assistant-session.mjs','test-chat-privacy.mjs','test-auth-session.mjs','test-auth-flows.mjs','test-server-workspace.mjs','test-service-address.mjs','client-pipeline.mjs', 'build-api-contracts.mjs', 'build-regional-contracts.mjs', 'build-client-contracts.mjs', 'test-client-ai-contracts.mjs', 'test-regional-contracts.mjs', 'sync-client-release.mjs', 'test-stable-api-types.mjs','test-client-catalog-sync.mjs','test-api-base.mjs','sync-document-clients.mjs']) writeFileSync(join(f.root, 'scripts', file), '// initial check body')
      for(const name of ['frontend/package.json','frontend/package-lock.json'])writeFileSync(join(f.root,name),'{}')
      for(const name of ['test-public-draft-scope.mjs','test-official-collector.mjs','test-digital-service-config.mjs','test-regional-online-link.mjs'])writeFileSync(join(f.root,'scripts',name),'// initial overnight check')
      const result = await api.runPipeline({ ...f, inputs: undefined, runner: async command => {
        if (command.args[0] !== 'shared') f.writeArtifact(command.args[0])
        return { status: 0 }
      } })
      assert.equal(result.receipt.status, 'passed')
      writeFileSync(join(f.root, changed), '// changed check body')
      await assert.rejects(api.prepareArtifacts({ root: f.root, receiptPath: result.receiptPath, graph: f.graph }), /source/, changed)
    }
  })

  test('the default graph checks release metadata once before client checks', async t => {
    const f = fixture(t)
    const result = await api.runPipeline({ root: f.root, action: 'check', dryRun: true, targets: ['web', 'mini'] })
    const checks = result.receipt.steps.filter(step => step.command?.args[0] === 'scripts/sync-client-release.mjs')
    assert.equal(checks.length, 1)
    assert.deepEqual(checks[0].command.args, ['scripts/sync-client-release.mjs', '--check'])
    assert(result.receipt.steps.findIndex(step => step.id === checks[0].id) < result.receipt.steps.findIndex(step => step.id === 'web:check'))
  })

  test('every client runs session, account flow, isolation and service address checks first', async t => {
    const f=fixture(t)
    const result=await api.runPipeline({root:f.root,action:'check',dryRun:true,targets:['web','mini']})
    for(const script of ['test-assistant-session.mjs','test-chat-privacy.mjs','test-digital-chat-privacy.cjs','test-auth-session.mjs','test-auth-flows.mjs','test-server-workspace.mjs','test-service-address.mjs','test-official-collector.mjs','test-digital-service-config.mjs','test-regional-online-link.mjs']){
      const matches=result.receipt.steps.filter(step=>step.command?.args[0]===`scripts/${script}`)
      assert.equal(matches.length,1,script)
      assert(result.receipt.steps.indexOf(matches[0])<result.receipt.steps.findIndex(step=>step.id==='mini:check'))
    }
  })

  test('release Android command rebuilds Gradle outputs rather than attesting an up-to-date old APK', t => {
    const f=fixture(t),command=api.createGraph(f.root,['android'])['android:build'].command
    assert.deepEqual(command.args.slice(-2),['--','--rerun-tasks'],'The forced rebuild flag must reach Gradle through npm run')
  })

  test('unchanged static source copies keep old mtimes and carry independently checked source evidence', async t => {
    const f = fixture(t)
    f.targets = ['web']
    f.graph['web:build'].artifacts[0].staticRoot = 'src/public'
    mkdirSync(join(f.root, 'src/public/brand'), { recursive: true })
    writeFileSync(join(f.root, 'src/public/brand/mark.svg'), '<svg>fixture mark</svg>')
    utimesSync(join(f.root, 'src/public/brand/mark.svg'), new Date(0), new Date(0))
    const result = await api.runPipeline({ ...f, runner: async command => {
      if (command.args[0] === 'web') {
        f.writeArtifact('web')
        mkdirSync(join(f.root, 'out/web/brand'))
        writeFileSync(join(f.root, 'out/web/brand/mark.svg'), '<svg>fixture mark</svg>')
        utimesSync(join(f.root, 'out/web/brand/mark.svg'), new Date(0), new Date(0))
      }
      return { status: 0 }
    } })
    assert.equal(result.receipt.status, 'passed')
    const copied = result.receipt.artifacts.find(file => file.path === 'out/web/brand/mark.svg')
    assert.equal(copied.staticCopy, true)
    assert.equal(copied.sourcePath, 'src/public/brand/mark.svg')
    assert.equal(copied.observedMtimeMs, 0)
    assert.equal(copied.reused, false)
    const staged = await api.prepareArtifacts({ root: f.root, receiptPath: result.receiptPath, graph: f.graph, inputs: f.inputs })
    assert.equal(staged.files.find(file => file.path === copied.path).sourcePath, copied.sourcePath)
    copied.sourcePath = 'src/public/other.svg'
    writeFileSync(result.receiptPath, JSON.stringify(result.receipt))
    await assert.rejects(api.prepareArtifacts({ root: f.root, receiptPath: result.receiptPath, graph: f.graph, inputs: f.inputs }), /static|source/i)
  })

  test('static copy evidence cannot bless mismatched assets, stale compiled code, or sources outside the snapshot', async t => {
    for (const state of ['mismatch', 'compiled', 'unfingerprinted']) {
      const f = fixture(t)
      f.targets = ['web']
      f.graph['web:build'].artifacts[0].staticRoot = 'src/public'
      mkdirSync(join(f.root, 'src/public'))
      writeFileSync(join(f.root, 'src/public/mark.svg'), '<svg>fixture mark</svg>')
      if (state === 'unfingerprinted') f.inputs = ['src/input.txt']
      const result = await api.runPipeline({ ...f, runner: async command => {
        if (command.args[0] === 'web') {
          f.writeArtifact('web')
          writeFileSync(join(f.root, 'out/web/mark.svg'), state === 'mismatch' ? '<svg>wrong</svg>' : '<svg>fixture mark</svg>')
          utimesSync(join(f.root, 'out/web/mark.svg'), new Date(0), new Date(0))
          if (state === 'compiled') utimesSync(join(f.root, 'out/web/index.js'), new Date(0), new Date(0))
        }
        return { status: 0 }
      } })
      assert.equal(result.receipt.status, 'failed', state)
      assert.match(result.receipt.steps.at(-1).error, /Stale artifact/)
    }
  })

  test('desktop source icons under build are fingerprinted, not treated as generated output', async t => {
    const f=fixture(t)
    mkdirSync(join(f.root,'desktop/build'),{recursive:true})
    writeFileSync(join(f.root,'desktop/build/icon.ico'),'icon version one')
    f.inputs=['src','desktop']
    const result=await api.runPipeline({...f,runner:async command=>{if(command.args[0]!=='shared')f.writeArtifact(command.args[0]);return {status:0}}})
    assert.equal(result.receipt.status,'passed')
    writeFileSync(join(f.root,'desktop/build/icon.ico'),'icon version two')
    await assert.rejects(api.prepareArtifacts({root:f.root,receiptPath:result.receiptPath,graph:f.graph,inputs:f.inputs}),/source/)
  })
}
