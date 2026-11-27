import { api } from "@/lib/api";

export type FunnelStep = {
  layer: string;
  label: string;
  entered: number;
  stopped: number;
};

export type Outlook = {
  name: string;
  pass_rate: number | null;
  blocked_rate: number | null;
  passed: number | null;
  blocked: number | null;
  runs: number;
  closed_form: number | null;
  funnel: FunnelStep[];
  uncertainty: { p05: number; p50: number; p95: number; kappa: number } | null;
};

export type CommandCenter = {
  summary: {
    dataset_id: string;
    name: string;
    email_count: number;
    phishing_count: number | null;
    genuine_count: number | null;
    accuracy: number | null;
    correct: number | null;
    labeled: number | null;
    pass_rate_before: number | null;
    pass_rate_after: number | null;
    relative_reduction: number | null;
  };
  before: Outlook;
  after: Outlook;
  trained_pass_rate: number | null;
  recommendation: {
    id: string;
    title: string;
    detail: string;
    layer: string;
    absolute_reduction: number;
    relative_reduction: number;
  } | null;
  threats: {
    email_id: string;
    subject: string;
    sender: string;
    risk_score: number;
    band: string;
    label: string;
    attack_vector: string;
    top_evidence: string | null;
  }[];
  brands: { brand: string; occurrences: number; technique: string; similarity: number }[];
  user_layer_source: "config" | "quiz";
  user_catch_rate: number | null;
  note: string;
};

export type DomainReport = {
  dataset_id: string;
  domains: {
    domain: string;
    closest_brand: string | null;
    similarity: number;
    technique: string;
    occurrences: number;
    email_ids: string[];
    diff: string;
    sentence: string;
  }[];
  deceptive_links: {
    email_id: string;
    subject: string;
    visible_text: string;
    href: string;
    visible_domain: string;
    real_domain: string;
    technique: string;
    sentence: string;
  }[];
};

export type SimilarityView = {
  candidate: string;
  score: number;
  closest: string | null;
  technique: string;
  diff: string;
  sentence: string;
  legitimate: boolean;
};

export type QuizQuestion = {
  id: string;
  email_id: string;
  kind: string;
  prompt: string;
  subject: string;
  sender: string;
  excerpt: string;
  options: { id: string; text: string }[];
};

export type QuizGrade = {
  correct: number;
  total: number;
  accuracy: number;
  catch_rate: number;
  weak_areas: string[];
  recorded: boolean;
  results: {
    question_id: string;
    chosen: string;
    correct: boolean;
    correct_option_id: string;
    explanation: string;
  }[];
};

export function loadCommand(datasetId: string): Promise<CommandCenter> {
  return api<CommandCenter>(`/api/v1/datasets/${datasetId}/command`);
}

export function loadDomains(datasetId: string): Promise<DomainReport> {
  return api<DomainReport>(`/api/v1/datasets/${datasetId}/domains`);
}

export function checkDomain(candidate: string): Promise<SimilarityView> {
  return api<SimilarityView>("/api/v1/domains/similarity", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ candidate }),
  });
}

export function loadQuiz(datasetId: string): Promise<QuizQuestion[]> {
  return api<QuizQuestion[]>(`/api/v1/datasets/${datasetId}/quiz?n=10&seed=42`);
}

export function gradeQuiz(
  datasetId: string,
  answers: { question_id: string; chosen: string }[],
  record: boolean,
): Promise<QuizGrade> {
  return api<QuizGrade>("/api/v1/quiz/attempts", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ dataset_id: datasetId, n: 10, seed: 42, answers, record }),
  });
}

export function applyQuizRate(datasetId: string, reset = false): Promise<{ catch_rate: number | null }> {
  return api("/api/v1/quiz/user-layer", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ dataset_id: datasetId, reset }),
  });
}
