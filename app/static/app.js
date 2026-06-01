(function () {
  const APP_PREFIX = "clg";
  const COOKIE_SELECTED = `${APP_PREFIX}_selected_apps`;
  const COOKIE_THEME = `${APP_PREFIX}_theme`;
  const THEME_KEY = `${APP_PREFIX}-theme`;

  const chipRow = document.getElementById("app-chip-row");
  const feedEmptyFiltered = document.getElementById("feed-empty-filtered");
  const selectAllBtn = document.getElementById("select-all-apps");
  const themeToggle = document.getElementById("theme-toggle");

  function hasSelectionCookie() {
    return document.cookie.split("; ").some((part) => part.startsWith(`${COOKIE_SELECTED}=`));
  }

  function readSelectedFromDom() {
    return Array.from(chipRow.querySelectorAll(".app-chip.is-active")).map(
      (chip) => chip.dataset.appSlug
    );
  }

  function setChipState(slug, active) {
    const chip = chipRow.querySelector(`[data-app-slug="${slug}"]`);
    if (!chip) return;
    chip.classList.toggle("is-active", active);
    chip.setAttribute("aria-pressed", active ? "true" : "false");
  }

  function selectAllChips() {
    chipRow.querySelectorAll(".app-chip").forEach((chip) => {
      setChipState(chip.dataset.appSlug, true);
    });
  }

  function applyFeedFilter(selectedApps) {
    const selected = new Set(selectedApps);
    const cards = document.querySelectorAll(".feed-card[data-app-slug]");
    let visibleCount = 0;

    cards.forEach((card) => {
      const show = selected.has(card.dataset.appSlug);
      card.classList.toggle("is-hidden", !show);
      if (show) visibleCount += 1;
    });

    if (feedEmptyFiltered) {
      const hasCards = cards.length > 0;
      feedEmptyFiltered.classList.toggle("is-hidden", !hasCards || visibleCount > 0);
    }
  }

  function savePreferences(selectedApps, theme) {
    return fetch("/api/preferences", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ selected_apps: selectedApps, theme: theme || null }),
    }).then((response) => {
      if (!response.ok) {
        throw new Error("Could not save preferences.");
      }
    });
  }

  function persistSelection(selectedApps) {
    savePreferences(selectedApps, document.documentElement.dataset.theme).catch((error) => {
      console.error(error);
    });
  }

  chipRow.addEventListener("click", (event) => {
    const chip = event.target.closest(".app-chip");
    if (!chip) return;

    const slug = chip.dataset.appSlug;
    const currentlyActive = chip.classList.contains("is-active");
    const activeSlugs = readSelectedFromDom();

    if (currentlyActive && activeSlugs.length === 1) {
      return;
    }

    setChipState(slug, !currentlyActive);
    const nextSelection = readSelectedFromDom();
    applyFeedFilter(nextSelection);
    persistSelection(nextSelection);
  });

  selectAllBtn.addEventListener("click", () => {
    selectAllChips();
    const nextSelection = readSelectedFromDom();
    applyFeedFilter(nextSelection);
    persistSelection(nextSelection);
  });

  function applyTheme(theme) {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem(THEME_KEY, theme);
    document.cookie = `${COOKIE_THEME}=${theme};path=/;max-age=31536000;SameSite=Lax`;
  }

  themeToggle.addEventListener("click", () => {
    const nextTheme = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
    applyTheme(nextTheme);
    savePreferences(readSelectedFromDom(), nextTheme).catch((error) => {
      console.error(error);
    });
  });

  if (!hasSelectionCookie()) {
    selectAllChips();
    persistSelection(readSelectedFromDom());
  }

  applyFeedFilter(readSelectedFromDom());
})();
