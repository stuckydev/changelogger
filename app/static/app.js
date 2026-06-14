(function () {
  const APP_PREFIX = "clg";
  const COOKIE_MUTED = `${APP_PREFIX}_muted_apps`;
  const COOKIE_THEME = `${APP_PREFIX}_theme`;
  const SIDEBAR_POLL_MS = 60_000;

  const filterList = document.getElementById("app-filter-list");
  const feedRoot = document.getElementById("feed-root");
  const sidebarSyncStatus = document.getElementById("sidebar-sync-status");
  const themeToggle = document.getElementById("theme-toggle");
  const sidebar = document.getElementById("app-sidebar");
  const sidebarToggle = document.getElementById("sidebar-toggle");
  const sidebarClose = document.getElementById("sidebar-close");
  const sidebarBackdrop = document.getElementById("sidebar-backdrop");
  const mobileSidebarQuery = window.matchMedia("(max-width: 47.99rem)");

  let focusedAppSlug = null;

  function isMobileSidebar() {
    return mobileSidebarQuery.matches;
  }

  function readMutedFromDom() {
    return Array.from(filterList.querySelectorAll(".app-filter-item.is-muted")).map(
      (item) => item.dataset.appSlug
    );
  }

  function readTheme() {
    return document.documentElement.dataset.theme === "light" ? "light" : "dark";
  }

  function savePreferences(mutedApps, theme) {
    const payload = { muted_apps: mutedApps, theme: theme || null };
    return fetch("/api/preferences", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }).then((response) => {
      if (!response.ok) {
        throw new Error("Einstellungen konnten nicht gespeichert werden.");
      }
    });
  }

  function refreshSidebar() {
    if (!filterList) return Promise.resolve();
    return fetch("/api/sidebar")
      .then((response) => {
        if (!response.ok) {
          throw new Error("Sidebar konnte nicht aktualisiert werden.");
        }
        return response.json();
      })
      .then((data) => {
        filterList.innerHTML = data.apps_html;
        if (sidebarSyncStatus) {
          sidebarSyncStatus.innerHTML = data.sync_html;
        }
        setFocusedApp(focusedAppSlug);
      })
      .catch((error) => {
        console.error(error);
      });
  }

  function refreshFeed() {
    if (!feedRoot) return Promise.resolve();
    feedRoot.setAttribute("aria-busy", "true");
    return fetch("/api/feed")
      .then((response) => {
        if (!response.ok) {
          throw new Error("Feed konnte nicht aktualisiert werden.");
        }
        return response.text();
      })
      .then((html) => {
        feedRoot.innerHTML = html;
        applyFeedFocus();
      })
      .catch((error) => {
        console.error(error);
      })
      .finally(() => {
        feedRoot.setAttribute("aria-busy", "false");
      });
  }

  function persistMutedApps(mutedApps) {
    return savePreferences(mutedApps, readTheme())
      .then(() => Promise.all([refreshFeed(), refreshSidebar()]))
      .catch((error) => {
        console.error(error);
      });
  }

  function updateFeedDividers() {
    const feedList = feedRoot?.querySelector("#feed-list");
    if (!feedList) return;

    const items = Array.from(feedList.children);
    for (let index = 0; index < items.length; index += 1) {
      const item = items[index];
      if (!item.classList.contains("feed-month-divider")) continue;

      let hasVisible = false;
      for (let next = index + 1; next < items.length; next += 1) {
        if (items[next].classList.contains("feed-month-divider")) break;
        if (!items[next].classList.contains("is-hidden")) {
          hasVisible = true;
          break;
        }
      }
      item.classList.toggle("is-hidden", !hasVisible);
    }

    updateStickyMonthDividers();
  }

  function getMonthDividerStickyTop() {
    const divider = feedRoot?.querySelector(".feed-month-divider:not(.is-hidden)");
    if (!divider) return 0;
    const top = parseFloat(getComputedStyle(divider).top);
    return Number.isFinite(top) ? top : 0;
  }

  function updateStickyMonthDividers() {
    const feedList = feedRoot?.querySelector("#feed-list");
    if (!feedList) return;

    const dividers = Array.from(feedList.querySelectorAll(".feed-month-divider:not(.is-hidden)"));
    if (!dividers.length) return;

    const stickyTop = getMonthDividerStickyTop();
    let pinnedIndex = -1;

    dividers.forEach((divider, index) => {
      divider.style.zIndex = String(6 + index);
      if (divider.getBoundingClientRect().top <= stickyTop + 1) {
        pinnedIndex = index;
      }
    });

    dividers.forEach((divider, index) => {
      divider.classList.toggle("is-pinned-hidden", pinnedIndex >= 0 && index < pinnedIndex);
    });
  }

  function updateFeedEmptyStates() {
    const feedList = feedRoot?.querySelector("#feed-list");
    const emptyFiltered = feedRoot?.querySelector("#feed-empty-filtered");
    if (!emptyFiltered) return;

    const cards = feedList ? feedList.querySelectorAll(".feed-card") : [];
    const visibleCards = feedList ? feedList.querySelectorAll(".feed-card:not(.is-hidden)") : [];
    const showEmpty = cards.length > 0 && visibleCards.length === 0;
    emptyFiltered.classList.toggle("is-hidden", !showEmpty);
  }

  function applyFeedFocus() {
    const feedList = feedRoot?.querySelector("#feed-list");
    if (!feedList) return;

    feedList.querySelectorAll(".feed-card").forEach((card) => {
      const visible = !focusedAppSlug || card.dataset.appSlug === focusedAppSlug;
      card.classList.toggle("is-hidden", !visible);
    });

    updateFeedDividers();
    updateFeedEmptyStates();
  }

  function setFocusedApp(slug) {
    focusedAppSlug = slug || null;
    if (!filterList) return;

    filterList.classList.toggle("is-focusing", Boolean(focusedAppSlug));
    filterList.querySelectorAll(".app-filter-item").forEach((item) => {
      const isFocused = item.dataset.appSlug === focusedAppSlug;
      item.classList.toggle("is-focused", isFocused);
      const focusArea = item.querySelector(".app-filter-item__focus");
      if (focusArea) {
        focusArea.setAttribute("aria-pressed", isFocused ? "true" : "false");
      }
    });
    applyFeedFocus();
  }

  function toggleMute(slug) {
    const item = filterList.querySelector(`.app-filter-item[data-app-slug="${slug}"]`);
    const muteBtn = filterList.querySelector(`.app-filter-item__mute-btn[data-app-slug="${slug}"]`);
    if (!item || !muteBtn) return;

    const nextMuted = !item.classList.contains("is-muted");
    item.classList.toggle("is-muted", nextMuted);
    muteBtn.setAttribute("aria-pressed", nextMuted ? "true" : "false");

    persistMutedApps(readMutedFromDom());
  }

  function syncSidebarLayout() {
    if (!sidebar || !sidebarToggle) return;

    if (isMobileSidebar()) {
      const isOpen = sidebar.classList.contains("is-open");
      sidebar.setAttribute("aria-hidden", isOpen ? "false" : "true");
      sidebarToggle.setAttribute("aria-expanded", isOpen ? "true" : "false");
      if (sidebarClose) sidebarClose.hidden = !isOpen;
      return;
    }

    sidebar.classList.remove("is-open");
    sidebar.setAttribute("aria-hidden", "false");
    sidebarToggle.setAttribute("aria-expanded", "false");
    if (sidebarClose) sidebarClose.hidden = true;
    if (sidebarBackdrop) {
      sidebarBackdrop.classList.remove("is-visible");
      sidebarBackdrop.hidden = true;
    }
    document.body.classList.remove("sidebar-open");
  }

  function openSidebar() {
    if (!isMobileSidebar()) return;
    sidebar.classList.add("is-open");
    sidebar.setAttribute("aria-hidden", "false");
    sidebarToggle.setAttribute("aria-expanded", "true");
    if (sidebarClose) sidebarClose.hidden = false;
    sidebarBackdrop.hidden = false;
    requestAnimationFrame(() => {
      sidebarBackdrop.classList.add("is-visible");
    });
    document.body.classList.add("sidebar-open");
  }

  function closeSidebar() {
    if (!isMobileSidebar()) return;
    sidebar.classList.remove("is-open");
    sidebar.setAttribute("aria-hidden", "true");
    sidebarToggle.setAttribute("aria-expanded", "false");
    if (sidebarClose) sidebarClose.hidden = true;
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
    if (!isMobileSidebar()) return;
    if (sidebar.classList.contains("is-open")) {
      closeSidebar();
    } else {
      openSidebar();
    }
  }

  const THEME_COLORS = { dark: "#06080f", light: "#eef1f8" };

  function applyTheme(theme) {
    document.documentElement.dataset.theme = theme;
    document.cookie = `${COOKIE_THEME}=${theme};path=/;max-age=31536000;SameSite=Lax`;
    const meta = document.getElementById("meta-theme-color");
    if (meta) meta.content = THEME_COLORS[theme] || THEME_COLORS.dark;
  }

  if (sidebarToggle) {
    sidebarToggle.addEventListener("click", toggleSidebar);
  }
  if (sidebarClose) {
    sidebarClose.addEventListener("click", closeSidebar);
  }
  if (sidebarBackdrop) {
    sidebarBackdrop.addEventListener("click", closeSidebar);
  }

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && isMobileSidebar() && sidebar.classList.contains("is-open")) {
      closeSidebar();
      sidebarToggle.focus();
    }
  });

  if (typeof mobileSidebarQuery.addEventListener === "function") {
    mobileSidebarQuery.addEventListener("change", syncSidebarLayout);
  } else if (typeof mobileSidebarQuery.addListener === "function") {
    mobileSidebarQuery.addListener(syncSidebarLayout);
  }

  syncSidebarLayout();

  function toggleAppFilter(slug) {
    setFocusedApp(focusedAppSlug === slug ? null : slug);
    if (isMobileSidebar()) {
      closeSidebar();
    }
  }

  filterList.addEventListener("click", (event) => {
    const muteBtn = event.target.closest(".app-filter-item__mute-btn");
    if (muteBtn) {
      event.preventDefault();
      event.stopPropagation();
      toggleMute(muteBtn.dataset.appSlug);
      return;
    }

    const focusArea = event.target.closest(".app-filter-item__focus");
    if (!focusArea) return;
    event.preventDefault();
    event.stopPropagation();
    toggleAppFilter(focusArea.dataset.appSlug);
  });

  filterList.addEventListener("keydown", (event) => {
    const focusArea = event.target.closest(".app-filter-item__focus");
    if (!focusArea) return;
    if (event.key !== "Enter" && event.key !== " ") return;
    event.preventDefault();
    toggleAppFilter(focusArea.dataset.appSlug);
  });

  if (themeToggle) {
    themeToggle.addEventListener("click", () => {
      const nextTheme = readTheme() === "dark" ? "light" : "dark";
      applyTheme(nextTheme);
      savePreferences(readMutedFromDom(), nextTheme).catch((error) => {
        console.error(error);
      });
    });
  }

  let stickyMonthTicking = false;
  function scheduleStickyMonthUpdate() {
    if (stickyMonthTicking) return;
    stickyMonthTicking = true;
    requestAnimationFrame(() => {
      stickyMonthTicking = false;
      updateStickyMonthDividers();
    });
  }

  window.addEventListener("scroll", scheduleStickyMonthUpdate, { passive: true });
  window.addEventListener("resize", scheduleStickyMonthUpdate, { passive: true });
  scheduleStickyMonthUpdate();

  const scrollTopBtn = document.getElementById("scroll-top");
  if (scrollTopBtn) {
    let scrollTopVisible = false;
    const updateScrollTop = () => {
      const shouldShow = window.scrollY > 600;
      if (shouldShow !== scrollTopVisible) {
        scrollTopVisible = shouldShow;
        scrollTopBtn.classList.toggle("is-visible", shouldShow);
      }
    };
    window.addEventListener("scroll", updateScrollTop, { passive: true });
    updateScrollTop();
    scrollTopBtn.addEventListener("click", () => {
      const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      window.scrollTo({ top: 0, behavior: reduceMotion ? "auto" : "smooth" });
    });
  }

  window.setInterval(() => {
    if (document.visibilityState === "visible") {
      refreshSidebar();
    }
  }, SIDEBAR_POLL_MS);

  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible") {
      refreshSidebar();
    }
  });

})();
