// =====================================================================
// 内存数据存储 —— 演示用。真实实现由 core/parser + core/analysis 注入。
// =====================================================================
import { SAMPLE_SESSION, SAMPLE_ANALYSES } from "./data.js";

const state = {
  session: null,
  analyses: [],
  importedText: "",
};

export function loadSample() {
  state.session = SAMPLE_SESSION;
  state.analyses = SAMPLE_ANALYSES;
}

export function importSession({ session, analyses }) {
  state.session = session;
  state.analyses = analyses;
}

export function getSession() {
  return state.session;
}

export function getAnalyses() {
  return state.analyses;
}

export function getAnalysis(segmentId) {
  return state.analyses.find((a) => a.segment_id === segmentId) || null;
}

export function isLoaded() {
  return Boolean(state.session && state.analyses.length);
}
