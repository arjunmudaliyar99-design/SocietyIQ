// When usage analytics may run (docs/04 §10): a key, not local, and the person's consent.

export interface AnalyticsConfig {
  key?: string;
  host?: string;
  /** Same names as the backend APP_ENV: local, test, staging, production. */
  env?: string;
}

export function analyticsAllowed(config: AnalyticsConfig, consented: boolean): boolean {
  return Boolean(config.key) && (config.env ?? "local") !== "local" && consented;
}
