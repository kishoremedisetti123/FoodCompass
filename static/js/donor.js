document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("donation-form");
  const listEl = document.getElementById("my-donations");

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    clearFormError(form);

    const payload = {
      food_type: document.getElementById("foodType").value.trim(),
      quantity: document.getElementById("quantity").value.trim(),
      expiry_datetime: document.getElementById("expiry").value,
      pickup_location: document.getElementById("location").value.trim(),
      notes: document.getElementById("notes").value.trim(),
    };

    try {
      await api.post("/api/donations", payload);
      form.reset();
      const feedback = document.getElementById("form-feedback");
      feedback.classList.add("show");
      setTimeout(() => feedback.classList.remove("show"), 4000);
      loadMyDonations();
    } catch (err) {
      showFormError(form, err.message);
    }
  });

  async function loadMyDonations() {
    try {
      const data = await api.get("/api/donations");
      renderMyDonations(data.donations);
    } catch (err) {
      listEl.innerHTML = `<p class="state-message">Couldn't load your donations right now.</p>`;
    }
  }

  function renderMyDonations(donations) {
    if (!donations.length) {
      listEl.innerHTML = `<p class="state-message">You haven't posted any donations yet — the form above takes less than a minute.</p>`;
      return;
    }
    listEl.innerHTML = donations
      .map((d) => {
        let actions = "";
        if (d.status === "available") {
          actions = `<button class="btn-ghost btn-cancel" data-id="${d.id}">Cancel</button>`;
        } else if (d.claiming_org_name) {
          actions = `<span class="state-message" style="padding:0;">Claimed by ${escapeHtml(d.claiming_org_name)}</span>`;
        }
        return donationCard(d, { actionsHtml: actions });
      })
      .join("");

    listEl.querySelectorAll(".btn-cancel").forEach((btn) => {
      btn.addEventListener("click", async () => {
        try {
          await api.post(`/api/donations/${btn.dataset.id}/cancel`);
          showToast("Donation cancelled.");
          loadMyDonations();
        } catch (err) {
          showToast(err.message);
        }
      });
    });
  }

  loadMyDonations();
  setInterval(loadMyDonations, 15000); // light polling so status updates show up without a manual refresh
});
