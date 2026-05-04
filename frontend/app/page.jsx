"use client";

import { useEffect, useMemo, useState } from "react";
import {
  BarChart3,
  CalendarDays,
  CheckCircle2,
  ChevronRight,
  Clock,
  Copy,
  Flag,
  Map,
  Radio,
  RefreshCw,
  ShieldCheck,
  Trophy
} from "lucide-react";

const DATA_BASE =
  process.env.NEXT_PUBLIC_F1_DATA_BASE_URL ||
  "https://raw.githubusercontent.com/ShreyTriesToCode/f1-race-intel/main";
const LOCAL_DATA_ENDPOINT = "/api/local-data";

const F1_IMG = "https://media.formula1.com/image/upload";
const F1_MEDIA = "https://media.formula1.com";

const DRIVER_IMAGES = {
  "lando norris": `${F1_IMG}/c_fill%2Cw_720/q_auto/v1740000001/common/f1/2026/mclaren/lannor01/2026mclarenlannor01right.webp`,
  "oscar piastri": `${F1_IMG}/c_fill%2Cw_720/q_auto/v1740000001/common/f1/2026/mclaren/oscpia01/2026mclarenoscpia01right.webp`,
  "max verstappen": `${F1_IMG}/c_fill%2Cw_720/q_auto/v1740000001/common/f1/2026/redbullracing/maxver01/2026redbullracingmaxver01right.webp`,
  "charles leclerc": `${F1_IMG}/c_fill%2Cw_720/q_auto/v1740000001/common/f1/2026/ferrari/chalec01/2026ferrarichalec01right.webp`,
  "lewis hamilton": `${F1_IMG}/c_fill%2Cw_720/q_auto/v1740000001/common/f1/2026/ferrari/lewham01/2026ferrarilewham01right.webp`,
  "george russell": `${F1_IMG}/c_fill%2Cw_720/q_auto/v1740000001/common/f1/2026/mercedes/georus01/2026mercedesgeorus01right.webp`,
  "kimi antonelli": `${F1_IMG}/c_fill%2Cw_720/q_auto/v1740000001/common/f1/2026/mercedes/andant01/2026mercedesandant01right.webp`,
  "andrea kimi antonelli": `${F1_IMG}/c_fill%2Cw_720/q_auto/v1740000001/common/f1/2026/mercedes/andant01/2026mercedesandant01right.webp`,
  "fernando alonso": `${F1_IMG}/c_fill%2Cw_720/q_auto/v1740000001/common/f1/2026/astonmartin/feralo01/2026astonmartinferalo01right.webp`,
  "carlos sainz": `${F1_IMG}/c_fill%2Cw_720/q_auto/v1740000001/common/f1/2026/williams/carsai01/2026williamscarsai01right.webp`,
  "alex albon": `${F1_IMG}/c_fill%2Cw_720/q_auto/v1740000001/common/f1/2026/williams/alealb01/2026williamsalealb01right.webp`,
  "alexander albon": `${F1_IMG}/c_fill%2Cw_720/q_auto/v1740000001/common/f1/2026/williams/alealb01/2026williamsalealb01right.webp`,
  "nico hulkenberg": `${F1_IMG}/c_fill%2Cw_720/q_auto/v1740000001/common/f1/2026/audi/nichul01/2026audinichul01right.webp`,
  "nico hülkenberg": `${F1_IMG}/c_fill%2Cw_720/q_auto/v1740000001/common/f1/2026/audi/nichul01/2026audinichul01right.webp`,
  "gabriel bortoleto": `${F1_IMG}/c_fill%2Cw_720/q_auto/v1740000001/common/f1/2026/audi/gabbor01/2026audigabbor01right.webp`,
  "sergio perez": `${F1_IMG}/c_fill%2Cw_720/q_auto/v1740000001/common/f1/2026/cadillac/serper01/2026cadillacserper01right.webp`,
  "sergio pérez": `${F1_IMG}/c_fill%2Cw_720/q_auto/v1740000001/common/f1/2026/cadillac/serper01/2026cadillacserper01right.webp`,
  "valtteri bottas": `${F1_IMG}/c_fill%2Cw_720/q_auto/v1740000001/common/f1/2026/cadillac/valbot01/2026cadillacvalbot01right.webp`
};

const DRIVER_MEDIA = {
  "lando norris": { slug: "lannor01", team: "mclaren", display: "Lando_Norris" },
  "oscar piastri": { slug: "oscpia01", team: "mclaren", display: "Oscar_Piastri" },
  "max verstappen": { slug: "maxver01", team: "redbullracing", display: "Max_Verstappen" },
  "charles leclerc": { slug: "chalec01", team: "ferrari", display: "Charles_Leclerc" },
  "lewis hamilton": { slug: "lewham01", team: "ferrari", display: "Lewis_Hamilton" },
  "george russell": { slug: "georus01", team: "mercedes", display: "George_Russell" },
  "kimi antonelli": { slug: "andant01", team: "mercedes", display: "Kimi_Antonelli" },
  "andrea kimi antonelli": { slug: "andant01", team: "mercedes", display: "Kimi_Antonelli" },
  "fernando alonso": { slug: "feralo01", team: "astonmartin", display: "Fernando_Alonso" },
  "lance stroll": { slug: "lanstr01", team: "astonmartin", display: "Lance_Stroll" },
  "carlos sainz": { slug: "carsai01", team: "williams", display: "Carlos_Sainz" },
  "alex albon": { slug: "alealb01", team: "williams", display: "Alexander_Albon" },
  "alexander albon": { slug: "alealb01", team: "williams", display: "Alexander_Albon" },
  "nico hulkenberg": { slug: "nichul01", team: "audi", display: "Nico_Hulkenberg" },
  "nico hülkenberg": { slug: "nichul01", team: "audi", display: "Nico_Hulkenberg" },
  "gabriel bortoleto": { slug: "gabbor01", team: "audi", display: "Gabriel_Bortoleto" },
  "sergio perez": { slug: "serper01", team: "cadillac", display: "Sergio_Perez" },
  "sergio pérez": { slug: "serper01", team: "cadillac", display: "Sergio_Perez" },
  "valtteri bottas": { slug: "valbot01", team: "cadillac", display: "Valtteri_Bottas" },
  "pierre gasly": { slug: "piegas01", team: "alpine", display: "Pierre_Gasly" },
  "franco colapinto": { slug: "fracol01", team: "alpine", display: "Franco_Colapinto" },
  "isack hadjar": { slug: "isahad01", team: "redbullracing", display: "Isack_Hadjar" },
  "liam lawson": { slug: "lialaw01", team: "racingbulls", display: "Liam_Lawson" },
  "esteban ocon": { slug: "estoco01", team: "haas", display: "Esteban_Ocon" },
  "oliver bearman": { slug: "olibea01", team: "haas", display: "Oliver_Bearman" },
  "arvid lindblad": { slug: "arvlin01", team: "racingbulls", display: "Arvid_Lindblad" }
};

