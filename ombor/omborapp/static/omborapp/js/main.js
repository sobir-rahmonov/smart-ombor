"use strict";

/* ===== Yordamchi funksiyalar ===== */

const numberFormat = new Intl.NumberFormat("ru-RU");

function formatNumber(value) {
  return numberFormat.format(Math.round(value));
}

function isTypingTarget(element) {
  return ["INPUT", "TEXTAREA", "SELECT"].includes(element.tagName) || element.isContentEditable;
}

/* ===== Qidiruv: "/" tugmasi bilan o'tish ===== */

function initSearchShortcut() {
  const search = document.getElementById("global-search");
  if (!search) return;

  document.addEventListener("keydown", (event) => {
    if (event.key === "/" && !isTypingTarget(event.target)) {
      event.preventDefault();
      search.focus();
    }
  });
}

/* ===== Xabarlarni yopish ===== */

function initMessages() {
  document.querySelectorAll(".message").forEach((message) => {
    const closeButton = message.querySelector(".message-close");
    if (closeButton) {
      closeButton.addEventListener("click", () => message.remove());
    }
    if (message.classList.contains("message-success")) {
      setTimeout(() => message.remove(), 5000);
    }
  });
}

/* ===== Kirim / Chiqim formasi ===== */

function initMovementForm() {
  const form = document.getElementById("movement-form");
  const dataElement = document.getElementById("products-data");
  if (!form || !dataElement) return;

  const products = JSON.parse(dataElement.textContent);
  const productSelect = form.querySelector("select[name='product']");
  const quantityInput = form.querySelector("input[name='quantity']");
  const priceInput = form.querySelector("input[name='price']");
  const typeInputs = form.querySelectorAll("input[name='movement_type']");
  const submitButton = document.getElementById("submit-btn");
  const infoBox = document.getElementById("product-info");
  const summary = document.getElementById("summary");
  const summaryTotal = document.getElementById("summary-total");
  const summaryLeft = document.getElementById("summary-left");

  const getProduct = () => products[productSelect.value] || null;

  const getType = () => {
    const checked = form.querySelector("input[name='movement_type']:checked");
    return checked ? checked.value : "in";
  };

  const getQuantity = () => Math.max(parseInt(quantityInput.value, 10) || 0, 0);

  function createChip(text, extraClass = "") {
    const chip = document.createElement("span");
    chip.className = `chip ${extraClass}`.trim();
    chip.textContent = text;
    return chip;
  }

  function renderProductInfo() {
    infoBox.replaceChildren();
    const product = getProduct();
    if (!product) return;

    infoBox.append(
      createChip(`Omborda: ${formatNumber(product.quantity)} dona`, product.quantity === 0 ? "chip-warn" : ""),
      createChip(`Narxi: ${formatNumber(product.price)} so'm`)
    );
  }

  function renderSummary() {
    const product = getProduct();
    const quantity = getQuantity();
    if (!product || quantity === 0) {
      summary.hidden = true;
      return;
    }

    const price = parseFloat(priceInput.value) || 0;
    const left = getType() === "in" ? product.quantity + quantity : product.quantity - quantity;

    summaryTotal.textContent = `${formatNumber(price * quantity)} so'm`;
    summaryLeft.textContent = left < 0 ? "Qoldiq yetmaydi" : `${formatNumber(left)} dona`;
    summaryLeft.style.color = left < 0 ? "var(--danger-text)" : "";
    summary.hidden = false;
  }

  function renderSubmitButton() {
    const isIncome = getType() === "in";
    submitButton.textContent = isIncome ? "Kirimni saqlash" : "Chiqimni saqlash";
    submitButton.classList.toggle("btn-in", isIncome);
    submitButton.classList.toggle("btn-out", !isIncome);
  }

  function fillPriceFromProduct() {
    const product = getProduct();
    if (product) priceInput.value = Number(product.price);
  }

  function refresh() {
    renderProductInfo();
    renderSummary();
    renderSubmitButton();
  }

  productSelect.addEventListener("change", () => {
    fillPriceFromProduct();
    refresh();
  });

  typeInputs.forEach((input) => input.addEventListener("change", refresh));
  quantityInput.addEventListener("input", renderSummary);
  priceInput.addEventListener("input", renderSummary);

  form.querySelectorAll(".stepper-btn").forEach((button) => {
    button.addEventListener("click", () => {
      const step = parseInt(button.dataset.step, 10);
      quantityInput.value = Math.max(getQuantity() + step, 1);
      renderSummary();
    });
  });

  // Sahifa ochilganda: tezkor tugmadan kelgan holatni ko'rsatish
  if (getProduct() && !priceInput.value) fillPriceFromProduct();
  refresh();
}

/* ===== Ishga tushirish ===== */

document.addEventListener("DOMContentLoaded", () => {
  initSearchShortcut();
  initMessages();
  initMovementForm();
});