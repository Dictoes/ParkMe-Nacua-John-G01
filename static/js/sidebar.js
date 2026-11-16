document.querySelectorAll("[data-sidebar-toggle]").forEach((toggle) => {
    const sidebar = document.getElementById(toggle.getAttribute("aria-controls"));
    if (!sidebar) {
        return;
    }

    toggle.addEventListener("click", () => {
        const isOpen = sidebar.classList.toggle("is-open");
        toggle.setAttribute("aria-expanded", String(isOpen));
    });

    sidebar.querySelectorAll("a").forEach((link) => {
        link.addEventListener("click", () => {
            sidebar.classList.remove("is-open");
            toggle.setAttribute("aria-expanded", "false");
        });
    });
});
