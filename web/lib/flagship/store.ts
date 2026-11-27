"use client";

import { create } from "zustand";

import {
  DATASET_NAME,
  trainedConfig,
  untrainedConfig,
  WORKSPACE_EMAILS,
} from "@/lib/flagship/fixtures";
import type { FilterRule, LayerConfig, SimEmail, TrainingLevel } from "@/lib/flagship/types";

export interface SavedVersion {
  id: string;
  version: number;
  savedAt: string;
  config: LayerConfig;
}

interface FlagshipState {
  datasetName: string;
  emails: SimEmail[];
  versions: SavedVersion[];
  activeId: string;
  compareId: string;
  draft: LayerConfig;
  dirty: boolean;
  assumptionsOpen: boolean;
  hydrated: boolean;
  hydrate: (untrained: LayerConfig, trained: LayerConfig) => void;
  updateDraft: (recipe: (config: LayerConfig) => LayerConfig) => void;
  setTrainingLevel: (level: TrainingLevel) => void;
  setCustomCatchRate: (rate: number | null) => void;
  toggleRule: (id: string) => void;
  setRuleCatchRate: (id: string, rate: number) => void;
  removeRule: (id: string) => void;
  addRule: (rule: FilterRule) => void;
  replaceDraft: (config: LayerConfig) => void;
  saveVersion: () => void;
  loadVersion: (id: string) => void;
  setCompareId: (id: string) => void;
  setAssumptionsOpen: (open: boolean) => void;
}

function version(id: string, number: number, config: LayerConfig): SavedVersion {
  return {
    id,
    version: number,
    savedAt: "2026-11-27T00:00:00.000Z",
    config,
  };
}

const initialVersions = [
  version("cfg-v1", 1, untrainedConfig()),
  version("cfg-v2", 2, trainedConfig()),
];

export const useFlagship = create<FlagshipState>((set) => ({
  datasetName: DATASET_NAME,
  emails: WORKSPACE_EMAILS,
  versions: initialVersions,
  activeId: "cfg-v1",
  compareId: "cfg-v2",
  draft: untrainedConfig(),
  dirty: false,
  assumptionsOpen: false,
  hydrated: false,
  hydrate: (untrained, trained) =>
    set((state) => {
      if (state.hydrated || state.dirty) return { hydrated: true };
      return {
        hydrated: true,
        versions: [version("untrained", 1, untrained), version("trained", 2, trained)],
        activeId: "untrained",
        compareId: "trained",
        draft: structuredClone(untrained),
        dirty: false,
      };
    }),
  updateDraft: (recipe) =>
    set((state) => ({ draft: recipe(state.draft), dirty: true })),
  setTrainingLevel: (level) =>
    set((state) => ({
      dirty: true,
      draft: { ...state.draft, user_training: { level, catch_rate: null } },
    })),
  setCustomCatchRate: (rate) =>
    set((state) => ({
      dirty: true,
      draft: {
        ...state.draft,
        user_training: { ...state.draft.user_training, catch_rate: rate },
      },
    })),
  toggleRule: (id) =>
    set((state) => ({
      dirty: true,
      draft: {
        ...state.draft,
        email_filter: {
          ...state.draft.email_filter,
          rules: state.draft.email_filter.rules.map((rule) =>
            rule.id === id ? { ...rule, enabled: !rule.enabled } : rule,
          ),
        },
      },
    })),
  setRuleCatchRate: (id, rate) =>
    set((state) => ({
      dirty: true,
      draft: {
        ...state.draft,
        email_filter: {
          ...state.draft.email_filter,
          rules: state.draft.email_filter.rules.map((rule) =>
            rule.id === id ? { ...rule, catch_rate: rate } : rule,
          ),
        },
      },
    })),
  removeRule: (id) =>
    set((state) => ({
      dirty: true,
      draft: {
        ...state.draft,
        email_filter: {
          ...state.draft.email_filter,
          rules: state.draft.email_filter.rules.filter((rule) => rule.id !== id),
        },
      },
    })),
  addRule: (rule) =>
    set((state) => ({
      dirty: true,
      draft: {
        ...state.draft,
        email_filter: {
          ...state.draft.email_filter,
          rules: [...state.draft.email_filter.rules.filter((item) => item.id !== rule.id), rule],
        },
      },
    })),
  replaceDraft: (config) => set({ draft: config, dirty: true }),
  saveVersion: () =>
    set((state) => {
      const nextNumber = state.versions.reduce((max, item) => Math.max(max, item.version), 0) + 1;
      const id = `cfg-v${nextNumber}`;
      const saved = version(id, nextNumber, structuredClone(state.draft));
      saved.savedAt = new Date().toISOString();
      return {
        versions: [...state.versions, saved],
        activeId: id,
        dirty: false,
        draft: structuredClone(state.draft),
      };
    }),
  loadVersion: (id) =>
    set((state) => {
      const saved = state.versions.find((item) => item.id === id);
      if (!saved) return state;
      return { activeId: id, draft: structuredClone(saved.config), dirty: false };
    }),
  setCompareId: (id) => set({ compareId: id }),
  setAssumptionsOpen: (open) => set({ assumptionsOpen: open }),
}));

export function activeVersion(state: FlagshipState): SavedVersion | undefined {
  return state.versions.find((item) => item.id === state.activeId);
}

export function compareVersion(state: FlagshipState): SavedVersion | undefined {
  return state.versions.find((item) => item.id === state.compareId);
}
