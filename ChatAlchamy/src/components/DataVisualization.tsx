import React from 'react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ArcElement,
} from 'chart.js';
import { Line, Bar, Pie } from 'react-chartjs-2';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend
);

interface ChartData {
  type: 'line' | 'bar' | 'pie';
  labels: string[];
  datasets: {
    label: string;
    data: number[];
    backgroundColor?: string | string[];
    borderColor?: string;
    borderWidth?: number;
  }[];
}

interface DataVisualizationProps {
  data: ChartData;
  title: string;
}

export function DataVisualization({ data, title }: DataVisualizationProps) {
  const options = {
    responsive: true,
    plugins: {
      legend: {
        position: 'top' as const,
      },
      title: {
        display: true,
        text: title,
      },
    },
  };

  const renderChart = () => {
    switch (data.type) {
      case 'line':
        return <Line options={options} data={data} />;
      case 'bar':
        return <Bar options={options} data={data} />;
      case 'pie':
        return <Pie options={options} data={data} />;
      default:
        return null;
    }
  };

  return (
    <div className="w-full max-w-3xl mx-auto p-4 bg-white rounded-lg shadow-md">
      {renderChart()}
    </div>
  );
}