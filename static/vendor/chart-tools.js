/*
 * chart-tools.js — progressive "Show data / Download CSV" affordance for every
 * dataset dashboard chart, shared across all pages and all locales.
 *
 * Each chart card already renders an accessible, screen-reader-only mirror
 * <table> of its exact numbers (the `#chart-*-table` divs, kept `.sr-only`).
 * This script surfaces that data for *sighted* users too: a small toolbar under
 * each chart with a "Show data" toggle (reveals the mirror table, reusing the
 * page's existing `.chart-fallback` styling) and a "Download CSV" button
 * (serialises the same table, formula-injection-safe). No new API calls — the
 * data is already in the DOM.
 *
 * Served same-origin from /static/vendor/ so the page CSP stays `script-src
 * 'self'` (no inline-hash, no third-party origin). Self-localises from the
 * page's <html lang> so the 7 locale builds need no extra translation strings.
 */
(function () {
  "use strict";

  var chartCounter = 0;

  var I18N = {
    en: { show: "Show data", hide: "Hide data", csv: "Download CSV" },
    es: { show: "Ver datos", hide: "Ocultar datos", csv: "Descargar CSV" },
    fr: { show: "Afficher les données", hide: "Masquer les données", csv: "Télécharger le CSV" },
    de: { show: "Daten anzeigen", hide: "Daten ausblenden", csv: "CSV herunterladen" },
    it: { show: "Mostra i dati", hide: "Nascondi i dati", csv: "Scarica CSV" },
    ja: { show: "データを表示", hide: "データを隠す", csv: "CSVをダウンロード" },
    zh: { show: "显示数据", hide: "隐藏数据", csv: "下载 CSV" },
    ko: { show: "데이터 보기", hide: "데이터 숨기기", csv: "CSV 다운로드" },
  };

  function labels() {
    var lang = (document.documentElement.getAttribute("lang") || "en").slice(0, 2).toLowerCase();
    return I18N[lang] || I18N.en;
  }

  // Neutralise spreadsheet formula injection: a cell starting =, +, -, @ or a
  // control char is prefixed with a single quote — matches the server's
  // `_csv_safe` and the flagship dashboard's `toCSV`.
  function csvSafe(s) {
    s = s == null ? "" : String(s);
    return /^[=+\-@\t\r]/.test(s) ? "'" + s : s;
  }

  function tableToCsv(table) {
    var out = [];
    table.querySelectorAll("tr").forEach(function (tr) {
      var cells = [];
      tr.querySelectorAll("th,td").forEach(function (c) {
        var v = csvSafe(c.textContent.trim());
        if (/[",\r\n]/.test(v)) v = '"' + v.replace(/"/g, '""') + '"';
        cells.push(v);
      });
      if (cells.length) out.push(cells.join(","));
    });
    return out.join("\r\n");
  }

  function slug(s) {
    return String(s || "").toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 40);
  }

  function downloadCsv(name, text) {
    // Prepend a UTF-8 BOM (escape, not a literal char, so tooling can't strip it)
    // so Excel reads non-ASCII labels correctly.
    var blob = new Blob(["\ufeff" + text], { type: "text/csv;charset=utf-8" });
    var url = URL.createObjectURL(blob);
    var a = document.createElement("a");
    a.href = url;
    a.download = name;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
  }

  function styleButton(btn) {
    btn.type = "button";
    btn.style.cssText =
      "font: inherit; font-size: 12px; line-height: 1; cursor: pointer;" +
      "background: var(--panel2); color: var(--accent);" +
      "border: 1px solid var(--border); border-radius: 7px; padding: 5px 11px;";
  }

  function enhance(card) {
    if (card.getAttribute("data-ct") === "1") return;
    var mirror = card.querySelector('[id$="-table"]');
    if (!mirror) return;
    card.setAttribute("data-ct", "1");
    chartCounter++;

    var L = labels();
    var heading = card.querySelector("h3");
    var title = heading ? heading.textContent.trim() : "chart";
    // The mirror already carries its own id (the [id$="-table"] selector requires
    // one), so reuse it for aria-controls. titleSlug backs the CSV filename; the
    // counter is its fallback when a non-ASCII title slugs to empty.
    var titleSlug = slug(title);

    var tools = document.createElement("div");
    tools.className = "ct-tools";
    tools.style.cssText = "display: none; gap: 8px; margin-top: 12px; flex-wrap: wrap;";

    var toggle = document.createElement("button");
    styleButton(toggle);
    toggle.textContent = L.show;
    toggle.setAttribute("aria-expanded", "false");
    toggle.setAttribute("aria-controls", mirror.id);
    toggle.addEventListener("click", function () {
      var shown = mirror.classList.toggle("chart-fallback");
      mirror.classList.toggle("sr-only", !shown);
      toggle.textContent = shown ? L.hide : L.show;
      toggle.setAttribute("aria-expanded", String(shown));
    });

    var csv = document.createElement("button");
    styleButton(csv);
    csv.textContent = L.csv;
    csv.addEventListener("click", function () {
      var table = mirror.tagName === "TABLE" ? mirror : mirror.querySelector("table");
      if (!table) return;
      var page = (location.pathname.split("/").filter(Boolean).pop() || "dataset").replace(/\..*$/, "");
      downloadCsv(page + "-" + (titleSlug || "chart-" + chartCounter) + ".csv", tableToCsv(table));
    });

    tools.appendChild(toggle);
    tools.appendChild(csv);
    card.appendChild(tools);

    // Reveal the toolbar only once the mirror table actually holds rows — charts
    // render asynchronously, and empty/"no data" cards should stay tool-less.
    function reveal() {
      if (mirror.querySelector("tr")) {
        tools.style.display = "flex";
        return true;
      }
      return false;
    }
    if (!reveal() && window.MutationObserver) {
      var obs = new MutationObserver(function () { if (reveal()) obs.disconnect(); });
      obs.observe(mirror, { childList: true, subtree: true });
    }
  }

  function run() {
    document.querySelectorAll(".chart-card").forEach(enhance);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", run);
  } else {
    run();
  }
})();