const TEAM_CARS = {
  "mclaren": ["mclaren"],
  "ferrari": ["ferrari"],
  "mercedes": ["mercedes"],
  "red bull racing": ["redbullracing", "red-bull-racing"],
  "red bull": ["redbullracing", "red-bull-racing"],
  "williams": ["williams"],
  "aston martin": ["astonmartin", "aston-martin"],
  "aston martin aramco f1 team": ["astonmartin", "aston-martin"],
  "alpine": ["alpine"],
  "alpine f1 team": ["alpine"],
  "bwt alpine f1 team": ["alpine"],
  "haas": ["haas", "haasf1team"],
  "haas f1 team": ["haas", "haasf1team"],
  "moneygram haas f1 team": ["haas", "haasf1team"],
  "racing bulls": ["racingbulls", "rb"],
  "visa cash app rb": ["racingbulls", "rb"],
  "rb": ["racingbulls", "rb"],
  "sauber": ["audi", "kicksauber", "sauber"],
  "kick sauber": ["audi", "kicksauber", "sauber"],
  "audi": ["audi", "kicksauber", "sauber"],
  "cadillac": ["cadillac"]
};

const TEAM_THEMES = {
  "mclaren": ["#ff8700", "#47c7fc"],
  "ferrari": ["#e10600", "#ffd200"],
  "mercedes": ["#00d2be", "#c7c7c7"],
  "red bull racing": ["#1e41ff", "#fcd700"],
  "red bull": ["#1e41ff", "#fcd700"],
  "williams": ["#00a0de", "#ffffff"],
  "aston martin": ["#006f62", "#cedc00"],
  "aston martin aramco f1 team": ["#006f62", "#cedc00"],
  "alpine": ["#0090ff", "#ff4fa3"],
  "alpine f1 team": ["#0090ff", "#ff4fa3"],
  "bwt alpine f1 team": ["#0090ff", "#ff4fa3"],
  "haas": ["#ffffff", "#e6002b"],
  "haas f1 team": ["#ffffff", "#e6002b"],
  "moneygram haas f1 team": ["#ffffff", "#e6002b"],
  "racing bulls": ["#2b4562", "#ffffff"],
  "visa cash app rb": ["#2b4562", "#ffffff"],
  "rb": ["#2b4562", "#ffffff"],
  "sauber": ["#52e252", "#111111"],
  "kick sauber": ["#52e252", "#111111"],
  "audi": ["#e31b23", "#d8d8d8"],
  "cadillac": ["#b9975b", "#d50032"]
};

