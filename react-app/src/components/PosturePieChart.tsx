import React from 'react';
import { PieChart, Pie, Cell, Tooltip, Legend } from 'recharts';

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#FF6666', '#AA66CC'];

interface Props {
  data: Record<string, number>;
}

const PosturePieChart: React.FC<Props> = ({ data }) => {
  const chartData = Object.entries(data).map(([name, value]) => ({
    name,
    value: Number((value * 100).toFixed(1)) // 비율을 퍼센트로 표시
  }));

  return (
    <PieChart width={400} height={300}>
      <Pie
            data={chartData}
            cx="50%"
            cy="50%"
            outerRadius={100}
            labelLine={false}
            label={({ name, percent }: { name: string; percent?: number }) =>
                `${name} (${((percent ?? 0) * 100).toFixed(1)}%)`
            }
            dataKey="value"
            >
        {chartData.map((entry, index) => (
          <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
        ))}
      </Pie>
      <Tooltip />
      <Legend />
    </PieChart>
  );
};

export default PosturePieChart;
