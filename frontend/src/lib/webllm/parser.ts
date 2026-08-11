/**
 * Output parsing for WebLLM responses
 * Ported from backend/app/main.py generate_gemini_suggestions parsing logic
 * 
 * Hardened to handle common LLM output issues:
 * - Trailing commas in arrays/objects
 * - Truncated JSON (incomplete arrays/objects)
 * - Markdown code fences wrapping JSON
 * - Preamble/postamble text around JSON
 * - Both English (suggestions/overallComment) and Japanese (指摘/全体講評) keys
 */

export type CorrectionSuggestion = {
  id: string;
  original: string;
  reason: string;
};

export type ParsedResponse = {
  suggestions: CorrectionSuggestion[];
  overallComment: string;
};

/**
 * Remove trailing commas from JSON string
 * Handles: [1,2,] -> [1,2] and {"a":1,} -> {"a":1}
 */
function removeTrailingCommas(json: string): string {
  return json
    .replace(/,\s*]/g, ']')
    .replace(/,\s*}/g, '}');
}

/**
 * Strip markdown code fences from text
 * Handles: ```json ... ``` and ``` ... ```
 */
function stripMarkdownFences(text: string): string {
  return text
    .replace(/```json\s*/gi, '')
    .replace(/```\s*/g, '');
}

/**
 * Attempt to repair truncated JSON by closing open brackets/braces
 * Returns the repaired string, or original if repair seems unlikely to help
 */
function repairTruncatedJson(json: string): string {
  let repaired = json;
  
  // Count open/close brackets and braces
  const openBrackets = (repaired.match(/\[/g) || []).length;
  const closeBrackets = (repaired.match(/\]/g) || []).length;
  const openBraces = (repaired.match(/\{/g) || []).length;
  const closeBraces = (repaired.match(/\}/g) || []).length;
  
  // Remove trailing partial content that might break parsing
  // e.g., trailing comma, partial string, etc.
  repaired = repaired.replace(/,\s*$/, '');
  repaired = repaired.replace(/:\s*$/, ': null');
  repaired = repaired.replace(/:\s*"[^"]*$/, ': ""');
  
  // Close missing brackets/braces
  const missingBrackets = openBrackets - closeBrackets;
  const missingBraces = openBraces - closeBraces;
  
  // Add closing brackets (arrays close before objects typically)
  for (let i = 0; i < missingBrackets; i++) {
    repaired += ']';
  }
  for (let i = 0; i < missingBraces; i++) {
    repaired += '}';
  }
  
  return repaired;
}

/**
 * Extract JSON object from text, trying multiple strategies
 */
function extractJson(text: string): string | null {
  // Strategy 1: Look for JSON object with "suggestions" key (canonical English format)
  const matchEn = text.match(/\{\s*"suggestions"[^]*\}/s);
  if (matchEn) return matchEn[0];
  
  // Strategy 2: Look for JSON object with "指摘" key (legacy Japanese format)
  const matchJp = text.match(/\{\s*"指摘"[^]*\}/s);
  if (matchJp) return matchJp[0];
  
  // Strategy 3: Find first { and last } (greedy extraction)
  const firstBrace = text.indexOf('{');
  const lastBrace = text.lastIndexOf('}');
  if (firstBrace !== -1 && lastBrace > firstBrace) {
    return text.substring(firstBrace, lastBrace + 1);
  }
  
  // Strategy 4: Truncated - find first { and try to repair
  if (firstBrace !== -1) {
    return text.substring(firstBrace);
  }
  
  return null;
}

/**
 * Safely parse JSON with repair attempts
 * Returns parsed object or null on failure
 */
function safeJsonParse(text: string): Record<string, unknown> | null {
  // Clean up the text
  const cleaned = stripMarkdownFences(text);
  
  // Try to extract JSON
  const jsonStr = extractJson(cleaned);
  if (!jsonStr) return null;
  
  // Attempt 1: Direct parse
  try {
    return JSON.parse(jsonStr) as Record<string, unknown>;
  } catch {
    // Continue to repair attempts
  }
  
  // Attempt 2: Remove trailing commas and parse
  try {
    const noTrailingCommas = removeTrailingCommas(jsonStr);
    return JSON.parse(noTrailingCommas) as Record<string, unknown>;
  } catch {
    // Continue to repair attempts
  }
  
  // Attempt 3: Full repair (trailing commas + truncation)
  try {
    let repaired = removeTrailingCommas(jsonStr);
    repaired = repairTruncatedJson(repaired);
    return JSON.parse(repaired) as Record<string, unknown>;
  } catch {
    // All attempts failed
  }
  
  return null;
}

/**
 * Parse WebLLM model output into structured suggestions
 * Following design.md Decision 3: reuse backend parsing strategy
 * 
 * Supports two key formats:
 * 1. English keys (canonical, per AGENTS.md): {"suggestions": [...], "overallComment": "..."}
 * 2. Japanese keys (legacy): {"指摘": [...], "全体講評": "..."}
 * 
 * Unlike backend's fixed 5-item padding, we return however many entries
 * the model produced (no forced padding to 5)
 * 
 * HARDENED: Never throws SyntaxError - returns empty on parse failure
 */
export function parseModelOutput(text: string): ParsedResponse {
  // Log raw output preview for debugging (never throws)
  const preview = text.length > 300 ? text.substring(0, 300) + '...' : text;
  console.log('[webllm] parseModelOutput input preview:', preview);
  
  const parsed = safeJsonParse(text);
  
  if (!parsed) {
    console.warn('[webllm] Failed to extract/parse JSON from model output');
    return {
      suggestions: [],
      overallComment: "AIの応答からJSONを抽出できませんでした。再度お試しください。",
    };
  }
  
  // Try English keys first (canonical format), then Japanese keys (fallback)
  let suggestionsList: unknown[];
  if (Array.isArray(parsed["suggestions"])) {
    suggestionsList = parsed["suggestions"];
    console.log('[webllm] Using English "suggestions" key');
  } else if (Array.isArray(parsed["指摘"])) {
    suggestionsList = parsed["指摘"];
    console.log('[webllm] Using Japanese "指摘" key');
  } else {
    suggestionsList = [];
  }
  
  // Try English key first, then Japanese
  let overallComment: string;
  if (typeof parsed["overallComment"] === 'string') {
    overallComment = parsed["overallComment"];
    console.log('[webllm] Using English "overallComment" key');
  } else if (typeof parsed["全体講評"] === 'string') {
    overallComment = parsed["全体講評"];
    console.log('[webllm] Using Japanese "全体講評" key');
  } else {
    overallComment = "";
  }

  // Map to CorrectionSuggestion format with defensive coding
  const suggestions: CorrectionSuggestion[] = [];
  for (let i = 0; i < suggestionsList.length; i++) {
    const item = suggestionsList[i];
    if (item && typeof item === 'object') {
      const entry = item as Record<string, unknown>;
      // Try English keys first, then Japanese
      const original = typeof entry["original"] === 'string' ? entry["original"]
        : typeof entry["箇所"] === 'string' ? entry["箇所"] : "";
      const reason = typeof entry["reason"] === 'string' ? entry["reason"]
        : typeof entry["コメント"] === 'string' ? entry["コメント"] : "";
      
      suggestions.push({
        id: String(i + 1),
        original,
        reason,
      });
    }
  }

  return { suggestions, overallComment };
}
