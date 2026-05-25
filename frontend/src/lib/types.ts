// Mirror of backend Pydantic schemas

export type DoctorRole = "Doctor" | "Admin";
export type Gender = "Male" | "Female" | "Other";
export type ImageFormat = "DICOM" | "JPEG" | "PNG";
export type ImageSetUsability =
  | "IschemicAssessable"
  | "HemorrhagicPresent"
  | "Anomaly"
  | "Irrelevant";
export type Region = "None" | "BasalGanglia" | "CoronaRadiata";
export type RegionScore =
  | "Affected"
  | "Not_Affected"
  | "Not_In_This_Slice"
  | "Not_Applicable";

export interface Doctor {
  uuid: string;
  username: string;
  role: DoctorRole;
  email: string | null;
  is_active: boolean;
  must_change_password: boolean;
  registration_source: string;
  created_at: string;
}

export interface DataSet {
  dataset_uuid: string;
  name: string;
  description: string | null;
  is_active: boolean;
  created_at: string;
}

export interface Patient {
  patient_uuid: string;
  patient_id: string;
  dataset_uuid: string;
  category: string | null;
  age: number | null;
  gender: Gender | null;
}

export interface ImageSet {
  uuid: string;
  dataset_uuid: string;
  patient_uuid: string;
  image_set_name: string;
  image_format: ImageFormat;
  image_window_level: number | null;
  image_window_width: number | null;
  num_images: number;
  folder_path?: string;
  description: string | null;
  icd_code: string | null;
  is_active: boolean;
  created_at: string;
}

export interface ImageSetWithProgress extends ImageSet {
  dataset_index: number;
  patient_id: string | null;
  evaluated_by_me: boolean;
  in_draft_by_me: boolean;
  total_evaluators: number;
}

export interface ImageRecord {
  uuid: string;
  image_name: string;
  image_set_uuid: string;
  slice_index: number;
}

export interface AnnotationSession {
  annotation_session_uuid: string;
  doctor_uuid: string;
  image_set_uuid: string;
  login_session_uuid: string;
  started_at: string;
  submitted_at: string | null;
}

export interface DraftItem {
  annotation_session_uuid: string;
  image_set_uuid: string;
  image_set_name: string;
  dataset_index: number;
  patient_id: string | null;
  icd_code: string | null;
  num_images: number;
  draft_saved_at: string;
  evaluated_by_me: boolean;
  doctor_uuid?: string;
  doctor_username?: string;
}

export interface HistoryEvent {
  event_type: "submitted" | "draft_saved" | "draft_deleted";
  timestamp: string;
  annotation_session_uuid: string;
  image_set_uuid: string;
  image_set_name: string;
  dataset_index: number;
  icd_code: string | null;
}

export interface DashboardStats {
  assigned_dataset: DataSet | null;
  my_progress: number;
  global_progress: number;
  total_image_sets: number;
}

export interface DoctorDatasetAssignment {
  id: number;
  doctor_uuid: string;
  dataset_uuid: string;
  assigned_at: string;
  is_active: boolean;
}

export interface AdminAuditLog {
  id: number;
  admin_uuid: string;
  action: string;
  target_table: string;
  target_id: string | null;
  detail: string | null;
  timestamp: string;
}

// Zone scores — one entry per zone per evaluation
export type ZoneScoreMap = Record<string, RegionScore | null>;

// Per-slice state in the frontend label store
export interface SliceEvalState {
  region: Region;
  scores: ZoneScoreMap;
  notes: string;
}

export const BASAL_ZONES = ["c", "ic", "l", "i", "m1", "m2", "m3"] as const;
export const CORONA_ZONES = ["m4", "m5", "m6"] as const;
export const ALL_ZONES = [...BASAL_ZONES, ...CORONA_ZONES] as const;
export type Zone = (typeof ALL_ZONES)[number];

export const SCORE_LABELS: Record<Exclude<RegionScore, "Not_Applicable">, string> = {
  Affected: "Damaged",
  Not_Affected: "Not Damaged",
  Not_In_This_Slice: "Not Visible",
};

export const USABILITY_LABELS: Record<ImageSetUsability, string> = {
  IschemicAssessable: "Ischemic Assessable",
  HemorrhagicPresent: "Hemorrhagic Present",
  Anomaly: "Anomaly",
  Irrelevant: "Irrelevant",
};
