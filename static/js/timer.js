function renderParkingTimer(element) {
    const expiration = Date.parse(element.dataset.expiration);
    if (!Number.isFinite(expiration)) {
        element.textContent = "Timer unavailable";
        return;
    }

    const update = () => {
        const remaining = Math.max(0, Math.floor((expiration - Date.now()) / 1000));
        const hours = Math.floor(remaining / 3600);
        const minutes = Math.floor((remaining % 3600) / 60);
        const seconds = remaining % 60;
        element.textContent = [hours, minutes, seconds]
            .map((part) => String(part).padStart(2, "0"))
            .join(":");
        element.classList.toggle("timer-expired", remaining === 0);
    };

    update();
    window.setInterval(update, 1000);
}

document.querySelectorAll(".timer-countdown").forEach(renderParkingTimer);
