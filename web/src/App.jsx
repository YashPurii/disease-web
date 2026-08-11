import { useMemo, useState } from 'react'
import {
  Activity,
  ArrowRight,
  BadgeCheck,
  ChevronRight,
  CircleAlert,
  ExternalLink,
  FlaskConical,
  GitBranch,
  Info,
  Search,
  ShieldCheck,
  SlidersHorizontal,
  Target,
  X,
} from 'lucide-react'
import './App.css'
import appData from './data/disease-web.json'

const EDGE_LABELS = {
  approved_for: 'Approved use',
  investigational_for: 'Active trial use',
  targets: 'Drug target',
  associated_with: 'Gene-disease association',
}

const nodeCategory = (node) => node?.attributes?.node_category ?? node?.kind ?? 'unknown'
const citationUrl = (edge) => edge?.citation?.url

function findShortestPaths(sourceId, targetId, maxPaths = 3) {
  const allowed = new Set(appData.nodes.map((node) => node.id))
  if (!allowed.has(sourceId) || !allowed.has(targetId)) return []
  const adjacency = new Map()
  appData.edges.forEach((edge) => {
    if (!allowed.has(edge.source_id) || !allowed.has(edge.target_id)) return
    ;[[edge.source_id, edge.target_id], [edge.target_id, edge.source_id]].forEach(([from, to]) => {
      if (!adjacency.has(from)) adjacency.set(from, [])
      adjacency.get(from).push(to)
    })
  })
  const distance = new Map([[sourceId, 0]])
  const parents = new Map()
  const queue = [sourceId]
  for (let pointer = 0; pointer < queue.length; pointer += 1) {
    const current = queue[pointer]
    for (const next of adjacency.get(current) ?? []) {
      if (!distance.has(next)) {
        distance.set(next, distance.get(current) + 1)
        parents.set(next, [current])
        queue.push(next)
      } else if (distance.get(next) === distance.get(current) + 1) {
        parents.get(next).push(current)
      }
    }
  }
  if (!distance.has(targetId)) return []
  const build = (id) => {
    if (id === sourceId) return [[id]]
    return (parents.get(id) ?? []).flatMap((parent) => build(parent).map((path) => [...path, id]))
  }
  return build(targetId).slice(0, maxPaths)
}

function pathEdge(from, to) {
  return appData.edges.find((edge) => (
    (edge.source_id === from && edge.target_id === to) ||
    (edge.source_id === to && edge.target_id === from)
  ))
}

function NodeBadge({ node }) {
  const category = nodeCategory(node)
  return <span className={`node-badge ${category}`}>{category.replace('_', ' ')}</span>
}

function Citation({ edge, compact = false }) {
  const citation = edge?.citation ?? {}
  const id = citation.nct_id ?? (citation.setid ? `DailyMed ${citation.setid}` : edge?.source)
  if (!id) return null
  return (
    <a className={compact ? 'citation compact' : 'citation'} href={citationUrl(edge)} target="_blank" rel="noreferrer">
      <ExternalLink size={13} /> {id}
    </a>
  )
}

function Inspector({ selected, onClose }) {
  if (!selected) return null
  const isEdge = selected.type === 'edge'
  const item = selected.item
  const node = isEdge ? null : item
  return (
    <aside className="inspector" aria-label="Evidence inspector">
      <div className="inspector-head">
        <div>
          <p className="eyebrow">{isEdge ? EDGE_LABELS[item.type] ?? item.type : node.kind}</p>
          <h2>{isEdge ? `${appData.node_lookup[item.source_id]?.label} to ${appData.node_lookup[item.target_id]?.label}` : node.label}</h2>
        </div>
        <button className="icon-button" onClick={onClose} aria-label="Close inspector"><X size={18} /></button>
      </div>
      {isEdge ? (
        <div className="inspector-body">
          <NodeBadge node={{ kind: item.type, attributes: { node_category: item.type } }} />
          <p>{item.source}</p>
          <dl>
            <div><dt>Relationship</dt><dd>{EDGE_LABELS[item.type] ?? item.type}</dd></div>
            <div><dt>Confidence</dt><dd>{item.confidence ?? 'Not provided by source'}</dd></div>
            {item.attributes?.trial_arm_type && <div><dt>Trial arm</dt><dd>{item.attributes.trial_arm_type}</dd></div>}
          </dl>
          <Citation edge={item} />
        </div>
      ) : (
        <div className="inspector-body">
          <NodeBadge node={node} />
          <dl>
            <div><dt>Identifier</dt><dd className="mono">{node.id}</dd></div>
            <div><dt>Source</dt><dd>{node.attributes?.source ?? node.kind}</dd></div>
            <div><dt>Path search</dt><dd>{node.attributes?.pathfinding_default ? 'Included by default' : 'Not a default disease endpoint'}</dd></div>
          </dl>
          {node.attributes?.mesh?.url && <a className="citation" href={node.attributes.mesh.url} target="_blank" rel="noreferrer"><ExternalLink size={13} /> MeSH record</a>}
        </div>
      )}
    </aside>
  )
}

