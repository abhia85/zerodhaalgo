
import React, {useEffect, useState} from 'react'
import axios from 'axios'

export default function TradeJournal(){
  const [trades, setTrades] = useState([])
  useEffect(()=>{ fetchTrades() }, [])
  async function fetchTrades(){
    try{
      const res = await axios.get('/api/trades')
      setTrades(res.data)
    }catch(e){
      console.error(e)
    }
  }
  return (
    <div className="card">
      <h3>Trade Journal</h3>
      <table style={{width:'100%', borderCollapse:'collapse'}}>
        <thead><tr><th>Entry</th><th>Symbol</th><th>Side</th><th>Qty</th><th>PnL</th></tr></thead>
        <tbody>
          {trades.map(t=>(
            <tr key={t.id}>
              <td>{new Date(t.created_at).toLocaleString()}</td>
              <td>{t.symbol}</td>
              <td>{t.side}</td>
              <td>{t.qty}</td>
              <td>{t.pnl ?? '-'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
