"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useRef, useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { ApplicabilityMatrix, FunnelChart } from "@/components/flagship/charts";
import { EmptyState } from "@/components/shell/empty-state";
import { formatPct, formatRel } from "@/lib/flagship/format";
import { compareVersion, useFlagship } from "@/lib/flagship/store";
import { LAYER_LABEL, LEVEL_LABEL, type FilterRule, type TrainingLevel } from "@/lib/flagship/types";
import { useComparisonPreview, useSimulationPreview } from "@/lib/flagship/use-results";
import { useWorkspaceDataset } from "@/lib/use-dataset";
import { exportConfigYaml, parseConfigYaml } from "@/lib/flagship/yaml-config";

const ruleSchema = z.object({
  id: z
    .string()
    .trim()
    .min(1, "Give the rule an id")
    .regex(/^[a-z0-9_]+$/, "Use lowercase letters, numbers, and underscores"),
  description: z.string().trim().min(1, "Say what the rule does"),
  feature: z.string().trim().min(1, "Name the feature to match"),
  op: z.enum(["eq", "ne", "in", "gte", "lte", "contains", "exists"]),
  value: z.string(),
  catch_rate: z.number().min(0).max(100),
});

type RuleForm = z.infer<typeof ruleSchema>;

function RateField({
  label,
  value,
  onChange,
}: {
  label: string;
  value: number;
  onChange: (next: number) => void;
}) {
  const percent = Math.round(value * 100);
  return (
    <label className="grid gap-1 text-sm">
      <span className="flex items-baseline justify-between gap-3">
        <span>{label}</span>
        <span className="ls-mono">{percent}%</span>
      </span>
      <input
        type="range"
        min={0}
        max={100}
        value={percent}
        aria-valuetext={`${percent}%`}
        onChange={(event) => onChange(Number(event.target.value) / 100)}
      />
    </label>
  );
}

function Switch({
  checked,
  label,
  onClick,
}: {
  checked: boolean;
  label: string;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      onClick={onClick}
      className={`relative h-6 w-11 rounded-full ${checked ? "bg-[#8b7cff]" : "bg-[#2a2e3c]"}`}
    >
      <span
        className={`absolute top-0.5 h-5 w-5 rounded-full bg-[#f4f6fb] transition-transform ${
          checked ? "translate-x-5" : "translate-x-0.5"
        }`}
      />
    </button>
  );
}

function matchValue(op: RuleForm["op"], raw: string): FilterRule["match"]["value"] {
  if (op === "exists") return undefined;
  if (op === "in") {
    return raw
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean);
  }
  if (op === "gte" || op === "lte") return Number(raw);
  if (raw === "true") return true;
  if (raw === "false") return false;
  return raw;
}

