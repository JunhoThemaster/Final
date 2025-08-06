import { useState, useCallback } from 'react';
import { setupInterview } from '../api/interviewSetup';
import { InterviewSetupResponse } from '../api/types';

export interface ChatMessage {
  type: 'question' | 'answer';
  text: string;
  number: number;
  timestamp: string;
}

export const useInterviewState = () => {
  const [selectedJob, setSelectedJob] = useState('');
  const [jobUrl, setJobUrl] = useState(''); // ✅ jobUrl 상태 추가
  const [numQuestions, setNumQuestions] = useState(3);
  const [interviewSession, setInterviewSession] = useState<InterviewSetupResponse | null>(null);
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [step, setStep] = useState<'setup' | 'interview' | 'results'>('setup');
  const [isInterviewComplete, setIsInterviewComplete] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const addMessageToChat = useCallback((type: 'question' | 'answer', text: string, number: number) => {
    const timestamp = new Date().toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' });
    setChatMessages(prev => [...prev, { type, text, number, timestamp }]);
  }, []);

  const startInterview = async () => {
    if (!selectedJob || !jobUrl) {
      console.warn("🚨 selectedJob 또는 jobUrl이 비어 있음", { selectedJob, jobUrl });
      return;
    }

    setIsLoading(true);
    try {
      const session = await setupInterview(selectedJob, jobUrl, numQuestions);
      setInterviewSession(session);
      setStep('interview');
      setCurrentQuestionIndex(0);
      setIsInterviewComplete(false);
      setChatMessages([
        { type: 'question', text: 'AI 면접을 시작합니다.', number: 0, timestamp: new Date().toLocaleTimeString('ko-KR') },
        { type: 'question', text: session.questions[0], number: 1, timestamp: new Date().toLocaleTimeString('ko-KR') }
      ]);
    } catch (err) {
      alert('면접 시작에 실패했습니다.');
      console.error("❌ setupInterview 실패:", err);
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
      addMessageToChat('question', '모든 질문이 완료되었습니다.', 999);
    }
  };

  return {
    selectedJob,
    setSelectedJob,
    jobUrl,              // ✅ export
    setJobUrl,           // ✅ export
    numQuestions,
    setNumQuestions,
    interviewSession,
    step,
    isInterviewComplete,
    isLoading,
    currentQuestionIndex,
    chatMessages,
    startInterview,
    handleNextQuestion,
    addMessageToChat,
  };
};
