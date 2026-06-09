const MARKER_APP1 = 0xe1;
const MARKER_APP2 = 0xe2;
const MARKER_SOS = 0xda;
const MARKER_EOI = 0xd9;
const JPEG_SOI_FIRST = 0xff;
const JPEG_SOI_SECOND = 0xd8;

const chromeLikeBrowserExclusions = /\b(?:EdgA|OPR|Opera|SamsungBrowser|Firefox|FxiOS|CriOS)\b/i;
const jpegExtensionPattern = /\.jpe?g(?:$|[\s?#])/i;
const xmpEnhancedJpegMarkers = [
  'http://ns.adobe.com/hdr-gain-map/1.0/',
  'hdrgm',
  'GainMap',
  'Camera:MotionPhoto',
  'GCamera:MicroVideo',
  'GCamera:MicroVideoOffset',
  'MotionPhoto',
];

interface JpegSanitizeResult {
  bytes: Uint8Array;
  changed: boolean;
}

export function shouldUseChromeSafePhotoPreview(
  imageUrl: string | null | undefined,
  fileName?: string | null,
): boolean {
  if (!imageUrl || typeof navigator === 'undefined') {
    return false;
  }

  const userAgent = navigator.userAgent;
  const vendor = navigator.vendor;
  const isAndroidChrome = /\bAndroid\b/i.test(userAgent)
    && /\bChrome\/\d+/i.test(userAgent)
    && !chromeLikeBrowserExclusions.test(userAgent)
    && (!vendor || vendor.includes('Google'));

  if (!isAndroidChrome) {
    return false;
  }

  const candidate = `${fileName ?? ''} ${imageUrl}`;
  return jpegExtensionPattern.test(candidate) || imageUrl.includes('/api/photo-original/');
}

export async function createChromeSafePhotoPreviewUrl(imageUrl: string): Promise<string> {
  const response = await fetch(imageUrl, { credentials: 'same-origin' });
  if (!response.ok) {
    throw new Error('Photo preview fetch failed');
  }

  const sourceBytes = new Uint8Array(await response.arrayBuffer());
  const sanitized = sanitizeJpegForChromePreview(sourceBytes);
  const contentType = normalizeImageContentType(response.headers.get('Content-Type'));
  const blob = new Blob([toArrayBuffer(sanitized.bytes)], { type: contentType });
  return URL.createObjectURL(blob);
}

export function sanitizeJpegForChromePreview(sourceBytes: Uint8Array): JpegSanitizeResult {
  if (!isJpeg(sourceBytes)) {
    return { bytes: sourceBytes, changed: false };
  }

  const parts: Uint8Array[] = [sourceBytes.subarray(0, 2)];
  let offset = 2;
  let changed = false;

  while (offset < sourceBytes.length) {
    const markerStart = offset;
    if (sourceBytes[offset] !== 0xff) {
      return { bytes: sourceBytes, changed: false };
    }

    while (offset < sourceBytes.length && sourceBytes[offset] === 0xff) {
      offset += 1;
    }
    if (offset >= sourceBytes.length) {
      return { bytes: sourceBytes, changed: false };
    }

    const marker = sourceBytes[offset];
    offset += 1;

    if (marker === MARKER_EOI) {
      parts.push(sourceBytes.subarray(markerStart, offset));
      if (offset < sourceBytes.length) {
        changed = true;
      }
      return buildSanitizedResult(sourceBytes, parts, changed);
    }

    if (marker === MARKER_SOS) {
      if (offset + 2 > sourceBytes.length) {
        return { bytes: sourceBytes, changed: false };
      }

      const segmentLength = readUint16(sourceBytes, offset);
      const entropyStart = offset + segmentLength;
      if (segmentLength < 2 || entropyStart > sourceBytes.length) {
        return { bytes: sourceBytes, changed: false };
      }

      const imageEnd = findEntropyEnd(sourceBytes, entropyStart);
      if (imageEnd < 0) {
        return { bytes: sourceBytes, changed: false };
      }

      parts.push(sourceBytes.subarray(markerStart, imageEnd));
      if (imageEnd < sourceBytes.length) {
        changed = true;
      }
      return buildSanitizedResult(sourceBytes, parts, changed);
    }

    if (!markerHasLength(marker)) {
      parts.push(sourceBytes.subarray(markerStart, offset));
      continue;
    }

    if (offset + 2 > sourceBytes.length) {
      return { bytes: sourceBytes, changed: false };
    }

    const segmentLength = readUint16(sourceBytes, offset);
    const segmentEnd = offset + segmentLength;
    if (segmentLength < 2 || segmentEnd > sourceBytes.length) {
      return { bytes: sourceBytes, changed: false };
    }

    const payload = sourceBytes.subarray(offset + 2, segmentEnd);
    if (shouldRemoveMetadataSegment(marker, payload)) {
      changed = true;
    } else {
      parts.push(sourceBytes.subarray(markerStart, segmentEnd));
    }
    offset = segmentEnd;
  }

  return { bytes: sourceBytes, changed: false };
}

function buildSanitizedResult(
  sourceBytes: Uint8Array,
  parts: Uint8Array[],
  changed: boolean,
): JpegSanitizeResult {
  if (!changed) {
    return { bytes: sourceBytes, changed: false };
  }

  const bytes = concatenateByteParts(parts);
  return { bytes, changed: true };
}

function shouldRemoveMetadataSegment(marker: number, payload: Uint8Array): boolean {
  if (marker === MARKER_APP1 && includesAnyAscii(payload, xmpEnhancedJpegMarkers)) {
    return true;
  }

  if (marker === MARKER_APP2 && startsWithAscii(payload, 'MPF\0')) {
    return true;
  }

  return false;
}

function findEntropyEnd(bytes: Uint8Array, startOffset: number): number {
  let offset = startOffset;
  while (offset < bytes.length - 1) {
    if (bytes[offset] !== 0xff) {
      offset += 1;
      continue;
    }

    let markerOffset = offset + 1;
    while (markerOffset < bytes.length && bytes[markerOffset] === 0xff) {
      markerOffset += 1;
    }
    if (markerOffset >= bytes.length) {
      return -1;
    }

    const marker = bytes[markerOffset];
    if (marker === 0x00) {
      offset = markerOffset + 1;
      continue;
    }
    if (marker >= 0xd0 && marker <= 0xd7) {
      offset = markerOffset + 1;
      continue;
    }
    if (marker === MARKER_EOI) {
      return markerOffset + 1;
    }

    offset = markerOffset + 1;
  }

  return -1;
}

function markerHasLength(marker: number): boolean {
  return marker !== 0x01 && !(marker >= 0xd0 && marker <= 0xd9);
}

function isJpeg(bytes: Uint8Array): boolean {
  return bytes.length >= 4
    && bytes[0] === JPEG_SOI_FIRST
    && bytes[1] === JPEG_SOI_SECOND;
}

function readUint16(bytes: Uint8Array, offset: number): number {
  return (bytes[offset] << 8) | bytes[offset + 1];
}

function concatenateByteParts(parts: Uint8Array[]): Uint8Array {
  const totalLength = parts.reduce((sum, part) => sum + part.byteLength, 0);
  const output = new Uint8Array(totalLength);
  let offset = 0;
  for (const part of parts) {
    output.set(part, offset);
    offset += part.byteLength;
  }
  return output;
}

function normalizeImageContentType(contentType: string | null): string {
  if (!contentType) {
    return 'image/jpeg';
  }
  return contentType.split(';', 1)[0].trim() || 'image/jpeg';
}

function toArrayBuffer(bytes: Uint8Array): ArrayBuffer {
  const output = new ArrayBuffer(bytes.byteLength);
  new Uint8Array(output).set(bytes);
  return output;
}

function includesAnyAscii(bytes: Uint8Array, values: string[]): boolean {
  return values.some((value) => includesAscii(bytes, value));
}

function includesAscii(bytes: Uint8Array, value: string): boolean {
  if (value.length === 0 || value.length > bytes.length) {
    return false;
  }

  const lastStart = bytes.length - value.length;
  for (let start = 0; start <= lastStart; start += 1) {
    let matched = true;
    for (let offset = 0; offset < value.length; offset += 1) {
      if (bytes[start + offset] !== value.charCodeAt(offset)) {
        matched = false;
        break;
      }
    }
    if (matched) {
      return true;
    }
  }

  return false;
}

function startsWithAscii(bytes: Uint8Array, value: string): boolean {
  if (value.length > bytes.length) {
    return false;
  }

  for (let offset = 0; offset < value.length; offset += 1) {
    if (bytes[offset] !== value.charCodeAt(offset)) {
      return false;
    }
  }

  return true;
}
