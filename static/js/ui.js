import {
  getModules,
  setCurrentModuleIndex,
  getCurrentModuleIndex,
  setModules,
  refreshModules
} from "./state.js";

import { updateModule, addModule, deleteModule, loadModulesRequest, getRecommendationsRequest, completeTaskRequest, addTask } from "./api.js";

export function openTutorialModal() {
  const tutorialModal = document.getElementById("tutorialModal");

  tutorialModal.style.display = "flex";
}

export function closeTutorialModal() {
  const tutorialModal = document.getElementById("tutorialModal");

  tutorialModal.style.display = "none";
}


export function renderTasks(tasks) {
  const recommendationBox = document.getElementById("recommendationBox");

  if (!tasks || tasks.length === 0) {
    recommendationBox.innerHTML =
      `<div class="placeholder">No active tasks available, please add tasks.</div>`;
    return;
  }

  recommendationBox.innerHTML = tasks
  .map(
    (t) => `
      <div class="task-item">
        <div class="task-content">
          <div class="task-name">
          ${t.rank <= 5 ? "⭐ " : ""}${t.rank}. ${t.task_description}
          </div>
          <div class="task-type">
            ${t.task_type} • ${t.module_name}
          </div>
        </div>
        <button class="task-btn" data-id="${t.task_id}">
          Done
        </button>
      </div>
    `
  )
  .join("");

  // attach events AFTER rendering
  recommendationBox.querySelectorAll(".task-btn").forEach((btn) => {
    btn.onclick = () => completeTask(btn.dataset.id);
  });
  console.log("TASK ITEMS:", recommendationBox.querySelectorAll(".task-item").length);
  setTimeout(() => {
  console.log("1s later HTML:", recommendationBox.innerHTML);
}, 1000);
}

export function openEditModule(index) {
  setCurrentModuleIndex(index);

  const modules = getModules(); // ✅ always read fresh state
  const m = modules[index];

  const editModal = document.getElementById("editModuleModal");
  const difficultySlider = document.getElementById("editDifficulty");
  const difficultyVal = document.getElementById("difficultyVal");
  const likenessSlider = document.getElementById("editLikeness");
  const likenessVal = document.getElementById("likenessVal");

  document.getElementById("editModuleName").value = m.name;
  likenessSlider.value = m.likeness;
  difficultySlider.value = m.difficulty;
  difficultyVal.textContent = m.difficulty;
  likenessVal.textContent = m.likeness;

  difficultySlider.oninput = () => {
    difficultyVal.textContent = difficultySlider.value;
  };

  likenessSlider.oninput = () => {
    likenessVal.textContent = likenessSlider.value;
  };

  editModal.style.display = "flex";
  document.getElementById("closeEditModal").onclick = closeEditModule;
}

export function closeEditModule() {
  const editModal = document.getElementById("editModuleModal");
  editModal.style.display = "none";
}

export async function saveModuleChanges() {
  const index = getCurrentModuleIndex();
  const modules = getModules();

  const editModuleName = document.getElementById("editModuleName");
  const editLikeness = document.getElementById("editLikeness");
  const editDifficulty = document.getElementById("editDifficulty");
  const editModal = document.getElementById("editModuleModal");

  const name = editModuleName.value.trim();
  if (!name) return alert("Enter name");

  const updatedModule = {
    name,
    likeness: parseFloat(editLikeness.value),
    difficulty: parseFloat(editDifficulty.value),
  };

  // attach id if editing
  if (index !== null) {
    updatedModule.module_id = modules[index].module_id;
  }

  try {
    const data = await updateModule(updatedModule);

    if (data.status !== "completed") {
      return alert("Failed to save module");
    }

    if (index === null) {
      modules.push(updatedModule);
    } else {
      modules[index] = updatedModule;
    }

    setModules(modules);
    editModal.style.display = "none";
  } catch (err) {
    console.error("Error saving module:", err);
    alert("Error saving module");
  }
}

export async function openAddModuleModal() {
  const addModuleDropdown = document.getElementById("addModuleDropdown");
  const addLikeness = document.getElementById("addLikeness");
  const addLikenessVal = document.getElementById("addLikenessVal");
  const addDifficulty = document.getElementById("addDifficulty");
  const addDifficultyVal = document.getElementById("addDifficultyVal");
  const addModuleModal = document.getElementById("addModuleModal");


  addModuleDropdown.value = "";

  addLikeness.value = 0.5;
  addLikenessVal.textContent = "0.5";

  addDifficulty.value = 0.5;
  addDifficultyVal.textContent = "0.5";

  addModuleModal.style.display = "flex";

  addLikeness.oninput = () => {
    addLikenessVal.textContent = addLikeness.value;
  };

  addDifficulty.oninput = () => {
    addDifficultyVal.textContent = addDifficulty.value;
  };
}

export function closeAddModuleModal() {
  const modal = document.getElementById("addModuleModal");
  if (modal) modal.style.display = "none";
}

