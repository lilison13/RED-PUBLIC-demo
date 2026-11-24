(() => {
  const SNAPSHOT_URL = "/red/api/beready_snapshot";
  const META_POLL_MS = 1000;
  const RETRY_POLL_MS = 2500;
  const AUTO_TIMEOUT_MS = 30000;

  const HAIFA_POINT = { lat: 32.7940, lon: 34.9896 };

  const STATE_META = {
    NORMAL: {
      source: "Прогноз BeReady",
      sourceClass: "source-prediction",
      meaning: "Сейчас нет необычных признаков",
      color: "#24c18a"
    },
    READY: {
      source: "Прогноз BeReady",
      sourceClass: "source-prediction",
      meaning: "Есть активность, требующая повышенного внимания",
      color: "#ffbf47"
    },
    HIGH: {
      source: "Прогноз BeReady",
      sourceClass: "source-prediction",
      meaning: "Есть эскалация или несколько признаков одновременно",
      color: "#ff8f5a"
    },
    PRE_SHELTER: {
      source: "Прогноз BeReady",
      sourceClass: "source-prediction",
      meaning: "Расчетный прогноз только от BeReady",
      color: "#d68bff"
    },
    POST_ALERT_HIGH: {
      source: "BeReady Prediction",
      sourceClass: "source-prediction",
      meaning: "высокая готовность после официальной тревоги",
      color: "#ff7b54"
    },
    OFFICIAL_EARLY_WARNING: {
      source: "Официальный",
      sourceClass: "source-official",
      meaning: "Только официальное раннее предупреждение Командования тыла",
      color: "#65c4ff"
    },
    SHELTER_NOW: {
      source: "Официальный",
      sourceClass: "source-official",
      meaning: "Официальная тревога, относящаяся к Хайфе",
      color: "#ff5c73"
    }
  };

  let pollTimer = null;
  let map = null;
  let haifaMarker = null;
  let mapMarkers = [];
  let mapPolyline = null;
  let mapAutoMode = true;
  let mapAutoTimer = null;
  let mapInteractionLock = false;
  let lastSnapshot = null;
  let hasDoneInitialFocus = false;

  function stateMeta(state) {
    return STATE_META[state] || STATE_META.NORMAL;
  }

  function setApiStatus(ok, text) {
    const badge = document.getElementById("apiStatus");
    if (!badge) return;
    badge.textContent = text || (ok ? "API: OK" : "API: ОШИБКА");
    badge.classList.remove("api-ok", "api-error");
    badge.classList.add(ok ? "api-ok" : "api-error");
  }

  function safeArray(value) {
    return Array.isArray(value) ? value : [];
  }

  function normalizeSnapshot(snapshot) {
    return {
      state: snapshot?.state || "NORMAL",
      riskScore: Number(snapshot?.riskScore || 0),
      rocketScore: Number(snapshot?.rocketScore || 0),
      uavScore: Number(snapshot?.uavScore || 0),
      confidence: snapshot?.confidence || "LOW",
      eta: snapshot?.eta || "—",
      possibleApproach: snapshot?.possibleApproach || "Сейчас нет явного направления подхода",
      uniqueCount: Number(snapshot?.uniqueCount || 0),
      areas: safeArray(snapshot?.areas),
      reasons: safeArray(snapshot?.reasons),
      activeText: snapshot?.activeText || "Сейчас не активно",
      lastAlertsHtml: snapshot?.lastAlertsHtml || "Нет",
      clusterText: snapshot?.clusterText || "0 уникальных тревог в 0 населенных пунктах",
      simpleTitle: snapshot?.simpleTitle || "Сейчас нет необычных признаков для Хайфы",
      simpleBody: snapshot?.simpleBody || "Система сейчас не видит активности, которая оправдывала бы повышение расчетного уровня готовности для Хайфы.",
      stateReasoning: snapshot?.stateReasoning || "Недостаточно признаков для повышения уровня готовности.",
      rocketReasoning: snapshot?.rocketReasoning || "Сейчас нет ракетной активности, относящейся к Хайфе",
      uavReasoning: snapshot?.uavReasoning || "Сейчас нет активности летательных аппаратов, относящейся к Хайфе",
      rocketTechnical: snapshot?.rocketTechnical || "Нет активных ракетных факторов",
      uavTechnical: snapshot?.uavTechnical || "Нет активных факторов БПЛА",
      mapPoints: safeArray(snapshot?.mapPoints),
      uavTrackLine: safeArray(snapshot?.uavTrackLine),
      nearestText: snapshot?.nearestText || snapshot?.message?.nearestText || "Подходящие близкие события не обнаружены",
      generatedAtText: snapshot?.generatedAtText || "—",
      generatedAtIso: snapshot?.generatedAtIso || null,
      generatedAtTs: Number(snapshot?.generatedAtTs || 0)
    };
  }

  function initMap() {
    if (map || typeof L === "undefined") return;

    map = L.map("map", {
      zoomControl: true,
      attributionControl: true
    }).setView([32.92, 35.08], 9);

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 18,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>'
    }).addTo(map);

    haifaMarker = L.marker([HAIFA_POINT.lat, HAIFA_POINT.lon]).addTo(map);
    haifaMarker.bindPopup("Хайфа");

    map.on("dragstart zoomstart", () => {
      if (mapInteractionLock) return;
      setManualMode();
    });

    map.on("touchstart mousedown", () => {
      if (mapInteractionLock) return;
      setManualMode();
    });

    const btn = document.getElementById("mapAutoBtn");
    if (btn) {
      btn.addEventListener("click", () => setAutoMode(true));
    }
  }

  function setManualMode() {
    mapAutoMode = false;
    updateMapStatus();

    clearTimeout(mapAutoTimer);
    mapAutoTimer = setTimeout(() => {
      setAutoMode(true);
    }, AUTO_TIMEOUT_MS);
  }

  function setAutoMode(refocus) {
    mapAutoMode = true;
    clearTimeout(mapAutoTimer);
    mapAutoTimer = null;
    updateMapStatus();

    if (refocus && lastSnapshot) {
      focusMap(lastSnapshot);
    }
  }

  function updateMapStatus() {
    const status = document.getElementById("mapStatus");
    if (!status) return;

    status.textContent = mapAutoMode ? "Автоотслеживание" : "Ручной режим · авто через 30 с";
  }

  function clearMapLayers() {
    if (!map) return;

    for (const marker of mapMarkers) {
      map.removeLayer(marker);
    }
    mapMarkers = [];

    if (mapPolyline) {
      map.removeLayer(mapPolyline);
      mapPolyline = null;
    }
  }

  function markerTypeClass(point) {
    const t = String(point?.type || "").toLowerCase();
    if (t.includes("uav") || t.includes("aircraft")) return "uav";
    if (t.includes("rocket") || t.includes("missile")) return "rocket";
    if (t.includes("official") || t.includes("warning")) return "official";
    return "general";
  }

  function markerColor(point) {
    const cls = markerTypeClass(point);
    if (cls === "uav") return "#65c4ff";
    if (cls === "rocket") return "#ff5c73";
    if (cls === "official") return "#ffbf47";
    return "#d68bff";
  }

  function renderMap(snapshot) {
    initMap();
    if (!map) return;

    clearMapLayers();

    const points = safeArray(snapshot.mapPoints);
    for (const p of points) {
      if (!Number.isFinite(p?.lat) || !Number.isFinite(p?.lon)) continue;

      const marker = L.circleMarker([p.lat, p.lon], {
        radius: (String(p.type || "").includes("aircraft") || String(p.type || "").includes("uav")) ? 7 : 6,
        color: markerColor(p),
        fillColor: markerColor(p),
        weight: 2,
        fillOpacity: 0.82
      }).addTo(map);

      marker.bindPopup(`
        <div style="direction:rtl;text-align:right;min-width:150px">
          <strong>${escapeHtml(p.area || "Неизвестная зона")}</strong><br>
          ${escapeHtml(p.typeLabel || p.type || "")}${p.timeText ? `<br>${escapeHtml(p.timeText)}` : ""}
        </div>
      `);

      mapMarkers.push(marker);
    }

    if (Array.isArray(snapshot.uavTrackLine) && snapshot.uavTrackLine.length >= 2) {
      mapPolyline = L.polyline(snapshot.uavTrackLine, {
        color: "#65c4ff",
        weight: 3,
        opacity: 0.84,
        dashArray: "8 8"
      }).addTo(map);
    }
  }

  function focusMap(snapshot) {
    if (!map) return;

    const points = safeArray(snapshot.mapPoints)
      .filter(p => Number.isFinite(p?.lat) && Number.isFinite(p?.lon))
      .map(p => [p.lat, p.lon]);

    const linePoints = safeArray(snapshot.uavTrackLine)
      .filter(p => Array.isArray(p) && p.length >= 2 && Number.isFinite(p[0]) && Number.isFinite(p[1]));

    const allPoints = [[HAIFA_POINT.lat, HAIFA_POINT.lon], ...points, ...linePoints];

    mapInteractionLock = true;
    try {
      if (allPoints.length <= 1) {
        map.setView([32.92, 35.08], 9);
      } else {
        const bounds = L.latLngBounds(allPoints);
        map.fitBounds(bounds.pad(0.18), { animate: true, duration: 0.8 });
      }
    } finally {
      setTimeout(() => {
        mapInteractionLock = false;
      }, 900);
    }
  }

  function stateSourceLabel(state) {
    const meta = stateMeta(state);
    return meta.source;
  }

  function applyStateTheme(snapshot) {
    const meta = stateMeta(snapshot.state);
    document.documentElement.style.setProperty("--accent", meta.color);
    document.documentElement.style.setProperty("--accent-soft", `${hexToRgba(meta.color, 0.15)}`);

    const sourceBadge = document.getElementById("sourceBadge");
    const stateSource = document.getElementById("stateSource");
    if (sourceBadge) {
      sourceBadge.textContent = meta.source;
      sourceBadge.classList.remove("source-official", "source-prediction");
      sourceBadge.classList.add(meta.sourceClass);
    }
    if (stateSource) stateSource.textContent = meta.source;

    const modeLabel = document.getElementById("modeLabel");
    if (modeLabel) modeLabel.textContent = meta.source;

    const currentMeaning = document.getElementById("currentStateMeaning");
    if (currentMeaning) currentMeaning.textContent = meta.meaning;
  }

  function renderAlertsList(snapshot) {
    const container = document.getElementById("alertsList");
    if (!container) return;

    const points = safeArray(snapshot.mapPoints).filter(p => Number.isFinite(p?.lat) && Number.isFinite(p?.lon));

    if (!points.length) {
      container.innerHTML = `
        <div class="alert-row">
          <div class="alert-main">
            <div class="alert-area">Сейчас нет активных тревог для отображения</div>
            <div class="alert-meta">Подходящие близкие события сейчас не обнаружены.</div>
          </div>
          <div class="type-chip general">Нет тревог</div>
        </div>
      `;
      return;
    }

    container.innerHTML = points.map((p) => {
      const cls = markerTypeClass(p);
      const label = escapeHtml(p.typeLabel || p.type || "Событие");
      const area = escapeHtml(p.area || "Неизвестная зона");
      const timeText = escapeHtml(p.timeText || "Время недоступно");
      return `
        <div class="alert-row">
          <div class="alert-main">
            <div class="alert-area">${area}</div>
            <div class="alert-meta">${label}<br>${timeText}</div>
          </div>
          <div class="type-chip ${cls}">${label}</div>
        </div>
      `;
    }).join("");
  }

  function joinList(items, fallback) {
    return items.length ? items.map(escapeHtml).join(" | ") : fallback;
  }

  function render(snapshotRaw) {
    const snapshot = normalizeSnapshot(snapshotRaw);
    lastSnapshot = snapshot;

    applyStateTheme(snapshot);

    setText("state", snapshot.state);
    setText("simpleTitle", snapshot.simpleTitle);
    setText("simpleBody", snapshot.simpleBody);
    setText("score", snapshot.riskScore);
    setText("uniqueCount", snapshot.uniqueCount);
    setText("rocketScore", snapshot.rocketScore);
    setText("uavScore", snapshot.uavScore);
    setText("eta", snapshot.eta);
    setText("updatedAt", snapshot.generatedAtText || "—");
    setText("confidenceTop", snapshot.confidence);
    setText("confidenceText", snapshot.confidence);
    setText("possibleApproach", snapshot.possibleApproach);
    setText("nearest", snapshot.nearestText);
    setText("activeNow", snapshot.activeText);
    setText("clusterSummary", snapshot.clusterText);
    setText("stateReasoning", snapshot.stateReasoning);
    setText("rocketReasoning", snapshot.rocketReasoning);
    setText("rocketTechnical", snapshot.rocketTechnical);
    setText("uavReasoning", snapshot.uavReasoning);
    setText("uavTechnical", snapshot.uavTechnical);
    setText("areas", joinList(snapshot.areas, "Нет"));
    setText("reasons", joinList(snapshot.reasons, "Сейчас нет необычных признаков"));

    const lastAlertsEl = document.getElementById("lastAlerts");
    if (lastAlertsEl) lastAlertsEl.innerHTML = snapshot.lastAlertsHtml || "Нет";

    renderAlertsList(snapshot);
    renderMap(snapshot);

    if (!hasDoneInitialFocus) {
      focusMap(snapshot);
      hasDoneInitialFocus = true;
    } else if (mapAutoMode) {
      focusMap(snapshot);
    }
  }

  function setText(id, value) {
    const el = document.getElementById(id);
    if (el) el.textContent = value;
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/\"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function hexToRgba(hex, alpha) {
    const clean = String(hex).replace("#", "");
    const full = clean.length === 3 ? clean.split("").map(ch => ch + ch).join("") : clean;
    const r = parseInt(full.slice(0, 2), 16);
    const g = parseInt(full.slice(2, 4), 16);
    const b = parseInt(full.slice(4, 6), 16);
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
  }

  async function fetchJson(url) {
    const res = await fetch(`${url}?_=${Date.now()}`, { cache: "no-store" });
    if (!res.ok) throw new Error(`HTTP ${res.status} for ${url}`);
    return res.json();
  }

  async function pollSnapshot() {
    try {
      const snapshot = await fetchJson(SNAPSHOT_URL);
      setApiStatus(true, "API: OK");
      render(snapshot);
      scheduleNextPoll(META_POLL_MS);
    } catch (err) {
      console.error(err);
      setApiStatus(false, "API: ОШИБКА");

      render({
        state: "NORMAL",
        riskScore: 0,
        rocketScore: 0,
        uavScore: 0,
        confidence: "LOW",
        eta: "—",
        possibleApproach: "Сейчас нет явного направления подхода",
        uniqueCount: 0,
        areas: [],
        reasons: ["Ошибка связи"],
        activeText: "Сейчас не активно",
        lastAlertsHtml: "Нет",
        clusterText: "Нет данных",
        simpleTitle: "Не удалось загрузить данные",
        simpleBody: "Сейчас нет нормальной связи с API. Проверь, что endpoint `/red/api/beready_snapshot` доступен через nginx.",
        stateReasoning: "Статус не был пересчитан из-за ошибки API.",
        rocketReasoning: "Сейчас невозможно рассчитать ракетный движок.",
        uavReasoning: "Сейчас невозможно рассчитать движок летательных аппаратов.",
        rocketTechnical: "API unavailable",
        uavTechnical: "API unavailable",
        mapPoints: [],
        uavTrackLine: [],
        nearestText: "Сейчас нет данных для отображения."
      });

      scheduleNextPoll(RETRY_POLL_MS);
    }
  }

  function scheduleNextPoll(delay) {
    clearTimeout(pollTimer);
    pollTimer = setTimeout(pollSnapshot, delay);
  }

  document.addEventListener("DOMContentLoaded", async () => {
    setApiStatus(false, "API: ...");
    initMap();
    updateMapStatus();

    try {
      await pollSnapshot();
    } catch (err) {
      console.error(err);
      scheduleNextPoll(RETRY_POLL_MS);
    }
  });
})();
