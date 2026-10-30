import { createHash, randomUUID } from 'node:crypto'
import { existsSync, lstatSync, mkdirSync, readFileSync, readdirSync, realpathSync, writeFileSync } from 'node:fs'
import { delimiter, dirname, isAbsolute, join, relative, resolve, sep } from 'node:path'
import { fileURLToPath } from 'node:url'
import { spawnSync } from 'node:child_process'

const PROJECT_ROOT = fileURLToPath(new URL('../', import.meta.url))
const TARGETS = ['web', 'mini', 'android', 'desktop', 'avatar']
const RUNTIME = '.runtime/client-pipeline'
const MAX_AGE_MS = 24 * 60 * 60 * 1000
const slash = value => value.replaceAll('\\', '/')
const hash = value => createHash('sha256').update(value).digest('hex')
const json = value => JSON.stringify(value, null, 2) + '\n'
const same = (a, b) => JSON.stringify(a) === JSON.stringify(b)

// Lexical and existing-ancestor checks prevent traversal through symlinks/junctions.
function bounded(root, value) {
  if (typeof value !== 'string' || !value || isAbsolute(value) || /^[A-Za-z]:|^\\\\/.test(value)) throw new Error('Paths must be workspace relative')
  const full = resolve(root, value), rel = relative(root, full)
  if (rel === '..' || rel.startsWith('..' + sep) || isAbsolute(rel)) throw new Error('Path outside workspace bounds')
  let current = root
  for (const part of rel.split(/[\\/]/).filter(Boolean)) {
    current = join(current, part)
    if (existsSync(current) && lstatSync(current).isSymbolicLink()) throw new Error('Symlink/junction paths are not allowed')
  }
  return full
}

function filesUnder(root, item, exclude = () => false) {
  const result = []
  function visit(value) {
    if (exclude(value)) return
    const full = bounded(root, value)
    if (!existsSync(full)) throw new Error(`Missing input or artifact output: ${value}`)
    const stat = lstatSync(full)
    if (stat.isDirectory()) {
      for (const entry of readdirSync(full).sort()) visit(slash(join(value, entry)))
    } else if (stat.isFile()) result.push({ path: slash(value), bytes: stat.size, sha256: hash(readFileSync(full)), mtimeMs: stat.mtimeMs })
    else throw new Error(`Unsupported file type: ${value}`)
  }
  visit(item)
  return result
}

const excludedPrivateRuntime = value => /^backend\/(data|uploads)(\/|$)/.test(value)
  || /\.(db|sqlite|sqlite3)(-(wal|shm|journal))?$/i.test(value)

const excludedInput = value => excludedPrivateRuntime(value)
  || (!/^desktop\/build(\/|$)/.test(value) && /(^|\/)(node_modules|\.git|\.next|\.gradle|\.idea|\.runtime|dist|build|__pycache__)(\/|$)/.test(value))
  || /(^|\/)(\.env(?:\..*)?|project\.private\.config\.json|private\.config\.json)$/.test(value)
  || /\.(tsbuildinfo|pyc)$/.test(value)
  || /^mobile\/android\/app\/src\/main\/assets\/public(\/|$)/.test(value)

function sourceSnapshot(root, inputs) {
  const files=inputs.flatMap(input => filesUnder(root,input,excludedInput)).map(({mtimeMs,...file})=>file)
  return [...new Map(files.map(file=>[file.path,file])).values()].sort((a,b)=>a.path.localeCompare(b.path,'en'))
}

function defaultInputs(targets) {
  return [...new Set(['frontend', 'ChatVRM/src/pages/index.tsx', 'scripts/test-digital-chat-privacy.cjs', 'scripts/react-mount-fixture/package.json', 'scripts/react-mount-fixture/package-lock.json', 'scripts/test-assistant-session.mjs', 'scripts/test-chat-privacy.mjs', 'scripts/test-auth-session.mjs', 'scripts/test-auth-flows.mjs', 'scripts/test-server-workspace.mjs', 'scripts/test-service-address.mjs', 'scripts/test-stable-api-types.mjs', 'scripts/test-client-catalog-sync.mjs', 'scripts/test-api-base.mjs', 'scripts/sync-document-clients.mjs', 'scripts/client-pipeline.mjs', 'scripts/build-api-contracts.mjs', 'scripts/build-regional-contracts.mjs', 'scripts/build-client-contracts.mjs', 'scripts/test-client-ai-contracts.mjs', 'scripts/test-regional-contracts.mjs', 'scripts/sync-client-release.mjs', 'packages', 'backend', 'config', 'data/public-regions',
    ...(targets.includes('mini') ? ['miniprogram'] : []),
    ...(targets.includes('android') ? ['mobile'] : []),
    ...(targets.includes('desktop') ? ['desktop', 'LICENSE'] : []),
    ...(targets.includes('avatar') ? ['ChatVRM'] : []),
  ])].sort()
}

