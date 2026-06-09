(function () {
  const APP_PREFIX = "clg";
  const COOKIE_SELECTED = `${APP_PREFIX}_selected_apps`;
  const COOKIE_THEME = `${APP_PREFIX}_theme`;
  const THEME_KEY = `${APP_PREFIX}-theme`;

  const filterList = document.getElementById("app-filter-list");
  const feedRoot = document.getElementById("feed-root");
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

  function savePreferences(selectedApps, theme) {
    const payload = { selected_apps: selectedApps, theme: theme || null };
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
      })
      .catch((error) => {
        console.error(error);
      })
      .finally(() => {
        feedRoot.setAttribute("aria-busy", "false");
      });
  }

  function persistSelection(selectedApps) {
    return savePreferences(selectedApps, document.documentElement.dataset.theme)
      .then(() => refreshFeed())
      .catch((error) => {
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

  updateFilterCount();
})();
