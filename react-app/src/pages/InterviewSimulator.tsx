import React, { useState } from 'react';
import { useInterviewState } from '../hooks/useInterviewState';
import InterviewSetup from '../components/InterviewSetup';
import InterviewPanel from '../components/InterviewPanel';
import ChatPanel from '../components/ChatPanel';

export interface AudioAnalysisResult {
  text: string;
  emotion: string;
  probabilities: Record<string, number>;
}

const InterviewSimulator: React.FC = () => {
  const {
    numQuestions,
    setNumQuestions,
    interviewSession,
    currentQuestionIndex,
    chatMessages,
    step,
    isInterviewComplete,
    isLoading,
    startInterview,
    handleNextQuestion,
    
    addMessageToChat,
    setSelectedJob,
    selectedJob,
    jobUrl,            // ✅ 가져옴
    setJobUrl,         // ✅ 가져옴
  } = useInterviewState();

  const [isRecording, setIsRecording] = useState(false);
  const [cameraOn, setCameraOn] = useState(false);
  const [voiceResult, setVoiceResult] = useState('분석 대기 중');
  const [audioAnalysisResult, setAudioAnalysisResult] = useState<AudioAnalysisResult | null>(null);
  const token1 = localStorage.getItem('access_token') ?? '';
  const currentQuestion = interviewSession?.questions[currentQuestionIndex] ?? '';
  const interviewId = interviewSession?.interview_id;

  return (
    <div style={{ minHeight: '100vh', backgroundColor: '#f8f9fa' }}>
      {step === 'setup' && (
        <InterviewSetup
          jobUrl={jobUrl}
          onJobUrlChange={setJobUrl}
          selectedJob={selectedJob}
          onSelectJob={setSelectedJob}
          numQuestions={numQuestions}
          onChangeNum={setNumQuestions}
          onStart={() => {
            setCameraOn(true);
            startInterview();
          }}
          isLoading={isLoading}
        />
      )}

      {step === 'interview' && interviewSession && (
        <div style={{ display: 'flex', height: '100vh' }}>
          <InterviewPanel
            isRecording={isRecording}
            setIsRecording={setIsRecording}
            token={token1}
            userId="admin"
            interviewId={interviewId ?? ''}
            cameraOn={cameraOn}
            selectedJob={selectedJob}
            voiceResult={voiceResult}
            currentQuestion={currentQuestion}
            audioAnalysisResult={audioAnalysisResult}
            onResult={(result: AudioAnalysisResult) => {
              setVoiceResult(result.text);
              setAudioAnalysisResult(result);
              addMessageToChat('answer', result.text, currentQuestionIndex + 1);
              handleNextQuestion();
            }}
            onCameraReady={() => setCameraOn(true)}
          />
          <ChatPanel chatMessages={chatMessages} />
        </div>
      )}
    </div>
  );
};

export default InterviewSimulator;
