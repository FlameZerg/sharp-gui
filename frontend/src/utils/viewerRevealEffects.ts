import { dyno, type GsplatModifier, type SplatMesh } from '@sparkjsdev/spark';
import * as THREE from 'three';

export type ActiveRevealEffectId = 'default' | 'magic' | 'spread' | 'unroll' | 'twister' | 'rain';
export type RevealEffectId = 'none' | ActiveRevealEffectId;
export type RevealEffectPreferenceId = ActiveRevealEffectId;

export interface RevealEffectOption<TId extends string = RevealEffectId> {
  id: TId;
  labelKey: string;
  shortLabel: string;
}

export const REVEAL_EFFECT_NONE_ID = 'none' as const satisfies RevealEffectId;
export const DEFAULT_REVEAL_EFFECT_ID = 'default' as const satisfies ActiveRevealEffectId;
export const DEFAULT_REVEAL_EFFECT_PREFERENCE_ID = 'default' as const satisfies RevealEffectPreferenceId;

export const REVEAL_EFFECT_DEFAULT_OPTION: RevealEffectOption<typeof DEFAULT_REVEAL_EFFECT_PREFERENCE_ID> = {
  id: DEFAULT_REVEAL_EFFECT_PREFERENCE_ID,
  labelKey: 'revealEffectsDefault',
  shortLabel: 'DEF',
};

export const VIEWER_REVEAL_EFFECTS: Array<RevealEffectOption<ActiveRevealEffectId>> = [
  REVEAL_EFFECT_DEFAULT_OPTION,
  { id: 'magic', labelKey: 'revealEffectsMagic', shortLabel: 'MAG' },
  { id: 'spread', labelKey: 'revealEffectsSpread', shortLabel: 'SPD' },
  { id: 'unroll', labelKey: 'revealEffectsUnroll', shortLabel: 'UNR' },
  { id: 'twister', labelKey: 'revealEffectsTwister', shortLabel: 'TWS' },
  { id: 'rain', labelKey: 'revealEffectsRain', shortLabel: 'RAN' },
];

export const REVEAL_EFFECT_SETTINGS_OPTIONS: Array<RevealEffectOption<RevealEffectPreferenceId>> = [
  ...VIEWER_REVEAL_EFFECTS,
];

const REVEAL_EFFECT_TYPES: Record<Exclude<ActiveRevealEffectId, 'default'>, number> = {
  magic: 1,
  spread: 2,
  unroll: 3,
  twister: 4,
  rain: 5,
};

function getRevealEffectType(effectId: RevealEffectId): number {
  if (effectId === 'none' || effectId === 'default') return 0;
  return REVEAL_EFFECT_TYPES[effectId];
}

export function isRevealEffectEnabled(
  effectId: RevealEffectId,
): effectId is ActiveRevealEffectId {
  return effectId !== REVEAL_EFFECT_NONE_ID;
}

export function isRevealEffectId(value: unknown): value is RevealEffectId {
  return value === REVEAL_EFFECT_NONE_ID
    || VIEWER_REVEAL_EFFECTS.some((effect) => effect.id === value);
}

export function isRevealEffectPreferenceId(
  value: unknown,
): value is RevealEffectPreferenceId {
  return REVEAL_EFFECT_SETTINGS_OPTIONS.some((effect) => effect.id === value);
}

export function resolveRevealEffectPreference(
  preferenceId: RevealEffectPreferenceId,
): RevealEffectId {
  return preferenceId;
}

export function getRevealEffectOption(effectId: RevealEffectId): RevealEffectOption<string> {
  if (effectId === REVEAL_EFFECT_NONE_ID) {
    return REVEAL_EFFECT_DEFAULT_OPTION;
  }

  return VIEWER_REVEAL_EFFECTS.find((effect) => effect.id === effectId)
    ?? REVEAL_EFFECT_DEFAULT_OPTION;
}