export async function saveAddModule() {
  const addModuleDropdown = document.getElementById("addModuleDropdown");
  const addLikeness = document.getElementById("addLikeness");
  const addDifficulty = document.getElementById("addDifficulty");
  const addModuleModal = document.getElementById("addModuleModal");

  const name = addModuleDropdown.value;
  const likeness = parseFloat(addLikeness.value);
  const difficulty = parseFloat(addDifficulty.value);

  if (!name) return alert("Select a module");

  try {
    const data = await addModule({ name, likeness, difficulty });

    if (data.status === "created" ||data.status === "reactivated") {
      addModuleModal.style.display = "none";

      
      await refreshModules();
      renderModules(
    document.getElementById("modulesList"),
    document.getElementById("moduleSelect")
  );
    } else {
      alert(data.message || "Failed to add module");
    }
  } catch (err) {
    console.error("Error adding module:", err);
    alert("Error adding module");
  }
}

export async function deleteCurrentModule() {
  const index = getCurrentModuleIndex();
  const modules = getModules();

  if (index === null || index === undefined) return;

  const m = modules[index];

  const confirmDelete = confirm(
    `Are you sure you want to delete "${m.name}"?\nAll your current tasks for this module will be removed.`
  );

  if (!confirmDelete) return;

  try {
    const data = await deleteModule(m.module_id);

    if (data.status === "deleted") {
      modules.splice(index, 1);
      setModules(modules);

      document.getElementById("editModuleModal").style.display = "none";
      await refreshModules();
      renderModules(
    document.getElementById("modulesList"),
    document.getElementById("moduleSelect")
  );
  await getRecommendations()
    } else {
      alert(data.message || "Failed to delete module");
    }
  } catch (err) {
    console.error("Error deleting module:", err);
    alert("Error deleting module");
  }
}

export function renderModules(modulesList, moduleSelect) {
  const modules = getModules();

  // 🚨 EMPTY STATE
  if (!modules || modules.length === 0) {
    modulesList.innerHTML = `
      <div class="placeholder">
        No modules yet, press "+ Add Module" to add a new module
      </div>
    `;

    moduleSelect.innerHTML = `
      <option disabled selected>No modules available</option>
    `;

    return; // stop here
  }

  // ✅ render list
  modulesList.innerHTML = modules
    .map(
      (m, i) => `
        <div class="module-item">
          <span>${m.name}</span>
          <button class="edit-btn" data-index="${i}">Edit</button>
        </div>
      `
    )
    .join("");

  // ✅ dropdown
  moduleSelect.innerHTML = `
    <option disabled selected>Select module</option>
    ${modules
      .map((m) => `<option value="${m.name}">${m.name}</option>`)
      .join("")}
  `;

  // ✅ attach edit handlers
  modulesList.querySelectorAll(".edit-btn").forEach((btn) => {
    btn.onclick = () => openEditModule(btn.dataset.index);
  });
}

export async function getRecommendations() {
  const slider = document.getElementById("motivation");
  const recommendationBox = document.getElementById("recommendationBox");
  
  recommendationBox.innerHTML = `
      <div class="loading-container">
        <div class="loading-bar"></div>
      </div>
    `;;

  const data = await getRecommendationsRequest(parseFloat(slider.value));

  if (data.status === "success") {
    renderTasks(data.tasks);
  } else {
    renderTasks([]);
  }
}

export async function completeTask(taskId) {
  const slider = document.getElementById("motivation");

  await completeTaskRequest(taskId, parseFloat(slider.value));

  // refresh UI after completion
  await getRecommendations();
}




export function openTaskModal() {
  const modules = getModules();

  // 🚨 BLOCK if no modules
  if (!modules || modules.length === 0) {
    alert("You must add a module before creating tasks.");
    return;
  }

  const taskModal = document.getElementById("taskModal");
  const taskDifficulty = document.getElementById("taskDifficulty");
  const taskDifficultyVal = document.getElementById("taskDifficultyVal");

  taskDifficulty.value = 0.5;
  taskDifficultyVal.textContent = "0.5";

  taskDifficulty.oninput = () => {
    taskDifficultyVal.textContent = taskDifficulty.value;
  };

  taskModal.style.display = "flex";
}
export function closeTaskModal(){
    const taskModal = document.getElementById("taskModal");
    taskModal.style.display = "none";

}

export async function saveTask() {
  const taskModal = document.getElementById("taskModal");

  const description = document.getElementById("taskNameInput").value.trim();
  const module = document.getElementById("moduleSelect").value;
  const type = document.getElementById("taskTypeSelect").value;
  const difficulty = parseFloat(
    document.getElementById("taskDifficulty").value
  );
  const estimated_time = parseInt(
    document.getElementById("estimatedTime").value
  );

  if (!description || !module || !type) {
    alert("Fill all fields");
    return;
  }

  try {
    const res = await addTask({
      user_id: 1,
      task_description: description,
      module,
      task_type: type,
      difficulty,
      estimated_time,
    });

    // ✅ STOP if backend returned error
    if (!res || res.status !== "created") {
      alert(res?.message || "Failed to add task");
      return;
    }

    taskModal.style.display = "none";

    document.getElementById("taskNameInput").value = "";

    await getRecommendations(); // refresh tasks
  } catch (err) {
    console.error(err);
    alert("Something went wrong while saving the task");
  }
}