const npm = (cwd, script, skipLifecycle = false) => ({ bin: 'npm', args: [...(skipLifecycle ? ['--ignore-scripts'] : []), 'run', script], cwd })
const node = (script, ...args) => ({ bin: 'node', args: [script, ...args], cwd: '.' })

export function createGraph(root, targets) {
  const graph = {
    'release:metadata': { deps: [], command: node('scripts/sync-client-release.mjs', '--check') },
    'contracts:api': { deps: [], command: node('scripts/build-api-contracts.mjs', '--check') },
    'contracts:api-test': { deps: ['contracts:api'], command: node('scripts/test-stable-api-types.mjs') },
    'contracts:catalog-test': {deps:['contracts:api'],command:node('scripts/test-client-catalog-sync.mjs')},
    'contracts:base-test': {deps:['contracts:client'],command:node('scripts/test-api-base.mjs')},
    'contracts:regional': { deps: [], command: node('scripts/build-regional-contracts.mjs', '--check') },
    'contracts:client': { deps: [], command: node('scripts/build-client-contracts.mjs', '--check') },
    'contracts:ai-test': { deps: ['contracts:client'], command: node('scripts/test-client-ai-contracts.mjs') },
    'contracts:regional-test': { deps: ['contracts:regional'], command: node('scripts/test-regional-contracts.mjs') },
    'chat:session-test': {deps: ['contracts:client'], command: node('scripts/test-assistant-session.mjs')},
    'chat:privacy-test': {deps: ['contracts:client'], command: node('scripts/test-chat-privacy.mjs')},
    'chat:digital-privacy-test': {deps: ['contracts:client'], command: node('scripts/test-digital-chat-privacy.cjs')},
    'auth:session-test': {deps: ['contracts:client'], command: node('scripts/test-auth-session.mjs')},
    'auth:flows-test': {deps: ['contracts:client'], command: node('scripts/test-auth-flows.mjs')},
    'auth:workspace-test': {deps: ['contracts:client'], command: node('scripts/test-server-workspace.mjs')},
    'contracts:address-test': {deps: ['contracts:client'], command: node('scripts/test-service-address.mjs')},
    shared: { deps: ['chat:session-test','chat:privacy-test','chat:digital-privacy-test','auth:session-test','auth:flows-test','auth:workspace-test','contracts:address-test','release:metadata','contracts:api-test','contracts:catalog-test','contracts:base-test', 'contracts:api', 'contracts:regional', 'contracts:client', 'contracts:ai-test', 'contracts:regional-test'] },
    'web:check': { deps: ['shared'], command: npm('frontend', 'typecheck') },
    'mini:check': { deps: ['shared'], command: npm('miniprogram', 'test') },
    'android:check': { deps: ['web:check'] },
    'desktop:check': { deps: ['web:check'], command: npm('desktop', 'test') },
    'avatar:check': { deps: ['shared'], command: { bin: 'node', args: ['node_modules/typescript/bin/tsc', '--noEmit'], cwd: 'ChatVRM' } },
    'web:build': targets.includes('android')
      ? { deps: ['android:build'] }
      : { deps: ['web:check'], command: npm('frontend', 'build', true), artifacts: [{ path: 'frontend/dist', fresh: true, staticRoot: 'frontend/public', required: ['index.html'] }] },
    'mini:build': { deps: ['mini:check'], command: npm('miniprogram', 'build'), artifacts: [{ path: 'miniprogram', kind: 'mini', fresh: false, required: ['app.js', 'app.json', 'app.wxss'] }] },
    'android:build': { deps: ['android:check'], command: npm('mobile', 'android:apk', true), artifacts: [{ path: 'frontend/dist', fresh: true, staticRoot: 'frontend/public', required: ['index.html'] }, { path: 'mobile/android/app/build/outputs/apk/debug/app-debug.apk', fresh: true }] },
    'avatar:build': { deps: ['avatar:check'], command: npm('ChatVRM', 'build'), artifacts: [{ path: 'ChatVRM/.next', kind: 'next', fresh: true, required: ['BUILD_ID'] }] },
  }
  if (targets.includes('desktop')) {
    const version = JSON.parse(readFileSync(bounded(root, 'desktop/package.json'), 'utf8')).version
    if (!/^[0-9]+\.[0-9]+\.[0-9]+(?:-[a-zA-Z0-9.-]+)?$/.test(version)) throw new Error('Invalid desktop version')
    graph['desktop:build'] = { deps: ['desktop:check'], command: npm('desktop', 'dist'), artifacts: ['setup', 'portable'].map(kind => ({ path: `.runtime/releases/${version}/desktop/artifacts/LabourLawyer-${version}-windows-x64-${kind}.exe`, fresh: true })) }
  }
  return graph
}