function key(value) {
  return String(value || "").toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/\s+/g, " ").trim();
}
function cleanTitle(title) {
  return String(title || "F1 Race Intel")
    .replace(/^F1 Briefing:\s*/i, "")
    .replace(/^F1 Weekend Briefing:\s*/i, "")
    .replace(/\s*Grand Prix$/i, "");
}
function initials(name) {
  return String(name || "?").split(" ").filter(Boolean).slice(0, 2).map((part) => part[0]).join("").toUpperCase();
}
function unique(list) {
  return Array.from(new Set(list.filter(Boolean)));
}
function driverMedia(driver) {
  const normalized = key(driver?.name || driver);
  if (DRIVER_MEDIA[normalized]) return DRIVER_MEDIA[normalized];
  const compact = normalized.replace(/[^a-z0-9]+/g, "");
  const entry = Object.entries(DRIVER_MEDIA).find(([alias]) => {
    const aliasCompact = alias.replace(/[^a-z0-9]+/g, "");
    return compact.includes(aliasCompact) || aliasCompact.includes(compact);
  });
  return entry?.[1] || null;
}
function driverBodyUrl(meta, year = 2026) {
  if (!meta?.slug || !meta?.team) return "";
  return `${F1_IMG}/c_fill%2Cw_720/q_auto/v1740000001/common/f1/${year}/${meta.team}/${meta.slug}/${year}${meta.team}${meta.slug}right.webp`;
}
function driverHeadshotUrl(meta) {
  if (!meta?.slug || !meta?.display) return "";
  const folder = meta.display.slice(0, 1).toUpperCase();
  return `${F1_MEDIA}/d_driver_fallback_image.png/content/dam/fom-website/drivers/${folder}/${meta.slug.toUpperCase()}_${meta.display}/${meta.slug}.png.transform/1col/image.png`;
}
function driverImageCandidates(driver) {
  const mapped = DRIVER_IMAGES[key(driver?.name || driver)];
  const mappedList = Array.isArray(mapped) ? mapped : [mapped];
  const meta = driverMedia(driver);
  return unique([
    driver?.image,
    driver?.headshot_url,
    ...mappedList,
    driverBodyUrl(meta, 2026),
    driverBodyUrl(meta, 2025),
    driverBodyUrl(meta, 2024),
    driverHeadshotUrl(meta)
  ]);
}
function teamLookup(team, table) {
  const normalized = key(team);
  if (table[normalized]) return table[normalized];
  const compact = normalized.replace(/[^a-z0-9]+/g, "");
  const entry = Object.entries(table)
    .sort((a, b) => b[0].length - a[0].length)
    .find(([alias]) => {
      const aliasCompact = alias.replace(/[^a-z0-9]+/g, "");
      return normalized.includes(alias) || alias.includes(normalized) || compact.includes(aliasCompact) || aliasCompact.includes(compact);
    });
  return entry?.[1];
}
function mediaCar(slug, year = 2026) {
  return `${F1_IMG}/c_lfill%2Cw_3392/q_auto/v1740000001/common/f1/${year}/${slug}/${year}${slug}carright.webp`;
}
function teamCarCandidates(team) {
  const slugs = teamLookup(team, TEAM_CARS) || [key(team).replace(/[^a-z0-9]+/g, "")].filter(Boolean);
  return unique(slugs.flatMap((slug) => [mediaCar(slug, 2026), mediaCar(slug, 2025), mediaCar(slug, 2024)]));
}
function teamTheme(team) {
  const [primary, secondary] = teamLookup(team, TEAM_THEMES) || ["#e10600", "#ffffff"];
  return { "--team-primary": primary, "--team-secondary": secondary };
}
function esc(value) {
  return String(value ?? "").replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;");
}
function inline(text) {
  return esc(text).replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>").replace(/`(.*?)`/g, "<code>$1</code>");
}
function mdToHtml(md) {
  const lines = String(md || "").split("\n");
  let html = "";
  let list = null;
  const close = () => {
    if (list) html += `</${list}>`;
    list = null;
  };
  for (const raw of lines) {
    const line = raw.trim();
    if (!line) {
      close();
      continue;
    }
    if (line.startsWith("# ")) {
      close();
      html += `<h1>${inline(line.slice(2))}</h1>`;
    } else if (line.startsWith("## ")) {
      close();
      html += `<h2>${inline(line.slice(3))}</h2>`;
    } else if (line.startsWith("- ")) {
      if (list !== "ul") {
        close();
        html += "<ul>";
        list = "ul";
      }
      html += `<li>${inline(line.slice(2))}</li>`;
    } else if (/^\d+\.\s/.test(line)) {
      if (list !== "ol") {
        close();
        html += "<ol>";
        list = "ol";
      }
      html += `<li>${inline(line.replace(/^\d+\.\s/, ""))}</li>`;
    } else if (line.startsWith("---")) {
      close();
      html += "<hr>";
    } else {
      close();
      html += `<p>${inline(line)}</p>`;
    }
  }
  close();
  return html;
}
function cleanDataPath(path) {
  return String(path || "").replace(/^\/+/, "");
}
function remoteDataUrl(path) {
  return `${DATA_BASE}/${cleanDataPath(path)}?v=${Date.now()}`;
}
function localDataUrl(path) {
  return `${LOCAL_DATA_ENDPOINT}?path=${encodeURIComponent(cleanDataPath(path))}&v=${Date.now()}`;
}
async function fetchProjectData(path, type = "json") {
  let lastError = null;
  for (const url of [remoteDataUrl(path), localDataUrl(path)]) {
    try {
      const res = await fetch(url, { cache: "no-store" });
      if (!res.ok) throw new Error(`${url} HTTP ${res.status}`);
      return type === "text" ? await res.text() : await res.json();
    } catch (error) {
      lastError = error;
    }
  }
  throw lastError || new Error(`Unable to load ${path}`);
}
function level(value) {
  const t = String(value || "").toLowerCase();
  if (t.includes("high")) return 82;
  if (t.includes("medium-high")) return 74;
  if (t.includes("medium-good")) return 68;
  if (t.includes("medium")) return 54;
  if (t.includes("low-medium")) return 38;
  if (t.includes("low")) return 26;
  return 50;
}
function parseBriefingTop10(md) {
  const matches = String(md || "").matchAll(/^\d+\.\s+([^,\n]+)(?:,\s*(.*))?$/gm);
  return Array.from(matches).slice(0, 10).map((match) => ({
    name: match[1]?.trim(),
    reason: match[2]?.trim() || "Model estimate"
  }));
}
function formatTime(value) {
  const date = new Date(value || "");
  if (Number.isNaN(date.getTime())) return "Start unavailable";
  return date.toLocaleString([], { dateStyle: "medium", timeStyle: "short" });
}
function dateParts(value) {
  const date = new Date(value || "");
  if (Number.isNaN(date.getTime())) return { day: "--", month: "---", time: "--" };
  return {
    day: date.toLocaleDateString([], { day: "2-digit" }),
    month: date.toLocaleDateString([], { month: "short" }).toUpperCase(),
    time: date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
  };
}
function metric(value, suffix = "") {
  const number = Number(value);
  if (!Number.isFinite(number)) return "-";
  return `${number.toFixed(number >= 10 ? 1 : 2)}${suffix}`;
}

function Countdown({ startIso }) {
  const [time, setTime] = useState({ d: "--", h: "--", m: "--" });
  useEffect(() => {
    const target = new Date(startIso || "");
    if (Number.isNaN(target.getTime())) return;
    const tick = () => {
      const diff = target - Date.now();
      if (diff <= 0) return setTime({ d: "00", h: "00", m: "00" });
      const seconds = Math.floor(diff / 1000);
      setTime({
        d: String(Math.floor(seconds / 86400)).padStart(2, "0"),
        h: String(Math.floor((seconds % 86400) / 3600)).padStart(2, "0"),
        m: String(Math.floor((seconds % 3600) / 60)).padStart(2, "0")
      });
    };
    tick();
    const id = setInterval(tick, 30000);
    return () => clearInterval(id);
  }, [startIso]);

  return (
    <div className="countdown">
      <div><strong>{time.d}</strong><span>Days</span></div>
      <div><strong>{time.h}</strong><span>Hours</span></div>
      <div><strong>{time.m}</strong><span>Minutes</span></div>
    </div>
  );
}

function RaceWeekendSchedule({ targets, activeIndex, setActiveIndex, active, status }) {
  const rows = (targets?.length ? targets : [{
    target_type: active?.prediction_model?.output_target_type || "race",
    event: { title: active?.event_title || active?.title || "Prediction target", start: active?.start_iso || active?.start }
  }]).slice(0, 4);
  return (
    <div className="monaco-schedule-grid">
      {rows.map((target, index) => {
        const parts = dateParts(target.event?.start);
        return (
          <button
            className={`monaco-schedule-row ${activeIndex === index ? "active" : ""}`}
            key={`${target.target_type}-${target.event?.title || index}`}
            onClick={() => setActiveIndex(index)}
          >
            <span className="schedule-date"><b>{parts.day}</b><small>{parts.month}</small></span>
            <span className="schedule-copy">
              <strong>{target.event?.title || "F1 prediction"}</strong>
              <small>{String(target.target_type || "target").toUpperCase()} · {parts.time}</small>
            </span>
            <span className="schedule-action">Open <ChevronRight size={15} /></span>
          </button>
        );
      })}
      <a className="monaco-schedule-row live-link" href="/live">
        <span className="schedule-date"><b>LIVE</b><small>F1</small></span>
        <span className="schedule-copy">
          <strong>Timing room</strong>
          <small>Leaderboard, race control, radio</small>
        </span>
        <span className="schedule-action">Launch <ChevronRight size={15} /></span>
      </a>
      <div className="monaco-schedule-status">
        <span><Radio size={15} /> Data state</span>
        <strong>{status}</strong>
      </div>
    </div>
  );
}

