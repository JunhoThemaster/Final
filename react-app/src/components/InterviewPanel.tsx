import React from 'react';
import PoseTracker from './PoseTracker';
import VoiceLevelMeter from './VoiceLevelMeter';
interface AudioAnalysisResult {
  text: string;
  emotion: string;
  probabilities: Record<string, number>;
}
interface Props {
  isRecording: boolean;
  setIsRecording: (value: boolean) => void;
  token: string;
  userId: string;
  cameraOn: boolean;
  selectedJob: string;
  voiceResult: string;
  interviewId: string;
  audioAnalysisResult: AudioAnalysisResult | null;
  onResult: (result: AudioAnalysisResult) => void;
  onCameraReady: () => void;
  currentQuestion: string;
}

const InterviewPanel: React.FC<Props> = ({
  isRecording,
  setIsRecording,
  token,
  userId,
  cameraOn,
  selectedJob,
  interviewId,
  voiceResult,
  audioAnalysisResult,
  onResult,
  onCameraReady,
  currentQuestion,
}) => {
  return (
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
              <PoseTracker onCameraReady={onCameraReady} />
            </div>
            <div style={{
              marginTop: '1rem', padding: '1rem',
              backgroundColor: '#f9f9f9', borderRadius: '10px',
              width: '640px', boxShadow: '0 2px 5px rgba(0,0,0,0.1)'
            }}>
              <VoiceLevelMeter
                interviewId={interviewId}
                isRecording={isRecording}
                currentQuestion={currentQuestion}
                userId={userId}
                token={token}
                onResult={onResult}
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
                  <strong>🔍 전체 분석 결과:</strong><br />
                  {JSON.stringify(audioAnalysisResult, null, 2)}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default InterviewPanel;
