
import React, {useState} from 'react'
import axios from 'axios'
export default function BacktestPanel(){
  const [symbol, setSymbol] = useState('RELIANCE.NS')
  const [fromTs, setFromTs] = useState('2024-01-01')
  const [toTs, setToTs] = useState('2024-12-31')
  const [interval, setInterval] = useState('1d')
  const [strategyId, setStrategyId] = useState('')
  const [result, setResult] = useState(null)

  async function run(){
    const res = await axios.post('/api/backtest', {symbol, interval, from_ts: fromTs, to_ts: toTs, strategy_id: strategyId})
    setResult(res.data)
    // dispatch a global event so App can pick it for chart display
    window.dispatchEvent(new CustomEvent('backtestResult', {detail: res.data}))
  }

  return (
    <div className="card">
      <h2>Backtest</h2>
      <div style={{display:'grid', gridTemplateColumns:'1fr 1fr', gap:8}}>
        <input value={symbol} onChange={e=>setSymbol(e.target.value)} />
        <select value={interval} onChange={e=>setInterval(e.target.value)}>
          <option>1m</option>
          <option>5m</option>
          <option>15m</option>
          <option>1d</option>
        </select>
        <input type="date" value={fromTs} onChange={e=>setFromTs(e.target.value)} />
        <input type="date" value={toTs} onChange={e=>setToTs(e.target.value)} />
        <input placeholder="strategy id" value={strategyId} onChange={e=>setStrategyId(e.target.value)} />
        <button onClick={run} style={{gridColumn:'1 / -1'}}>Run Backtest</button>
      </div>
      {result && <pre style={{marginTop:12, maxHeight:300, overflow:'auto'}}>{JSON.stringify(result, null, 2)}</pre>}
    </div>
  )
}
