export type AuthResponse = {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user_id: string;
  email: string;
  display_name: string;
};

export type UserProfile = {
  id: string;
  email: string;
  display_name: string;
  is_active: boolean;
};

export type Team = {
  id: string;
  name: string;
  created_by: string;
};

export type TeamMember = {
  id: string;
  team_id: string;
  user_id: string;
  role: 'owner' | 'admin' | 'editor' | 'viewer';
};

export type SearchJob = {
  id: string;
  team_id: string;
  query: string;
  status: string;
  iteration_count: number;
  final_output: string | null;
  created_at: string;
  updated_at: string;
};

export type SearchResult = {
  id: string;
  title: string;
  authors: string[];
  abstract: string | null;
  year: number | null;
  source: string | null;
  url: string | null;
  score: number;
  metadata: Record<string, unknown>;
};

export type SearchEvent = {
  id: string;
  event_type: string;
  from_agent: string | null;
  to_agent: string | null;
  reason: string | null;
  payload: Record<string, unknown>;
  created_at: string;
  job_id?: string;
  team_id?: string;
};

export type FavoriteDetail = {
  id: string;
  team_id: string;
  user_id: string;
  result_id: string;
  title: string;
  authors: string[];
  abstract: string | null;
  year: number | null;
  source: string | null;
  url: string | null;
  score: number;
  metadata: Record<string, unknown>;
};

export type ExportJob = {
  id: string;
  team_id: string;
  job_id: string;
  export_type: 'pdf' | 'csv';
  status: string;
  file_path: string | null;
};