function planSteps(root, graph, targets, action) {
  if (!targets.length || targets.some(t => !TARGETS.includes(t))) throw new Error(`Targets must be one of: ${TARGETS.join(',')}`)
  const visiting = new Set(), visited = new Set(), plan = []
  function visit(id) {
    if (visiting.has(id)) throw new Error(`Dependency cycle: ${id}`)
    if (visited.has(id)) return
    const step = graph[id]
    if (!step) throw new Error(`Missing pipeline step: ${id}`)
    if (step.command) {
      bounded(root, step.command.cwd)
      if (!['node', 'npm'].includes(step.command.bin) || !Array.isArray(step.command.args) || step.command.args.some(x => typeof x !== 'string')) throw new Error(`Invalid command: ${id}`)
    }
    for (const artifact of step.artifacts || []) {
      bounded(root, artifact.path)
      if (artifact.staticRoot) bounded(root, artifact.staticRoot)
    }
    visiting.add(id)
    for (const dep of step.deps || []) visit(dep)
    visiting.delete(id)
    visited.add(id)
    plan.push({ id, deps: step.deps || [], command: step.command || null, artifacts: step.artifacts || [] })
  }
  for (const target of [...new Set(targets)].sort((a, b) => TARGETS.indexOf(a) - TARGETS.indexOf(b))) visit(`${target}:${action}`)
  return plan
}

const contentFiles = files => files.map(({ path, bytes, sha256 }) => ({ path, bytes, sha256 }))

function artifactManifest(root, definitions, startedAt, priorFiles = [], enforceFresh = true, sourceFiles = []) {
  const result = new Map()
  const sources = new Map(sourceFiles.map(file => [file.path, file]))
  for (const definition of definitions) {
    const excluded = value => excludedPrivateRuntime(value) || (definition.kind === 'mini'
      ? /(^|\/)(node_modules|scripts|tests|types)(\/|$)/.test(value) || !(/\.(js|json|wxss|wxml|svg|png|jpe?g|webp|gif|ttf|woff2?)$/.test(value) || !/\.[^/]+$/.test(value)) || /(^|\/)(package(?:-lock)?\.json|project(?:\.private)?\.config\.json|private\.config\.json|tsconfig\.json)$/.test(value)
      : definition.kind === 'next' && /(^|\/)(cache|trace)(\/|$)/.test(value))
    const files = filesUnder(root, definition.path, excluded)
    if (!files.length || !files.some(file => file.bytes > 0)) throw new Error(`Empty artifact output: ${definition.path}`)
    for (const required of definition.required || []) {
      const expected = slash(join(definition.path, required))
      bounded(root, expected)
      if (!files.some(file => file.path === expected && file.bytes > 0)) throw new Error(`Missing required artifact output: ${expected}`)
    }
    for (const { mtimeMs, ...file } of files) {
      let sourcePath = null
      if (definition.staticRoot) {
        const candidate = slash(join(definition.staticRoot, relative(bounded(root, definition.path), bounded(root, file.path))))
        bounded(root, candidate)
        const source = sources.get(candidate)
        if (source && source.bytes === file.bytes && source.sha256 === file.sha256) sourcePath = candidate
      }
      const staticCopy = sourcePath !== null
      const stale = definition.fresh && mtimeMs < Date.parse(startedAt) - 2000
      const reused = Boolean(stale && !staticCopy && priorFiles.some(prior => prior.path === file.path && prior.bytes === file.bytes && prior.sha256 === file.sha256))
      if (enforceFresh && stale && !staticCopy && !reused) throw new Error(`Stale artifact output: ${file.path}; rebuild or supply a verified --reuse-receipt`)
      result.set(file.path, { ...file, observedMtimeMs: mtimeMs, staticCopy, sourcePath, reused })
    }
  }
  return [...result.values()].sort((a, b) => a.path.localeCompare(b.path, 'en'))
}