function ModelSignalMarquee({ predictions, profile, modelMetrics }) {
  const top = predictions?.slice(0, 4) || [];
  const signals = [
    { label: "Track trait", value: profile.car_trait || "Car balance", note: profile.speed_profile || "Circuit profile" },
    { label: "Finish MAE", value: metric(modelMetrics.finish_position?.mae), note: "Backtest regression" },
    { label: "Podium AUC", value: metric(modelMetrics.podium?.auc), note: "Classifier quality" },
    { label: "Lap MAE", value: metric(modelMetrics.neural_lap_time_forecast?.mae_seconds, "s"), note: "Neural pace model" },
    ...top.map((driver, index) => ({
      label: `P${index + 1} pick`,
      value: driver.name || "Driver",
      note: driver.team || driver.reason || "Prediction signal"
    }))
  ].filter((item) => item.value && item.value !== "-");
  const loop = [...signals, ...signals];
  return (
    <section className="signal-strip" aria-label="Model signal stream">
      <div className="signal-track">
        {loop.map((item, index) => (
          <article className="signal-card" key={`${item.label}-${item.value}-${index}`}>
            <span>{item.label}</span>
            <strong>{item.value}</strong>
            <small>{item.note}</small>
          </article>
        ))}
      </div>
    </section>
  );
}

const CIRCUIT_REGISTRY = {
  gilles_villeneuve: {
    aliases: ["gilles", "villeneuve", "canadian", "canada", "montreal", "circuit gilles villeneuve"],
    name: "Circuit Gilles Villeneuve",
    countrySlug: "canada",
    officialPage: "https://www.formula1.com/en/racing/2026/canada",
    raceLaps: 70,
    sprintLaps: null,
    lengthKm: 4.361,
    raceDistanceKm: 305.27,
    viewBox: "0 0 900 520",
    path:
      "M126 330 C114 280 145 242 210 226 C286 207 363 193 433 181 C510 168 587 162 648 184 C707 205 746 252 751 303 C756 356 720 394 654 414 C576 438 455 434 330 417 C221 402 144 370 126 330 Z",
    turns: [
      [130, 326, "T1"],
      [170, 246, "T5"],
      [207, 226, "T7"],
      [492, 173, "T9"],
      [724, 254, "T12"],
      [656, 414, "T14"],
    ],
  },

  interlagos: {
    aliases: ["interlagos", "sao paulo", "são paulo", "brazil", "brasil", "autodromo jose carlos pace", "autódromo josé carlos pace"],
    name: "Autódromo José Carlos Pace",
    countrySlug: "brazil",
    officialPage: "https://www.formula1.com/en/racing/2026/brazil",
    raceLaps: 71,
    sprintLaps: null,
    lengthKm: 4.309,
    raceDistanceKm: 305.879,
    viewBox: "0 0 900 520",
    path:
      "M138 352 C118 297 143 245 196 224 C246 205 300 226 333 255 C372 291 421 283 449 241 C486 187 548 160 617 179 C691 200 742 256 735 315 C728 371 658 415 560 414 C475 413 416 389 356 399 C273 413 166 429 138 352 Z",
    turns: [
      [148, 345, "S/F"],
      [198, 224, "Senna S"],
      [333, 255, "T4"],
      [448, 241, "Ferradura"],
      [617, 179, "T8"],
      [735, 315, "Juncao"],
      [560, 414, "Subida"],
    ],
  },

  monaco: {
    aliases: ["monaco", "monte carlo", "monte-carlo"],
    name: "Circuit de Monaco",
    countrySlug: "monaco",
    officialPage: "https://www.formula1.com/en/racing/2026/monaco",
    raceLaps: 78,
    sprintLaps: null,
    lengthKm: 3.337,
    raceDistanceKm: 260.286,
    viewBox: "0 0 900 520",
    path:
      "M130 345 C160 250 230 208 318 235 C370 251 384 186 442 160 C520 126 618 166 636 238 C652 300 575 327 522 354 C450 391 365 430 264 408 C199 394 145 386 130 345 Z",
    turns: [
      [146, 333, "T1"],
      [302, 236, "Casino"],
      [438, 163, "Mirabeau"],
      [636, 238, "Tunnel"],
      [520, 355, "Tabac"],
      [263, 408, "Rascasse"],
    ],
  },

  silverstone: {
    aliases: ["silverstone", "british", "great britain", "uk", "united kingdom"],
    name: "Silverstone Circuit",
    countrySlug: "great-britain",
    officialPage: "https://www.formula1.com/en/racing/2026/great-britain",
    raceLaps: 52,
    sprintLaps: null,
    lengthKm: 5.891,
    raceDistanceKm: 306.198,
    viewBox: "0 0 900 520",
    path:
      "M115 330 L225 242 C295 186 407 182 496 202 L705 250 C764 264 780 323 725 356 L552 438 C486 470 373 445 324 390 L270 330 C242 300 190 304 115 330 Z",
    turns: [
      [125, 327, "Abbey"],
      [229, 243, "Village"],
      [495, 203, "Copse"],
      [704, 250, "Maggotts"],
      [552, 438, "Stowe"],
      [323, 389, "Club"],
    ],
  },

  monza: {
    aliases: ["monza", "italian", "italy", "autodromo nazionale monza"],
    name: "Autodromo Nazionale Monza",
    countrySlug: "italy",
    officialPage: "https://www.formula1.com/en/racing/2026/italy",
    raceLaps: 53,
    sprintLaps: null,
    lengthKm: 5.793,
    raceDistanceKm: 306.72,
    viewBox: "0 0 900 520",
    path:
      "M145 375 L280 178 C318 122 407 111 466 164 L712 379 C760 420 723 476 657 450 L495 387 C430 362 366 388 297 420 C235 449 122 421 145 375 Z",
    turns: [
      [276, 181, "T1"],
      [464, 165, "T4"],
      [607, 289, "Ascari"],
      [710, 380, "Parabolica"],
      [494, 388, "Straight"],
      [146, 375, "Start"],
    ],
  },

  spa: {
    aliases: ["spa", "belgian", "belgium", "spa-francorchamps", "francorchamps"],
    name: "Circuit de Spa-Francorchamps",
    countrySlug: "belgium",
    officialPage: "https://www.formula1.com/en/racing/2026/belgium",
    raceLaps: 44,
    sprintLaps: null,
    lengthKm: 7.004,
    raceDistanceKm: 308.052,
    viewBox: "0 0 900 520",
    path:
      "M110 362 C166 253 252 185 350 179 C437 174 464 239 532 230 C614 220 664 154 735 194 C788 224 776 298 713 337 C639 383 554 376 492 421 C433 464 335 458 280 400 C235 353 168 390 110 362 Z",
    turns: [
      [116, 360, "La Source"],
      [280, 400, "Eau Rouge"],
      [350, 179, "Kemmel"],
      [532, 230, "Bruxelles"],
      [713, 337, "Stavelot"],
      [492, 421, "Bus Stop"],
    ],
  },

  suzuka: {
    aliases: ["suzuka", "japanese", "japan"],
    name: "Suzuka Circuit",
    countrySlug: "japan",
    officialPage: "https://www.formula1.com/en/racing/2026/japan",
    raceLaps: 53,
    sprintLaps: null,
    lengthKm: 5.807,
    raceDistanceKm: 307.471,
    viewBox: "0 0 900 520",
    path:
      "M130 310 C170 210 284 170 384 204 C462 231 486 302 555 302 C633 302 697 238 745 280 C788 318 742 394 650 407 C556 420 506 372 426 367 C333 361 262 420 183 390 C142 374 116 345 130 310 Z",
    turns: [
      [135, 310, "T1"],
      [384, 204, "S Curves"],
      [555, 302, "Degner"],
      [745, 280, "130R"],
      [650, 407, "Chicane"],
      [426, 367, "S/F"],
    ],
  },

  yas_marina: {
    aliases: ["yas marina", "abu dhabi", "united arab emirates", "uae"],
    name: "Yas Marina Circuit",
    countrySlug: "abu-dhabi",
    officialPage: "https://www.formula1.com/en/racing/2026/abu-dhabi",
    raceLaps: 58,
    sprintLaps: null,
    lengthKm: 5.281,
    raceDistanceKm: 306.183,
    viewBox: "0 0 900 520",
    path:
      "M150 360 L306 188 C354 136 438 142 475 200 L540 302 L730 316 C776 320 786 378 742 402 L562 430 C485 442 423 411 386 350 L330 258 L206 390 C184 414 130 391 150 360 Z",
    turns: [
      [150, 360, "T1"],
      [306, 188, "T5"],
      [540, 302, "T9"],
      [730, 316, "T12"],
      [562, 430, "T16"],
      [386, 350, "T1"],
    ],
  },
};

