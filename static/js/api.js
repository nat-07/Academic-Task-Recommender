export async function loginUser(username, password) {
  const res = await fetch("/session", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });

  return res.json();
}

export async function signupUser(username, password) {
  const res = await fetch("/auth/signup", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });

  return res.json();
}

export async function logoutUser() {
  const res = await fetch("/session", {
    method: "DELETE",
  });

  return res.ok;
}

export async function checkSession() {
  const res = await fetch("/session");
  return res.json();
}

// -------------------- MODULES --------------------

export async function loadModulesRequest() {
  const res = await fetch("/modules");
  const data = await res.json();
  return data.modules;
}

export async function addModule(payload) {
  const res = await fetch("/modules", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  return res.json();
}

export async function updateModule(moduleId, payload) {
  const res = await fetch(`/modules/${moduleId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  return res.json();
}

export async function deleteModule(moduleId) {
  const res = await fetch(`/modules/${moduleId}`, {
    method: "DELETE",
  });

  return res.json();
}

// -------------------- TASKS --------------------

export async function addTask(payload) {
  const res = await fetch("/tasks", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  return res.json();
}

export async function completeTaskRequest(taskId) {
  const res = await fetch(`/tasks/${taskId}/complete`, {
    method: "PATCH",
  });

  return res.json();
}

export async function getRecommendationsRequest(motivation = 2.5) {
  const res = await fetch(
    `/tasks/recommendations?motivation=${encodeURIComponent(motivation)}`
  );

  return res.json();
}