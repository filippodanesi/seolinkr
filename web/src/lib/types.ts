/* TypeScript interfaces mirroring Python data models. */

export interface AuditIssue {
  type: string;
  severity: "error" | "warning" | "info";
  message: string;
  url: string;
  anchor: string;
}

export interface LinkInfo {
  anchor_text: string;
  target_url: string;
  link_type: "category" | "magazine" | "product" | "external" | "other";
}

export interface AuditResult {
  file: string;
  total_links: number;
  category_links: number;
  magazine_links: number;
  product_links: number;
  external_links: number;
  issues: AuditIssue[];
  links: LinkInfo[];
}

export interface CandidatePage {
  url: string;
  title: string;
  meta_description: string;
  h1: string;
  impressions: number;
  clicks: number;
  avg_position: number;
  top_queries: string[];
  opportunity_score: number;
}

export interface LinkInsertion {
  anchor_text: string;
  target_url: string;
  reasoning: string;
}

export interface LinkingResult {
  original_text: string;
  linked_text: string;
  insertions: LinkInsertion[];
  candidate_pages_count: number;
  total_sitemap_pages: number;
  rewritten_text: string;
  seo_title: string;
  seo_meta_description: string;
  output_content?: string;
}

export interface Opportunity {
  url: string;
  impressions: number;
  clicks: number;
  position: number;
  ctr: number;
  opportunity_score: number;
  priority: "high" | "medium" | "quick_win" | "low";
  reason: string;
}

export interface CrossLinkOpportunity {
  source_url: string;
  target_url: string;
  shared_queries: string[];
  shared_query_count: number;
  target_impressions: number;
  target_position: number;
  relevance_score: number;
  suggestion: string;
}

export interface AppConfig {
  api_key: string;
  default_model: string;
  max_links: number;
  top_n: number;
  embedding_model: string;
  cache_ttl_hours: number;
  sitemaps: Record<string, string>;
  gsc_service_account: string;
  gsc_oauth_secrets: string;
  gsc_cache_ttl: number;
}

export interface SSELogEvent {
  type: "log";
  message: string;
}

export interface SSEResultEvent {
  type: "result";
  data: LinkingResult;
}

export interface SSEErrorEvent {
  type: "error";
  message: string;
}

export type SSEEvent = SSELogEvent | SSEResultEvent | SSEErrorEvent;
