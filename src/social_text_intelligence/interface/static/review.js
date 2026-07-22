"use strict";

for (const group of document.querySelectorAll("[data-review-dimension]")) {
  const fields = group.querySelector("[data-correct-fields]");
  const radios = group.querySelectorAll('input[type="radio"]');
  const refresh = () => {
    const selected = group.querySelector('input[type="radio"]:checked');
    fields.hidden = !selected || selected.value !== "correct";
  };
  for (const radio of radios) radio.addEventListener("change", refresh);
  refresh();
}
