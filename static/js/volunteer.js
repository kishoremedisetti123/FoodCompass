document.addEventListener("DOMContentLoaded", () => {
  const listEl = document.getElementById("donations-list");
  let currentUserId = null;

  api.get("/api/me").then((d) => {
    if (d.authenticated) currentUserId = d.user.id;
  });

  async function load() {
    try {
      const data = await api.get("/api/donations");
      render(data.donations);
    } catch (err) {
      listEl.innerHTML = `<p class="state-message">Couldn't load pickups right now.</p>`;
    }
  }

  function render(donations) {
    if (!donations.length) {
      listEl.innerHTML = `<p class="state-message">No pickups waiting right now — check back shortly.</p>`;
      return;
    }

    const sorted = [...donations].sort((a, b) => a.hours_left - b.hours_left);

    listEl.innerHTML = sorted
      .map((d) => {
        const metaExtra = `<span>🏢 ${escapeHtml(d.claiming_org_name || "—")}</span>`;
        let actions = "";

        if (d.status === "claimed" && !d.volunteer_name) {
          actions = `<button class="btn-claim btn-take" data-id="${d.id}">Take this pickup</button>`;
        } else if (d.status === "claimed" && d.volunteer_name) {
          actions = `<button class="btn-claim btn-pickedup" data-id="${d.id}">Mark picked up</button>`;
        } else if (d.status === "picked_up") {
          actions = `<span class="state-message" style="padding:0;">On the way — awaiting delivery confirmation</span>`;
        }

        return donationCard(d, { metaExtra, actionsHtml: actions });
      })
      .join("");

    listEl.querySelectorAll(".btn-take").forEach((btn) => {
      btn.addEventListener("click", async () => {
        try {
          await api.post(`/api/donations/${btn.dataset.id}/assign-volunteer`);
          showToast("Pickup added to your list.");
          load();
        } catch (err) {
          showToast(err.message);
        }
      });
    });

    listEl.querySelectorAll(".btn-pickedup").forEach((btn) => {
      btn.addEventListener("click", async () => {
        try {
          await api.post(`/api/donations/${btn.dataset.id}/picked-up`);
          showToast("Marked as picked up.");
          load();
        } catch (err) {
          showToast(err.message);
        }
      });
    });
  }

  load();
  setInterval(load, 15000);
});
