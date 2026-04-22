import { loginUser } from "../api.js";

document.addEventListener("DOMContentLoaded", () => {
  const loginBtn = document.getElementById("loginBtn");
  const goToSignupBtn = document.getElementById("goToSignupBtn");

  goToSignupBtn.addEventListener("click", () => {
    window.location.href = "/signup";
  });

  loginBtn.addEventListener("click", async () => {
    const username = document.getElementById("username").value.trim();
    const password = document.getElementById("password").value.trim();

    if (!username || !password) {
      alert("Please fill all fields");
      return;
    }

    try {
      const data = await loginUser(username, password);

      if (data.status === "success") {
        window.location.href = "/homepage";
      } else {
        alert(data.message || "Invalid login");
      }
    } catch (err) {
      console.error(err);
      alert("Login error");
    }
  });
});

async function checkSessionAndRedirect() {
  const res = await fetch("/session");
  const data = await res.json();

  if (data.logged_in) {
    window.location.href = "/homepage";
  }
}

// normal load
window.onload = checkSessionAndRedirect;

// back/forward navigation
window.addEventListener("pageshow", checkSessionAndRedirect);