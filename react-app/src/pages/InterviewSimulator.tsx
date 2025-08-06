// src/pages/InterviewSimulator.tsx
import React, { useState, useEffect, useCallback } from 'react';
import { setupInterview } from '../api/interviewSetup';
import { generateFeedback } from '../api/finalFeedback';
import { getJobCategories } from '../api/jobCategories';
import { InterviewSetupResponse, FinalFeedbackResponse } from '../api/types';

import AudioRecorder from '../components/AudioRecorder';
import PoseTracker from '../components/PoseTracker';
import VoiceLevelMeter from '../components/VoiceLevelMeter';

export interface AudioAnalysisResult {
  text: string;
  emotion: string;
  probabilities: Record<string, number>;
}
const InterviewSimulator: React.FC = () => {
  // 설정
  const [jobCategories, setJobCategories] = useState<string[]>([]);
  const [selectedJob, setSelectedJob] = useState('');
  const [numQuestions, setNumQuestions] = useState(3);

  // 면접 상태
  const [interviewSession, setInterviewSession] = useState<InterviewSetupResponse | null>(null);
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [isRecording, setIsRecording] = useState(false);
  const [chatMessages, setChatMessages] = useState<Array<{ type: 'question' | 'answer'; text: string; number: number; timestamp: string }>>([]);
  const [step, setStep] = useState<'setup' | 'interview' | 'results'>('setup');
  const [isInterviewComplete, setIsInterviewComplete] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  // 카메라 & 오디오 분석 결과
  const [cameraOn, setCameraOn] = useState(false);
  const [voiceResult, setVoiceResult] = useState('분석 대기 중');
  const [audioAnalysisResult, setAudioAnalysisResult] = useState<AudioAnalysisResult | null>(null);

  const token1 = localStorage.getItem('access_token') ?? '';

  // 직무 불러오기
  useEffect(() => {
    (async () => {
      try {
        const data = await getJobCategories();
        setJobCategories(data.categories);
        setSelectedJob(data.categories[0] || '');
      } catch {
        alert('직무 카테고리를 불러오지 못했습니다.');
      }
    })();
  }, []);

  const addMessageToChat = useCallback((type: 'question' | 'answer', text: string, number: number) => {
    const timestamp = new Date().toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' });
    setChatMessages(prev => [...prev, { type, text, number, timestamp }]);
  }, []);

  const startInterview = async () => {
    if (!selectedJob) return;
    setIsLoading(true);
    setCameraOn(true);

    try {
      const session = await setupInterview(selectedJob, numQuestions);
      setInterviewSession(session);
      setStep('interview');
      setCurrentQuestionIndex(0);
      setIsInterviewComplete(false);
      setChatMessages([
        { type: 'question', text: 'AI 면접을 시작합니다.', number: 0, timestamp: new Date().toLocaleTimeString('ko-KR') },
        { type: 'question', text: session.questions[0], number: 1, timestamp: new Date().toLocaleTimeString('ko-KR') }
      ]);
    } catch {
      alert('면접 시작에 실패했습니다.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleNextQuestion = () => {
    if (!interviewSession) return;
    const nextIndex = currentQuestionIndex + 1;
    if (nextIndex < interviewSession.questions.length) {
      setCurrentQuestionIndex(nextIndex);
      addMessageToChat('question', interviewSession.questions[nextIndex], nextIndex + 1);
    } else {  
      setIsInterviewComplete(true);
      setIsRecording(false);
      addMessageToChat('question', '모든 질문이 완료되었습니다.', 999);
    }
  };

  return (
    <div style={{ minHeight: '100vh', backgroundColor: '#f8f9fa' }}>
      {step === 'setup' && (
        <div style={{ maxWidth: '600px', margin: '0 auto', padding: '2rem' }}>
          <h1 style={{ textAlign: 'center', marginBottom: '2rem' }}>🤖 AI 면접 시뮬레이터</h1>
          <div style={{ marginBottom: '2rem' }}>
            <label htmlFor="job-select" style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 'bold' }}>직무 선택</label>
            <select
              id="job-select"
              value={selectedJob}
              onChange={e => setSelectedJob(e.target.value)}
              style={{ width: '100%', padding: '0.75rem', fontSize: '1rem', borderRadius: '8px', border: '2px solid #ddd' }}
            >
              {jobCategories.map(job => <option key={job} value={job}>{job}</option>)}
            </select>
          </div>
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
              onChange={e => setNumQuestions(Number(e.target.value))}
              style={{ width: '100%' }}
            />
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.9rem', color: '#666' }}>
              <span>1개</span><span>5개</span>
            </div>
          </div>
          <button
            onClick={startInterview}
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
      )}

      {step === 'interview' && interviewSession && (
        <div style={{ display: 'flex', height: '100vh' }}>
          {/* 왼쪽 패널 */}
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', borderRight: '1px solid #e0e0e0' }}>
            {/* 헤더 */}
            <div style={{ background: 'linear-gradient(45deg,#667eea,#764ba2)', color: 'white', padding: '20px', textAlign: 'center' }}>
              <h1 style={{
                margin: '0 0 10px 0', borderRadius: '12px',
                backgroundColor: '#667eea', padding: '10px 20px',
                fontSize: '24px', display: 'inline-block'
              }}>🎤 AI 면접</h1>
              <div style={{ background: 'rgba(255,255,255,0.2)', padding: '10px', borderRadius: '10px' }}>
                <div>직무: {selectedJob}</div>
              </div>
            </div>

            {/* 카메라 + 오디오 UI */}
            <div style={{
              flex: 1, padding: '30px', display: 'flex',
              flexDirection: 'column', alignItems: 'center',
              background: '#f8f9fa', gap: '1rem'
            }}>
              {cameraOn && (
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                  <div style={{ width: '640px', height: '480px' }}>
                    <PoseTracker onCameraReady={() => setCameraOn(true)} />
                  </div>
                  <div style={{
                    marginTop: '1rem', padding: '1rem',
                    backgroundColor: '#f9f9f9', borderRadius: '10px',
                    width: '640px', boxShadow: '0 2px 5px rgba(0,0,0,0.1)'
                  }}>
                    <VoiceLevelMeter
                      isRecording={isRecording}
                      userId="admin"
                      token={token1}
                      onResult={result => {
                        setVoiceResult(result.text);
                        setAudioAnalysisResult(result);
                        addMessageToChat('answer', result.text, currentQuestionIndex + 1);
                        handleNextQuestion();
                      }}
                    />
                    <button
                      onClick={() => setIsRecording(!isRecording)}
                      style={{
                        marginTop: '1rem', padding: '0.5rem 1.5rem',
                        fontSize: '1rem', backgroundColor: isRecording ? '#dc3545' : '#28a745',
                        color: 'white', border: 'none', borderRadius: '5px',
                        cursor: 'pointer', width: '100%'
                      }}
                    >
                      {isRecording ? '응답 종료' : '응답 시작'}
                    </button>

                    <div style={{ marginTop: '1rem', padding: '1rem', backgroundColor: '#fff', border: '1px solid #ccc', borderRadius: '8px' }}>
                      <strong>🎧 전사된 텍스트:</strong><br />
                      {voiceResult}
                    </div>

                    {audioAnalysisResult && (
                      <div style={{
                        marginTop: '1rem', padding: '1rem',
                        backgroundColor: '#eef', border: '1px solid #99c',
                        borderRadius: '8px', fontFamily: 'monospace',
                        fontSize: '0.85rem', whiteSpace: 'pre-wrap',
                        maxHeight: '150px', overflowY: 'auto'
                      }}>
                        <strong>🔍 전체 분석 결과:</strong><br/>
                        {JSON.stringify(audioAnalysisResult, null, 2)}
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* 오른쪽 채팅 패널 */}
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
        </div>
      )}
    </div>
  );
};

export default InterviewSimulator;
