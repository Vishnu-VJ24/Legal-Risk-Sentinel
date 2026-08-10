/**
 * Utility for recognizing and manipulating internal section identifiers
 * like ARTICLE_1, 2.1, 3.6, EXHIBIT_4.72 within raw text.
 */

// Matches patterns like: ARTICLE_1, EXHIBIT_4.72, 2.1, 12.3.4
export const SECTION_ID_REGEX = /\b(ARTICLE_\d+|EXHIBIT_\d+(?:\.\d+)?|\d+\.\d+(?:\.\d+)?)\b/g;

/**
 * Extracts all section IDs from a given text block.
 */
export const extractSectionIds = (text: string): string[] => {
  const matches = text.match(SECTION_ID_REGEX);
  return matches ? Array.from(new Set(matches)) : [];
};

/**
 * Pre-processes markdown text, finding standalone section references
 * and converting them into clickable markdown links in the format [ID](#section-ID).
 * 
 * We check if the match is already inside an existing link to prevent double-linking.
 */
export const injectSectionMarkdownLinks = (markdownText: string): string => {
  // A naive approach: replace occurrences, but avoid existing links.
  // Using a negative lookahead/lookbehind is tricky, instead we can replace globally
  // but if it's already [ARTICLE_1] it gets messy. Fast and safe approach for this demo:
  
  // We'll replace occurrences that are NOT preceded by `[` and followed by `]`
  // We can do this with a replace function
  return markdownText.replace(SECTION_ID_REGEX, (match, p1, offset) => {
    const prevChar = markdownText.charAt(offset - 1);
    const nextChar = markdownText.charAt(offset + match.length);
    
    // If it's already bounded by brackets, it's likely a link or structured, ignore.
    if (prevChar === '[' || nextChar === ']') {
      return match;
    }
    
    // Convert to markdown link format with a special custom scheme
    return `[${match}](section://${match})`;
  });
};
