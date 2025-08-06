// ✅ AudioRecorderProps.ts
export interface AudioRecorderProps {
  onRecordingComplete: (audioBlob: Blob) => void;
  isRecording: boolean;
  onRecordingStart: () => void;
  onRecordingStop: () => void;
  continuousMode?: boolean;
}