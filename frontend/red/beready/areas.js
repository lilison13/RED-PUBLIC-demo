(() => {
  const HAIFA_POINT = { lat: 32.7940, lon: 34.9896 };

  const AREA_COORDS = {
    // Haifa core
    "חיפה": { lat: 32.7940, lon: 34.9896, weight: 1.0, corridor: "haifa", track: "coast", trackOrder: 10 },
    "haifa": { lat: 32.7940, lon: 34.9896, weight: 1.0, corridor: "haifa", track: "coast", trackOrder: 10 },
    "חיפה - כרמל": { lat: 32.8000, lon: 34.9800, weight: 1.0, corridor: "haifa", track: "coast", trackOrder: 9 },
    "חיפה - מפרץ": { lat: 32.8200, lon: 35.0400, weight: 1.0, corridor: "haifa", track: "coast", trackOrder: 12 },
    "חיפה - מערב": { lat: 32.8150, lon: 34.9650, weight: 1.0, corridor: "haifa", track: "coast", trackOrder: 11 },

    // Haifa ring / Krayot
    "נשר": { lat: 32.7650, lon: 35.0450, weight: 0.95, corridor: "haifa", track: "inland", trackOrder: 15 },
    "nesher": { lat: 32.7650, lon: 35.0450, weight: 0.95, corridor: "haifa", track: "inland", trackOrder: 15 },
    "טירת כרמל": { lat: 32.7600, lon: 34.9700, weight: 0.95, corridor: "coast", track: "coast", trackOrder: 8 },
    "tirat carmel": { lat: 32.7600, lon: 34.9700, weight: 0.95, corridor: "coast", track: "coast", trackOrder: 8 },
    "רכסים": { lat: 32.8200, lon: 35.1000, weight: 0.88, corridor: "haifa", track: "inland", trackOrder: 18 },
    "rechasim": { lat: 32.8200, lon: 35.1000, weight: 0.88, corridor: "haifa", track: "inland", trackOrder: 18 },

    "קריית אתא": { lat: 32.8100, lon: 35.1100, weight: 0.95, corridor: "krayot", track: "inland", trackOrder: 28 },
    "קרית אתא": { lat: 32.8100, lon: 35.1100, weight: 0.95, corridor: "krayot", track: "inland", trackOrder: 28 },
    "kiryat ata": { lat: 32.8100, lon: 35.1100, weight: 0.95, corridor: "krayot", track: "inland", trackOrder: 28 },

    "קריית ביאליק": { lat: 32.8300, lon: 35.0850, weight: 0.95, corridor: "krayot", track: "coast", trackOrder: 48 },
    "קרית ביאליק": { lat: 32.8300, lon: 35.0850, weight: 0.95, corridor: "krayot", track: "coast", trackOrder: 48 },
    "kiryat bialik": { lat: 32.8300, lon: 35.0850, weight: 0.95, corridor: "krayot", track: "coast", trackOrder: 48 },

    "קריית ים": { lat: 32.8500, lon: 35.0700, weight: 0.95, corridor: "krayot", track: "coast", trackOrder: 50 },
    "קרית ים": { lat: 32.8500, lon: 35.0700, weight: 0.95, corridor: "krayot", track: "coast", trackOrder: 50 },
    "kiryat yam": { lat: 32.8500, lon: 35.0700, weight: 0.95, corridor: "krayot", track: "coast", trackOrder: 50 },

    "קריית מוצקין": { lat: 32.8400, lon: 35.0800, weight: 0.95, corridor: "krayot", track: "coast", trackOrder: 45 },
    "קרית מוצקין": { lat: 32.8400, lon: 35.0800, weight: 0.95, corridor: "krayot", track: "coast", trackOrder: 45 },
    "kiryat motzkin": { lat: 32.8400, lon: 35.0800, weight: 0.95, corridor: "krayot", track: "coast", trackOrder: 45 },

    "קריית חיים": { lat: 32.8300, lon: 35.0300, weight: 0.95, corridor: "krayot", track: "coast", trackOrder: 35 },
    "קרית חיים": { lat: 32.8300, lon: 35.0300, weight: 0.95, corridor: "krayot", track: "coast", trackOrder: 35 },
    "kiryat haim": { lat: 32.8300, lon: 35.0300, weight: 0.95, corridor: "krayot", track: "coast", trackOrder: 35 },

    // Coast corridor
    "ראש הנקרה": { lat: 33.0860, lon: 35.1080, weight: 0.66, corridor: "coast", track: "coast", trackOrder: 100 },
    "rosh hanikra": { lat: 33.0860, lon: 35.1080, weight: 0.66, corridor: "coast", track: "coast", trackOrder: 100 },

    "שלומי": { lat: 33.0720, lon: 35.1470, weight: 0.72, corridor: "coast", track: "coast", trackOrder: 90 },
    "shlomi": { lat: 33.0720, lon: 35.1470, weight: 0.72, corridor: "coast", track: "coast", trackOrder: 90 },

    "נהריה": { lat: 33.0050, lon: 35.0940, weight: 0.85, corridor: "coast", track: "coast", trackOrder: 80 },
    "nahariya": { lat: 33.0050, lon: 35.0940, weight: 0.85, corridor: "coast", track: "coast", trackOrder: 80 },

    "עכו": { lat: 32.9280, lon: 35.0820, weight: 0.92, corridor: "coast", track: "coast", trackOrder: 70 },
    "acco": { lat: 32.9280, lon: 35.0820, weight: 0.92, corridor: "coast", track: "coast", trackOrder: 70 },
    "akko": { lat: 32.9280, lon: 35.0820, weight: 0.92, corridor: "coast", track: "coast", trackOrder: 70 },

    "לוחמי הגטאות": { lat: 32.9780, lon: 35.0960, weight: 0.74, corridor: "coast", track: "coast", trackOrder: 60 },
    "lochamei hagetaot": { lat: 32.9780, lon: 35.0960, weight: 0.74, corridor: "coast", track: "coast", trackOrder: 60 },

    "עברון": { lat: 33.0000, lon: 35.0940, weight: 0.68, corridor: "western_galilee", track: "coast", trackOrder: 78 },
    "evron": { lat: 33.0000, lon: 35.0940, weight: 0.68, corridor: "western_galilee", track: "coast", trackOrder: 78 },

    "כברי": { lat: 33.0170, lon: 35.1630, weight: 0.68, corridor: "western_galilee", track: "coast", trackOrder: 84 },
    "cabri": { lat: 33.0170, lon: 35.1630, weight: 0.68, corridor: "western_galilee", track: "coast", trackOrder: 84 },
    "kabri": { lat: 33.0170, lon: 35.1630, weight: 0.68, corridor: "western_galilee", track: "coast", trackOrder: 84 },

    "יחיעם": { lat: 33.0380, lon: 35.1970, weight: 0.68, corridor: "western_galilee", track: "coast", trackOrder: 86 },
    "yehiam": { lat: 33.0380, lon: 35.1970, weight: 0.68, corridor: "western_galilee", track: "coast", trackOrder: 86 },

    "מעלות תרשיחא": { lat: 33.0160, lon: 35.2740, weight: 0.68, corridor: "western_galilee", track: "inland", trackOrder: 82 },
    "מעלות-תרשיחא": { lat: 33.0160, lon: 35.2740, weight: 0.68, corridor: "western_galilee", track: "inland", trackOrder: 82 },
    "maalot tarshiha": { lat: 33.0160, lon: 35.2740, weight: 0.68, corridor: "western_galilee", track: "inland", trackOrder: 82 },

    // Inland north
    "כרמיאל": { lat: 32.9170, lon: 35.3050, weight: 0.62, corridor: "inland", track: "inland", trackOrder: 70 },
    "karmiel": { lat: 32.9170, lon: 35.3050, weight: 0.62, corridor: "inland", track: "inland", trackOrder: 70 },

    "סכנין": { lat: 32.8620, lon: 35.2930, weight: 0.60, corridor: "inland", track: "inland", trackOrder: 62 },
    "sakhnin": { lat: 32.8620, lon: 35.2930, weight: 0.60, corridor: "inland", track: "inland", trackOrder: 62 },

    "טמרה": { lat: 32.8530, lon: 35.1990, weight: 0.68, corridor: "inland", track: "inland", trackOrder: 58 },
    "tamra": { lat: 32.8530, lon: 35.1990, weight: 0.68, corridor: "inland", track: "inland", trackOrder: 58 },

    "שפרעם": { lat: 32.8050, lon: 35.1700, weight: 0.72, corridor: "inland", track: "inland", trackOrder: 50 },
    "שפרעם - שפרעם": { lat: 32.8050, lon: 35.1700, weight: 0.72, corridor: "inland", track: "inland", trackOrder: 50 },
    "shefa-amr": { lat: 32.8050, lon: 35.1700, weight: 0.72, corridor: "inland", track: "inland", trackOrder: 50 },

    "אעבלין": { lat: 32.8320, lon: 35.1930, weight: 0.66, corridor: "inland", track: "inland", trackOrder: 54 },
    "ibillin": { lat: 32.8320, lon: 35.1930, weight: 0.66, corridor: "inland", track: "inland", trackOrder: 54 },

    // Wide context
    "קריית שמונה": { lat: 33.2070, lon: 35.5700, weight: 0.40, corridor: "upper_north", track: "upper_north", trackOrder: 100 },
    "קרית שמונה": { lat: 33.2070, lon: 35.5700, weight: 0.40, corridor: "upper_north", track: "upper_north", trackOrder: 100 },
    "kiryat shmona": { lat: 33.2070, lon: 35.5700, weight: 0.40, corridor: "upper_north", track: "upper_north", trackOrder: 100 },

    "מטולה": { lat: 33.2790, lon: 35.5790, weight: 0.36, corridor: "upper_north", track: "upper_north", trackOrder: 110 },
    "metula": { lat: 33.2790, lon: 35.5790, weight: 0.36, corridor: "upper_north", track: "upper_north", trackOrder: 110 },

    "משגב עם": { lat: 33.2400, lon: 35.6100, weight: 0.36, corridor: "upper_north", track: "upper_north", trackOrder: 108 },
    "misgav am": { lat: 33.2400, lon: 35.6100, weight: 0.36, corridor: "upper_north", track: "upper_north", trackOrder: 108 },

    "כפר גלעדי": { lat: 33.2330, lon: 35.5710, weight: 0.36, corridor: "upper_north", track: "upper_north", trackOrder: 103 },
    "kfar giladi": { lat: 33.2330, lon: 35.5710, weight: 0.36, corridor: "upper_north", track: "upper_north", trackOrder: 103 },

    "מרגליות": { lat: 33.2160, lon: 35.5500, weight: 0.36, corridor: "upper_north", track: "upper_north", trackOrder: 102 },
    "margaliot": { lat: 33.2160, lon: 35.5500, weight: 0.36, corridor: "upper_north", track: "upper_north", trackOrder: 102 }
  };

  const AREA_ALIASES = {
    "קרית אתא": "קריית אתא",
    "קרית ביאליק": "קריית ביאליק",
    "קרית ים": "קריית ים",
    "קרית מוצקין": "קריית מוצקין",
    "קרית חיים": "קריית חיים",
    "קרית שמונה": "קריית שמונה",
    "מעלות תרשיחא": "מעלות תרשיחא",
    "מעלות-תרשיחא": "מעלות תרשיחא",
    "חיפה כרמל": "חיפה - כרמל",
    "חיפה מפרץ": "חיפה - מפרץ",
    "חיפה מערב": "חיפה - מערב",
    "שפרעם": "שפרעם",
    "עכו": "עכו",
    "נהריה": "נהריה",
    "טירת הכרמל": "טירת כרמל"
  };

  const RAW_NOISE_ZONES = [
    "גליל עליון",
    "קו העימות",
    "גליל מערבי",
    "הקריות",
    "כרמל",
    "מרכז הכרמל"
  ];

  function normalizeAreaName(raw) {
    let area = String(raw || "").trim();
    if (!area) return "";

    area = area.replace(/\s+/g, " ");
    area = area.replace(/׳|`/g, "'");
    area = area.replace(/״/g, '"');
    area = area.replace(/\u200f|\u200e/g, "");
    area = area.replace(/\s*-\s*/g, " - ");

    if (AREA_ALIASES[area]) return AREA_ALIASES[area];

    const lower = area.toLowerCase();
    if (AREA_ALIASES[lower]) return AREA_ALIASES[lower];

    return area;
  }

  AREA_ALIASES["\u05d7\u05d9\u05e4\u05d4 \u05e7\u05e8\u05d9\u05d9\u05ea \u05d7\u05d9\u05d9\u05dd \u05d5\u05e9\u05de\u05d5\u05d0\u05dc"] = "\u05d7\u05d9\u05e4\u05d4 - \u05e7\u05e8\u05d9\u05d9\u05ea \u05d7\u05d9\u05d9\u05dd \u05d5\u05e9\u05de\u05d5\u05d0\u05dc";
  AREA_COORDS["\u05d7\u05d9\u05e4\u05d4 - \u05e7\u05e8\u05d9\u05d9\u05ea \u05d7\u05d9\u05d9\u05dd \u05d5\u05e9\u05de\u05d5\u05d0\u05dc"] = { lat: 32.8300, lon: 35.0300, weight: 1.0, corridor: "krayot", track: "coast", trackOrder: 35 };

  const NOISE_ZONES = new Set(RAW_NOISE_ZONES.map(normalizeAreaName));

  function getAreaMeta(area) {
    const normalized = normalizeAreaName(area);
    return AREA_COORDS[normalized] || null;
  }

  function isNoiseZone(area) {
    return NOISE_ZONES.has(normalizeAreaName(area));
  }

  window.HAIFA_POINT = HAIFA_POINT;
  window.AREA_COORDS = AREA_COORDS;
  window.AREA_ALIASES = AREA_ALIASES;
  window.NOISE_ZONES = NOISE_ZONES;
  window.normalizeAreaName = normalizeAreaName;
  window.getAreaMeta = getAreaMeta;
  window.isNoiseZone = isNoiseZone;
})();
