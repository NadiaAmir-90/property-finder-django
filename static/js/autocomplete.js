
document.addEventListener("DOMContentLoaded", () => {
    const input = document.getElementById("property-search");
    const dropdown = document.getElementById("property-suggestions");

    if (!input || !dropdown) return;

    let timer;
    let controller;
    let latestRequest = 0;

    input.addEventListener("input", () => {
        const query = input.value.trim();

        clearTimeout(timer);

        if (controller) {
            controller.abort();
        }

        dropdown.replaceChildren();
        dropdown.hidden = true;

        if (query.length < 3) return;

        timer = setTimeout(async () => {
            const requestId = ++latestRequest;
            controller = new AbortController();

            try {
                const url = new URL(
                    "/api/properties/suggestions/",
                    window.location.origin
                );
                url.searchParams.set("q", query);

                const response = await fetch(url, {
                    signal: controller.signal,
                    headers: { Accept: "application/json" }
                });

                if (!response.ok) {
                    throw new Error(`Request failed: ${response.status}`);
                }

                const data = await response.json();

                // Ignore outdated responses
                if (
                    requestId !== latestRequest ||
                    input.value.trim() !== query
                ) return;

                // Supports normal arrays and paginated Django REST responses
                const properties = Array.isArray(data)
                    ? data
                    : (data.results || []);

                if (!properties.length) return;

                properties.forEach((property) => {
                    const item = document.createElement("button");

                    item.type = "button";
                    item.className = "suggestion-item";
                    item.setAttribute("role", "option");

                    const title =
                        property.title ||
                        property.name ||
                        "Untitled property";

                    const location =
                        property.location_name ||
                        property.city_name ||
                        property.location ||
                        "";

                    item.textContent = location
                        ? `${title} — ${location}`
                        : title;

                    item.addEventListener("click", () => {
                        input.value = title;
                        dropdown.hidden = true;
                        input.form.requestSubmit();
                    });

                    dropdown.appendChild(item);
                });

                dropdown.hidden = false;

            } catch (error) {
                if (error.name !== "AbortError") {
                    console.error("Property suggestions failed:", error);
                }
            }
        }, 250);
    });

    document.addEventListener("click", (event) => {
        if (
            !input.contains(event.target) &&
            !dropdown.contains(event.target)
        ) {
            dropdown.hidden = true;
        }
    });

    input.addEventListener("keydown", (event) => {
        if (event.key === "Escape") {
            dropdown.hidden = true;
        }
    });
});