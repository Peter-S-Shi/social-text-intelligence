"use strict";

const controls = document.querySelector("[data-insight-controls]");
if (controls) {
  const perspective = controls.querySelector("[data-perspective-select]");
  const metric = controls.querySelector("[data-metric-select]");
  const refreshMetrics = () => {
    const selectedPerspective = perspective.value;
    const options = [...metric.options];
    for (const option of options) {
      option.hidden = option.dataset.perspective !== selectedPerspective;
    }
    if (metric.selectedOptions[0]?.hidden) {
      const firstVisible = options.find((option) => !option.hidden);
      if (firstVisible) firstVisible.selected = true;
    }
  };
  perspective.addEventListener("change", refreshMetrics);
  refreshMetrics();
}
