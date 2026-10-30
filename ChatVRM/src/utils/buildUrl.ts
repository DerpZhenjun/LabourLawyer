/** Local asset URLs use the same public prefix fixed by next.config.js at build time. */
export function buildUrl(path: string): string {
  return (process.env.NEXT_PUBLIC_BASE_PATH || "") + path;
}
