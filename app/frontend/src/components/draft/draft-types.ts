export interface SectionPayload {
  key: string;
  title: string;
  filled: boolean;
  content: string;
  human_confirmed: boolean;
  hitl: boolean;
  matchStatus: string;
  ai_draft?: string;
  big?: boolean;
  subs?: { key: string; title: string; content: string; filled: boolean }[];
}

export interface ReviewSuggestion {
  id: string;
  section_key: string;
  category: string;
  suggested_text: string;
}
