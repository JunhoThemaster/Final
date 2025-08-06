import React from 'react';

interface Props {
  jobRoleText: string;                          // ✅ 직무 텍스트 입력
  onChangeJobRoleText: (text: string) => void;
  jobPostUrl: string;                           // ✅ 채용공고 URL
  onChangeJobPostUrl: (url: string) => void;
  numQuestions: number;
  onChangeNum: (n: number) => void;
  onStart: () => void;
  isLoading: boolean;
}

export default function SetupPanel({
  jobRoleText,
  onChangeJobRoleText,
  jobPostUrl,
  onChangeJobPostUrl,
  numQuestions,
  onChangeNum,  
  onStart,
  isLoading,
}: Props) {
  return (
    <div style={{ maxWidth: '600px', margin: '0 auto', padding: '2rem' }}>
      <h1 style={{ textAlign: 'center', marginBottom: '2rem' }}>🤖 AI 면접 시뮬레이터</h1>

      {/* ✅ 1. 직무 설명 입력 */}
      <label htmlFor="job-role" style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 'bold' }}>
        직무 또는 간단한 역할 설명
      </label>
      <input
        type="text"
        id="job-role"
        value={jobRoleText}
        onChange={e => onChangeJobRoleText(e.target.value)}
        placeholder="예: 백엔드 개발자, 데이터 분석, 서비스 기획 등"
        style={{ width: '100%', padding: '0.75rem', marginBottom: '1.5rem', fontSize: '1rem', borderRadius: '8px', border: '2px solid #ddd' }}
      />

      {/* ✅ 2. 채용공고 URL 입력 */}
      <label htmlFor="job-url" style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 'bold' }}>
        채용공고 URL (선택)
      </label>
      <input
        type="text"
        id="job-url"
        value={jobPostUrl}
        onChange={e => onChangeJobPostUrl(e.target.value)}
        placeholder="https://example.com/job/123"
        style={{ width: '100%', padding: '0.75rem', marginBottom: '1.5rem', fontSize: '1rem', borderRadius: '8px', border: '2px solid #ddd' }}
      />

      {/* ✅ 3. 질문 개수 슬라이더 */}
      <label htmlFor="num-questions" style={{ display: 'block', margin: '1.5rem 0 0.5rem', fontWeight: 'bold' }}>
        질문 개수: {numQuestions}개
      </label>
      <input
        id="num-questions"
        type="range"
        min={1}
        max={5}
        value={numQuestions}
        onChange={e => onChangeNum(Number(e.target.value))}
        style={{ width: '100%' }}
      />
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.9rem', color: '#666' }}>
        <span>1개</span><span>5개</span>
      </div>

      {/* ✅ 4. 시작 버튼 */}
      <button
        onClick={onStart}
        disabled={isLoading}
        style={{
          width: '100%',
          padding: '1rem',
          fontSize: '1.1rem',
          backgroundColor: '#007bff',
          color: 'white',
          border: 'none',
          borderRadius: '8px',
          cursor: 'pointer',
          opacity: isLoading ? 0.6 : 1,
          marginTop: '1rem'
        }}
      >
        {isLoading ? '준비 중...' : '면접 시작'}
      </button>
    </div>
  );
}
