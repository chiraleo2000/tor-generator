// Shared TypeScript interfaces for the TOR Drafting and Review Application

/** User roles matching backend RBAC */
export type UserRole = 'officer' | 'reviewer' | 'admin';

/** Project status lifecycle */
export type ProjectStatus = 'draft' | 'in_review' | 'approved' | 'rejected' | 'archived';

/** Project types */
export type ProjectType = 'it' | 'construction' | 'consulting' | 'general';

/** Toast severity levels */
export type ToastType = 'success' | 'error' | 'warning' | 'info';

/** Authenticated user */
export interface User {
  id: string;
  name: string;
  email: string;
  organization: string;
  role: UserRole;
  createdAt: string;
  updatedAt: string;
}

/** TOR Project */
export interface Project {
  id: string;
  ownerId: string;
  name: string;
  ministry: string;
  budget: number;
  projectType: ProjectType;
  status: ProjectStatus;
  currentStep: number;
  currentPhase?: number;
  analysisJson?: Record<string, unknown>;
  extractedFields?: Record<string, unknown>;
  qualityScore: number | null;
  templateId: string | null;
  createdAt: string;
  updatedAt: string;
}

/** Input for creating a new project */
export interface CreateProjectInput {
  name: string;
  ministry: string;
  budget: number;
  projectType: ProjectType;
  templateId?: string;
}

/** Pagination metadata */
export interface Pagination {
  page: number;
  pageSize: number;
  total: number;
}

/** Toast notification */
export interface Toast {
  id: string;
  type: ToastType;
  title: string;
  message?: string;
  duration?: number;
}

/** API response envelope */
export interface ApiResponse<T = unknown> {
  ok: boolean;
  data?: T;
  error?: {
    code: string;
    message: string;
    field?: string;
    details?: unknown;
  };
  meta?: {
    requestId: string;
    timestamp: string;
  };
}

/** Paginated API response */
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
}

/** Login response from the API */
export interface LoginResponse {
  token: string;
  user: User;
  expiresIn: number;
}

/** Severity levels for validation findings */
export type ValidationSeverity = 'error' | 'warning' | 'suggestion';

/** A single finding from real-time validation */
export interface ValidationFinding {
  severity: ValidationSeverity;
  rule_violated: string;
  affected_section: string;
  message: string;
  recommended_correction: string;
}

/** Response from POST /api/v1/projects/{id}/validate */
export interface ValidationResult {
  quality_score: number;
  is_valid: boolean;
  findings: ValidationFinding[];
}