function getCircuitMap(profile) {
  const lookupText = key(
    [
      profile?.circuit,
      profile?.race_name,
      profile?.event_title,
      profile?.country,
      profile?.city,
      profile?.circuit_key,
      profile?.jolpica_race?.raceName,
      profile?.jolpica_race?.Circuit?.circuitName,
      profile?.jolpica_race?.Circuit?.circuitId,
      profile?.jolpica_race?.Circuit?.Location?.country,
    ]
      .filter(Boolean)
      .join(" ")
  );

  return (
    Object.values(CIRCUIT_REGISTRY).find((circuit) =>
      circuit.aliases.some((alias) => lookupText.includes(key(alias)))
    ) || null
  );
}

function sessionLaps(profile, circuitMap, selectedTarget) {
  const targetType = key(
    selectedTarget?.target_type ||
      profile?.prediction_model?.output_target_type ||
      profile?.output_target_type ||
      profile?.event_title ||
      profile?.title
  );

  const explicitSprint =
    selectedTarget?.sprint_laps ??
    profile?.sprint_laps ??
    profile?.weekend?.sprint_laps ??
    profile?.race_info?.sprint_laps;

  const explicitRace =
    selectedTarget?.race_laps ??
    profile?.race_laps ??
    profile?.laps ??
    profile?.weekend?.race_laps ??
    profile?.race_info?.race_laps;

  const isSprint = targetType.includes("sprint");

  if (isSprint) {
    return {
      label: "Sprint laps",
      value: explicitSprint ?? circuitMap?.sprintLaps ?? "Not confirmed",
      note:
        explicitSprint || circuitMap?.sprintLaps
          ? "Sprint lap count from generated data or circuit registry."
          : "Sprint lap count not present in generated data yet.",
    };
  }

  return {
    label: "Race laps",
    value: explicitRace ?? circuitMap?.raceLaps ?? "Not confirmed",
    note:
      explicitRace || circuitMap?.raceLaps
        ? "Race lap count from generated data or circuit registry."
        : "Race lap count not present in generated data yet.",
  };
}

