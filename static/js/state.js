import { loadModulesRequest } from "./api.js";

export let modules = [];
export let currentModuleIndex = null;

export function getModules() {
  return modules;
}

export function setModules(newModules) {
  modules.length = 0;
  modules.push(...newModules);
}

export function setCurrentModuleIndex(index) {
  currentModuleIndex = index;
}

export function getCurrentModuleIndex() {
  return currentModuleIndex;
}
export async function refreshModules() {
  const data = await loadModulesRequest();
  setModules(data);
  return data;
}