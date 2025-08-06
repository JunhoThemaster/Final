import React from 'react';
import { ChatMessage } from '../hooks/useInterviewState';

interface Props {
  chatMessages: ChatMessage[];
}

const ChatPanel: React.FC<Props> = ({ chatMessages }) => {
  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', background: '#f0f4f8' }}>
      <div style={{ background: 'white', padding: '20px', borderBottom: '1px solid #e0e0e0', textAlign: 'center' }}>
        <h2 style={{ margin: 0, color: '#333', fontSize: '20px' }}>💬 면접 대화</h2>
      </div>
      <div style={{ flex: 1, padding: '20px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '15px' }}>
        {chatMessages.map((m, i) => (
          <div
            key={i}
            style={{
              alignSelf: m.type === 'question' ? 'flex-start' : 'flex-end',
              background: m.type === 'question' ? '#fff' : '#667eea',
              color: m.type === 'question' ? '#000' : '#fff',
              padding: '10px 15px', borderRadius: '15px', maxWidth: '80%'
            }}
          >
            {m.text}
            <div style={{ fontSize: '11px', opacity: 0.6, marginTop: '5px', textAlign: 'right' }}>{m.timestamp}</div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default ChatPanel;
