document.addEventListener("DOMContentLoaded", () => {
  const listEl = document.getElementById("available-donations");

  async function load() {
    try {
      const data = await api.get("/api/donations");
      render(data.donations);
    } catch (err) {
      listEl.innerHTML = `<p class="state-message">Couldn't load donations right now.</p>`;
    }
  }

  function render(donations) {
    if (!donations.length) {
      listEl.innerHTML = `<p class="state-message">No donations nearby right now — check back shortly.</p>`;
      return;
    }

    const sorted = [...donations].sort((a, b) => a.hours_left - b.hours_left);

    listEl.innerHTML = sorted
      .map((d) => {
        const metaExtra = `<span>🙋 ${escapeHtml(d.donor_name || "—")}</span>`;
        let actions = "";

        if (d.status === "available") {
          actions = window.ORG_VERIFIED
            ? `<button class="btn-claim btn-claim-action" data-id="${d.id}">Claim</button>`
            : `<span class="state-message" style="padding:0;">Claim opens once verified</span>`;
        } else if (d.status === "claimed" && !d.volunteer_name) {
          actions = `<span class="state-message" style="padding:0;">Waiting for a volunteer to pick up</span>`;
        } else if (d.status === "claimed" && d.volunteer_name) {
          actions = `<span class="state-message" style="padding:0;">${escapeHtml(d.volunteer_name)} is on the way</span>`;
        } else if (d.status === "picked_up") {
          actions = `<button class="btn-claim btn-confirm" data-id="${d.id}">Confirm delivery</button>`;
        }

        return donationCard(d, { metaExtra, actionsHtml: actions });
      })
      .join("");

    listEl.querySelectorAll(".btn-claim-action").forEach((btn) => {
      btn.addEventListener("click", async () => {
        try {
          await api.post(`/api/donations/${btn.dataset.id}/claim`);
          showToast("Donation claimed.");
          load();
        } catch (err) {
          showToast(err.message);
        }
      });
    });

    listEl.querySelectorAll(".btn-confirm").forEach((btn) => {
      btn.addEventListener("click", async () => {
        try {
          await api.post(`/api/donations/${btn.dataset.id}/confirm-delivery`);
          showToast("Delivery confirmed — thank you!");
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
