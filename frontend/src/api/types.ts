export type EntityType =
  | "Department"
  | "Person"
  | "Laboratory"
  | "Program"
  | "Entity";
export type RelationshipType =
  | "AFFILIATED_WITH"
  | "HAS_LABORATORY"
  | "OFFERS_PROGRAM"
  | "IS_HOD_OF";

export interface Provenance {
  source_url?: string | null;
  source_url_scope?: string | null;
  source_section?: string | null;
  source_evidence?: string | null;
  evidence_note?: string | null;
  content_hash?: string | null;
  extraction_method?: string | null;
  extraction_status?: string | null;
  department_link_status?: string | null;
  pipeline_id?: string | null;
}

export interface EntitySummary {
  id: string;
  type: EntityType;
  name: string;
  attributes: Record<string, string | number | boolean | null>;
  missing_fields: string[];
  status: { raw: Record<string, string>; display_codes: string[] };
  provenance: Provenance;
  badges?: { code: string; source_field?: string; raw_value?: string }[];
  conflict?: {
    id?: string;
    status_code?: string;
    raw_status?: string;
    [key: string]: unknown;
  } | null;
}

export interface PageResult<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
  facets: Record<string, Record<string, number>>;
}

export interface HealthResponse {
  api: "up" | "down";
  database: "up" | "down";
  data_loaded: boolean;
}
export interface SummaryResponse {
  department: {
    id: string | null;
    name: string | null;
    description: string | null;
    source_url: string | null;
  };
  department_count: number;
  counts: {
    people: number;
    faculty: number;
    support_staff: number;
    laboratories: number;
    programs: number;
    relationships: number;
  };
  data_status: {
    relationships_total: number;
    relationships_inferred: number;
    relationships_user_confirmed: number;
    unverified_claims: number;
    conflicts: number;
    open_data_quality_items: number;
  };
}
export interface AboutResponse {
  scope: {
    institution: string;
    department: string;
    scope: string;
    language: string;
    access_mode: string;
    data_source: string;
  };
  pipeline_run: {
    run_id: string | null;
    run_timestamp: string | null;
    pipeline_version: string | null;
    source_hash: string | null;
  } | null;
  known_limitations: { id: string; title: string; description: string }[];
}
export interface RelatedEntity {
  /** Current backend uses `id` and `rel_type`; the API contract describes entity_id/type. */
  id?: string;
  entity_id?: string;
  name?: string;
  entity_name?: string;
  type?: EntityType;
  entity_type?: EntityType;
  direction: "incoming" | "outgoing";
  rel_type?: RelationshipType;
  type_name?: RelationshipType;
  relationship_id?: string;
  raw_status?: string | null;
  status_code: string;
  confirmation_source?: string | null;
  confirmed_on?: string | null;
  independent_source_verified: boolean;
  source_url?: string | null;
}
export interface Observation {
  id: string;
  observation_type: string;
  status_code: string;
  raw_status?: string;
  program_name?: string;
  person_name?: string;
  role_title?: string;
  source_evidence?: string;
  source_url?: string | null;
  conflicting_entity_ids?: string[];
  members?: {
    id: string;
    level: string | null;
    intake_count: string | null;
    duration: string | null;
  }[];
  claim_promoted_to_relationship?: boolean;
}
export interface ProjectNote {
  id: string;
  kind: string;
  origin: "project_note";
  text: string;
  quotes: string[];
  source_refs: string[];
}
export interface EntityDetail {
  entity: EntitySummary & { absent_attributes?: string[] };
  status: { raw: Record<string, string>; display_codes: string[] };
  provenance: Provenance;
  related: Record<string, RelatedEntity[]>;
  observations: Observation[];
  notes: ProjectNote[];
}
export interface GraphNode {
  data: { id: string; label: string; type: EntityType; status_codes: string[] };
}
export interface GraphEdge {
  data: {
    id: string;
    source: string;
    target: string;
    type: RelationshipType;
    raw_status?: string | null;
    status_code: string;
    confirmation_source?: string | null;
    confirmed_on?: string | null;
    independent_source_verified: boolean;
    source_url?: string | null;
  };
}
export interface GraphResponse {
  nodes: GraphNode[];
  edges: GraphEdge[];
  meta: {
    node_count: number;
    edge_count: number;
    relationship_types: RelationshipType[];
  };
}
export interface DataQualityItem {
  id: string;
  kind: string;
  origin: string;
  severity: "low" | "medium" | "high";
  title: string;
  summary: string;
  explanation: string;
  entity_refs: string[];
  source_refs: string[];
  route: string | null;
  details: Record<string, unknown>;
}
export interface DataQualityResponse {
  items: DataQualityItem[];
  total: number;
}
