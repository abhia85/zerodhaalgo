
import React from 'react';
import { Line } from 'react-chartjs-2';
import 'chart.js/auto';

export default function EquityChart({ equity }) {
  const data = {
    labels: equity.map((_, i) => i+1),
    datasets: [
      {
        label: 'Equity',
        data: equity,
        fill: false,
        tension: 0.2,
      },
    ],
  };
  return <div style={{width:'100%', height:300}}><Line data={data} /></div>;
}
