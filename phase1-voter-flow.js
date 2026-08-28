/*
RIEP homepage cleanup after Phase 1 merge.
Keeps the existing homepage design but simplifies navigation and search results.
*/

(() => {
  function norm(value) {
    return String(value || "")
      .replace(/\s+/g, " ")
      .trim()
      .toLowerCase();
  }

  function cleanupHomeButtons() {
    const links = [...document.querySelectorAll("a")];

    const ballotLinks = links.filter(a => {
      const text = norm(a.textContent);
      return (
        text.includes("find my ballot") ||
        text.includes("who's on my ballot") ||
        text.includes("who’s on my ballot")
      );
    });

    if (ballotLinks[0]) {
      ballotLinks[0].textContent = "Find My Ballot";
      ballotLinks[0].href = "ballot.html";
    }

    if (ballotLinks[1]) {
      ballotLinks[1].textContent = "Find My Precinct";
      ballotLinks[1].href = "lookup.html";
    }

    links.forEach(a => {
      const text = norm(a.textContent);

      if (
        text === "meet the candidates" ||
        text === "compare candidates"
      ) {
        a.textContent = "Races & Candidates";
        a.href = "running.html";
      }

      if (
        text === "who's running?" ||
        text === "who’s running?" ||
        text === "all races"
      ) {
        a.textContent = "Races & Candidates";
        a.href = "running.html";
      }
    });
  }

  function simplifyCandidateResults() {
    const anchors = [...document.querySelectorAll("a")];

    anchors.forEach(anchor => {
      const text = norm(anchor.textContent);

      if (
        text === "who's on this ballot?" ||
        text === "who’s on this ballot?"
      ) {
        anchor.style.display = "none";

        const container = anchor.parentElement;

        if (!container) return;

        const compareLink = [...container.querySelectorAll("a")].find(a => {
          const label = norm(a.textContent);
          return (
            label === "compare candidates" ||
            label === "races & candidates"
          );
        });

        if (compareLink) {
          compareLink.textContent = "Compare race candidates";

          try {
            const oldUrl = new URL(compareLink.href, location.href);

            const chamber = oldUrl.searchParams.get("chamber");
            const district = oldUrl.searchParams.get("district");

            const targetUrl = new URL("running.html", location.href);

            if (chamber) {
              targetUrl.searchParams.set("chamber", chamber);
            }

            if (district) {
              targetUrl.searchParams.set("district", district);
            }

            compareLink.href = targetUrl.href;
          } catch (error) {
            console.warn("Could not rebuild candidate comparison link", error);
          }
        }
      }
    });
  }

  function cleanupSearchResultButtons() {
    const resultCards = [...document.querySelectorAll("body *")].filter(el => {
      const links = [...el.children].filter(child => child.tagName === "A");

      if (links.length < 2) return false;

      const labels = links.map(a => norm(a.textContent));

      return (
        labels.some(label =>
          label.includes("compare candidates")
        ) &&
        labels.some(label =>
          label.includes("campaign finance")
        )
      );
    });

    resultCards.forEach(container => {
      const links = [...container.querySelectorAll(":scope > a")];

      const compare = links.find(a => {
        const text = norm(a.textContent);
        return (
          text === "compare candidates" ||
          text === "races & candidates" ||
          text === "compare race candidates"
        );
      });

      const ballot = links.find(a => {
        const text = norm(a.textContent);
        return (
          text.includes("who's on this ballot") ||
          text.includes("who’s on this ballot")
        );
      });

      if (ballot) {
        ballot.style.display = "none";
      }

      if (compare) {
        compare.textContent = "Compare race candidates";

        try {
          const currentUrl = new URL(compare.href, location.href);

          const chamber = currentUrl.searchParams.get("chamber");
          const district = currentUrl.searchParams.get("district");

          const target = new URL("running.html", location.href);

          if (chamber) {
            target.searchParams.set("chamber", chamber);
          }

          if (district) {
            target.searchParams.set("district", district);
          }

          compare.href = target.href;
        } catch (error) {
          console.warn("Unable to update compare link", error);
        }
      }
    });
  }

  function runPhaseOneCleanup() {
    cleanupHomeButtons();
    simplifyCandidateResults();
    cleanupSearchResultButtons();
  }

  function startObserver() {
    const observer = new MutationObserver(() => {
      runPhaseOneCleanup();
    });

    observer.observe(document.body, {
      subtree: true,
      childList: true
    });
  }

  function init() {
    runPhaseOneCleanup();
    startObserver();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