function npmCLI() {
  const candidates = [process.env.npm_execpath, join(dirname(process.execPath), 'node_modules/npm/bin/npm-cli.js')]
  for (const entry of (process.env.PATH || '').split(delimiter)) {
    candidates.push(join(entry, 'node_modules/npm/bin/npm-cli.js'))
    const executable = join(entry, 'npm')
    if (existsSync(executable)) candidates.push(realpathSync(executable))
  }
  const found = candidates.find(candidate => candidate && /(?:npm-cli\.js|\/npm)$/.test(slash(candidate)) && existsSync(candidate))
  if (!found) throw new Error('npm CLI was not found; install/configure Node.js and npm before running the pipeline')
  return found
}

function processRunner(root, command) {
  const args = command.bin === 'npm' ? [npmCLI(), ...command.args] : command.args
  return spawnSync(process.execPath, args, {
    cwd: bounded(root, command.cwd), env: process.env, stdio: 'inherit', windowsHide: true,
  })
}

export async function runPipeline(options = {}) {
  const root = realpathSync(resolve(options.root || PROJECT_ROOT))
  const targets = [...new Set(options.targets || ['web', 'mini', 'android', 'desktop'])]
  const action = options.action || 'check', dryRun = Boolean(options.dryRun || action === 'plan')
  const effectiveAction = action === 'plan' ? 'build' : action
  if (!['check', 'build'].includes(effectiveAction)) throw new Error('Action must be check, build, plan or artifact')
  const graph = options.graph || createGraph(root, targets)
  const plan = planSteps(root, graph, targets, effectiveAction)
  const inputs = options.inputs || defaultInputs(targets)
  for (const input of inputs) bounded(root, input)
  const runId = new Date().toISOString().replace(/[:.]/g, '-') + '-' + randomUUID().slice(0, 8)
  const receiptPath = bounded(root, `${RUNTIME}/${runId}/receipt.json`)
  const receipt = { schemaVersion: 1, runId, action: effectiveAction, dryRun, targets, inputs, startedAt: new Date().toISOString(), finishedAt: null,
    status: dryRun ? 'planned' : 'running', publishEvidence: false, planSha256: hash(JSON.stringify(plan)), sourceSha256: null, reusedFrom: null, artifacts: [],
    steps: plan.map(step => ({ ...step, status: dryRun ? 'planned' : 'pending', exitCode: null, signal: null, startedAt: null, finishedAt: null })),
  }
  mkdirSync(dirname(receiptPath), { recursive: true })
  const save = () => writeFileSync(receiptPath, json(receipt))
  if (dryRun) { receipt.finishedAt = new Date().toISOString(); save(); return { receipt, receiptPath } }
  let priorFiles = [], snapshot = []
  try {
    snapshot = sourceSnapshot(root, inputs)
    receipt.sourceSha256 = hash(JSON.stringify(snapshot))
    if (options.reuseReceiptPath) {
      const verified = verifyReceipt({ root, receiptPath: options.reuseReceiptPath, graph: options.graph, inputs })
      if (verified.receipt.sourceSha256 !== receipt.sourceSha256) throw new Error('Prior receipt source differs from this build')
      receipt.reusedFrom = slash(relative(root, verified.receiptPath))
      priorFiles = verified.receipt.artifacts
    }
  } catch (error) {
    receipt.status = 'failed'; receipt.error = error.message; receipt.finishedAt = new Date().toISOString()
    for (const step of receipt.steps) step.status = 'blocked'
    save(); return { receipt, receiptPath }
  }
  save()
  let failed = false
  const runner = options.runner || (command => processRunner(root, command))
  for (const step of receipt.steps) {
    if (failed) { step.status = 'blocked'; continue }
    step.startedAt = new Date().toISOString()
    step.status = 'running'
    save()
    try {
      if (step.command) {
        const result = await runner(step.command)
        step.exitCode = Number.isInteger(result?.status) ? result.status : null
        step.signal = result?.signal || null
        if (result?.error || step.signal || step.exitCode !== 0) throw new Error(result?.error?.message || `Command failed (${step.signal || step.exitCode || 'no exit status'})`)
      }
      if (step.artifacts.length) artifactManifest(root, step.artifacts, step.startedAt, priorFiles, true, snapshot)
      step.status = 'passed'
    } catch (error) {
      step.status = 'failed'; step.error = error.message; failed = true
    }
    step.finishedAt = new Date().toISOString()
    save()
  }
  if (!failed) {
    try {
      if (receipt.sourceSha256 !== hash(JSON.stringify(sourceSnapshot(root, inputs)))) throw new Error('Source changed during the pipeline; rerun to obtain current evidence')
      receipt.artifacts = artifactManifest(root, plan.flatMap(step => step.artifacts), receipt.startedAt, priorFiles, true, snapshot)
    } catch (error) { failed = true; receipt.error = error.message }
  }
  receipt.finishedAt = new Date().toISOString()
  receipt.status = failed ? 'failed' : 'passed'
  save()
  return { receipt, receiptPath }
}

