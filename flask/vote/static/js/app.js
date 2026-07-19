document.addEventListener("DOMContentLoaded", () => {
    const root = document.querySelector("[data-app]");
    if (!root) {
        return;
    }

    const participantPanel = document.querySelector('[data-role="participant"]');
    const adminPanel = document.querySelector('[data-role="admin"]');

    if (participantPanel) {
        initParticipant(participantPanel);
    }

    if (adminPanel) {
        initAdmin(adminPanel);
    }
});


const CARD_THEMES = [
    "poll-soft-blue",
    "poll-soft-green",
    "poll-soft-purple",
    "poll-soft-gray",
];


function themeFor(index) {
    return CARD_THEMES[index % CARD_THEMES.length];
}


function initParticipant(panel) {
    const stateUrl = panel.dataset.stateUrl;
    const stateTarget = document.getElementById("participant-state");
    const participantName = panel.querySelector("[data-participant-name]");
    const badge = panel.querySelector("[data-session-badge]");

    const render = (state) => {
        if (!state.session) {
            participantName.textContent = "Waiting for QR login";
            badge.textContent = "Not connected";
            stateTarget.innerHTML = `
                <div class="text-secondary py-3">
                    No active session yet. Scan the lecturer QR code to join the room.
                </div>
            `;
            return;
        }

        participantName.textContent = state.participant.display_name;
        badge.textContent = "Joined";

        const questions = state.session.questions
            .map((question, index) => {
                const theme = themeFor(index);
                const statusText = question.has_voted
                    ? "Voted"
                    : question.is_open
                        ? "Open"
                        : "Closed";

                const bodyMarkup = (question.has_voted || !question.is_open)
                    ? `
                        <div class="vstack gap-3">
                            ${question.options.map((option) => `
                                <div>
                                    <div class="d-flex justify-content-between gap-2 small mb-1">
                                        <strong>${escapeHtml(option.label)}</strong>
                                        <span>${option.votes} vote${option.votes === 1 ? "" : "s"} · ${option.percent}%</span>
                                    </div>
                                    <div class="progress vote-result">
                                        <div class="progress-bar" style="width:${option.percent}%"></div>
                                    </div>
                                </div>
                            `).join("")}
                        </div>
                    `
                    : `
                        <div class="list-group list-group-flush rounded-4 overflow-hidden">
                            ${question.options.map((option) => `
                                <button
                                    class="list-group-item list-group-item-action d-flex justify-content-between align-items-center choice-button border-0 py-3 px-3"
                                    type="button"
                                    data-vote-question="${question.id}"
                                    data-vote-option="${option.id}"
                                >
                                    <span class="fw-semibold">${escapeHtml(option.label)}</span>
                                    <span class="badge rounded-pill option-chip">${option.votes} vote${option.votes === 1 ? "" : "s"}</span>
                                </button>
                            `).join("")}
                        </div>
                    `;

                return `
                    <article class="card poll-card border-0 shadow-sm mb-3 overflow-hidden">
                        <div class="card-header ${theme} border-0 py-3 py-lg-4">
                            <div class="d-flex justify-content-between align-items-start gap-3">
                                <div>
                                    <div class="small text-uppercase fw-semibold opacity-75 mb-1">Question ${question.position}</div>
                                    <h3 class="h6 fw-semibold mb-2">${escapeHtml(question.prompt)}</h3>
                                    <div class="small opacity-75">
                                        ${question.total_votes} vote${question.total_votes === 1 ? "" : "s"} total
                                    </div>
                                </div>
                                <span class="badge rounded-pill text-bg-light text-dark">${statusText}</span>
                            </div>
                        </div>
                        <div class="card-body bg-white p-3 p-lg-4">
                            ${bodyMarkup}
                        </div>
                    </article>
                `;
            })
            .join("");

        stateTarget.innerHTML = questions || `
            <div class="text-secondary py-3">
                This session has no questions yet. The lecturer can add them from the admin dashboard.
            </div>
        `;
    };

    const refresh = async () => {
        const response = await fetch(stateUrl, {
            headers: { Accept: "application/json" },
        });
        render(await response.json());
    };

    panel.addEventListener("click", async (event) => {
        const voteButton = event.target.closest("[data-vote-question]");
        if (voteButton) {
            voteButton.disabled = true;
            await fetch(`/api/questions/${voteButton.dataset.voteQuestion}/vote`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    Accept: "application/json",
                },
                body: JSON.stringify({ option_id: Number(voteButton.dataset.voteOption) }),
            });
            await refresh();
            return;
        }
    });

    refresh();
    window.setInterval(refresh, 3000);
}


