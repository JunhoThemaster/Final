// AudioRecorder.tsx
// 📌 컴포넌트 전체의 역할: 마이크 권한 확인, 음성 녹음 및 음성 인식, 녹음 중지, 실시간 UI 상태 렌더링을 담당

import React, { useState, useRef, useEffect, useCallback } from 'react';
import { AudioRecorderProps } from './AudioRecorderProps'; // 🎯 props 타입 분리
import { SpeechRecognition, SpeechRecognitionErrorEvent, SpeechRecognitionEvent } from './SpeechRecognitionTypes'; // 🎯 Web Speech API 관련 타입
import AudioVisualizer from './AudioVisualizer'; // 🎯 오디오 레벨 시각화 컴포넌트

const AudioRecorder: React.FC<AudioRecorderProps> = ({
  onRecordingComplete,
  isRecording,
  onRecordingStart,
  onRecordingStop,
  continuousMode = false
}) => {
  // 🧠 상태 정의
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [recordingDuration, setRecordingDuration] = useState(0);
  const [microphoneAccess, setMicrophoneAccess] = useState<'granted' | 'denied' | 'pending'>('pending');
  const [audioLevel, setAudioLevel] = useState<number>(0);
  const [isProcessing, setIsProcessing] = useState(false);

  // 🧠 참조 정의
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const speechRecognitionRef = useRef<SpeechRecognition | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const durationTimerRef = useRef<NodeJS.Timeout | null>(null);
  const isStoppingRef = useRef<boolean>(false);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const audioLevelTimerRef = useRef<NodeJS.Timeout | null>(null);

  // ✅ 권한 확인 함수
  const checkMicrophonePermission = useCallback(async () => {
    try {
      const result = await navigator.permissions.query({ name: 'microphone' as PermissionName });
      if (result.state === 'granted') {
        setMicrophoneAccess('granted');
        return true;
      } else if (result.state === 'denied') {
        setMicrophoneAccess('denied');
        return false;
      } else {
        try {
          const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
          stream.getTracks().forEach(track => track.stop());
          setMicrophoneAccess('granted');
          return true;
        } catch {
          setMicrophoneAccess('denied');
          return false;
        }
      }
    } catch {
      setMicrophoneAccess('granted');
      return true;
    }
  }, []);

  // ✅ 오디오 레벨 측정 시작 함수
  const startAudioLevelMonitoring = useCallback(() => {
    if (!analyserRef.current) return;
    const bufferLength = analyserRef.current.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);
    const updateLevel = () => {
      if (!analyserRef.current || isStoppingRef.current) return;
      analyserRef.current.getByteFrequencyData(dataArray);
      const average = dataArray.reduce((sum, value) => sum + value, 0) / bufferLength;
      setAudioLevel(Math.min(100, (average / 128) * 100));
    };
    audioLevelTimerRef.current = setInterval(updateLevel, 50);
  }, []);

  // ✅ 녹음 중지 및 리소스 정리 함수
  const stopRecording = useCallback(() => {
    if (isStoppingRef.current) return;
    isStoppingRef.current = true;
    if (durationTimerRef.current) clearInterval(durationTimerRef.current);
    if (audioLevelTimerRef.current) clearInterval(audioLevelTimerRef.current);
    speechRecognitionRef.current?.abort();
    mediaRecorderRef.current?.state === 'recording' && mediaRecorderRef.current.stop();
    audioContextRef.current?.close();
    streamRef.current?.getTracks().forEach(track => track.stop());
    streamRef.current = null;
    setIsListening(false);
    setAudioLevel(0);
    onRecordingStop();
    setTimeout(() => { isStoppingRef.current = false; }, 500);
  }, [onRecordingStop]);

  // ✅ Web Speech API 초기화 함수
  const initSpeechRecognition = useCallback(() => {
    const SpeechRecognitionConstructor = window.webkitSpeechRecognition || window.SpeechRecognition;
    if (!SpeechRecognitionConstructor) return null;
    try {
      const recognition = new SpeechRecognitionConstructor() as SpeechRecognition;
      recognition.continuous = true;
      recognition.interimResults = true;
      recognition.lang = 'ko-KR';
      recognition.onresult = (event: SpeechRecognitionEvent) => {
        if (isStoppingRef.current) return;
        let finalTranscript = '';
        let interimTranscript = '';
        for (let i = event.resultIndex; i < event.results.length; i++) {
          const result = event.results[i];
          result.isFinal ? finalTranscript += result[0].transcript : interimTranscript += result[0].transcript;
        }
        const allTranscript = finalTranscript + interimTranscript;
        setTranscript(allTranscript);
        const endKeywords = ['이상입니다', '끝입니다', '마칩니다', '감사합니다', '이상이에요', '끝이에요', '완료입니다', '다했습니다', '이상', '끝', '완료', '마침', '답변 끝'];
        if (endKeywords.some(keyword => allTranscript.toLowerCase().includes(keyword.toLowerCase())) && finalTranscript.length > 0) {
          setTimeout(() => isListening && stopRecording(), 500);
        }
      };
      recognition.onerror = (event: SpeechRecognitionErrorEvent) => {
        if (event.error === 'not-allowed') setMicrophoneAccess('denied');
      };
      recognition.onend = () => {
        if (isListening && !isStoppingRef.current && continuousMode) {
          setTimeout(() => speechRecognitionRef.current?.start(), 100);
        }
      };
      return recognition;
    } catch {
      return null;
    }
  }, [isListening, continuousMode, stopRecording]);

  // ✅ MediaRecorder 초기화 함수
  const initMediaRecorder = useCallback(async (): Promise<boolean> => {
    const hasPermission = await checkMicrophonePermission();
    if (!hasPermission) return false;
    const stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: false } });
    streamRef.current = stream;
    const audioContext = new AudioContext();
    const analyser = audioContext.createAnalyser();
    audioContextRef.current = audioContext;
    analyserRef.current = analyser;
    audioContext.createMediaStreamSource(stream).connect(analyser);
    const mimeType = ['audio/webm;codecs=opus', 'audio/webm', 'audio/wav'].find(type => MediaRecorder.isTypeSupported(type));
    const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
    recorder.ondataavailable = e => { if (e.data.size > 0) audioChunksRef.current.push(e.data); };
    recorder.onstop = () => {
      if (audioChunksRef.current.length > 0) {
        const audioBlob = new Blob(audioChunksRef.current, { type: mimeType || 'audio/wav' });
        onRecordingComplete(audioBlob);
      }
      audioChunksRef.current = [];
    };
    mediaRecorderRef.current = recorder;
    startAudioLevelMonitoring();
    return true;
  }, [checkMicrophonePermission, onRecordingComplete, startAudioLevelMonitoring]);

  // ✅ 녹음 시간 측정 타이머
  const startDurationTimer = () => {
    setRecordingDuration(0);
    durationTimerRef.current = setInterval(() => setRecordingDuration(prev => prev + 1), 1000);
  };

  // ✅ 녹음 시작 함수
  const startRecording = useCallback(async () => {
    if (isStoppingRef.current || isListening) return;
    setIsProcessing(true);
    const ready = await initMediaRecorder();
    if (!ready) return setIsProcessing(false);
    const recognition = initSpeechRecognition();
    recognition?.start();
    speechRecognitionRef.current = recognition;
    mediaRecorderRef.current?.start(500);
    startDurationTimer();
    setIsListening(true);
    setTranscript('');
    onRecordingStart();
    setIsProcessing(false);
  }, [isListening, initMediaRecorder, initSpeechRecognition, onRecordingStart]);

  // ✅ 마운트 시 마이크 권한 확인
  useEffect(() => {
    checkMicrophonePermission();
    return () => { isListening && stopRecording(); };
  }, [isListening]);

  // ✅ isRecording 상태 변화 감지 (연속 녹음용)
  useEffect(() => {
    if (continuousMode && isRecording && !isListening && microphoneAccess === 'granted') {
      const timer = setTimeout(() => startRecording(), 1000);
      return () => clearTimeout(timer);
    } else if (!isRecording && isListening) {
      stopRecording();
    }
  }, [isRecording, isListening, microphoneAccess]);

  const formatDuration = (seconds: number): string => `${Math.floor(seconds / 60)}:${(seconds % 60).toString().padStart(2, '0')}`;

  if (microphoneAccess === 'denied') return <div>🎤 마이크 권한이 필요합니다</div>;

  return (
    <div>
      {!continuousMode && (
        <button onClick={isListening ? stopRecording : startRecording}>
          {isListening ? '⏹️ 녹음 중지' : '🎤 녹음 시작'}
        </button>
      )}
      {isListening && (
        <>
          <div>🎙️ 녹음 중... {formatDuration(recordingDuration)}</div>
          <AudioVisualizer audioLevel={audioLevel} />
          {transcript && <div>💬 인식: {transcript}</div>}
        </>
      )}
    </div>
  );
};

export default AudioRecorder;
