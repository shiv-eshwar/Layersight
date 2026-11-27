/** Two consecutive clean demo runs must finish under three minutes. */

export const REHEARSAL_LIMIT_SECONDS = 180;

/**
 * @param {{ ok: boolean, seconds: number }[]} runs
 * @returns {{ pass: boolean, consecutive: number }}
 */
export function evaluateRehearsals(runs) {
  let consecutive = 0;
  let streak = 0;
  for (const run of runs) {
    const clean = run.ok && run.seconds < REHEARSAL_LIMIT_SECONDS;
    streak = clean ? streak + 1 : 0;
    consecutive = Math.max(consecutive, streak);
  }
  return { pass: consecutive >= 2, consecutive };
}
