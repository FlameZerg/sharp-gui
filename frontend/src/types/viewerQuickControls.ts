export interface ViewerTransformState {
  positionX: number;
  positionY: number;
  positionZ: number;
  rotationX: number;
  rotationY: number;
  rotationZ: number;
  scale: number;
}

export interface ViewerInteractionState {
  reversePointerDirection: boolean;
  reversePointerSlide: boolean;
}

export interface ViewerQualityState {
  lodEnabled: boolean;
  lodScale: number;
  coneFoveate: number;
  behindFoveate: number;
}

export interface ViewerQuickControlsOverride {
  transform: ViewerTransformState;
  interaction: ViewerInteractionState;
  quality: ViewerQualityState;
}

export type ViewerOrientationPreset =
  | 'default'
  | 'openCv'
  | 'openGl'
  | 'zUp'
  | 'flipUpsideDown';
