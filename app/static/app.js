(function () {

  const APP_PREFIX = "clg";

  const COOKIE_SELECTED = `${APP_PREFIX}_selected_apps`;

  const COOKIE_THEME = `${APP_PREFIX}_theme`;

  const THEME_KEY = `${APP_PREFIX}-theme`;

  const READ_KEY = `${APP_PREFIX}-read-entries`;

  const COOKIE_READ = `${APP_PREFIX}_read_entries`;



  const filterList = document.getElementById("app-filter-list");

  const feedEmptyFiltered = document.getElementById("feed-empty-filtered");

  const selectAllBtn = document.getElementById("select-all-apps");

  const filterCount = document.getElementById("app-filter-count");

  const themeToggle = document.getElementById("theme-toggle");

  const sidebar = document.getElementById("app-sidebar");

  const sidebarToggle = document.getElementById("sidebar-toggle");

  const sidebarBackdrop = document.getElementById("sidebar-backdrop");



  function updateFilterCount() {

    if (!filterCount || !filterList) return;

    const inputs = filterList.querySelectorAll(".app-toggle__input");

    const selected = filterList.querySelectorAll(".app-toggle__input:checked");

    filterCount.textContent = `${selected.length}/${inputs.length}`;

  }



  function hasSelectionCookie() {

    return document.cookie.split("; ").some((part) => part.startsWith(`${COOKIE_SELECTED}=`));

  }



  function readSelectedFromDom() {

    return Array.from(filterList.querySelectorAll(".app-toggle__input:checked")).map(

      (input) => input.dataset.appSlug

    );

  }



  function setToggleState(slug, active) {

    const input = filterList.querySelector(`.app-toggle__input[data-app-slug="${slug}"]`);

    if (!input) return;

    input.checked = active;

  }



  function selectAllToggles() {

    filterList.querySelectorAll(".app-toggle__input").forEach((input) => {

      input.checked = true;

    });

  }



  function deselectAllToggles() {

    filterList.querySelectorAll(".app-toggle__input").forEach((input) => {

      input.checked = false;

    });

  }



  function allTogglesSelected() {

    const inputs = filterList.querySelectorAll(".app-toggle__input");

    return inputs.length > 0 && Array.from(inputs).every((input) => input.checked);

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



    document.querySelectorAll(".feed-month-divider[data-month]").forEach((divider) => {

      const month = divider.dataset.month;

      const hasVisibleEntry = Array.from(cards).some(

        (card) => card.dataset.month === month && !card.classList.contains("is-hidden")

      );

      divider.classList.toggle("is-hidden", !hasVisibleEntry);

    });



    if (feedEmptyFiltered) {

      const hasCards = cards.length > 0;

      feedEmptyFiltered.classList.toggle("is-hidden", !hasCards || visibleCount > 0);

    }

  }



  function savePreferences(selectedApps, theme, readEntries) {

    const payload = { selected_apps: selectedApps, theme: theme || null };

    if (readEntries !== undefined) {

      payload.read_entries = readEntries;

    }

    return fetch("/api/preferences", {

      method: "POST",

      headers: { "Content-Type": "application/json" },

      body: JSON.stringify(payload),

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



  function openSidebar() {

    sidebar.classList.add("is-open");

    sidebar.setAttribute("aria-hidden", "false");

    sidebarToggle.setAttribute("aria-expanded", "true");

    sidebarToggle.setAttribute("aria-label", "Close menu");

    sidebarBackdrop.hidden = false;

    requestAnimationFrame(() => {

      sidebarBackdrop.classList.add("is-visible");

    });

    document.body.classList.add("sidebar-open");

  }



  function closeSidebar() {

    sidebar.classList.remove("is-open");

    sidebar.setAttribute("aria-hidden", "true");

    sidebarToggle.setAttribute("aria-expanded", "false");

    sidebarToggle.setAttribute("aria-label", "Open menu");

    sidebarBackdrop.classList.remove("is-visible");

    document.body.classList.remove("sidebar-open");

    sidebarBackdrop.addEventListener(

      "transitionend",

      () => {

        if (!sidebar.classList.contains("is-open")) {

          sidebarBackdrop.hidden = true;

        }

      },

      { once: true }

    );

  }



  function toggleSidebar() {

    if (sidebar.classList.contains("is-open")) {

      closeSidebar();

    } else {

      openSidebar();

    }

  }



  sidebarToggle.addEventListener("click", toggleSidebar);

  sidebarBackdrop.addEventListener("click", closeSidebar);



  document.addEventListener("keydown", (event) => {

    if (event.key === "Escape" && sidebar.classList.contains("is-open")) {

      closeSidebar();

      sidebarToggle.focus();

    }

  });



  filterList.addEventListener("change", (event) => {

    const input = event.target.closest(".app-toggle__input");

    if (!input) return;



    const slug = input.dataset.appSlug;

    setToggleState(slug, input.checked);

    const nextSelection = readSelectedFromDom();

    applyFeedFilter(nextSelection);

    updateFilterCount();

    persistSelection(nextSelection);

  });



  selectAllBtn.addEventListener("click", () => {

    if (allTogglesSelected()) {

      deselectAllToggles();

    } else {

      selectAllToggles();

    }

    const nextSelection = readSelectedFromDom();

    applyFeedFilter(nextSelection);

    updateFilterCount();

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

    selectAllToggles();

    persistSelection(readSelectedFromDom());

  }



  applyFeedFilter(readSelectedFromDom());

  updateFilterCount();



  function loadReadIdsFromCookie() {

    const part = document.cookie.split("; ").find((chunk) => chunk.startsWith(`${COOKIE_READ}=`));

    if (!part) return new Set();

    const raw = decodeURIComponent(part.slice(COOKIE_READ.length + 1));

    if (!raw) return new Set();

    return new Set(raw.split(",").filter(Boolean));

  }



  function persistReadEntries(ids) {

    savePreferences(readSelectedFromDom(), document.documentElement.dataset.theme, [...ids]).catch((error) => {

      console.error(error);

    });

  }



  function updateReadToggle(card, isRead) {

    const toggle = card.querySelector(".feed-card__read-toggle");

    if (!toggle) return;

    toggle.setAttribute("aria-pressed", isRead ? "true" : "false");

    toggle.setAttribute("aria-label", isRead ? "Als ungelesen markieren" : "Als gelesen markieren");

  }



  function applyReadState(readIds) {

    document.querySelectorAll(".feed-card[data-entry-id]").forEach((card) => {

      const isRead = readIds.has(card.dataset.entryId);

      card.classList.toggle("is-read", isRead);

      updateReadToggle(card, isRead);

    });

  }



  function setReadState(entryId, isRead, readIds) {

    if (isRead) {

      readIds.add(entryId);

    } else {

      readIds.delete(entryId);

    }

    applyReadState(readIds);

    persistReadEntries(readIds);

  }



  let readIds = loadReadIdsFromCookie();

  applyReadState(readIds);



  function migrateLocalReadState(readIds) {

    try {

      const raw = localStorage.getItem(READ_KEY);

      if (!raw) return;

      const parsed = JSON.parse(raw);

      localStorage.removeItem(READ_KEY);

      if (!Array.isArray(parsed) || !parsed.length) return;

      parsed.forEach((entryId) => readIds.add(entryId));

      applyReadState(readIds);

      persistReadEntries(readIds);

    } catch {

      localStorage.removeItem(READ_KEY);

    }

  }



  migrateLocalReadState(readIds);



  document.addEventListener("click", (event) => {

    const toggle = event.target.closest(".feed-card__read-toggle");

    if (toggle) {

      event.preventDefault();

      const card = toggle.closest(".feed-card[data-entry-id]");

      if (!card) return;

      const entryId = card.dataset.entryId;

      if (!entryId) return;

      setReadState(entryId, !readIds.has(entryId), readIds);

      return;

    }



    const link = event.target.closest(".feed-card__more");

    if (!link) return;

    const card = link.closest(".feed-card[data-entry-id]");

    if (!card) return;

    const entryId = card.dataset.entryId;

    if (!entryId || readIds.has(entryId)) return;

    setReadState(entryId, true, readIds);

  });

})();

