// Sisyphus/Gui/Dashboard/assets/execsum_qr.js
// Uses QRCode.js from CDN on demand (lazy loaded).
(function () {
  function loadQRCodeLib(cb) {
    if (window.QRCode) return cb();
    const s = document.createElement("script");
    s.src = "https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js";
    s.onload = cb;
    document.head.appendChild(s);
  }

  function renderAll() {
    const nodes = document.querySelectorAll("[data-qr-url]");
    if (!nodes.length) return;

    loadQRCodeLib(function () {
      nodes.forEach((el) => {
        const url = el.getAttribute("data-qr-url") || "";
        if (!url) return;

        // idempotent: only render once per url
        const last = el.getAttribute("data-qr-last");
        if (last === url) return;

        el.innerHTML = "";
        el.setAttribute("data-qr-last", url);

        // eslint-disable-next-line no-new
        new QRCode(el, {
          text: url,
          width: 260,
          height: 260,
          correctLevel: QRCode.CorrectLevel.M,
        });
      });
    });
  }

  // re-render whenever DOM changes (Dash updates modal)
  const obs = new MutationObserver(() => renderAll());
  obs.observe(document.documentElement, { childList: true, subtree: true });

  // initial
  document.addEventListener("DOMContentLoaded", renderAll);
})();
