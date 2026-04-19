import {logoutUser } from "./api.js";
import {

  renderTasks,
  openTutorialModal,
  closeTutorialModal,
  closeEditModule,
  openEditModule,
  saveModuleChanges,
  closeAddModuleModal,
  openAddModuleModal,
  saveAddModule,
  deleteCurrentModule,
  renderModules,
  getRecommendations,
  openTaskModal,
  closeTaskModal,
  saveTask
} from "./ui.js";
import { setModules, refreshModules } from "./state.js";

const slider = document.getElementById("motivation");
const recommendationBox = document.getElementById("recommendationBox");
const val = document.getElementById("val");

slider.oninput = () => {
  val.textContent = slider.value;
};

document.getElementById("tutorialBtn").onclick = openTutorialModal;
document.getElementById("closeTutorialBtn").onclick = closeTutorialModal;
document.getElementById("openModalBtn").onclick = openTaskModal;
document.getElementById("closeModalBtn").onclick = closeTaskModal;
document.getElementById("saveTaskBtn").onclick = saveTask;
document.getElementById("saveAddModuleBtn").onclick = saveAddModule;
document.getElementById("openAddModuleBtn").onclick = openAddModuleModal;
document.getElementById("closeAddModuleModal").onclick = closeAddModuleModal;
document.getElementById("deleteModuleBtn").onclick = deleteCurrentModule;
document.getElementById("saveModuleChanges").onclick = saveModuleChanges;

document.getElementById("getTasksBtn").onclick = getRecommendations;
window.onload = async () => {
     const res = await fetch("/api/check-session");
  const data = await res.json();

  if (!data.logged_in) {
    window.location.href = "/login";
  }
   await refreshModules();

  renderModules(
    document.getElementById("modulesList"),
    document.getElementById("moduleSelect")
  );

};


const toggleBtn = document.getElementById("toggleModulesBtn");
const modulesPanel = document.getElementById("modulesPanel");


toggleBtn.onclick = () => {
  const show = modulesPanel.style.display === "none";

  modulesPanel.style.display = show ? "block" : "none";

  // ✅ update button text
  toggleBtn.textContent = show ? "Hide Modules" : "View Modules";
};

document.getElementById("logout-btn").onclick = async () => {
  try {
    await logoutUser();

    // redirect after logout
    window.location.href = "/login";
  } catch (err) {
    console.error("Logout failed:", err);
  }
};