export interface RevealEffectRuntime {
  activeEffect: RevealEffectId;
  replayToken: number;
  playbackTime: number;
  lastFrameAt: number | null;
  effectTypeUniform: ReturnType<typeof dyno.dynoInt>;
  timeUniform: ReturnType<typeof dyno.dynoFloat>;
  boundsCenterUniform: ReturnType<typeof dyno.dynoVec3>;
  boundsRadiusUniform: ReturnType<typeof dyno.dynoFloat>;
  boundsHeightUniform: ReturnType<typeof dyno.dynoFloat>;
  minScaleUniform: ReturnType<typeof dyno.dynoFloat>;
  modifier: GsplatModifier;
}

function resetRevealEffectPlayback(runtime: RevealEffectRuntime): void {
  runtime.playbackTime = 0;
  runtime.lastFrameAt = null;
  runtime.timeUniform.value = 0;
}

function createRevealEffectModifier(runtime: RevealEffectRuntime): GsplatModifier {
  return dyno.dynoBlock({ gsplat: dyno.Gsplat }, { gsplat: dyno.Gsplat }, ({ gsplat }) => {
    const program = new dyno.Dyno({
      inTypes: {
        gsplat: dyno.Gsplat,
        t: 'float',
        effectType: 'int',
        boundsCenter: 'vec3',
        boundsRadius: 'float',
        boundsHeight: 'float',
        minScale: 'float',
      },
      outTypes: { gsplat: dyno.Gsplat },
      globals: () => [
        dyno.unindent(`
          vec3 hash(vec3 p) {
            p = fract(p * 0.3183099 + 0.1);
            p *= 17.0;
            return fract(vec3(p.x * p.y * p.z, p.x + p.y * p.z, p.x * p.y + p.z));
          }

          vec3 noise3(vec3 p) {
            vec3 i = floor(p);
            vec3 f = fract(p);
            f = f * f * (3.0 - 2.0 * f);

            vec3 n000 = hash(i + vec3(0.0, 0.0, 0.0));
            vec3 n100 = hash(i + vec3(1.0, 0.0, 0.0));
            vec3 n010 = hash(i + vec3(0.0, 1.0, 0.0));
            vec3 n110 = hash(i + vec3(1.0, 1.0, 0.0));
            vec3 n001 = hash(i + vec3(0.0, 0.0, 1.0));
            vec3 n101 = hash(i + vec3(1.0, 0.0, 1.0));
            vec3 n011 = hash(i + vec3(0.0, 1.0, 1.0));
            vec3 n111 = hash(i + vec3(1.0, 1.0, 1.0));

            vec3 x0 = mix(n000, n100, f.x);
            vec3 x1 = mix(n010, n110, f.x);
            vec3 x2 = mix(n001, n101, f.x);
            vec3 x3 = mix(n011, n111, f.x);

            vec3 y0 = mix(x0, x1, f.y);
            vec3 y1 = mix(x2, x3, f.y);

            return mix(y0, y1, f.z);
          }

          mat2 rot(float a) {
            float s = sin(a);
            float c = cos(a);
            return mat2(c, -s, s, c);
          }

          vec4 twister(vec3 pos, float t) {
            vec3 h = hash(pos);
            float reveal = smoothstep(0.0, 8.0, t * t * 0.1 - length(pos.xz) * 2.0 + 2.0);
            pos.y = mix(-3.0, pos.y, pow(reveal, 2.0 * h.x));
            pos.xz = mix(pos.xz * 0.35, pos.xz, pow(reveal, 2.0 * h.x));
            float rotationTime = t * (1.0 - reveal) * 0.4;
            pos.xz *= rot(rotationTime + pos.y * 12.0 * (1.0 - reveal) * exp(-0.8 * length(pos.xz)));
            return vec4(pos, reveal);
          }

          vec4 rain(vec3 pos, float t) {
            vec3 h = hash(pos);
            float reveal = pow(smoothstep(0.0, 5.0, t * t * 0.1 - length(pos.xz) * 2.0 + 1.0), 0.6 + h.x);
            float originalY = pos.y;
            pos.y = min(-3.0 + reveal * 5.0, pos.y);
            pos.xz = mix(pos.xz * 0.2, pos.xz, reveal);
            pos.xz *= rot(t * 0.18);
            return vec4(pos, smoothstep(-3.0, originalY, pos.y));
          }
        `),
      ],
      statements: ({ inputs, outputs }) => dyno.unindentLines(`
        ${outputs.gsplat} = ${inputs.gsplat};

        float t = ${inputs.t};
        float radius = max(${inputs.boundsRadius}, 0.05);
        float halfHeight = max(${inputs.boundsHeight}, 0.05);
        float minScale = max(${inputs.minScale}, 0.0002);
        vec3 center = ${inputs.boundsCenter};
        vec3 scales = ${inputs.gsplat}.scales;

        vec3 basePos = ${inputs.gsplat}.center - center;
        vec3 localPos = vec3(basePos.x / radius, basePos.y / halfHeight, basePos.z / radius);
        float l = length(localPos.xz);

        if (${inputs.effectType} == 0) {
          float reveal = smoothstep(0.0, 0.75, t * 1.35);
          ${outputs.gsplat}.rgba = ${inputs.gsplat}.rgba * reveal;
        } else if (${inputs.effectType} == 1) {
          float sweep = smoothstep(0.0, 10.0, t - 1.5) * 3.2;
          float border = abs(sweep - l - 0.35);
          localPos *= 1.0 - 0.12 * exp(-18.0 * border);
          vec3 finalScales = mix(scales, vec3(minScale), smoothstep(sweep - 0.45, sweep, l + 0.35));
          vec3 jitter = noise3(localPos * 2.0 + t * 0.45);
          vec3 finalPos = vec3(localPos.x * radius, localPos.y * halfHeight, localPos.z * radius) + center;
          finalPos += vec3(jitter.x * 0.07 * radius, jitter.y * 0.04 * halfHeight, jitter.z * 0.07 * radius)
            * smoothstep(sweep - 0.45, sweep, l + 0.35);
          float angle = atan(localPos.x, localPos.z) / 3.1415926;
          ${outputs.gsplat}.center = finalPos;
          ${outputs.gsplat}.scales = finalScales;
          ${outputs.gsplat}.rgba *= step(angle, t - 3.1415926);
          ${outputs.gsplat}.rgba += exp(-18.0 * border) + exp(-40.0 * abs(t - angle - 3.1415926)) * 0.35;
        } else if (${inputs.effectType} == 2) {
          float tt = t * t * 0.3 + 0.6;
          localPos.xz *= min(1.0, 0.28 + max(0.0, tt * 0.07));
          ${outputs.gsplat}.center = vec3(localPos.x * radius, localPos.y * halfHeight, localPos.z * radius) + center;
          ${outputs.gsplat}.scales = max(
            mix(vec3(0.0), scales, min(tt - 6.0 - l * 2.3, 1.0)),
            mix(vec3(minScale), scales * 0.2, min(tt - 0.8 - l * 2.0, 1.0))
          );
          ${outputs.gsplat}.rgba = mix(vec4(0.25, 0.25, 0.25, 0.3), ${inputs.gsplat}.rgba, clamp(tt - l * 2.5 - 2.0, 0.0, 1.0));
        } else if (${inputs.effectType} == 3) {
          localPos.xz *= rot((localPos.y * 18.0 - 6.0) * exp(-t));
          vec3 finalPos = localPos * (1.0 - exp(-t) * 1.6);
          ${outputs.gsplat}.center = vec3(finalPos.x * radius, finalPos.y * halfHeight, finalPos.z * radius) + center;
          ${outputs.gsplat}.scales = mix(vec3(minScale), scales, smoothstep(0.25, 0.75, t + localPos.y - 1.0));
          ${outputs.gsplat}.rgba = ${inputs.gsplat}.rgba * step(0.0, t * 0.6 + localPos.y - 0.4);
        } else if (${inputs.effectType} == 4) {
          vec4 effectResult = twister(localPos, t);
          ${outputs.gsplat}.center = vec3(effectResult.x * radius, effectResult.y * halfHeight, effectResult.z * radius) + center;
          ${outputs.gsplat}.scales = mix(vec3(minScale), scales, pow(effectResult.w, 8.0));
        } else if (${inputs.effectType} == 5) {
          vec4 effectResult = rain(localPos, t);
          ${outputs.gsplat}.center = vec3(effectResult.x * radius, effectResult.y * halfHeight, effectResult.z * radius) + center;
          ${outputs.gsplat}.scales = mix(vec3(minScale), scales, pow(effectResult.w, 12.0));
          ${outputs.gsplat}.rgba = ${inputs.gsplat}.rgba * clamp(effectResult.w + 0.15, 0.0, 1.0);
        }
      `),
    });

    const nextGsplat = program.apply({
      gsplat,
      t: runtime.timeUniform,
      effectType: runtime.effectTypeUniform,
      boundsCenter: runtime.boundsCenterUniform,
      boundsRadius: runtime.boundsRadiusUniform,
      boundsHeight: runtime.boundsHeightUniform,
      minScale: runtime.minScaleUniform,
    }).gsplat;

    return { gsplat: nextGsplat };
  });
}

