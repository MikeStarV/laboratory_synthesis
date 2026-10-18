"use strict";

const laboratoryStatus = document.querySelector("#laboratory-synthesis-status");
function laboratoryError(error, element = laboratoryStatus) {
    if (element) {
        element.hidden = false;
        element.classList.remove("sr-only");
        element.classList.add("action-error");
        element.textContent = error.message || "Не удалось выполнить действие";
    }
}
async function laboratoryRequest(url, options) {
    const response = await fetch(url, options);
    if (!response.ok) {
        const result = await response.json().catch(() => ({}));
        const detail = result.detail;
        throw new Error(typeof detail === "string" ? detail :
            Array.isArray(detail) ? detail.map(item => item.msg).join("; ") :
            `Ошибка сервера: ${response.status}`);
    }
    return response.status === 204 ? null : response.json();
}

document.querySelectorAll("input[type=range]").forEach(input => {
    const output = document.querySelector(`output[for="${input.id}"]`);
    const update = () => {
        if (output) output.value = input.value;
        input.setAttribute("aria-valuetext", `${input.value} минут`);
    };
    input.addEventListener("input", update);
    update();
});

document.querySelectorAll("[data-laboratory-like]").forEach(button => {
    button.addEventListener("click", async () => {
        button.disabled = true;
        try {
            const liked = button.getAttribute("aria-pressed") === "true" ? 0 : 1;
            const result = await laboratoryRequest(button.dataset.laboratoryLike, {
                method: "POST", headers: {"Content-Type": "application/json"},
                body: JSON.stringify({laboratory_synthesis_liked: liked})
            });
            button.setAttribute("aria-pressed", String(result.laboratory_synthesis_liked === 1));
            button.setAttribute("aria-label", result.laboratory_synthesis_liked ? "Убрать лайк" : "Поставить лайк");
            document.querySelector("[data-laboratory-likes-count]").textContent = result.laboratory_synthesis_likes_count;
        } catch (error) { laboratoryError(error); }
        finally { button.disabled = false; }
    });
});

document.querySelectorAll("form[data-laboratory-delete]").forEach(form => {
    form.addEventListener("submit", async event => {
        event.preventDefault();
        const button = form.querySelector("button");
        button.disabled = true;
        try {
            await laboratoryRequest(form.dataset.laboratoryDelete, {method: "DELETE"});
            window.location.reload();
        } catch (error) { laboratoryError(error); button.disabled = false; }
    });
});

const laboratoryDraft = document.querySelector("form[data-laboratory-draft]");
if (laboratoryDraft) {
    laboratoryDraft.addEventListener("submit", async event => {
        event.preventDefault();
        const errorBox = laboratoryDraft.querySelector(".form-error");
        errorBox.hidden = true;
        const action = event.submitter?.value || "save";
        const buttons = laboratoryDraft.querySelectorAll("button[type=submit]");
        buttons.forEach(button => { button.disabled = true; });
        try {
            const fields = new FormData(laboratoryDraft);
            fields.delete("laboratory_synthesis_action");
            for (const [name, value] of [...fields]) {
                if (value instanceof File && !value.name) fields.delete(name);
            }
            const result = await laboratoryRequest(laboratoryDraft.action, {
                method: "POST", body: fields
            });
            if (action === "publish") {
                await laboratoryRequest(`/api/laboratory_syntheses/${result.laboratory_synthesis_id}/publication`, {
                    method: "PUT", headers: {"Content-Type": "application/json"}, body: "{}"
                });
                window.location.assign(`/laboratory_syntheses/feed/${result.laboratory_synthesis_id}`);
            } else {
                window.location.assign("/laboratory_syntheses/draft");
            }
        } catch (error) {
            laboratoryError(error, errorBox);
            buttons.forEach(button => { button.disabled = false; });
        }
    });
    for (const kind of ["image", "video"]) {
        const input = laboratoryDraft.querySelector(`input[type=file][name=laboratory_synthesis_${kind}]`);
        if (!input) continue;
        let localUrl;
        input.addEventListener("change", () => {
            if (!input.files[0]) return;
            if (localUrl) URL.revokeObjectURL(localUrl);
            localUrl = URL.createObjectURL(input.files[0]);
            laboratoryDraft.querySelector(`.draft-${kind}`).src = localUrl;
        });
    }
}

function laboratoryMeasureDescriptions() {
    document.querySelectorAll(".feed-description").forEach(details => {
        if (details.open) return;
        const preview = details.querySelector(".feed-description-preview");
        if (preview) details.classList.toggle("is-short", preview.scrollHeight <= preview.clientHeight + 1);
    });
}
window.addEventListener("resize", laboratoryMeasureDescriptions);
laboratoryMeasureDescriptions();
