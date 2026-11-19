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

const phonePattern = /^(?:\+7|8)\s?\(?\d{3}\)?[\s-]?\d{3}[\s-]?\d{2}[\s-]?\d{2}$/;
const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

document.querySelectorAll('form[method="post"]').forEach(form => {
    form.noValidate = true;
    const fields = [...form.querySelectorAll("input, select, textarea")]
        .filter(field => !["hidden", "submit", "button", "reset"].includes(field.type));

    const errorFor = field => {
        let error = field.parentElement.querySelector(`.client-field-error[data-for="${field.id}"]`);
        if (!error) {
            error = document.createElement("span");
            error.className = "client-field-error";
            error.dataset.for = field.id;
            error.id = `${field.id}-client-error`;
            error.setAttribute("aria-live", "polite");
            field.insertAdjacentElement("afterend", error);
        }
        return error;
    };

    const validate = field => {
        const value = field.value.trim();
        let message = "";
        if (field.required && !value) {
            message = "Заполните это поле.";
        } else if (value && field.dataset.contactInput === "true" && value.includes("@") && !emailPattern.test(value)) {
            message = "Введите корректный адрес электронной почты или номер телефона.";
        } else if (value && field.dataset.contactInput === "true" && !value.includes("@") && !phonePattern.test(value)) {
            message = "Введите корректную почту или телефон в формате +7 999 123-45-67.";
        } else if (value && field.type === "email" && !emailPattern.test(value)) {
            message = "Введите корректный адрес электронной почты.";
        } else if (value && field.type === "tel" && !phonePattern.test(value)) {
            message = "Введите телефон в формате +7 999 123-45-67 или 8 999 123-45-67.";
        } else if (value && field.minLength > 0 && value.length < field.minLength) {
            message = `Введите не менее ${field.minLength} символов.`;
        } else if (value && field.maxLength > 0 && value.length > field.maxLength) {
            message = `Введите не более ${field.maxLength} символов.`;
        }

        const error = errorFor(field);
        error.textContent = message;
        error.hidden = !message;
        field.setAttribute("aria-invalid", String(Boolean(message)));
        if (message) {
            field.setAttribute("aria-describedby", error.id);
        } else if (field.getAttribute("aria-describedby") === error.id) {
            field.removeAttribute("aria-describedby");
        }
        return !message;
    };

    fields.forEach(field => field.addEventListener("input", () => validate(field)));
    fields.forEach(field => field.addEventListener("change", () => validate(field)));
    form.addEventListener("submit", event => {
        const invalidFields = fields.filter(field => !validate(field));
        if (invalidFields.length) {
            event.preventDefault();
            invalidFields[0].focus();
        }
    });
});

const liveSearch = document.querySelector("#search-tool");
const productCards = [...document.querySelectorAll("[data-product-card]")];
const liveCount = document.querySelector("[data-live-count]");

if (liveSearch && productCards.length && liveCount) {
    const totalResults = Number(liveCount.dataset.total);
    const liveEmpty = document.createElement("p");
    liveEmpty.className = "catalog-live-empty";
    liveEmpty.textContent = "На этой странице совпадений нет. Измените запрос или нажмите «Найти», чтобы выполнить поиск по каталогу.";
    liveEmpty.hidden = true;
    document.querySelector(".product-grid").append(liveEmpty);

    const filterVisibleCards = () => {
        const query = liveSearch.value.trim().toLocaleLowerCase("ru");
        let visible = 0;
        productCards.forEach(card => {
            const matches = card.textContent.toLocaleLowerCase("ru").includes(query);
            card.hidden = !matches;
            if (matches) visible += 1;
        });
        liveEmpty.hidden = visible > 0;
        liveCount.textContent = query
            ? `Совпадений на этой странице: ${visible} из ${productCards.length}`
            : `Найдено в каталоге: ${totalResults}`;
    };

    liveSearch.addEventListener("input", filterVisibleCards);
    filterVisibleCards();
}

const rentalCalculator = document.querySelector("[data-rental-calculator]");
if (rentalCalculator) {
    const daysInput = rentalCalculator.querySelector('[name="srok"]');
    const extrasInput = rentalCalculator.querySelector('[name="osnastka"]');
    const totalOutput = rentalCalculator.querySelector("[data-rental-total]");
    const tariffs = JSON.parse(document.querySelector("#rental-tariffs").textContent);
    const extras = JSON.parse(document.querySelector("#rental-extras").textContent);
    const extraPrices = new Map(extras.map(item => [String(item.id), item.cena]));

    const updateRentalTotal = () => {
        const days = Number(daysInput.value);
        if (!Number.isInteger(days) || days < 1 || days > 60) {
            totalOutput.textContent = "Укажите срок аренды от 1 до 60 суток.";
            return;
        }
        const tariff = tariffs
            .filter(item => item.ot_dney <= days)
            .sort((a, b) => b.ot_dney - a.ot_dney)[0];
        const discount = tariff ? tariff.skidka : 0;
        const numerator = Number(rentalCalculator.dataset.dailyPrice) * days * (100 - discount);
        let rent = Math.floor(numerator / 100);
        const remainder = numerator % 100;
        if (remainder > 50 || (remainder === 50 && rent % 2 === 1)) rent += 1;
        const extrasTotal = [...extrasInput.selectedOptions]
            .reduce((sum, option) => sum + (extraPrices.get(option.value) || 0), 0);
        const total = rent + extrasTotal;
        totalOutput.textContent = `Итого к оплате: ${total.toLocaleString("ru-RU")} ₽${discount ? ` (скидка ${discount}%)` : ""}`;
    };

    daysInput.addEventListener("input", updateRentalTotal);
    extrasInput.addEventListener("change", updateRentalTotal);
    updateRentalTotal();
}

const stats = document.querySelector("#stats");
const diagramma = document.querySelector("#diagramma");

if (stats && diagramma) {
    fetch("/statistika/")
        .then(response => {
            if (!response.ok) throw new Error("Не удалось загрузить данные.");
            return response.json();
        })
        .then(data => {
            stats.textContent = `Свободно исправных экземпляров: ${data.svobodno} из ${data.ekzemplyarov}.`;
            diagramma.replaceChildren();

            const categories = data.po_kategoriyam;
            if (!categories.length) {
                diagramma.textContent = "Категорий пока нет.";
                return;
            }

            const max = Math.max(...categories.map(item => item.svobodno), 1);
            categories.forEach(item => {
                const row = document.createElement("div");
                const label = document.createElement("span");
                const track = document.createElement("div");
                const bar = document.createElement("div");
                const value = document.createElement("strong");

                row.className = "rental-stats__row";
                label.className = "rental-stats__category";
                label.textContent = item.nazvanie;
                track.className = "rental-stats__track";
                bar.className = "rental-stats__bar";
                bar.style.width = `${item.svobodno / max * 100}%`;
                track.setAttribute("aria-hidden", "true");
                value.className = "rental-stats__value";
                value.textContent = item.svobodno;
                row.append(label, track, value);
                track.append(bar);
                diagramma.append(row);
            });
        })
        .catch(() => {
            stats.textContent = "Не удалось загрузить статистику. Обновите страницу и попробуйте снова.";
            diagramma.replaceChildren();
        });
}
