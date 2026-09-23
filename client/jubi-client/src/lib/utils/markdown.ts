/**
 * Markdown -> sanitized HTML for chat messages.
 *
 * marked parses (GFM + single-newline breaks for chat feel);
 * DOMPurify strips scripts/event handlers — content comes from both
 * the user and the LLM, so nothing here is trusted.
 */
import { marked } from 'marked';
import DOMPurify from 'dompurify';

marked.setOptions({ gfm: true, breaks: true });

export function renderMarkdown(text: string): string {
	if (!text) return '';
	const html = marked.parse(text, { async: false }) as string;
	return DOMPurify.sanitize(html);
}