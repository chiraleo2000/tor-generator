/** Suggestion categories matching backend model */
export type SuggestionCategory =
  | "compliance"
  | "clarity"
  | "completeness"
  | "consistency";

/** Suggestion status */
export type SuggestionStatus = "pending" | "accepted" | "dismissed";

/** A single AI suggestion from the backend */
export interface Suggestion {
  id: string;
  section_key: string;
  category: SuggestionCategory;
  current_text: string;
  suggested_text: string;
  predicted_score_improvement: number;
  status: SuggestionStatus;
}

/** Response from GET /api/v1/projects/{id}/suggestions */
export interface SuggestionsResponse {
  items: Suggestion[];
  total: number;
  quality_score: number;
}

/** Request body for PUT /api/v1/projects/{id}/suggestions/{sid} */
export interface UpdateSuggestionRequest {
  status: "accepted" | "dismissed";
}

/** Category display configuration */
export interface CategoryConfig {
  label: string;
  color: string;
  bgColor: string;
  borderColor: string;
  icon: string;
}
