
import React, {useState, useEffect} from 'react'
import Navbar from './components/Navbar'
import Dashboard from './components/Dashboard'
import BacktestPanel from './components/BacktestPanel'
import StrategyBuilder from './components/StrategyBuilder'
import LiveTrading from './components/LiveTrading'
import TradeJournal from './components/TradeJournal'
import EquityChart from './components/EquityChart'
import axios from 'axios'

export default function App(){
  const [page, setPage] = useState('dashboard')
  const [lastBacktest, setLastBacktest] = useState(null)

  // Listen to custom event from BacktestPanel for results (simple approach)
  useEffect(()=>{
    window.addEventListener('backtestResult', (e)=> setLastBacktest(e.detail))
    return ()=> window.removeEventListener('backtestResult', ()=>{})
  },[])

  return (
    <div style={{minHeight:'100vh', padding:20}}>
      <Navbar onNavigate={setPage} />
      <main style={{marginTop:20}}>
        {page==='dashboard' && (
          <div style={{display:'grid', gridTemplateColumns:'1fr 2fr', gap:12}}>
            <div>
              <StrategyBuilder />
              <LiveTrading />
              <TradeJournal />
            </div>
            <div>
              {lastBacktest ? <EquityChart equity={lastBacktest.equity_curve} /> : <Dashboard />}
            </div>
          </div>
        )}
        {page==='backtest' && <BacktestPanel />}
        {page==='strategy' && <StrategyBuilder />}
        {page==='live' && <LiveTrading />}
      </main>
    </div>
  )
}
