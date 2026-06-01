const CONTENT_URL = "./content.json";

function el(tag, attrs = {}, children = []) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") node.className = v;
    else if (k.startsWith("on") && typeof v === "function") node.addEventListener(k.slice(2), v);
    else if (v === null || v === undefined) continue;
    else node.setAttribute(k, String(v));
  }
  for (const c of children) node.appendChild(typeof c === "string" ? document.createTextNode(c) : c);
  return node;
}

function escapeRegExp(str) {
  return str.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function highlight(text, q) {
  if (!q) return text;
  const re = new RegExp(`(${escapeRegExp(q)})`, "ig");
  return text.replace(re, "<mark>$1</mark>");
}

function relationBadge(rel) {
  const norm = (rel || "").toLowerCase();
  if (norm.includes("reproduce")) return `<span class="badge badge--reproduce">Reproduce</span>`;
  if (norm.includes("imit")) return `<span class="badge badge--imitate">Imitate</span>`;
  if (norm.includes("analogy")) return `<span class="badge badge--analogy">Analogy</span>`;
  return `<span class="badge">${rel}</span>`;
}

function setActiveNav(hash) {
  document.querySelectorAll("#nav a").forEach((a) => a.classList.toggle("active", a.getAttribute("href") === hash));
}

function openLightbox(src, cap) {
  const lb = document.getElementById("lightbox");
  const img = document.getElementById("lightboxImg");
  const c = document.getElementById("lightboxCap");
  img.src = src;
  img.alt = cap || "";
  c.textContent = cap || "";
  lb.setAttribute("aria-hidden", "false");
}

function closeLightbox() {
  document.getElementById("lightbox").setAttribute("aria-hidden", "true");
}

function mountFigures(figs, rawBase) {
  const root = document.getElementById("figures");
  root.innerHTML = "";
  for (const f of figs) {
    const src = `${rawBase}${f.path}`;
    const card = el("div", { class: "figure", role: "button", tabindex: "0" });
    card.appendChild(el("img", { src, alt: f.caption || "" }));
    card.appendChild(el("div", { class: "cap" }, [f.caption || f.path]));
    card.addEventListener("click", () => openLightbox(src, f.caption));
    card.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") openLightbox(src, f.caption);
    });
    root.appendChild(card);
  }
}

function mountMapping(table, q, relFilter) {
  const root = document.getElementById("mapping");
  root.innerHTML = "";
  if (!table) {
    root.appendChild(el("div", { class: "muted small" }, ["Missing mapping table in content.json."]));
    return;
  }
  const headers = table.headers || [];
  const rows = (table.rows || []).filter((r) => {
    const rel = (r[1] || "").toLowerCase();
    if (relFilter && !rel.includes(relFilter)) return false;
    if (!q) return true;
    return r.some((cell) => String(cell || "").toLowerCase().includes(q.toLowerCase()));
  });

  const tbl = el("table");
  const thead = el("thead");
  const trh = el("tr");
  for (const h of headers) trh.appendChild(el("th", {}, [h]));
  thead.appendChild(trh);
  tbl.appendChild(thead);

  const tbody = el("tbody");
  for (const r of rows) {
    const tr = el("tr");
    for (let i = 0; i < headers.length; i++) {
      const cell = r[i] ?? "";
      if (i === 1) {
        const td = el("td");
        td.innerHTML = relationBadge(cell);
        tr.appendChild(td);
      } else {
        const td = el("td");
        td.innerHTML = highlight(String(cell), q);
        tr.appendChild(td);
      }
    }
    tbody.appendChild(tr);
  }
  tbl.appendChild(tbody);
  root.appendChild(tbl);
  root.appendChild(
    el("div", { class: "table-note" }, [
      "Tip: use the filter chips on the left to focus on Reproduce/Imitate/Analogy.",
    ]),
  );
}

function mountSections(sections, q) {
  const root = document.getElementById("sections");
  root.innerHTML = "";
  for (const s of sections) {
    const box = el("div", { class: "section", id: s.id });
    box.appendChild(el("h2", {}, [s.title]));
    if (s.tagline) box.appendChild(el("p", { class: "tagline" }, [s.tagline]));
    const keep = (p) => {
      if (!q) return true;
      return (p || "").toLowerCase().includes(q.toLowerCase());
    };
    const ps = (s.paragraphs || []).filter(keep);
    for (const p of ps) {
      const para = el("p");
      para.innerHTML = highlight(p, q);
      box.appendChild(para);
    }
    root.appendChild(box);
  }
}

function mountNav(sections) {
  const nav = document.getElementById("nav");
  nav.innerHTML = "";
  for (const s of sections) nav.appendChild(el("a", { href: `#${s.id}` }, [s.title]));
  if (sections[0]) setActiveNav(`#${sections[0].id}`);
}

function mountHero(content) {
  const hero = document.getElementById("hero");
  hero.innerHTML = "";
  hero.appendChild(el("h1", {}, [content.title]));
  hero.appendChild(
    el("div", { class: "meta" }, [
      `${content.author} · ${content.affiliation} · ${content.date}`,
      el("br"),
      `Repo commit: ${content.repository_commit}`,
    ]),
  );
}

function mountChips(setter) {
  const chips = document.getElementById("chips");
  chips.innerHTML = "";
  const items = [
    { id: "", label: "All" },
    { id: "reproduce", label: "Reproduce" },
    { id: "imit", label: "Imitate" },
    { id: "analogy", label: "Analogy" },
  ];
  let cur = "";
  for (const it of items) {
    const c = el("button", { class: "chip", type: "button", "aria-pressed": it.id === cur }, [it.label]);
    c.addEventListener("click", () => {
      cur = it.id;
      chips.querySelectorAll(".chip").forEach((n, i) => n.setAttribute("aria-pressed", items[i].id === cur));
      setter(cur);
    });
    chips.appendChild(c);
  }
}

async function main() {
  const res = await fetch(CONTENT_URL, { cache: "no-store" });
  const content = await res.json();
  const rawBase = content.repo_raw_base || "";

  document.getElementById("downloadReport").href = `${rawBase}reports/Long_Range_Entanglement_Dynamic_Circuits_Report_EN.docx`;

  const sections = content.sections || [];
  mountHero(content);
  mountNav(sections);
  mountFigures(content.figures || [], rawBase);

  let relFilter = "";
  const search = document.getElementById("search");
  const stats = document.getElementById("stats");

  const rerender = () => {
    const q = search.value.trim();
    mountMapping(content.tables?.mapping, q, relFilter);
    mountSections(sections, q);
    const shownParas = sections.reduce((acc, s) => {
      const ps = s.paragraphs || [];
      if (!q) return acc + ps.length;
      return acc + ps.filter((p) => (p || "").toLowerCase().includes(q.toLowerCase())).length;
    }, 0);
    stats.textContent = q ? `Matches: ${shownParas} paragraphs (plus mapping table)` : `Loaded: ${shownParas} paragraphs`;
  };

  mountChips((v) => {
    relFilter = v;
    rerender();
  });

  search.addEventListener("input", () => rerender());
  rerender();

  window.addEventListener("hashchange", () => setActiveNav(location.hash));

  document.getElementById("lightbox").addEventListener("click", (e) => {
    if (e.target && e.target.dataset && e.target.dataset.close) closeLightbox();
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeLightbox();
  });
}

main().catch((e) => {
  console.error(e);
  document.getElementById("hero").textContent = `Failed to load content.json: ${String(e)}`;
});