export function DefenseScreen() {
  const datasetId = useWorkspaceDataset();
  const draft = useFlagship((state) => state.draft);
  const versions = useFlagship((state) => state.versions);
  const activeId = useFlagship((state) => state.activeId);
  const dirty = useFlagship((state) => state.dirty);
  const updateDraft = useFlagship((state) => state.updateDraft);
  const setTrainingLevel = useFlagship((state) => state.setTrainingLevel);
  const setCustomCatchRate = useFlagship((state) => state.setCustomCatchRate);
  const toggleRule = useFlagship((state) => state.toggleRule);
  const setRuleCatchRate = useFlagship((state) => state.setRuleCatchRate);
  const removeRule = useFlagship((state) => state.removeRule);
  const addRule = useFlagship((state) => state.addRule);
  const replaceDraft = useFlagship((state) => state.replaceDraft);
  const saveVersion = useFlagship((state) => state.saveVersion);
  const loadVersion = useFlagship((state) => state.loadVersion);
  const fileRef = useRef<HTMLInputElement>(null);
  const [importErrors, setImportErrors] = useState<{ field: string; message: string }[]>([]);
  const [importWarnings, setImportWarnings] = useState<string[]>([]);

  const preview = useSimulationPreview(
    draft,
    datasetId,
    draft.simulation.runs,
    draft.simulation.seed,
    true,
  );
  const other = useFlagship((state) => compareVersion(state)?.config);
  const versus = useComparisonPreview(
    draft,
    other ?? draft,
    other ? datasetId : null,
    draft.simulation.runs,
    draft.simulation.seed,
  );

  const form = useForm<RuleForm>({
    resolver: zodResolver(ruleSchema),
    defaultValues: {
      id: "",
      description: "",
      feature: "auth.dmarc",
      op: "eq",
      value: "fail",
      catch_rate: 85,
    },
  });

  function onExport() {
    const blob = new Blob([exportConfigYaml(draft)], { type: "application/yaml" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = "layersight-config.yaml";
    anchor.click();
    URL.revokeObjectURL(url);
  }

  async function onImport(file: File) {
    const text = await file.text();
    const parsed = parseConfigYaml(text);
    setImportWarnings(parsed.warnings);
    setImportErrors(parsed.errors);
    if (parsed.config) replaceDraft(parsed.config);
  }

  if (!datasetId) {
    return (
      <EmptyState title="No dataset selected">
        Load the 20-email test set in Triage. Residual risk is the engine&apos;s closed form for that set.
      </EmptyState>
    );
  }

  const closedForm = preview.result?.aggregate.closed_form;

  return (
    <div data-testid="defense-screen">
      <div className="flex flex-wrap items-end justify-end gap-2">
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            className="rounded-full border border-white/10 bg-black/30 px-3.5 py-1.5 text-sm"
            onClick={() => fileRef.current?.click()}
          >
            Import YAML
          </button>
          <input
            ref={fileRef}
            type="file"
            accept=".yaml,.yml,text/yaml"
            className="hidden"
            onChange={(event) => {
              const file = event.target.files?.[0];
              if (file) void onImport(file);
              event.target.value = "";
            }}
          />
          <button
            type="button"
            className="rounded-full border border-white/10 bg-black/30 px-3.5 py-1.5 text-sm"
            onClick={onExport}
          >
            Export YAML
          </button>
          <button
            type="button"
            className="rounded-full bg-white px-3.5 py-1.5 text-sm font-medium text-[#101218]"
            onClick={saveVersion}
          >
            Save as new version
          </button>
        </div>
      </div>

      {importErrors.length > 0 ? (
        <ul role="alert" className="mt-4 grid gap-1 rounded-md border border-[#ff5c6c] p-3 text-sm">
          {importErrors.map((error) => (
            <li key={`${error.field}-${error.message}`}>
              <span className="ls-mono text-[#ff5c6c]">{error.field}</span> {error.message}
            </li>
          ))}
        </ul>
      ) : null}
      {importWarnings.length > 0 ? (
        <ul className="mt-3 grid gap-1 text-sm text-[#ff8a3d]">
          {importWarnings.map((warning) => (
            <li key={warning}>{warning}</li>
          ))}
        </ul>
      ) : null}

      <div className="mt-6 grid items-start gap-4 lg:grid-cols-[minmax(0,1fr)_20rem]">
        <div className="grid gap-4">
          <section className="ls-card grid gap-3 p-4">
            <label className="grid gap-1 text-sm">
              Configuration name
              <input
                type="text"
                value={draft.name}
                onChange={(event) =>
                  updateDraft((config) => ({ ...config, name: event.target.value }))
                }
              />
            </label>
            <label className="grid gap-1 text-sm">
              Organization domains
              <input
                type="text"
                value={draft.org_domains.join(", ")}
                onChange={(event) =>
                  updateDraft((config) => ({
                    ...config,
                    org_domains: event.target.value
                      .split(",")
                      .map((domain) => domain.trim())
                      .filter(Boolean),
                  }))
                }
              />
            </label>
          </section>

          <section className="ls-card grid gap-4 p-4" data-testid="layer-email-filter">
            <header>
              <p className="text-xs text-[#949aab]">1</p>
              <h2 className="text-base font-semibold">{LAYER_LABEL.email_filter}</h2>
            </header>
            <RateField
              label="Base catch rate"
              value={draft.email_filter.base_catch_rate}
              onChange={(value) =>
                updateDraft((config) => ({
                  ...config,
                  email_filter: { ...config.email_filter, base_catch_rate: value },
                }))
              }
            />
            <ul className="grid gap-3">
              {draft.email_filter.rules.map((rule) => (
                <li key={rule.id} className="grid gap-2 border-t border-[#2a2e3c] pt-3">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-sm">{rule.description || rule.id}</p>
                      <p className="ls-mono text-xs text-[#949aab]">
                        {rule.match.feature} {rule.match.op}{" "}
                        {Array.isArray(rule.match.value)
                          ? rule.match.value.join(", ")
                          : String(rule.match.value ?? "")}
                      </p>
                    </div>
                    <Switch
                      checked={rule.enabled}
                      label={`${rule.enabled ? "Disable" : "Enable"} ${rule.id}`}
                      onClick={() => toggleRule(rule.id)}
                    />
                  </div>
                  <RateField
                    label="Catch rate"
                    value={rule.catch_rate}
                    onChange={(value) => setRuleCatchRate(rule.id, value)}
                  />
                  <button
                    type="button"
                    className="justify-self-start text-sm text-[#949aab]"
                    onClick={() => removeRule(rule.id)}
                  >
                    Remove rule
                  </button>
                </li>
              ))}
            </ul>
            <form
              className="grid gap-2 border-t border-[#2a2e3c] pt-3"
              onSubmit={form.handleSubmit((values) => {
                if (values.op !== "exists" && values.value.trim() === "") {
                  form.setError("value", { message: "Enter the value to match." });
                  return;
                }
                addRule({
                  id: values.id,
                  description: values.description,
                  match: { feature: values.feature, op: values.op, value: matchValue(values.op, values.value) },
                  catch_rate: values.catch_rate / 100,
                  enabled: true,
                });
                form.reset();
              })}
            >
              <p className="text-sm font-semibold">Add a filter rule</p>
              <div className="grid gap-2 sm:grid-cols-2">
                <input placeholder="id" aria-label="Rule id" {...form.register("id")} />
                <input
                  placeholder="What it does"
                  aria-label="Rule description"
                  {...form.register("description")}
                />
                <input
                  placeholder="feature"
                  aria-label="Feature"
                  list="feature-names"
                  {...form.register("feature")}
                />
                <datalist id="feature-names">
                  <option value="auth.dmarc" />
                  <option value="links.max_lookalike_score" />
                  <option value="attachment.risk_class" />
                  <option value="header.reply_to_mismatch" />
                  <option value="content.urgency" />
                  <option value="risk_score" />
                </datalist>
                <select aria-label="Operator" {...form.register("op")}>
                  {["eq", "ne", "in", "gte", "lte", "contains", "exists"].map((op) => (
                    <option key={op}>{op}</option>
                  ))}
                </select>
                <input placeholder="value" aria-label="Match value" {...form.register("value")} />
                <label className="text-sm text-[#949aab]">
                  Catch rate %
                  <input
                    type="number"
                    min={0}
                    max={100}
                    aria-label="Rule catch rate percent"
                    {...form.register("catch_rate", { valueAsNumber: true })}
                  />
                </label>
              </div>
              {Object.values(form.formState.errors).map((error) => (
                <p key={error.message} role="alert" className="text-sm text-[#ff5c6c]">
                  {error.message}
                </p>
              ))}
              <button
                type="submit"
                className="justify-self-start rounded-full border border-white/10 bg-black/30 px-3.5 py-1.5 text-sm"
              >
                Add rule
              </button>
            </form>
          </section>

          <section className="ls-card grid gap-3 p-4" data-testid="layer-user">
            <header>
              <p className="text-xs text-[#949aab]">2</p>
              <h2 className="text-base font-semibold">{LAYER_LABEL.user}</h2>
            </header>
            <div className="flex flex-wrap gap-2">
              {(["none", "basic", "advanced"] as TrainingLevel[]).map((level) => {
                const selected = draft.user_training.level === level && draft.user_training.catch_rate === null;
                return (
                  <button
                    key={level}
                    type="button"
                    data-testid={`training-${level}`}
                    aria-pressed={selected}
                    className={`rounded-full px-3 py-1.5 text-sm ${
                      selected ? "bg-white text-[#101218]" : "border border-white/10 text-[#c8cdd8]"
                    }`}
                    onClick={() => setTrainingLevel(level)}
                  >
                    {LEVEL_LABEL[level]}
                  </button>
                );
              })}
            </div>
            <RateField
              label="Custom catch rate"
              value={draft.user_training.catch_rate ?? 0}
              onChange={(value) => setCustomCatchRate(value)}
            />
            <button
              type="button"
              className="justify-self-start text-sm text-[#949aab]"
              onClick={() => setCustomCatchRate(null)}
            >
              Use the training-level table
            </button>
          </section>

          <section className="ls-card grid gap-3 p-4" data-testid="layer-application">
            <header>
              <p className="text-xs text-[#949aab]">3</p>
              <h2 className="text-base font-semibold">{LAYER_LABEL.application_control}</h2>
            </header>
            <RateField
              label="Effectiveness"
              value={draft.application_control.effectiveness}
              onChange={(value) =>
                updateDraft((config) => ({
                  ...config,
                  application_control: { ...config.application_control, effectiveness: value },
                }))
              }
            />
            <RateField
              label="Macro documents"
              value={draft.application_control.overrides.macro_document ?? 0}
              onChange={(value) =>
                updateDraft((config) => ({
                  ...config,
                  application_control: {
                    ...config.application_control,
                    overrides: { ...config.application_control.overrides, macro_document: value },
                  },
                }))
              }
            />
            <RateField
              label="Executables"
              value={draft.application_control.overrides.executable ?? 0}
              onChange={(value) =>
                updateDraft((config) => ({
                  ...config,
                  application_control: {
                    ...config.application_control,
                    overrides: { ...config.application_control.overrides, executable: value },
                  },
                }))
              }
            />
          </section>

          <section className="ls-card grid gap-3 p-4" data-testid="layer-antivirus">
            <header>
              <p className="text-xs text-[#949aab]">4</p>
              <h2 className="text-base font-semibold">{LAYER_LABEL.antivirus}</h2>
            </header>
            <RateField
              label="Detection rate"
              value={draft.antivirus.detection_rate}
              onChange={(value) =>
                updateDraft((config) => ({ ...config, antivirus: { detection_rate: value } }))
              }
            />
          </section>

          <section className="ls-card grid gap-3 p-4" data-testid="layer-segmentation">
            <header>
              <p className="text-xs text-[#949aab]">5</p>
              <h2 className="text-base font-semibold">{LAYER_LABEL.segmentation}</h2>
            </header>
            <RateField
              label="Containment rate"
              value={draft.segmentation.containment_rate}
              onChange={(value) =>
                updateDraft((config) => ({
                  ...config,
                  segmentation: { ...config.segmentation, containment_rate: value },
                }))
              }
            />
            <div className="flex items-center justify-between gap-3 text-sm">
              <span>Also contain credential harvesting</span>
              <Switch
                checked={draft.segmentation.applies_to_credential_harvest}
                label="Containment applies to credential harvesting"
                onClick={() =>
                  updateDraft((config) => ({
                    ...config,
                    segmentation: {
                      ...config.segmentation,
                      applies_to_credential_harvest: !config.segmentation.applies_to_credential_harvest,
                    },
                  }))
                }
              />
            </div>
          </section>
        </div>

        <aside className="grid gap-4 lg:sticky lg:top-28">
          <section className="ls-card p-4" aria-live="polite">
            <h2 className="text-sm font-semibold">Estimated pass-through</h2>
            <p className="mt-1 text-sm text-[#949aab]">Probability a phishing attack succeeds through all configured layers.</p>
            <p className="ls-mono mt-3 text-5xl font-semibold tracking-[-0.04em] text-[#ff5c6c]" data-testid="residual-risk">
              {closedForm == null ? "—" : formatPct(closedForm)}
            </p>
            <p className="mt-2 text-sm text-[#949aab]">
              {preview.result
                ? `Across ${preview.result.aggregate.email_count} predicted phishing emails. Modeled estimate.`
                : "Waiting for the engine."}
            </p>
            {versus.result ? (
              <p className="mt-2 text-sm">
                {versus.result.relative_reduction > 0
                  ? `${versus.result.config_b_name} models ${formatPct(versus.result.result_b.aggregate.closed_form)} on this dataset, ${formatRel(versus.result.relative_reduction)} lower.`
                  : `${versus.result.config_b_name} models the same ${formatPct(versus.result.result_b.aggregate.closed_form)} on this dataset.`}
              </p>
            ) : null}
            <p className="mt-2 text-xs text-[#949aab]">
              {preview.result
                ? `Engine ${preview.result.engine_version}. Closed form, so a training change updates without waiting on Monte Carlo.`
                : preview.error ?? "Closed form from the engine."}
              {preview.loading ? " Updating." : ""}
            </p>
            {dirty ? <p className="mt-2 text-xs text-[#ff8a3d]">Unsaved edits</p> : null}
          </section>
          <section className="ls-card p-4">
            <h2 className="text-base font-semibold">Versions</h2>
            <ul className="mt-3 grid gap-2">
              {versions.map((version) => (
                <li key={version.id}>
                  <button
                    type="button"
                    className={`w-full rounded-xl px-2 py-1.5 text-left text-sm ${
                      version.id === activeId ? "bg-white/10 text-white" : "text-[#c8cdd8]"
                    }`}
                    onClick={() => loadVersion(version.id)}
                  >
                    v{version.version} · {version.config.name}
                  </button>
                </li>
              ))}
            </ul>
            <p className="mt-2 text-xs text-[#949aab]">
              Choosing a version replaces the draft, including unsaved edits.
            </p>
          </section>
        </aside>
      </div>
      <div className="mt-4 grid gap-4">
        {preview.result ? <FunnelChart result={preview.result} /> : null}
        <ApplicabilityMatrix
          credentialSegmentation={draft.segmentation.applies_to_credential_harvest}
        />
      </div>
    </div>
  );
}