function PathExplorer({ onInspect }) {
  const diseases = appData.disease_search
  const [from, setFrom] = useState('Diabetes Mellitus, Type 2')
  const [to, setTo] = useState('Hypertension')
  const [committed, setCommitted] = useState({ from: 'Diabetes Mellitus, Type 2', to: 'Hypertension' })
  const [pathIndex, setPathIndex] = useState(0)
  const source = diseases.find((node) => node.label === committed.from)
  const target = diseases.find((node) => node.label === committed.to)
  const paths = useMemo(() => (source && target ? findShortestPaths(source.id, target.id) : []), [source, target])
  const activePath = paths[pathIndex] ?? []
  const edges = activePath.slice(1).map((nodeId, index) => pathEdge(activePath[index], nodeId))
  const connect = () => { setCommitted({ from, to }); setPathIndex(0) }

  return (
    <section className="workspace-grid">
      <div className="path-main">
        <div className="query-panel">
          <div className="query-copy">
            <p className="eyebrow">Mechanistic path explorer</p>
            <h1>Trace the evidence between diseases.</h1>
            <p>Default endpoints are resolved disease concepts only. Drug and target nodes can connect the route; unverified raw condition text cannot.</p>
          </div>
          <div className="query-controls">
            <label>From disease
              <input list="disease-options" value={from} onChange={(event) => setFrom(event.target.value)} />
            </label>
            <ArrowRight className="query-arrow" size={18} />
            <label>To disease
              <input list="disease-options" value={to} onChange={(event) => setTo(event.target.value)} />
            </label>
            <button className="primary-button" onClick={connect}><Search size={17} /> Connect</button>
            <datalist id="disease-options">{diseases.map((node) => <option key={node.id} value={node.label} />)}</datalist>
          </div>
        </div>

        <div className="path-card">
          <div className="card-header">
            <div>
              <p className="eyebrow">Result</p>
              <h2>{source && target ? `${source.label} to ${target.label}` : 'Choose two resolved diseases'}</h2>
            </div>
            {paths.length > 0 && <span className="edge-count">{activePath.length - 1} cited edges</span>}
          </div>
          {paths.length ? (
            <>
              <div className="path-track" aria-label="Shortest evidence path">
                {activePath.map((id, index) => {
                  const node = appData.node_lookup[id]
                  return <div className="path-step" key={id}>
                    <button className={`graph-node ${node.kind}`} onClick={() => onInspect({ type: 'node', item: node })}>
                      {node.kind === 'drug' ? <FlaskConical size={18} /> : node.kind === 'target' ? <Target size={18} /> : <Activity size={18} />}
                      <span>{node.label}</span>
                      <small>{node.kind}</small>
                    </button>
                    {index < activePath.length - 1 && <ChevronRight className="path-chevron" size={22} />}
                  </div>
                })}
              </div>
              <div className="edge-list">
                {edges.map((edge, index) => <button className="edge-row" key={edge.id} onClick={() => onInspect({ type: 'edge', item: edge })}>
                  <span className="edge-marker">{index + 1}</span>
                  <span><strong>{EDGE_LABELS[edge.type]}</strong><small>{edge.source}</small></span>
                  <Citation edge={edge} compact />
                </button>)}
              </div>
              {paths.length > 1 && <div className="path-switcher">{paths.map((_, index) => <button key={index} className={index === pathIndex ? 'active' : ''} onClick={() => setPathIndex(index)}>Path {index + 1}</button>)}</div>}
            </>
          ) : (
            <div className="empty-path"><CircleAlert size={24} /><div><strong>No eligible path in this current graph slice.</strong><p>This could be sparse source coverage, a missing seed drug, or a genuine lack of indexed shared evidence. It is not filled with a hand-picked route.</p></div></div>
          )}
        </div>
      </div>
      <HowToRead />
    </section>
  )
}

function HowToRead() {
  return <aside className="reading-panel">
    <div className="panel-title"><Info size={17} /><span>How to read this</span></div>
    <p>Short paths are often created by high-degree drugs. They are a graph property, not a biological law and not evidence that all diseases are closely related.</p>
    <div className="mini-stat"><strong>36</strong><span>seed drugs in this slice</span></div>
    <div className="mini-stat"><strong>9</strong><span>audited active signals</span></div>
    <div className="source-list"><span>Sources</span><p>FDA Orange Book, DailyMed, ClinicalTrials.gov, Open Targets, RxNorm/RxClass, MeSH.</p></div>
  </aside>
}