function CircuitShapeMap({ circuitMap }) {
  if (!circuitMap) {
    return (
      <div className="grid min-h-[330px] place-items-center">
        <div className="text-center">
          <div className="mx-auto mb-5 h-40 w-72 rounded-[50%] border-4 border-red-600/80 shadow-[0_0_60px_rgba(225,6,0,0.25)]" />
          <p className="text-sm text-zinc-400">
            Exact circuit SVG is not mapped yet for this venue.
          </p>
        </div>
      </div>
    );
  }

  return (
    <svg
      viewBox={circuitMap.viewBox}
      className="h-[360px] w-full"
      role="img"
      aria-label={`${circuitMap.name} circuit map`}
    >
      <defs>
        <filter id="trackGlowPlain" x="-40%" y="-40%" width="180%" height="180%">
          <feGaussianBlur stdDeviation="7" result="blur" />
          <feColorMatrix
            in="blur"
            type="matrix"
            values="1 0 0 0 0.85  0 1 0 0 0.06  0 0 1 0 0.04  0 0 0 0.75 0"
          />
          <feMerge>
            <feMergeNode />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>

        <linearGradient id="trackBasePlain" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#28282d" />
          <stop offset="45%" stopColor="#8b8b92" />
          <stop offset="100%" stopColor="#2f3036" />
        </linearGradient>

        <linearGradient id="trackHighlightPlain" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stopColor="#e10600" />
          <stop offset="50%" stopColor="#f5efe7" />
          <stop offset="100%" stopColor="#c1e328" />
        </linearGradient>
      </defs>

      <rect width="900" height="520" rx="28" fill="#0a0a0c" />

      <path
        d={circuitMap.path}
        fill="none"
        stroke="rgba(255,255,255,0.05)"
        strokeWidth="62"
      />

      <path
        d={circuitMap.path}
        fill="none"
        stroke="url(#trackBasePlain)"
        strokeWidth="20"
        strokeLinecap="round"
        strokeLinejoin="round"
        filter="url(#trackGlowPlain)"
      />

      <path
        d={circuitMap.path}
        fill="none"
        stroke="url(#trackHighlightPlain)"
        strokeWidth="5"
        strokeLinecap="round"
        strokeLinejoin="round"
        opacity="0.9"
      />

      {circuitMap.turns.map(([x, y, label]) => (
        <g key={label}>
          <circle
            cx={x}
            cy={y}
            r="16"
            fill="rgba(255,255,255,0.08)"
            stroke="rgba(255,255,255,0.22)"
          />
          <text
            x={x}
            y={y + 5}
            textAnchor="middle"
            fontSize="13"
            fontWeight="800"
            fill="#f5efe7"
          >
            {label}
          </text>
        </g>
      ))}

      <g>
        <rect
          x="36"
          y="30"
          width={Math.min(380, 100 + circuitMap.name.length * 8)}
          height="38"
          rx="19"
          fill="rgba(225,6,0,0.16)"
          stroke="rgba(225,6,0,0.45)"
        />
        <text x="56" y="55" fill="#f5efe7" fontSize="14" fontWeight="800">
          {circuitMap.name}
        </text>
      </g>
    </svg>
  );
}

function CircuitIntelCard({ profile, weather, selectedTarget }) {
  const circuitMap = getCircuitMap(profile);
  const lapInfo = sessionLaps(profile, circuitMap, selectedTarget);

  return (
    <section className="rounded-[2rem] border border-white/10 bg-[#111113] p-6 shadow-2xl">
      <div className="mb-5 flex items-center justify-between gap-4">
        <div>
          <h2 className="text-3xl font-black tracking-tight text-[#f5efe7]">
            Circuit Intel
          </h2>
          <p className="mt-1 text-sm text-zinc-400">
            {profile?.circuit || circuitMap?.name || "Circuit data"}
          </p>
        </div>

        <div className="rounded-2xl border border-white/10 bg-white/5 p-3 text-zinc-200">
          <Map size={26} />
        </div>
      </div>

      <div className="relative overflow-hidden rounded-[1.7rem] border border-white/10 bg-black/40 p-4">
        <CircuitShapeMap circuitMap={circuitMap} />

        <div className="mt-4 rounded-2xl border border-white/10 bg-white/[0.04] p-4">
          <p className="text-xs font-bold uppercase tracking-[0.18em] text-[#c1e328]">
            Circuit image
          </p>
          <p className="mt-2 text-sm leading-6 text-zinc-300">
            Showing the mapped circuit shape only. Zone markings are intentionally removed.
          </p>

          {circuitMap?.officialPage && (
            <a
              href={circuitMap.officialPage}
              target="_blank"
              rel="noreferrer"
              className="mt-3 inline-flex rounded-full border border-white/10 bg-white/5 px-4 py-2 text-xs font-bold text-zinc-200 hover:bg-white/10"
            >
              Open official F1 race page
            </a>
          )}
        </div>
      </div>

      <div className="mt-5 grid gap-3 md:grid-cols-2">
        <div className="rounded-2xl border border-lime-400/20 bg-lime-400/10 p-4">
          <p className="text-xs font-bold uppercase tracking-[0.18em] text-lime-300">
            {lapInfo.label}
          </p>
          <p className="mt-2 text-3xl font-black text-[#f5efe7]">
            {lapInfo.value}
          </p>
          <p className="mt-2 text-xs leading-5 text-zinc-400">{lapInfo.note}</p>
        </div>

        <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
          <p className="text-xs font-bold uppercase tracking-[0.18em] text-zinc-500">
            Circuit length
          </p>
          <p className="mt-2 text-lg font-black text-[#f5efe7]">
            {circuitMap?.lengthKm ? `${circuitMap.lengthKm} km` : "-"}
          </p>
        </div>

        <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
          <p className="text-xs font-bold uppercase tracking-[0.18em] text-zinc-500">
            Car trait
          </p>
          <p className="mt-2 text-lg font-black text-[#f5efe7]">
            {profile?.car_trait || profile?.dominance || "-"}
          </p>
        </div>

        <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
          <p className="text-xs font-bold uppercase tracking-[0.18em] text-zinc-500">
            Speed profile
          </p>
          <p className="mt-2 text-lg font-black text-[#f5efe7]">
            {profile?.speed_profile || "-"}
          </p>
        </div>

        <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
          <p className="text-xs font-bold uppercase tracking-[0.18em] text-zinc-500">
            Overtaking
          </p>
          <p className="mt-2 text-lg font-black text-[#f5efe7]">
            {profile?.overtaking || "-"}
          </p>
        </div>

        <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
          <p className="text-xs font-bold uppercase tracking-[0.18em] text-zinc-500">
            Tyre stress
          </p>
          <p className="mt-2 text-lg font-black text-[#f5efe7]">
            {profile?.tyre_stress || "-"}
          </p>
        </div>
      </div>

      <div className="mt-4 rounded-2xl border border-lime-400/20 bg-lime-400/10 p-4">
        <p className="text-sm leading-6 text-zinc-200">
          {weather?.impact || "Weather and tyre effects update after the next workflow run."}
        </p>
      </div>
    </section>
  );
}


function DriverArt({ driver }) {
  const candidates = driverImageCandidates(driver);
  const [index, setIndex] = useState(0);
  useEffect(() => setIndex(0), [driver?.name, driver?.team, driver?.image, driver?.headshot_url]);
  const src = candidates[index];
  if (!src) return <div className="driver-fallback">{initials(driver?.name)}</div>;
  return <img src={src} alt={driver?.name || "Driver"} onError={() => setIndex((value) => value + 1)} />;
}

