(function () {
  const APP_PREFIX = "clg";
  const COOKIE_MUTED = `${APP_PREFIX}_muted_apps`;
  const COOKIE_THEME = `${APP_PREFIX}_theme`;
  const THEME_KEY = `${APP_PREFIX}-theme`;

  const filterList = document.getElementById("app-filter-list");
  const feedRoot = document.getElementById("feed-root");
  const clearMutedBtn = document.getElementById("clear-muted-apps");
  const filterCount = document.getElementById("app-filter-count");
  const themeToggle = document.getElementById("theme-toggle");
  const sidebar = document.getElementById("app-sidebar");
  const sidebarToggle = document.getElementById("sidebar-toggle");
  const sidebarBackdrop = document.getElementById("sidebar-backdrop");
  const mobileSidebarQuery = window.matchMedia("(max-width: 47.99rem)");
  const coarsePointerQuery = window.matchMedia("(hover: none), (pointer: coarse)");

  let focusedAppSlug = null;

  function isMobileSidebar() {
    return mobileSidebarQuery.matches;
  }

  function usesTapFocus() {
    return coarsePointerQuery.matches;
  }

  function readMutedFromDom() {
    return Array.from(filterList.querySelectorAll(".app-toggle__input:checked")).map(
      (input) => input.dataset.appSlug
    );
  }

  function updateFilterCount() {
    if (!filterCount || !filterList) return;
    const inputs = filterList.querySelectorAll(".app-toggle__input");
    const muted = filterList.querySelectorAll(".app-toggle__input:checked");
    const mutedCount = muted.length;

    if (mutedCount === 0) {
      filterCount.textContent = "";
      filterCount.hidden = true;
      if (clearMutedBtn) clearMutedBtn.hidden = true;
      return;
    }

    filterCount.hidden = false;
    filterCount.textContent = `${mutedCount}/${inputs.length}`;
    if (clearMutedBtn) clearMutedBtn.hidden = false;
  }

  function clearAllMutes() {
    filterList.querySelectorAll(".app-toggle__input").forEach((input) => {
      input.checked = false;
    });
    filterList.querySelectorAll(".app-filter-item__mute-btn").forEach((btn) => {
      btn.setAttribute("aria-pressed", "false");
    });
  }

  function savePreferences(mutedApps, theme) {
    const payload = { muted_apps: mutedApps, theme: theme || null };
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

  function refreshFeed() {
    if (!feedRoot) return Promise.resolve();
    feedRoot.setAttribute("aria-busy", "true");
    return fetch("/api/feed")
      .then((response) => {
        if (!response.ok) {
          throw new Error("Could not refresh feed.");
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
    return savePreferences(mutedApps, document.documentElement.dataset.theme)
      .then(() => refreshFeed())
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
      item.classList.toggle("is-focused", item.dataset.appSlug === focusedAppSlug);
    });
    applyFeedFocus();
  }

  function toggleMute(slug) {
    const input = filterList.querySelector(`.app-toggle__input[data-app-slug="${slug}"]`);
    const muteBtn = filterList.querySelector(`.app-filter-item__mute-btn[data-app-slug="${slug}"]`);
    if (!input) return;

    input.checked = !input.checked;
    if (muteBtn) {
      muteBtn.setAttribute("aria-pressed", input.checked ? "true" : "false");
    }

    const nextMuted = readMutedFromDom();
    updateFilterCount();
    persistMutedApps(nextMuted);
  }

  function syncSidebarLayout() {
    if (!sidebar || !sidebarToggle) return;

    if (isMobileSidebar()) {
      const isOpen = sidebar.classList.contains("is-open");
      sidebar.setAttribute("aria-hidden", isOpen ? "false" : "true");
      sidebarToggle.setAttribute("aria-expanded", isOpen ? "true" : "false");
      sidebarToggle.setAttribute("aria-label", isOpen ? "Close menu" : "Open menu");
      return;
    }

    sidebar.classList.remove("is-open");
    sidebar.setAttribute("aria-hidden", "false");
    sidebarToggle.setAttribute("aria-expanded", "false");
    sidebarToggle.setAttribute("aria-label", "Open menu");
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
    sidebarToggle.setAttribute("aria-label", "Close menu");
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
    if (!isMobileSidebar()) return;
    if (sidebar.classList.contains("is-open")) {
      closeSidebar();
    } else {
      openSidebar();
    }
  }

  if (sidebarToggle) {
    sidebarToggle.addEventListener("click", toggleSidebar);
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

  filterList.addEventListener("click", (event) => {
    const muteBtn = event.target.closest(".app-filter-item__mute-btn");
    if (!muteBtn) return;

    event.preventDefault();
    event.stopPropagation();
    toggleMute(muteBtn.dataset.appSlug);
  });

  filterList.querySelectorAll(".app-filter-item__focus").forEach((focusArea) => {
    const slug = focusArea.dataset.appSlug;

    focusArea.addEventListener("mouseenter", () => {
      if (!usesTapFocus()) {
        setFocusedApp(slug);
      }
    });

    focusArea.addEventListener("click", () => {
      if (!usesTapFocus()) return;
      setFocusedApp(focusedAppSlug === slug ? null : slug);
    });

    focusArea.addEventListener("keydown", (event) => {
      if (event.key !== "Enter" && event.key !== " ") return;
      event.preventDefault();
      setFocusedApp(focusedAppSlug === slug ? null : slug);
    });
  });

  filterList.addEventListener("mouseleave", (event) => {
    if (usesTapFocus()) return;
    if (!event.relatedTarget || !filterList.contains(event.relatedTarget)) {
      setFocusedApp(null);
    }
  });

  document.addEventListener("click", (event) => {
    if (!usesTapFocus() || !focusedAppSlug) return;
    if (filterList.contains(event.target)) return;
    setFocusedApp(null);
  });

  if (clearMutedBtn) {
    clearMutedBtn.addEventListener("click", () => {
      clearAllMutes();
      updateFilterCount();
      persistMutedApps([]);
    });
  }

  function applyTheme(theme) {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem(THEME_KEY, theme);
    document.cookie = `${COOKIE_THEME}=${theme};path=/;max-age=31536000;SameSite=Lax`;
  }

  themeToggle.addEventListener("click", () => {
    const nextTheme = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
    applyTheme(nextTheme);
    savePreferences(readMutedFromDom(), nextTheme).catch((error) => {
      console.error(error);
    });
  });

  updateFilterCount();
})();
