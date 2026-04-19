import { setModules } from "./state.js";

export async function loginUser(username, password) {
  const res = await fetch("/api/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  return res.json();
}

export async function signupUser(username, password) {
  const res = await fetch("/api/sign-up", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ username, password }),
  });

  return res.json();
}

export async function logoutUser() {
  const res = await fetch("/api/logout", {
    method: "POST",
  });

  return res.json();
}


export async function loadModulesRequest() {
  const res = await fetch("/api/modules");
  const data = await res.json();
  return data.modules;
}



export async function addModule(payload) {
  return fetch("/api/add-module", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  }).then((r) => r.json());
}

export async function editModule(payload) {
  return fetch("/api/edit-module", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  }).then((r) => r.json());
}

export async function deleteModule(module_id) {
  return fetch("/api/delete-module", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ module_id }),
  }).then((r) => r.json());
}

export async function getRecommendationsRequest(motivation) {
  const res = await fetch("/api/recommend-task", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ motivation }),
  });

  return res.json();
}

export async function completeTaskRequest(taskId, motivation) {
  const res = await fetch("/api/complete-task", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      task_id: taskId,
      motivation,
    }),
  });

  return res.json();
}

export async function addTask(payload) {
  return fetch("/api/add-task", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export async function addTaskRequest(taskData) {
  const res = await fetch("/api/add-task", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(taskData),
  });

  return res.json();
}