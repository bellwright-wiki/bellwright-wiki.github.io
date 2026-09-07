// table sorting

document.querySelectorAll("table").forEach((table) => {
    const headers = table.querySelectorAll("thead th");
    const tbody = table.querySelector("tbody");

    if (!headers.length || !tbody) return;

    headers.forEach((header, column) => {
        header.classList.add("sortable");

        header.addEventListener("click", () => {
            const ascending = header.dataset.order !== "asc";
            const rows = [...tbody.rows];

            rows.sort((a, b) => {
                const x = a.cells[column]?.textContent.trim() ?? "";
                const y = b.cells[column]?.textContent.trim() ?? "";

                const nx = Number(x);
                const ny = Number(y);

                if (
                    x !== "" &&
                    y !== "" &&
                    !Number.isNaN(nx) &&
                    !Number.isNaN(ny)
                ) {
                    return ascending ? nx - ny : ny - nx;
                }

                return ascending
                    ? x.localeCompare(y)
                    : y.localeCompare(x);
            });

            rows.forEach((row) => tbody.appendChild(row));

            headers.forEach((other) => {
                delete other.dataset.order;
            });

            header.dataset.order = ascending ? "asc" : "desc";
        });
    });
});

// logo

document.querySelector(".logo")?.addEventListener("click", (event) => {
    const logo = event.currentTarget;
    logo.classList.remove("ringing");
    void logo.offsetWidth;
    logo.classList.add("ringing");
});

// Pagefind search

const markdownBody = document.querySelector(".markdown-body");

if (markdownBody) {
    const firstHeading = markdownBody.querySelector("h1");
    const siteSearch = document.createElement("div");
    const searchInput = document.createElement("input");
    const searchResults = document.createElement("div");

    siteSearch.className = "site-search";
    siteSearch.dataset.pagefindIgnore = "";

    searchInput.id = "search-input";
    searchInput.className = "form-control input-block";
    searchInput.type = "search";
    searchInput.placeholder = "Search Wiki";
    searchInput.autocomplete = "off";
    searchInput.setAttribute("aria-label", "Search Wiki");

    searchResults.id = "search-results";
    searchResults.setAttribute("aria-live", "polite");
    searchResults.dataset.pagefindIgnore = "";

    siteSearch.append(searchInput);
    firstHeading.after(siteSearch, searchResults);

    const scriptUrl = document.currentScript.src;
    let pagefind;
    let searchRequest = 0;

    searchInput.addEventListener("input", async () => {
        const query = searchInput.value.trim();
        const request = ++searchRequest;

        if (!query) {
            searchResults.replaceChildren();
            return;
        }

        pagefind ??= await import(
            new URL("../pagefind/pagefind.js", scriptUrl)
        ).then(async (module) => {
            const siteRoot = new URL("../", scriptUrl);
            await module.options({ baseUrl: siteRoot.pathname });
            return module;
        });

        const search = await pagefind.debouncedSearch(query);

        if (request !== searchRequest || search === null) return;

        const results = await Promise.all(
            search.results.slice(0, 20).map((result) => result.data())
        );

        searchResults.replaceChildren();

        if (!results.length) {
            searchResults.textContent = "No results found.";
            return;
        }

        results.forEach((result) => {
            const article = document.createElement("article");
            const heading = document.createElement("h2");
            const link = document.createElement("a");
            const excerpt = document.createElement("p");

            article.className = "search-result";
            link.href = result.url;
            link.textContent = result.meta.title;
            excerpt.innerHTML = result.excerpt;
            heading.append(link);
            article.append(heading, excerpt);
            searchResults.append(article);
        });
    });
}