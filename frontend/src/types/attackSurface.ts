export interface AttackSurfaceFinding {
  id: number;
  title: string;
  severity: string;
  confidence: string;
  risk_score: number | null;
  risk_level: string | null;
  status: string;
  category: string | null;
  location: string | null;
}

export interface AttackSurfaceEndpoint {
  id: number;
  web_application_id: number;
  path: string;
  method: string | null;
  status_code: number | null;
  content_type: string | null;
  source: string | null;
  created_at: string;
  updated_at: string;
  findings: AttackSurfaceFinding[];
}

export interface AttackSurfaceWebApplication {
  id: number;
  asset_id: number;
  network_service_id: number | null;
  base_url: string;
  hostname: string | null;
  port: number | null;
  scheme: string;
  title: string | null;
  tech_info: string | null;
  created_at: string;
  updated_at: string;
  endpoints: AttackSurfaceEndpoint[];
  findings: AttackSurfaceFinding[];
}

export interface AttackSurfaceService {
  id: number;
  asset_id: number;
  port: number;
  protocol: string;
  state: string;
  service_name: string | null;
  service_product: string | null;
  service_version: string | null;
  extra_info: string | null;
  created_at: string;
  updated_at: string;
  web_applications: AttackSurfaceWebApplication[];
  findings: AttackSurfaceFinding[];
}

export interface AttackSurfaceAsset {
  id: number;
  assessment_id: number;
  ip_address: string;
  hostname: string | null;
  asset_type: string;
  os: string | null;
  status: string;
  created_at: string;
  updated_at: string;
  services: AttackSurfaceService[];
  web_applications: AttackSurfaceWebApplication[];
  findings: AttackSurfaceFinding[];
}

export interface AttackSurfaceResponse {
  assessment_id: number;
  assets: AttackSurfaceAsset[];
}
