// EmotionBarChart.tsx
import React from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  LabelList,
} from 'recharts';

interface EmotionBarChartProps {
  data: Record<string, number>;
}

const metricLabelMap: Record<string, string> = {
  confidence: "감정 인식 신뢰도",
  blink_count: "눈 깜빡임 횟수",
  gaze_x: "시선 좌우 위치",
  gaze_y: "시선 상하 위치",
  ear: "눈 떠짐 정도",
  head_x: "머리 좌우 회전",
  head_y: "머리 상하 기울기",
  head_z: "머리 좌우 기울기",
};

const EmotionBarChart: React.FC<EmotionBarChartProps> = ({ data }) => {
  const chartData = Object.entries(data).map(([emotion, value]) => ({
    emotion: metricLabelMap[emotion] || emotion,  // ✅ 한글로 변환
    percentage: parseFloat((value * 100).toFixed(1)),
  }));

  return (
    <div style={{ width: '100%', height: 300 }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          layout="vertical"
          data={chartData}
          margin={{ top: 20, right: 30, left: 40, bottom: 20 }}
        >
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis type="number" domain={[0, 100]} unit="%" />
          <YAxis type="category" dataKey="emotion" width={150} /> {/* 넓이 조금 넓힘 */}
          <Tooltip />
          <Bar dataKey="percentage" fill="#8884d8">
            <LabelList dataKey="percentage" position="right" />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
};

export default EmotionBarChart;
