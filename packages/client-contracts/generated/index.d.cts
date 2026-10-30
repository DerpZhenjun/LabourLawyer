// Generated client contract declarations. Do not edit.
/** Portable application API contracts. No network, storage or model side effects. */
export interface ChatMessage {
    role: 'user' | 'ai';
    content: string;
}
export interface AskMessage {
    role: 'user' | 'assistant';
    content: string;
}
export interface AskRequest {
    question: string;
    history: AskMessage[];
}
export interface AIStatus {
    ready: boolean;
    provider: string;
    model: string;
    local_model_started: boolean;
    message?: string;
    status?: string;
}
export declare function apiURL(base: string, path: string): string;
export declare function assertAIStatus(raw: unknown): AIStatus;
export declare const remoteReady: (s: AIStatus) => boolean;
export declare function buildAskRequest(question: string, raw: unknown): AskRequest;
export declare function parseStoredChat(text: string | null): ChatMessage[] | null;
export declare function createAnswerDecoder(): {
    push: (value: Uint8Array) => string;
    finish: () => string;
};