function TeamCar({ team }) {
  const candidates = teamCarCandidates(team);
  const [index, setIndex] = useState(0);
  useEffect(() => setIndex(0), [team]);
  const src = candidates[index];
  if (!src) {
    return (
      <span className="team-fallback-car" style={teamTheme(team)} aria-label={`${team} livery`}>
        <i /><b>{initials(team)}</b>
      </span>
    );
  }
  return <img className="team-car" src={src} alt={`${team} car`} onError={() => setIndex((value) => value + 1)} />;
}

function HeroCar({ team }) {
  const candidates = teamCarCandidates(team);
  const [index, setIndex] = useState(0);
  useEffect(() => setIndex(0), [team]);
  const src = candidates[index];
  if (!src) return <span className="hero-car-fallback team-fallback-car" style={teamTheme(team)}><i /><b>{initials(team)}</b></span>;
  return <img className="hero-car" src={src} alt="" onError={() => setIndex((value) => value + 1)} />;
}

function PredictionList({ predictions }) {
  const list = predictions?.length ? predictions.slice(0, 10) : [{ name: "No prediction yet", reason: "Run the workflow once." }];
  return (
    <div className="prediction-list">
      {list.map((driver, index) => (
        <article className={`prediction-card ${index === 0 ? "leader" : ""}`} key={`${driver.driver_id || driver.name}-${index}`}>
          <div className="rank">{index + 1}</div>
          <div className="prediction-copy">
            <strong>{driver.name}</strong>
            <span>{driver.team || "Team pending"}</span>
            <p>{driver.reason || "Model estimate"}</p>
            <div className="chips tight">
              {driver.score !== undefined && <small>Score {driver.score}</small>}
              {driver.confidence !== undefined && <small>{driver.confidence}% confidence</small>}
              {driver.predicted_finish_position !== undefined && driver.predicted_finish_position !== null && <small>Model P{Number(driver.predicted_finish_position).toFixed(1)}</small>}
              {driver.predicted_lap_pace_seconds !== undefined && driver.predicted_lap_pace_seconds !== null && <small>Lap {Number(driver.predicted_lap_pace_seconds).toFixed(2)}s</small>}
            </div>
          </div>
          <div className="driver-art"><DriverArt driver={driver} /></div>
        </article>
      ))}
    </div>
  );
}

