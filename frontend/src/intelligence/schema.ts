import { z } from "zod";

export const EvidenceItemSchema = z.object({
  claim: z.string(),
  source: z.string(),
});

export const ReportSchema = z.object({
  moat: z.enum(["High", "Medium", "Low", "unknown"]),
  financial_health: z.enum(["Pass", "Fail", "unknown"]),
  valuation: z.enum(["Over-valued", "Under-valued", "unknown"]),
  base_case: z.string(),
  upside_case: z.string(),
  downside_case: z.string(),
  action: z.enum(["BUY", "HOLD", "SELL", "AVOID"]),
  reasoning: z.string(),
  evidence: z.array(EvidenceItemSchema).optional().nullable(),
});

export type ReportFields = z.infer<typeof ReportSchema>;

export const ReportFileSchema = z.object({
  ticker: z.string(),
  asOfUtc: z.string(),
  provider: z.string().optional().nullable(),
  model: z.string().optional().nullable(),
  inputsMissing: z.array(z.string()).optional().nullable(),
  filingFetchStatus: z.string().optional().nullable(),
  latestFilingMeta: z.unknown().optional().nullable(),
  report: ReportSchema,
});

export type ReportFile = z.infer<typeof ReportFileSchema>;

