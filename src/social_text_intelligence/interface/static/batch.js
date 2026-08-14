document.querySelectorAll(".analysis-form").forEach((form) => {
  form.addEventListener("submit", () => {
    const button = form.querySelector("button");
    const progress = form.querySelector(".progress-message");
    form.setAttribute("aria-busy", "true");
    if (button) button.disabled = true;
    if (progress) progress.hidden = false;
  });
});
