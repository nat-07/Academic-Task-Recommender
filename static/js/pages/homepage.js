import { logoutUser } from "../api.js";

/* -----------------------------
   ELEMENTS
----------------------------- */
const slider = document.getElementById("motivation");
const val = document.getElementById("val");
const recommendationBox = document.getElementById("recommendationBox");

// Task modal
const taskModal = document.getElementById("taskModal");
const openTaskBtn = document.getElementById("openModalBtn");
const closeTaskBtn = document.getElementById("closeModalBtn");
const saveTaskBtn = document.getElementById("saveTaskBtn");
const taskNameInput = document.getElementById("taskNameInput");
const moduleSelect = document.getElementById("moduleSelect");
const taskTypeSelect = document.getElementById("taskTypeSelect");

// Module modal
const editModal = document.getElementById("editModuleModal");
const moduleModalTitle = document.getElementById("moduleModalTitle");
const deleteModuleBtn = document.getElementById("deleteModuleBtn");
const closeEditModalBtn = document.getElementById("closeEditModal");
const saveModuleChangesBtn = document.getElementById("saveModuleChanges");
const editModuleName = document.getElementById("editModuleName");
const editLikeness = document.getElementById("editLikeness");
const likenessVal = document.getElementById("likenessVal");
const editDifficulty = document.getElementById("editDifficulty");
const difficultyVal = document.getElementById("difficultyVal");

const tutorialModal = document.getElementById("tutorialModal");
const tutorialBtn = document.getElementById("tutorialBtn");
const closeTutorialBtn = document.getElementById("closeTutorialBtn");
// Module panel
const toggleBtn = document.getElementById("toggleModulesBtn");
const modulesPanel = document.getElementById("modulesPanel");
const modulesList = document.getElementById("modulesList");

// Login
const loginBtn = document.getElementById("loginBtn");

const taskDifficulty = document.getElementById("taskDifficulty");
const taskDifficultyVal = document.getElementById("taskDifficultyVal");

taskDifficulty.oninput = () => {
  taskDifficultyVal.textContent = taskDifficulty.value;
};
/* -----------------------------
   STATE
----------------------------- */
let modules = []; // start empty

tutorialBtn.onclick = () => openModal(tutorialModal);
closeTutorialBtn.onclick = () => closeModal(tutorialModal);
// Fetch modules from backend
async function loadModules() {
  try {
    const res = await fetch("/api/modules");
    const data = await res.json();
    console.log("Loaded modules:", data.modules); // debug
    if (data.status === "success") {
      modules = data.modules.map((m) => ({
        module_id: m.module_id,
        name: m.name,
        likeness: m.likeness,
        difficulty: m.difficulty,
      }));
      renderModules(); // render after fetching
    }
  } catch (err) {
    console.error("Failed to load modules:", err);
  }
}
const addModuleModal = document.getElementById("addModuleModal");
const addModuleDropdown = document.getElementById("addModuleDropdown");
const addLikeness = document.getElementById("addLikeness");
const addLikenessVal = document.getElementById("addLikenessVal");
const addDifficulty = document.getElementById("addDifficulty");
const addDifficultyVal = document.getElementById("addDifficultyVal");
const saveAddModuleBtn = document.getElementById("saveAddModuleBtn");
const closeAddModuleModal = document.getElementById("closeAddModuleModal");

// Update slider label
addLikeness.oninput = () => {
  addLikenessVal.textContent = addLikeness.value;
};

addDifficulty.oninput = () => {
  addDifficultyVal.textContent = addDifficulty.value;
};
// Open/close modal
function openAddModuleModal() {
  addModuleDropdown.value = "";
  addLikeness.value = 0.5;
  addLikenessVal.textContent = "0.5";
  addDifficultyVal.value = 0.5;
  addModuleModal.style.display = "flex";
}



document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("logout-btn")?.addEventListener("click", async () => {
  console.log()
  await logoutUser();
  window.location.href = "/login";
});
});

