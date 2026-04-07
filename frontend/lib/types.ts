export type ScoreBand = "green" | "amber" | "red";

export type ModelInfo = {
  source: string;
  evaluation_target: string;
  calibration: string;
  fallback_reason?: string | null;
};

export type ScorePage = {
  page_id: string;
  title: string;
  reliability_score: number;
  score_band: ScoreBand;
  last_edited_time: string;
  days_since_edit: number;
  headline_reason: string;
  top_signals: string[];
};

export type ScoreResponse = {
  workspace_id: string;
  source: string;
  snapshot_time: string;
  page_count: number;
  model: ModelInfo;
  pages: ScorePage[];
};

export type FeatureValue = {
  name: string;
  value: number;
};

export type SimilarPage = {
  page_id: string;
  title: string;
  similarity: number;
};

export type PageDetailResponse = {
  workspace_id: string;
  source: string;
  page_id: string;
  title: string;
  reliability_score: number;
  score_band: ScoreBand;
  last_edited_time: string;
  structural_features: FeatureValue[];
  semantic_features: FeatureValue[];
  top_signals: string[];
  most_similar_neighbors: SimilarPage[];
  least_similar_neighbors: SimilarPage[];
};
