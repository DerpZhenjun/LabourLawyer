// Generated client contract declarations. Do not edit.
/** Portable application API contracts. No network, storage or model side effects. */
export interface ChatMessage {
    role: 'user' | 'ai';
    content: string;
}
import type { components } from '../src/generated/stable-api';
import { API_LIMITS } from '../src/generated/api-limits';
export { API_LIMITS };
export type AskMessage = components['schemas']['ChatMessage'];
export type AskRequest = Omit<components['schemas']['QuestionRequest'], 'history'> & {
    history: AskMessage[];
};
type StatusWire = components['schemas']['AIStatusResponse'];
export type AIStatus = Pick<StatusWire, 'ready' | 'provider' | 'model' | 'local_model_started'> & {
    message?: NonNullable<StatusWire['message']>;
    status?: NonNullable<StatusWire['status']>;
};
export declare function apiURL(base: string, path: string): string;
export declare function assertAIStatus(raw: unknown): AIStatus;
export declare const remoteReady: (s: AIStatus) => boolean;
export declare function buildAskRequest(question: string, raw: unknown): AskRequest;
export declare function parseStoredChat(text: string | null): ChatMessage[] | null;
export declare function createAnswerDecoder(): {
    push: (value: Uint8Array) => string;
    finish: () => string;
};
