import React from 'react';

interface Props {
  jobUrl: string;
  onJobUrlChange: (url: string) => void;

  selectedJob: string;
  onSelectJob: (job: string) => void;

  numQuestions: number;
  onChangeNum: (value: number) => void;

  onStart: () => void;
  isLoading: boolean;
}

const InterviewSetup: React.FC<Props> = ({
  jobUrl,
  onJobUrlChange,
  selectedJob,
  onSelectJob,
  numQuestions,
  onChangeNum,
  onStart,
  isLoading
}) => {
  return (
    <div style={{ maxWidth: '600px', margin: '0 auto', padding: '2rem' }}>
      <h1 style={{ textAlign: 'center', marginBottom: '2rem' }}>🤖 AI 면접 시뮬레이터</h1>

      {/* 채용공고 주소 입력 */}
      <div style={{ marginBottom: '2rem' }}>
        <label htmlFor="job-url" style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 'bold' }}>
          채용공고 주소
        </label>
        <input
          id="job-url"
          type="text"
          value={jobUrl}
          onChange={e => onJobUrlChange(e.target.value)}
          placeholder="https://example.com/job/..."
          style={{ width: '100%', padding: '0.75rem', fontSize: '1rem', borderRadius: '8px', border: '2px solid #ddd' }}
        />
      </div>

      {/* 지원 직무 입력 */}
      <div style={{ marginBottom: '2rem' }}>
        <label htmlFor="job-name" style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 'bold' }}>
          지원 직무
        </label>
        <input
          id="job-name"
          type="text"
          value={selectedJob}
          onChange={e => onSelectJob(e.target.value)}
          placeholder="예: 백엔드 개발자"
          style={{ width: '100%', padding: '0.75rem', fontSize: '1rem', borderRadius: '8px', border: '2px solid #ddd' }}
        />
      </div>

      {/* 질문 개수 슬라이더 */}
      <div style={{ marginBottom: '2rem' }}>
        <label htmlFor="num-questions" style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 'bold' }}>
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
      </div>

      {/* 면접 시작 버튼 */}
      <button
        onClick={onStart}
        disabled={isLoading}
        style={{
          width: '100%', padding: '1rem', fontSize: '1.1rem',
          backgroundColor: '#007bff', color: 'white', border: 'none',
          borderRadius: '8px', cursor: 'pointer', opacity: isLoading ? 0.6 : 1
        }}
      >
        {isLoading ? '준비 중...' : '면접 시작'}
      </button>
    </div>
  );
};

export default InterviewSetup;
