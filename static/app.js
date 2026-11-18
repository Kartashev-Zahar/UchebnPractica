const menuButton = document.querySelector(".menu-toggle");
const mainNavigation = document.querySelector("#main-navigation");

if (menuButton && mainNavigation) {
    menuButton.addEventListener("click", () => {
        const isExpanded = menuButton.getAttribute("aria-expanded") === "true";
        menuButton.setAttribute("aria-expanded", String(!isExpanded));
        menuButton.setAttribute("aria-label", isExpanded ? "Открыть меню" : "Закрыть меню");
        mainNavigation.classList.toggle("is-open", !isExpanded);
    });
}

if (document.querySelector("#stats") && document.querySelector("#diagramma")) {
fetch("/statistika/")
    .then(response => response.json())
    .then(data => {
        const stats = document.querySelector("#stats");
        const diagramma = document.querySelector("#diagramma");

        stats.textContent = [
            `Инструментов: ${data.pozicij}`,
            `экземпляров: ${data.ekzemplyarov}`,
            `свободно: ${data.svobodno}`,
            `средняя цена: ${data.srednyaya_cena} ₽`,
            `залоги: ${data.summa_zalogov} ₽`,
            `заказов: ${data.zakazov}`
        ].join(", ");

        const max = Math.max(...data.po_kategoriyam.map(item => item.svobodno), 1);

        data.po_kategoriyam.forEach(item => {
            const column = document.createElement("div");
            const value = document.createElement("span");
            const bar = document.createElement("div");
            const label = document.createElement("small");

            column.className = "kolonka";
            value.textContent = item.svobodno;
            bar.className = "stolbec";
            bar.style.height = `${item.svobodno / max * 100}px`;
            label.textContent = item.nazvanie;

            column.append(value, bar, label);
            diagramma.append(column);
        });
    });
}
