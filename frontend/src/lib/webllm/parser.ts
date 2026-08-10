/**
 * Output parsing for WebLLM responses
 * Ported from backend/app/main.py generate_gemini_suggestions parsing logic
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
 * Parse WebLLM model output into structured suggestions
 * Following design.md Decision 3: reuse backend parsing strategy
 * 
 * Unlike backend's fixed 5-item padding, we return however many entries
 * the model produced (no forced padding to 5)
 */
export function parseModelOutput(text: string): ParsedResponse {
  try {
    // Extract JSON blob from model output using same regex as backend
    const match = text.match(/\{\s*"指摘".*\}/s);
    
    if (!match) {
      return {
        suggestions: [],
        overallComment: "AIの応答からJSONを抽出できませんでした。再度お試しください。",
      };
    }

    const parsed = JSON.parse(match[0]);
    const shitekiList = parsed["指摘"] || [];
    const overallComment = parsed["全体講評"] || "";

    // Map to CorrectionSuggestion format
    const suggestions: CorrectionSuggestion[] = shitekiList.map(
      (shiteki: { 箇所?: string; コメント?: string }, index: number) => ({
        id: String(index + 1),
        original: shiteki["箇所"] || "",
        reason: shiteki["コメント"] || "",
      })
    );

    return { suggestions, overallComment };
  } catch (error) {
    // Handle malformed/unparsable output gracefully
    console.error("Failed to parse model output:", error);
    return {
      suggestions: [],
      overallComment: `AIの応答を解析できませんでした: ${error instanceof Error ? error.message : "不明なエラー"}`,
    };
  }
}