function SignalQueue({ onInspect }) {
  const [filter, setFilter] = useState('all')
  const [query, setQuery] = useState('')
  const signals = appData.signals.filter((signal) => {
    const categoryMatch = filter === 'all' || signal.investigational_use_category === filter
    const text = `${signal.drug} ${signal.approved_use} ${signal.investigational_use}`.toLowerCase()
    return categoryMatch && text.includes(query.toLowerCase())
  })
  return <section className="signals-view">
    <div className="signals-intro">
      <div><p className="eyebrow">Active repurposing screen</p><h1>Verified signals, ready for expert review.</h1><p>Each row has an approved-use anchor, active trial evidence, a full approved-label overlap check, and a visible arm type.</p></div>
      <div className="audit-chip"><ShieldCheck size={18} /><span>9/9 complete label audits</span></div>
    </div>
    <div className="signals-toolbar">
      <label className="search-box"><Search size={16} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Filter drug or condition" /></label>
      <div className="segmented" aria-label="Signal category"><button className={filter === 'all' ? 'selected' : ''} onClick={() => setFilter('all')}>All</button><button className={filter === 'disease' ? 'selected' : ''} onClick={() => setFilter('disease')}>Disease</button><button className={filter === 'research_condition' ? 'selected' : ''} onClick={() => setFilter('research_condition')}>Research condition</button></div>
    </div>
    <div className="signal-table" role="table">
      <div className="signal-heading" role="row"><span>Signal</span><span>Approved use</span><span>Active trial</span><span>Evidence strength</span></div>
      {signals.map((signal) => <article className="signal-row" key={`${signal.drug}-${signal.nct_id}`} role="row">
        <div className="signal-drug"><span className="score">{signal.ranking_score}</span><div><strong>{signal.drug}</strong><small>{signal.trial_arm_type === 'combination' ? `Combination: ${signal.combination_partner_drugs.join(' + ')}` : 'Single-drug trial arm'}</small></div></div>
        <div className="signal-use"><strong>{signal.approved_use}</strong><a href={signal.approved_url} target="_blank" rel="noreferrer"><ExternalLink size={13} /> DailyMed / Orange Book</a></div>
        <div className="signal-use"><strong>{signal.investigational_use}</strong><NodeBadge node={{ kind: signal.investigational_use_category, attributes: { node_category: signal.investigational_use_category } }} /><a href={signal.trial_url} target="_blank" rel="noreferrer"><ExternalLink size={13} /> {signal.nct_id}</a></div>
        <div className="signal-meta"><span className="phase">{signal.trial_phase.join(' + ').replaceAll('_', ' ')}</span><span>{signal.trial_status.replaceAll('_', ' ').toLowerCase()}</span><button className="inspect-button" onClick={() => onInspect({ type: 'signal', item: signal })}><SlidersHorizontal size={15} /> Details</button></div>
      </article>)}
    </div>
    {!signals.length && <div className="no-signals">No audited signals match this filter.</div>}
  </section>
}

function SignalInspector({ signal, onClose }) {
  if (!signal) return null
  return <aside className="inspector" aria-label="Signal evidence inspector"><div className="inspector-head"><div><p className="eyebrow">Audited signal</p><h2>{signal.drug}</h2></div><button className="icon-button" onClick={onClose} aria-label="Close inspector"><X size={18} /></button></div><div className="inspector-body"><div className="signal-flow"><span>{signal.approved_use}</span><ArrowRight size={16} /><span>{signal.investigational_use}</span></div><dl><div><dt>Score</dt><dd>{signal.ranking_score} / 64</dd></div><div><dt>Phase / status</dt><dd>{signal.trial_phase.join(', ')} / {signal.trial_status.replaceAll('_', ' ')}</dd></div><div><dt>Arm type</dt><dd>{signal.trial_arm_type}{signal.combination_partner_drugs.length ? ` (${signal.combination_partner_drugs.join(', ')})` : ''}</dd></div><div><dt>Label category</dt><dd>{signal.investigational_use_category}</dd></div></dl><a className="citation" href={signal.approved_url} target="_blank" rel="noreferrer"><ExternalLink size={13} /> {signal.approved_evidence}</a><a className="citation" href={signal.trial_url} target="_blank" rel="noreferrer"><ExternalLink size={13} /> ClinicalTrials.gov {signal.nct_id}</a><p className="anchor-note">{signal.approved_anchor_note}</p></div></aside>
}

function App() {
  const [view, setView] = useState('paths')
  const [selection, setSelection] = useState(null)
  const showInspector = (selection) => setSelection(selection)
  return <main className="app-shell">
    <header className="topbar"><div className="brand"><div className="brand-mark"><GitBranch size={18} /></div><span>Disease Web</span></div><nav><button className={view === 'paths' ? 'nav-active' : ''} onClick={() => { setView('paths'); setSelection(null) }}>Explore paths</button><button className={view === 'signals' ? 'nav-active' : ''} onClick={() => { setView('signals'); setSelection(null) }}>Verified signals <span>9</span></button></nav><div className="top-status"><BadgeCheck size={16} /> Audited slice</div></header>
    {view === 'paths' ? <PathExplorer onInspect={showInspector} /> : <SignalQueue onInspect={showInspector} />}
    <footer><span>Screening tool, not a clinical claim, investment thesis, or proof of efficacy.</span><span>Graph slice: {appData.summary.node_count} nodes / {appData.summary.edge_count} edges</span></footer>
    {selection?.type === 'signal' ? <SignalInspector signal={selection.item} onClose={() => setSelection(null)} /> : <Inspector selected={selection} onClose={() => setSelection(null)} />}
  </main>
}

export default App