export function createRevealEffectRuntime(): RevealEffectRuntime {
  const runtime: Omit<RevealEffectRuntime, 'modifier'> = {
    activeEffect: DEFAULT_REVEAL_EFFECT_ID,
    replayToken: 0,
    playbackTime: 0,
    lastFrameAt: null,
    effectTypeUniform: dyno.dynoInt(getRevealEffectType(DEFAULT_REVEAL_EFFECT_ID), 'revealEffectType'),
    timeUniform: dyno.dynoFloat(0, 'revealTime'),
    boundsCenterUniform: dyno.dynoVec3(new THREE.Vector3(0, 0, 0), 'revealBoundsCenter'),
    boundsRadiusUniform: dyno.dynoFloat(1, 'revealBoundsRadius'),
    boundsHeightUniform: dyno.dynoFloat(1, 'revealBoundsHeight'),
    minScaleUniform: dyno.dynoFloat(0.002, 'revealMinScale'),
  };

  return {
    ...runtime,
    modifier: createRevealEffectModifier(runtime as RevealEffectRuntime),
  };
}

export function syncRevealEffectSelection(
  runtime: RevealEffectRuntime,
  effectId: RevealEffectId,
  replayToken: number,
): void {
  const effectChanged = runtime.activeEffect !== effectId;
  const replayChanged = runtime.replayToken !== replayToken;

  if (!effectChanged && !replayChanged) return;

  runtime.activeEffect = effectId;
  runtime.replayToken = replayToken;
  runtime.effectTypeUniform.value = getRevealEffectType(effectId);
  resetRevealEffectPlayback(runtime);
}

