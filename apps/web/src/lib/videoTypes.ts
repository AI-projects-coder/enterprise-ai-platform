export type TranscriptSegment = { start_seconds: number; end_seconds: number; text: string };

export type QuizQuestion = {
  question: string;
  type: "single" | "multi";
  options: string[];
  correct_indices: number[];
};

export type VideoSummary = {
  id: string;
  user_id: string;
  title: string;
  description: string;
  content_type: string;
  status: "processing" | "ready" | "failed";
  visibility: "draft" | "published";
  published_at: string | null;
  created_at: string;
};

export type VideoDetail = VideoSummary & {
  transcript_segments: TranscriptSegment[] | null;
  summary_notes: string | null;
  key_points: string[] | null;
  quiz: QuizQuestion[] | null;
  playback_url: string;
};
