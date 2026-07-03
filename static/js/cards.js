// Shared donation card rendering — used by donor.js, volunteer.js, organization.js

const STATUS_LABELS = {
  available: "Available",
  claimed: "Claimed",
  picked_up: "Picked up",
  delivered: "Delivered",
  cancelled: "Cancelled",
};

function freshnessMarkup(donation) {
  if (donation.status === "delivered" || donation.status === "cancelled") {
    return ""; // urgency no longer matters once the lifecycle is over
  }
  const urgency = donation.urgency; // expired | urgent | soon | fresh
  const hoursLeft = donation.hours_left;

  if (urgency === "expired") {
    return `
      <div class="freshness urgent">
        <div class="track"><div class="fill" style="width:100%"></div></div>
        <span class="fl-label">Expired</span>
      </div>`;
  }

  const cls = urgency === "urgent" ? "urgent" : urgency === "soon" ? "soon" : "";
  const pct = Math.max(6, Math.min(100, (hoursLeft / 12) * 100));
  const label = hoursLeft < 1 ? "Less than 1h left" : `${hoursLeft}h left`;

  return `
    <div class="freshness ${cls}">
      <div class="track"><div class="fill" style="width:${pct}%"></div></div>
      <span class="fl-label">${label}</span>
    </div>`;
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str ?? "";
  return div.innerHTML;
}

function donationCard(d, { metaExtra = "", actionsHtml = "" } = {}) {
  return `
    <div class="donation-card" data-id="${d.id}">
      <div class="card-top">
        <span class="food-name">${escapeHtml(d.food_type)}</span>
        <span class="status-pill ${d.status}">${STATUS_LABELS[d.status] || d.status}</span>
      </div>
      <div class="meta">
        <span>📦 ${escapeHtml(d.quantity)}</span>
        <span>📍 ${escapeHtml(d.pickup_location)}</span>
        ${metaExtra}
      </div>
      ${freshnessMarkup(d)}
      ${d.notes ? `<div class="meta"><span>📝 ${escapeHtml(d.notes)}</span></div>` : ""}
      <div class="card-foot">
        <div></div>
        <div class="card-actions">${actionsHtml}</div>
      </div>
    </div>
  `;
}
