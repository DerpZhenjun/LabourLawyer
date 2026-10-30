/** Checked page instances; runtime registration remains the native WeChat Page API. */
export type MiniEvent = {
    detail: {
        value: string;
    };
    currentTarget: {
        dataset: Record<string, string | number | undefined>;
    };
};
export type PageSpec<D, M, S = object> = {
    data: D;
} & M & ThisType<M & S & {
    data: D;
    setData(values: Partial<D> & Record<string, unknown>): void;
}>;
export interface LocalCase {
    id: string;
    title: string;
    client: string;
    employer?: string;
    stage: string;
    deadline: string;
    progress: number;
    urgent?: boolean;
}
export interface AppState {
    globalData: {
        apiBase: string;
        cases: LocalCase[];
    };
}
export type Response<T = unknown> = {
    statusCode: number;
    data: T;
    header?: Record<string, unknown>;
};