function initAdmin(panel) {
    const stateUrl = panel.dataset.stateUrl;
    const sessionForm = document.getElementById("session-form");
    const questionForm = document.getElementById("question-form");
    const optionsList = document.getElementById("options-list");
    const sessionPicker = document.getElementById("session-picker");
    const qrImage = document.getElementById("qr-image");
    const joinLink = document.getElementById("join-link");
    const adminState = document.getElementById("admin-state");
    const addOptionButton = document.getElementById("add-option");
    let sessionsCache = [];

    const addOptionField = (value = "") => {
        const row = document.createElement("div");
        row.className = "input-group";
        row.innerHTML = `
            <span class="input-group-text">Option</span>
            <input class="form-control rounded-end-4" name="option" value="${escapeAttribute(value)}" placeholder="Answer option">
        `;
        optionsList.appendChild(row);
    };

    addOptionField("Yes");
    addOptionField("No");

    addOptionButton.addEventListener("click", () => addOptionField());

    const render = (state) => {
        const sessions = state.sessions || [];
        sessionsCache = sessions;

        sessionPicker.innerHTML = sessions.map((session) => `
            <option value="${session.id}">${escapeHtml(session.title)}</option>
        `).join("");

        if (sessions.length === 0) {
            qrImage.removeAttribute("src");
            joinLink.textContent = "Create a session to generate a QR join code.";
            adminState.innerHTML = `
                <div class="text-secondary py-3">
                    No sessions yet. Use the form above to create the first voting room.
                </div>
            `;
            return;
        }

        const selectedSession = sessions.find((item) => String(item.id) === String(sessionPicker.value)) || sessions[0];
        sessionPicker.value = selectedSession.id;
        updateQrPreview(selectedSession);

        adminState.innerHTML = sessions.map((session, sessionIndex) => {
            const sessionTheme = themeFor(sessionIndex);
            const questionMarkup = session.questions.length
                ? session.questions.map((question, questionIndex) => `
                    <article class="card question-card border-0 shadow-sm mb-3 overflow-hidden">
                        <div class="card-header ${themeFor(questionIndex)} border-0 py-3">
                            <div class="d-flex justify-content-between align-items-start gap-3">
                                <div>
                                    <div class="small text-uppercase fw-semibold opacity-75 mb-1">Question ${question.position}</div>
                                    <h3 class="h6 fw-semibold mb-1">${escapeHtml(question.prompt)}</h3>
                                    <div class="small opacity-75">${question.total_votes} vote${question.total_votes === 1 ? "" : "s"} total</div>
                                </div>
                                <div class="d-flex gap-2 flex-wrap justify-content-end">
                                    <span class="badge rounded-pill text-bg-light text-dark">${question.is_open ? "Open" : "Closed"}</span>
                                </div>
                            </div>
                        </div>
                        <div class="card-body bg-white p-3">
                            <div class="vstack gap-2">
                                ${question.options.map((option) => `
                                    <div>
                                        <div class="d-flex justify-content-between gap-2 small mb-1">
                                            <strong>${escapeHtml(option.label)}</strong>
                                            <span>${option.votes} vote${option.votes === 1 ? "" : "s"} · ${option.percent}%</span>
                                        </div>
                                        <div class="progress vote-result">
                                            <div class="progress-bar" style="width:${option.percent}%"></div>
                                        </div>
                                    </div>
                                `).join("")}
                            </div>
                            <div class="d-flex flex-wrap gap-2 mt-3">
                                <button class="btn btn-outline-secondary btn-sm rounded-pill" type="button" data-toggle-question="${question.id}">
                                    ${question.is_open ? "Close question" : "Open question"}
                                </button>
                                <button class="btn btn-outline-danger btn-sm rounded-pill" type="button" data-delete-question="${question.id}">
                                    Delete question
                                </button>
                            </div>
                        </div>
                    </article>
                `).join("")
                : `<div class="text-secondary py-2">No questions have been added yet.</div>`;

            return `
                <article class="card session-card border-0 shadow-sm mb-3 overflow-hidden">
                    <div class="card-header ${sessionTheme} border-0 py-3 py-lg-4">
                        <div class="d-flex justify-content-between align-items-start gap-3">
                            <div class="text-white">
                                <div class="small text-uppercase fw-semibold opacity-75 mb-1">Session ${session.id}</div>
                                <h3 class="h5 fw-semibold mb-2">${escapeHtml(session.title)}</h3>
                                <p class="mb-0 opacity-75">${escapeHtml(session.description || "No description provided.")}</p>
                            </div>
                            <div class="d-flex flex-column align-items-end gap-2">
                                <span class="badge rounded-pill text-bg-light text-dark">${session.is_active ? "Active" : "Closed"}</span>
                                <button class="btn btn-light btn-sm rounded-pill" type="button" data-delete-session="${session.id}">
                                    Delete session
                                </button>
                            </div>
                        </div>
                        <div class="d-flex flex-wrap gap-2 align-items-center mt-3 text-white-50 small">
                            <span class="badge rounded-pill text-bg-light text-dark">${session.questions.length} question${session.questions.length === 1 ? "" : "s"}</span>
                            <span class="session-join">${escapeHtml(session.join_url)}</span>
                        </div>
                    </div>
                    <div class="card-body bg-white p-3 p-lg-4">
                        ${questionMarkup}
                    </div>
                </article>
            `;
        }).join("");
    };

    const updateQrPreview = (session) => {
        const encodedUrl = encodeURIComponent(session.join_url);
        qrImage.src = `https://api.qrserver.com/v1/create-qr-code/?size=240x240&data=${encodedUrl}`;
        qrImage.alt = `QR code for ${session.title}`;
        joinLink.innerHTML = `<span class="fw-semibold">Join link:</span> ${escapeHtml(session.join_url)}`;
    };

    sessionPicker.addEventListener("change", () => {
        const selected = sessionsCache.find((item) => String(item.id) === String(sessionPicker.value));
        if (selected) {
            updateQrPreview(selected);
        }
    });

    sessionForm.addEventListener("submit", async (event) => {
        event.preventDefault();
        const formData = new FormData(sessionForm);
        const response = await fetch("/api/sessions", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                Accept: "application/json",
            },
            body: JSON.stringify({
                title: formData.get("title"),
                description: formData.get("description"),
            }),
        });

        if (response.ok) {
            sessionForm.reset();
            await refresh();
        }
    });

    questionForm.addEventListener("submit", async (event) => {
        event.preventDefault();
        const sessionId = sessionPicker.value;
        if (!sessionId) {
            return;
        }

        const formData = new FormData(questionForm);
        const options = formData.getAll("option").map((value) => String(value).trim()).filter(Boolean);

        const response = await fetch(`/api/sessions/${sessionId}/questions`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                Accept: "application/json",
            },
            body: JSON.stringify({
                prompt: formData.get("prompt"),
                options,
            }),
        });

        if (response.ok) {
            questionForm.reset();
            optionsList.innerHTML = "";
            addOptionField("Yes");
            addOptionField("No");
            await refresh();
        }
    });

    panel.addEventListener("click", async (event) => {
        const toggleButton = event.target.closest("[data-toggle-question]");
        if (toggleButton) {
            await fetch(`/api/questions/${toggleButton.dataset.toggleQuestion}/toggle`, {
                method: "POST",
                headers: { Accept: "application/json" },
            });
            await refresh();
            return;
        }

        const deleteQuestionButton = event.target.closest("[data-delete-question]");
        if (deleteQuestionButton) {
            await fetch(`/api/questions/${deleteQuestionButton.dataset.deleteQuestion}`, {
                method: "DELETE",
                headers: { Accept: "application/json" },
            });
            await refresh();
            return;
        }

        const deleteSessionButton = event.target.closest("[data-delete-session]");
        if (deleteSessionButton) {
            await fetch(`/api/sessions/${deleteSessionButton.dataset.deleteSession}`, {
                method: "DELETE",
                headers: { Accept: "application/json" },
            });
            await refresh();
        }
    });

    async function refresh() {
        const response = await fetch(stateUrl, {
            headers: { Accept: "application/json" },
        });
        const data = await response.json();
        render(data);

        if (data.sessions.length > 0) {
            const selected = data.sessions.find((item) => String(item.id) === String(sessionPicker.value)) || data.sessions[0];
            sessionPicker.value = selected.id;
            updateQrPreview(selected);
        }
    }

    refresh();
    window.setInterval(refresh, 5000);
}


function escapeHtml(value) {
    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#39;");
}


function escapeAttribute(value) {
    return escapeHtml(value).replaceAll("`", "&#96;");
}
