import type { Task } from './task';

export type VideoReconstructionMode = 'auto' | 'object' | 'environment';
export type VideoReconstructionQuality = 'preview' | 'high' | 'extreme';
export type VideoReconstructionEngine = 'auto' | 'stable' | 'experimental';
export type VideoReconstructionVramBudget = 'auto' | '8gb' | '12gb' | '16gb' | '24gb';

export interface VideoReconstructionConfig {
  default_quality: VideoReconstructionQuality;
  default_engine: VideoReconstructionEngine;
  vram_budget: VideoReconstructionVramBudget;
  keep_intermediate_files: boolean;
}

export interface VideoReconstructionToolStatus {
  name: string;
  category: 'required' | 'stable' | 'experimental' | string;
  required: boolean;
  available: boolean;
  version?: string | null;
  message?: string | null;
}

export interface VideoReconstructionDependencyGroup {
  available: boolean;
  tools: VideoReconstructionToolStatus[];
  message?: string | null;
}

export interface VideoReconstructionFeedforwardGroup extends VideoReconstructionDependencyGroup {
  engine_available?: boolean;
  weights_available?: boolean;
  weights_path?: string | null;
  weights_dir?: string | null;
}

export interface VideoReconstructionDependencies {
  required: VideoReconstructionDependencyGroup;
  stable: VideoReconstructionDependencyGroup;
  experimental: VideoReconstructionFeedforwardGroup;
  summary: {
    available: boolean;
    stable_available: boolean;
    experimental_available: boolean;
    training_available?: boolean;
    checking?: boolean;
    checked_at?: number | null;
    cached?: boolean;
  };
}

export interface VideoReconstructionStatusResponse {
  config: VideoReconstructionConfig;
  dependencies: VideoReconstructionDependencies;
}

export interface VideoReconstructionRequest {
  video_id: string;
  mode: VideoReconstructionMode;
  quality: VideoReconstructionQuality;
  engine: VideoReconstructionEngine;
  output_name?: string;
  keep_intermediate_files?: boolean;
}

export interface VideoReconstructionResponse {
  success: boolean;
  task?: Task;
  error?: string;
  code?: string;
  dependencies?: VideoReconstructionDependencies;
}
