import { signupUser } from "../api.js";

document.addEventListener("DOMContentLoaded", () => {
  const signupBtn = document.getElementById("signupBtn");
  const goToLoginBtn = document.getElementById("goToLoginBtn");

  signupBtn.addEventListener("click", handleSignup);
  goToLoginBtn.addEventListener("click", goToLogin);
});

async function handleSignup() {
  const username = document.getElementById("username").value.trim();
  const password = document.getElementById("password").value;
  const confirmPassword = document.getElementById("confirmPassword").value;

  // Validation
  if (!username || !password) {
    alert("Please fill all fields");
    return;
  }

  if (password !== confirmPassword) {
    alert("Passwords do not match");
    return;
  }

  try {
    const data = await signupUser(username, password);

    if (data.status === "created") {
      alert("Account created!");
      window.location.href = "/";
    } else {
      alert(data.message || "Signup failed");
    }
  } catch (err) {
    console.error(err);
    alert("Error signing up");
  }
}

function goToLogin() {
  window.location.href = "/login";
}