function verifyReceipt(options = {}, seen = new Set()) {
  const root = realpathSync(resolve(options.root || PROJECT_ROOT))
  if (!options.receiptPath) throw new Error('Artifact preparation requires --receipt from a successful build')
  const receiptRelative = isAbsolute(options.receiptPath) ? relative(root, options.receiptPath) : options.receiptPath
  const receiptPath = bounded(root, slash(receiptRelative))
  if (!slash(receiptRelative).startsWith(RUNTIME + '/')) throw new Error('Receipt must be in the scoped pipeline runtime')
  if (seen.has(receiptPath) || seen.size >= 10) throw new Error('Invalid receipt reuse cycle or excessive chain')
  seen.add(receiptPath)
  const receipt = JSON.parse(readFileSync(receiptPath, 'utf8'))
  if (receipt.schemaVersion !== 1 || receipt.action !== 'build' || receipt.status !== 'passed' || receipt.dryRun || receipt.publishEvidence !== false) throw new Error('A successful build receipt is required; plans/checks are not release evidence')
  if (!same(slash(relative(root, receiptPath)), `${RUNTIME}/${receipt.runId}/receipt.json`)) throw new Error('Invalid receipt path')
  const finished = Date.parse(receipt.finishedAt), started = Date.parse(receipt.startedAt), now = Date.now()
  if (!Number.isFinite(finished) || !Number.isFinite(started) || started > finished || finished > now + 2000 || now - started > MAX_AGE_MS) throw new Error('Build receipt expired or has invalid timestamps')
  const graph = options.graph || createGraph(root, receipt.targets)
  const plan = planSteps(root, graph, receipt.targets, 'build')
  if (receipt.planSha256 !== hash(JSON.stringify(plan)) || receipt.steps.length !== plan.length) throw new Error('Receipt plan/steps differ from the current pipeline')
  for (let i = 0; i < plan.length; i++) {
    const step = receipt.steps[i], expected = plan[i]
    if (!same({ id: step.id, deps: step.deps, command: step.command, artifacts: step.artifacts }, expected) || step.status !== 'passed' || step.signal !== null || (step.command ? step.exitCode !== 0 : step.exitCode !== null)
      || !Number.isFinite(Date.parse(step.startedAt)) || !Number.isFinite(Date.parse(step.finishedAt))
      || Date.parse(step.startedAt) < started || Date.parse(step.finishedAt) > finished || Date.parse(step.finishedAt) < Date.parse(step.startedAt)) throw new Error(`Invalid or failed receipt step: ${expected.id}`)
  }
  const inputs = options.inputs || defaultInputs(receipt.targets)
  const snapshot = sourceSnapshot(root, inputs)
  if (!same(receipt.inputs, inputs) || receipt.sourceSha256 !== hash(JSON.stringify(snapshot))) throw new Error('Build source snapshot is stale; rerun the build')
  let priorFiles = []
  if (receipt.reusedFrom) priorFiles = verifyReceipt({ ...options, receiptPath: receipt.reusedFrom }, seen).receipt.artifacts
  const files = artifactManifest(root, plan.flatMap(step => step.artifacts), receipt.startedAt, [], false, snapshot)
  if (!files.length || !Array.isArray(receipt.artifacts) || !same(contentFiles(files), contentFiles(receipt.artifacts))) throw new Error('Build artifact manifest is missing or changed')
  for (const file of receipt.artifacts) {
    const step = receipt.steps.find(candidate => candidate.artifacts.some(definition => file.path === definition.path || file.path.startsWith(definition.path + '/')))
    const definition = step.artifacts.find(candidate => file.path === candidate.path || file.path.startsWith(candidate.path + '/'))
    if (typeof file.reused !== 'boolean' || !Number.isFinite(file.observedMtimeMs)) throw new Error('Invalid artifact observation metadata')
    const current = files.find(candidate => candidate.path === file.path)
    if (typeof file.staticCopy !== 'boolean' || file.staticCopy !== current.staticCopy || file.sourcePath !== current.sourcePath) throw new Error('Static source-copy evidence differs from the declared current source')
    if (file.staticCopy) {
      if (file.reused) throw new Error('Static copy cannot also claim prior-receipt reuse')
    } else if (file.reused) {
      if (!priorFiles.some(prior => same(contentFiles([prior]), contentFiles([file])))) throw new Error('Reused artifact has no matching prior successful receipt')
    } else if (definition.fresh && file.observedMtimeMs < Date.parse(step.startedAt) - 2000) throw new Error('Stale artifact observation in receipt')
  }
  return { root, receiptPath, receipt, files: receipt.artifacts }
}

