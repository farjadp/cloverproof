/* Product form on /products: live grade summary and the liquids-only density field.
 * Convenience only. The form works without this file and the server validates everything. */
(function () {
  "use strict";

  var form = document.querySelector("[data-product-form]");
  if (!form) return;

  var problems = document.getElementById("error-summary");
  if (problems) problems.focus();

  var NUMBER = /^(?:\d+(?:\.\d*)?|\.\d+)$/;
  var inputs = form.querySelectorAll("[data-grade]");
  var summary = document.getElementById("grade-summary");
  var gradeText = summary.querySelector("[data-grade-text]");
  var gradeTotal = summary.querySelector("[data-grade-total]");

  // Hundredths, as whole numbers: 0.1 + 0.2 must not show 0.30000000000000004.
  function hundredths(raw) {
    var value = raw.trim().replace(",", ".");
    return NUMBER.test(value) ? Math.round(parseFloat(value) * 100) : null;
  }

  function updateSummary() {
    var parts = [];
    var total = 0;
    var complete = true;
    inputs.forEach(function (input) {
      var value = hundredths(input.value);
      if (value === null) {
        complete = false;
        parts.push("?");
      } else {
        total += value;
        parts.push(String(value / 100));
      }
    });
    var over = total > 10000;
    gradeText.textContent = parts.join("-");
    gradeTotal.textContent =
      "Total " + total / 100 + " of 100" +
      (over ? ": too high, the grade cannot exceed 100" : complete ? "" : " so far");
    summary.classList.toggle("is-over", over);
    summary.hidden = false;
  }

  inputs.forEach(function (input) {
    input.addEventListener("input", updateSummary);
  });
  updateSummary();

  var kind = document.getElementById("product_form");
  var densityField = document.getElementById("density-field");
  var density = document.getElementById("density_kg_per_l");
  var keptDensity = "";

  function updateDensity() {
    var liquid = kind.value === "liquid";
    if (liquid) {
      if (!density.value) density.value = keptDensity;
      densityField.hidden = false;
    } else if (density.getAttribute("aria-invalid") !== "true") {
      // A hidden value would be refused for a granular product: keep it aside instead.
      if (density.value) keptDensity = density.value;
      density.value = "";
      densityField.hidden = true;
    }
  }

  kind.addEventListener("change", function () {
    density.removeAttribute("aria-invalid");
    updateDensity();
  });
  updateDensity();
})();