export function updateRevealEffectPlayback(
  runtime: RevealEffectRuntime,
  nowMs: number,
): void {
  if (runtime.lastFrameAt === null) {
    runtime.lastFrameAt = nowMs;
    runtime.timeUniform.value = runtime.playbackTime;
    return;
  }

  const deltaSeconds = Math.min((nowMs - runtime.lastFrameAt) / 1000, 0.05);
  runtime.lastFrameAt = nowMs;
  runtime.playbackTime += deltaSeconds;
  runtime.timeUniform.value = runtime.playbackTime;
}

export function updateRevealEffectBounds(
  runtime: RevealEffectRuntime,
  mesh: SplatMesh,
): void {
  try {
    const bbox = mesh.getBoundingBox(true).clone();
    if (bbox.isEmpty()) return;

    const center = bbox.getCenter(new THREE.Vector3());
    const size = bbox.getSize(new THREE.Vector3());
    const radius = Math.max(size.x, size.z, 0.25) * 0.5;
    const height = Math.max(size.y, 0.25) * 0.5;
    const minScale = Math.max(Math.min(radius, height) * 0.002, 0.0015);

    runtime.boundsCenterUniform.value = center;
    runtime.boundsRadiusUniform.value = radius;
    runtime.boundsHeightUniform.value = height;
    runtime.minScaleUniform.value = minScale;
  } catch (error) {
    console.warn('[Viewer] Failed to update reveal-effect bounds:', error);
  }
}

export function applyRevealEffectToMesh(
  runtime: RevealEffectRuntime,
  mesh: SplatMesh,
): void {
  if (!isRevealEffectEnabled(runtime.activeEffect)) {
    mesh.objectModifier = undefined;
    mesh.updateGenerator();
    resetRevealEffectPlayback(runtime);
    return;
  }

  updateRevealEffectBounds(runtime, mesh);
  mesh.objectModifier = runtime.modifier;
  mesh.updateGenerator();
  resetRevealEffectPlayback(runtime);
}