export default function Home() {
  const [indexData, setIndexData] = useState([]);
  const [active, setActive] = useState(null);
  const [debug, setDebug] = useState(null);
  const [markdown, setMarkdown] = useState("");
  const [status, setStatus] = useState("Waiting for data");
  const [copied, setCopied] = useState(false);
  const [targetIndex, setTargetIndex] = useState(0);

  async function loadDebug() {
    try {
      setDebug(await fetchProjectData("data_cache/latest-model-debug.json"));
    } catch {
      setDebug(null);
    }
  }

  async function loadBriefing(item) {
    setStatus("Loading briefing");
    setActive(item);
    setMarkdown(await fetchProjectData(item.path, "text"));
    setTargetIndex(0);
    setStatus("Ready");
  }

  async function loadIndex() {
    setStatus("Syncing");
    const data = await fetchProjectData("briefings/index.json");
    const list = Array.isArray(data) ? data : data.briefings || [];
    list.sort((a, b) => String(b.generated_iso || b.generated || b.start || "").localeCompare(String(a.generated_iso || a.generated || a.start || "")));
    setIndexData(list);
    await loadDebug();
    if (list[0]) await loadBriefing(list[0]);
    else setStatus("No briefings");
  }

  useEffect(() => {
    loadIndex().catch((error) => {
      console.error(error);
      setStatus("No data");
    });
  }, []);

  const targets = useMemo(() => {
    const payloads = Array.isArray(debug?.payloads) ? debug.payloads.filter((p) => p?.ok !== false) : [];
    if (payloads.length) return payloads;
    if (!active) return [];
    return [{
      event: { title: active.event_title || active.title, start: active.start_iso || active.start },
      target_type: active.prediction_model?.output_target_type || "race",
      top10: active.top10 || [],
      profile: active,
      weather: active.weather || {},
      team_fit: active.team_fit || [],
      prediction_model: active.prediction_model || {}
    }];
  }, [debug, active]);

  const selectedTarget = targets[targetIndex] || targets[0] || {};
  const profile = selectedTarget.profile || active || {};
  const weather = selectedTarget.weather || active?.weather || {};
  const model = selectedTarget.prediction_model || active?.prediction_model || {};
  const modelMetrics = model.ml_model_meta?.metrics || {};
  const finishMetrics = modelMetrics.finish_position || {};
  const lapMetrics = modelMetrics.neural_lap_time_forecast || {};
  const rankingMetrics = finishMetrics.ranking || modelMetrics.win_probability_ranking || {};
  const predictions = selectedTarget.top10?.length ? selectedTarget.top10 : active?.top10?.length ? active.top10 : parseBriefingTop10(markdown);
  const topDriver = predictions[0] || {};
  const title = cleanTitle(active?.title || selectedTarget?.event?.title || "Race Intel");
  const html = useMemo(() => mdToHtml(markdown), [markdown]);
  const canCopy = Boolean(markdown);

  async function copyBriefing() {
    if (!canCopy) return;
    await navigator.clipboard.writeText(markdown);
    setCopied(true);
    setTimeout(() => setCopied(false), 1400);
  }

  return (
    <main className="app monaco-app">
      <nav className="monaco-nav">
        <a className="monaco-logo" href="#latest" aria-label="Race Intel home">
          <span>F1</span>
        </a>
        <div className="monaco-links">
          <a href="#schedule">Schedule</a>
          <a href="#predictions">Standings</a>
          <a href="#circuit">Circuit</a>
          <a href="#teams">Teams</a>
          <a href="/live">Live Timing</a>
        </div>
        <button className="monaco-menu-button" onClick={() => loadIndex().catch(() => setStatus("Refresh failed"))} aria-label="Refresh data">
          <i /><i />
        </button>
      </nav>

      <section className="monaco-hero" id="latest">
        <div className="monaco-hero-media">
          <HeroCar team={topDriver.team} />
          <div className="monaco-title-mask" aria-hidden="true">{title}</div>
          <div className="speed-light" aria-hidden="true" />
        </div>

        <div className="monaco-hero-copy">
          <div className="chips">
            <span>Race Intel</span>
            <span>{model.prediction_stage_label || "Model active"}</span>
            <span>{model.output_target_type || "Sprint/Race"}</span>
          </div>
          <h1>{title}</h1>
          <p>
            Sprint and Race predictions shaped by qualifying, practice, weather, upgrades, track traits,
            current-season car form, live timing signals, and the high-accuracy model audit.
          </p>
          <div className="monaco-hero-actions">
            <a href="#predictions">View prediction <ChevronRight size={16} /></a>
            <a href="/live">Live timing <Radio size={16} /></a>
          </div>
        </div>

        <aside className="monaco-countdown">
          <div className="section-head">
            <h2>Next target</h2>
            <Clock size={18} />
          </div>
          <p className="muted">{selectedTarget.event?.title || active?.event_title || "No target loaded"}</p>
          <strong className="time">{formatTime(selectedTarget.event?.start || active?.start_iso || active?.start)}</strong>
          <Countdown startIso={selectedTarget.event?.start || active?.start_iso} />
        </aside>

        <div className="hero-stats monaco-hero-stats">
          <div><span>Circuit</span><strong>{profile.circuit || active?.circuit || "-"}</strong></div>
          <div><span>Target</span><strong>{String(selectedTarget.target_type || model.output_target_type || "Race").toUpperCase()}</strong></div>
          <div><span>Generated</span><strong>{active?.generated || "-"}</strong></div>
        </div>
      </section>

      <section className="race-weekend-panel" id="schedule">
        <div className="race-weekend-heading">
          <span>Race Weekend</span>
          <h2>{selectedTarget.event?.title || active?.event_title || "Prediction schedule"}</h2>
          <p>Automatic workflow outputs, timing room, and current sync state in one race-weekend control surface.</p>
        </div>
        <RaceWeekendSchedule
          targets={targets}
          activeIndex={targetIndex}
          setActiveIndex={setTargetIndex}
          active={active}
          status={status}
        />
      </section>

      <ModelSignalMarquee predictions={predictions} profile={profile} modelMetrics={modelMetrics} />

      <section className="layout monaco-grid-main" id="predictions">
        <article className="card prediction-section">
          <div className="section-head">
            <h2>Prediction Standings</h2>
            <Trophy size={18} />
          </div>
          <PredictionList predictions={predictions} />
        </article>

        <aside className="stack">
          <CircuitIntelCard profile={profile} weather={weather} selectedTarget={selectedTarget} />

          <article className="card">
            <div className="section-head"><h2>Weather</h2><Flag size={18} /></div>
            <div className="mini-grid">
              <div><span>Temp</span><strong>{weather.temperature || "-"}</strong></div>
              <div><span>Rain</span><strong>{weather.rain || "-"}</strong></div>
              <div><span>Wind</span><strong>{weather.wind || "-"}</strong></div>
              <div><span>Source</span><strong>{weather.source || "Open-Meteo"}</strong></div>
            </div>
            <p className="note">{weather.impact || "Weather impact appears after the next run."}</p>
          </article>

          <article className="card">
            <div className="section-head"><h2>Strategy</h2><ShieldCheck size={18} /></div>
            <div className="fact"><span>Baseline</span><strong>{profile.strategy_bias || active?.strategy_bias || "-"}</strong></div>
            <div className="fact"><span>Pit window</span><strong>{profile.pit_window || active?.pit_window || "-"}</strong></div>
            <p className="note">Main risk: tyre drop-off, safety-car timing, traffic after pit stop, and weather crossover.</p>
          </article>
        </aside>
      </section>

      <section className="layout small monaco-support-grid" id="teams">
        <article className="card team-fit-card">
          <div className="section-head"><h2>Team fit</h2><CheckCircle2 size={18} /></div>
          <div className="team-list">
            {(selectedTarget.team_fit || active?.team_fit || []).slice(0, 5).map((team, index) => (
              <div className="team" key={`${team}-${index}`}>
                <TeamCar team={team} />
                <div><strong>{index + 1}. {team}</strong><span>Track-fit and form estimate</span></div>
              </div>
            ))}
          </div>
        </article>

        <article className="card model-status-card">
          <div className="section-head"><h2>Model Status</h2><BarChart3 size={18} /></div>
          <div className="fact"><span>Output mode</span><strong>{debug?.output_mode || "Latest"}</strong></div>
          <div className="fact"><span>Backfill used</span><strong>{debug?.backfill?.used ?? "-"}</strong></div>
          <div className="fact"><span>ML model</span><strong>{model.ml_model_loaded ? "Loaded" : "Fallback"}</strong></div>
          <div className="fact"><span>Timing source</span><strong>{model.available_components?.timing_provider_status || "Jolpica/FastF1 fallback"}</strong></div>
          <div className="fact"><span>Finish MAE</span><strong>{metric(finishMetrics.mae)}</strong></div>
          <div className="fact"><span>Lap MAE</span><strong>{metric(lapMetrics.mae_seconds, "s")}</strong></div>
          <div className="fact"><span>Top-5 recall</span><strong>{rankingMetrics.top5_recall !== undefined ? metric(rankingMetrics.top5_recall * 100, "%") : "-"}</strong></div>
        </article>

        <article className="card archive-card">
          <div className="section-head"><h2>Archive</h2><CalendarDays size={18} /></div>
          <div className="archive-list">
            {indexData.slice(0, 8).map((item) => (
              <button className={active?.path === item.path ? "active" : ""} key={item.path} onClick={() => loadBriefing(item)}>
                <strong>{item.title}</strong>
                <span>{item.generated || item.start || item.path}</span>
              </button>
            ))}
          </div>
        </article>
      </section>

      <section className="card briefing">
        <div className="section-head">
          <h2>Briefing text</h2>
          <button className="copy" onClick={copyBriefing}><Copy size={15} /> {copied ? "Copied" : "Copy"}</button>
        </div>
        <div className="briefing-text" dangerouslySetInnerHTML={{ __html: html || "<p>No briefing loaded.</p>" }} />
      </section>

      <footer>
        Race Intel uses generated GitHub Actions data and links to official viewing/timing sources. It does not stream race video.
      </footer>
    </main>
  );
}
