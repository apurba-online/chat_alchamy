import { Bar, Line, Pie } from 'react-chartjs-2';
import { Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, BarElement, ArcElement, Title, Tooltip, Legend } from 'chart.js';
import type { ChartData } from '../types';
ChartJS.register(CategoryScale,LinearScale,PointElement,LineElement,BarElement,ArcElement,Title,Tooltip,Legend);
export function DataVisualization({data}:{data:ChartData}){const chart={labels:data.labels,datasets:data.datasets};const options={responsive:true,maintainAspectRatio:false,plugins:{legend:{position:'top' as const},title:{display:!!data.title,text:data.title}}};return <div className="h-[360px] w-full rounded-xl border border-gray-100 bg-white p-4 dark:border-gray-700 dark:bg-gray-800">{data.type==='line'?<Line data={chart} options={options}/>:data.type==='pie'?<Pie data={chart} options={options}/>:<Bar data={chart} options={options}/>}</div>}