closeAddModuleModal.onclick = () => (addModuleModal.style.display = "none");
window.onclick = (e) => {
  if (e.target === editModal) closeModal(editModal);
  if (e.target === taskModal) closeModal(taskModal);
  if (e.target === addModuleModal) closeModal(addModuleModal);
  if (e.target === tutorialModal) closeModal(tutorialModal);
};
// Save module
saveAddModuleBtn.onclick = async () => {
  const name = addModuleDropdown.value;
  const likeness = parseFloat(addLikeness.value);
  const difficulty = parseInt(addDifficulty.value);

  if (!name) return alert("Select a module");

  try {
    const res = await fetch("/api/add-module", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, likeness, difficulty }),
    });

    const data = await res.json();
    if (data.status === "success") {
      addModuleModal.style.display = "none";
      loadModules(); // refresh modules list
    } else {
      alert(data.message || "Failed to add module");
    }
  } catch (err) {
    console.error("Error adding module:", err);
    alert("Error adding module");
  }
};

let currentModuleIndex = null;

/* -----------------------------
   HELPERS (MODALS)
----------------------------- */
function openModal(modal) {
  modal.style.display = "flex";
}

function closeModal(modal) {
  modal.style.display = "none";
}

/* -----------------------------
   MOTIVATION
----------------------------- */
slider.oninput = () => (val.textContent = slider.value);

/* -----------------------------
   INITIAL MESSAGE
----------------------------- */
recommendationBox.innerHTML = `
  <div class="placeholder">
    Set your motivation and press "Get Tasks"
  </div>
`;
recommendationBox.style.display = "block";

/* -----------------------------
   TASK RECOMMENDATIONS
----------------------------- */
document.getElementById("getTasksBtn").onclick = getRecommendations;

async function getRecommendations() {
  try {
    recommendationBox.innerHTML = `
      <div class="loading-container">
        <div class="loading-bar"></div>
      </div>
    `;

    const res = await fetch("/api/recommend-task", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        motivation: parseFloat(slider.value),
      }),
    });

    const data = await res.json();

    if (data.status === "ranked") {
      recommendationBox.innerHTML = data.tasks
        .slice(0, 5)
        .map(
          (t) => `
        <div class="task-item">
          <div class="task-content">
            <div class="task-name">${t.task_description}</div>
            <div class="task-type">${t.task_type}</div>
          </div>
          <button class="task-btn" onclick="completeTask(${t.task_id})">Done</button>
        </div>
      `,
        )
        .join("");
    } else {
      recommendationBox.innerHTML = `<div class="placeholder">No tasks available</div>`;
    }
  } catch {
    recommendationBox.innerHTML = `<div class="placeholder">Error</div>`;
  }
}

async function completeTask(taskId) {
  await fetch("/api/complete-task", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      task_id: taskId,
      motivation: parseFloat(slider.value),
    }),
  });

  getRecommendations();
}

/* -----------------------------
   MODULE PANEL
----------------------------- */
toggleBtn.onclick = () => {
  const show = modulesPanel.style.display === "none";
  modulesPanel.style.display = show ? "block" : "none";
  toggleBtn.textContent = show ? "Hide Modules" : "Edit Modules";

  if (show) renderModules();
};

/* -----------------------------
   RENDER MODULES
----------------------------- */
function renderModules() {
  modulesList.innerHTML = modules
    .map(
      (m, i) => `
    <div class="module-item">
      <span>${m.name}</span>
      <button class="edit-btn" onclick="openEditModule(${i})">Edit</button>
    </div>
  `,
    )
    .join("");

  updateModuleDropdown();
}

function updateModuleDropdown() {
  moduleSelect.innerHTML = `
    <option disabled selected>Select module</option>
    ${modules.map((m) => `<option value="${m.name}">${m.name}</option>`).join("")}
  `;
}

/* -----------------------------
   EDIT MODULE
----------------------------- */
function openEditModule(index) {
  currentModuleIndex = index;
  const m = modules[index];

  moduleModalTitle.textContent = "Edit Module";
  editModuleName.value = m.name;
  editLikeness.value = m.likeness;
  editDifficulty.value = m.difficulty;
  likenessVal.textContent = m.likeness;
  difficultyVal.textContent = m.difficulty;
  deleteModuleBtn.style.display = "inline-block";
  openModal(editModal);
}

