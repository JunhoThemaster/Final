import React from 'react';

export default function AnalysisSidebar({ result }: { result: any }) {
  return (
    <div style={{ marginTop: '1rem', padding: '1rem', backgroundColor: '#eef', border: '1px solid #99c', borderRadius: '8px', fontFamily: 'monospace', fontSize: '0.85rem', whiteSpace: 'pre-wrap', maxHeight: '150px', overflowY: 'auto' }}>
      <strong>🔍 전체 분석 결과:</strong><br />{JSON.stringify(result, null, 2)}
    </div>
  );
}