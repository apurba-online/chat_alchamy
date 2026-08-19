/** Compatibility wrapper. Model credentials never leave the server. */
import { chat } from './api';

export async function getAssistantResponse(messages: { role: string; content: string }[], uploadedContext?: string) {
  const response = await chat(messages, uploadedContext);
  return { content: response.answer, role: 'assistant' as const, response };
}