/* -----------------------------
   SAVE MODULE
----------------------------- */
saveModuleChangesBtn.onclick = async () => {
  const name = editModuleName.value.trim();
  if (!name) return alert("Enter name");

  const updatedModule = {
    name,
    likeness: parseFloat(editLikeness.value),
    difficulty: parseFloat(editDifficulty.value),
  };

  try {
    // Include module ID if editing an existing module
    if (currentModuleIndex !== null) {
      updatedModule.module_id = modules[currentModuleIndex].module_id;
    }

    const res = await fetch("/api/edit-module", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(updatedModule),
    });

    const data = await res.json();

    if (data.status !== "success") {
      return alert("Failed to save module");
    }

    if (currentModuleIndex === null) {
      // New module added
      modules.push(updatedModule);
    } else {
      // Update existing module locally
      modules[currentModuleIndex] = updatedModule;
    }

    closeModal(editModal);
    loadModules();
  } catch (err) {
    console.error("Error saving module:", err);
    alert("Error saving module");
  }
};

/* -----------------------------
   DELETE MODULE
----------------------------- */
deleteModuleBtn.onclick = async () => {
  if (currentModuleIndex === null || currentModuleIndex === undefined) return;

  const m = modules[currentModuleIndex];
  const confirmDelete = confirm(
    `Are you sure you want to delete "${m.name}"?\nAll your current tasks for this module will be removed.`,
  );

  if (!confirmDelete) return;

  try {
    const res = await fetch("/api/delete-module", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ module_id: m.module_id }),
    });

    const data = await res.json();

    if (data.status === "success") {
      // Remove locally after successful backend delete
      modules.splice(currentModuleIndex, 1);
      renderModules();
      closeModal(editModal);
    } else {
      alert(data.message || "Failed to delete module");
    }
  } catch (err) {
    console.error("Error deleting module:", err);
    alert("Error deleting module");
  }
};

/* -----------------------------
   MODAL CLOSE
----------------------------- */
closeEditModalBtn.onclick = () => closeModal(editModal);
closeTaskBtn.onclick = () => closeModal(taskModal);

window.onclick = (e) => {
  if (e.target === editModal) closeModal(editModal);
  if (e.target === taskModal) closeModal(taskModal);
};

/* -----------------------------
   SLIDER LABEL
----------------------------- */
editLikeness.oninput = () => {
  likenessVal.textContent = editLikeness.value;
};

editDifficulty.oninput = () => {
  difficultyVal.textContent = editDifficulty.value;
};

/* -----------------------------
   TASK MODAL
----------------------------- */
openTaskBtn.onclick = () => {
  taskDifficulty.value = 0.5;
  taskDifficultyVal.textContent = "0.5";
  openModal(taskModal);
};

saveTaskBtn.onclick = async () => {
  const description = taskNameInput.value.trim();
  const module = moduleSelect.value;
  const type = taskTypeSelect.value;
  const difficulty = parseFloat(taskDifficulty.value);
  const estimated_time = parseInt(
    document.getElementById("estimatedTime").value,
  );

  if (!description || !module || !type) return alert("Fill all fields");

  await fetch("/api/add-task", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      user_id: 1,
      task_description: description,
      module: module,
      task_type: type,
      difficulty: difficulty,
      estimated_time: estimated_time,
    }),
  });

  closeModal(taskModal);
  taskNameInput.value = "";
  getRecommendations();
};

/* -----------------------------
   LOGIN
----------------------------- */


window.onload = async () => {
  try {
    const res = await fetch("/api/check-session");
    const data = await res.json();

    if (data.logged_in) {
      // user still logged in

      loadModules();
    } else {
      // show login
    }
  } catch (err) {
    console.error("Session check failed", err);
  }
};

/* -----------------------------
   INIT
----------------------------- */