export async function prepareArtifacts(options = {}) {
  const { root, receiptPath, receipt, files } = verifyReceipt(options)
  const allowlistPath = bounded(root, `${RUNTIME}/${receipt.runId}/artifact-allowlist.json`)
  const result = { schemaVersion: 1, runId: receipt.runId, buildReceipt: slash(relative(root, receiptPath)), preparedAt: new Date().toISOString(), published: false,
    evidence: 'Local build and checksum verification only; no signing, upload, device install, or store submission.', files }
  writeFileSync(allowlistPath, json(result))
  return { ...result, allowlistPath }
}

async function main() {
  const args = process.argv.slice(2), action = args.shift() || 'check'
  if (action === '--help' || action === '-h') {
    console.log('node scripts/client-pipeline.mjs check|build|plan|artifact [--targets web,mini,android,desktop,avatar] [--dry-run] [--receipt .runtime/client-pipeline/<run>/receipt.json] [--reuse-receipt <prior-build-receipt>]')
    return
  }
  const options = { action }
  while (args.length) {
    const option = args.shift()
    if (option === '--dry-run') options.dryRun = true
    else if (['--targets', '--receipt', '--reuse-receipt'].includes(option)) {
      const value = args.shift()
      if (!value || value.startsWith('--')) throw new Error(`Missing value for ${option}`)
      if (option === '--targets') options.targets = value.split(',')
      else if (option === '--receipt') options.receiptPath = value
      else options.reuseReceiptPath = value
    } else throw new Error(`Unknown option: ${option}`)
  }
  if (action === 'artifact') {
    if (options.dryRun) throw new Error('Use plan for dry-run; artifact requires a current successful build receipt')
    const result = await prepareArtifacts(options)
    console.log(`Prepared ${result.files.length} files: ${slash(relative(PROJECT_ROOT, result.allowlistPath))}; published=false`)
  } else {
    const result = await runPipeline(options)
    for (const step of result.receipt.steps) console.log(`${step.status} ${step.id}${step.command ? `: ${step.command.bin} ${step.command.args.join(' ')} (cwd=${step.command.cwd})` : ''}${step.error ? ` — ${step.error}` : ''}`)
    console.log(`${result.receipt.status}: ${slash(relative(PROJECT_ROOT, result.receiptPath))}; publishEvidence=false`)
    if (result.receipt.error) console.error(result.receipt.error)
    if (result.receipt.status === 'failed') process.exitCode = 1
  }
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) main().catch(error => { console.error(error.message); process.exitCode = 1 })
