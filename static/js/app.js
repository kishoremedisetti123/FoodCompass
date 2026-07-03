// FoodCompass — shared frontend helpers

const api = {
  async post(url, body) {
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body || {}),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.error || "Something went wrong.");
    return data;
  },
  async get(url) {
    const res = await fetch(url);
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.error || "Something went wrong.");
    return data;
  },
};

function showToast(message) {
  let toast = document.querySelector(".toast");
  if (!toast) {
    toast = document.createElement("div");
    toast.className = "toast";
    document.body.appendChild(toast);
  }
  toast.textContent = message;
  toast.classList.add("show");
  clearTimeout(toast._hideTimer);
  toast._hideTimer = setTimeout(() => toast.classList.remove("show"), 3200);
}

function showFormError(formEl, message) {
  let err = formEl.querySelector(".api-error");
  if (!err) {
    err = document.createElement("div");
    err.className = "api-error";
    formEl.prepend(err);
  }
  err.textContent = message;
  err.classList.add("show");
}

function clearFormError(formEl) {
  const err = formEl.querySelector(".api-error");
  if (err) err.classList.remove("show");
}

async function logout() {
  try {
    const data = await api.post("/api/logout");
    window.location.href = data.redirect || "/";
  } catch (e) {
    window.location.href = "/";
  }
}

document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("[data-logout]").forEach((btn) => {
    btn.addEventListener("click", logout);
  });
});
