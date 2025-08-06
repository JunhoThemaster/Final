import React from 'react';

interface AudioVisualizerProps {
  audioLevel: number;
}

const AudioVisualizer: React.FC<AudioVisualizerProps> = ({ audioLevel }) => (
  <div style={{ display: 'flex', alignItems: 'center', gap: '3px', height: '40px', justifyContent: 'center', marginBottom: '10px' }}>
    {Array.from({ length: 20 }, (_, i) => (
      <div
        key={i}
        style={{
          width: '4px',
          height: `${Math.max(4, (audioLevel / 100) * 40 * (0.5 + Math.random() * 0.5))}px`,
          background: audioLevel > 10 ? `linear-gradient(to top, #4caf50, #8bc34a)` : '#e0e0e0',
          borderRadius: '2px',
          transition: 'height 0.1s ease',
          animation: audioLevel > 10 ? 'audio-wave 0.5s ease-in-out infinite alternate' : 'none',
          animationDelay: `${i * 0.05}s`
        }}
      />
    ))}
  </div>
);

export default AudioVisualizer;