/*
Rhode Island Elections Project — Phase 1 voter-flow simplification
*/

(() => {
  const page = (location.pathname.split("/").pop() || "index.html").toLowerCase();

  function normalize(text) {
    return String(text || "")
      .replace(/\s+/g, " ")
      .trim()
      .toLowerCase();
  }

  function addStyles() {
    if (document.getElementById("riepPhase1Styles")) return;

    const style = document.createElement("style");
    style.id = "riepPhase1Styles";

    style.textContent = `
      .riep-phase1-banner {
        margin: 18px auto 0;
        max-width: 1240px;
        padding: 14px 16px;
        border-radius: 18px;
        border: 1px solid rgba(79,124,255,.22);
        background: linear-gradient(135deg,#eef5ff,#f7fbff);
        color: #172554;
        display: flex;
        gap: 14px;
        align-items: center;
        justify-content: space-between;
        box-shadow: 0 10px 28px rgba(15,23,42,.06);
      }

      .riep-phase1-banner strong {
        font-size: 14px;
      }

      .riep-phase1-banner span {
        font-size: 12px;
        color: #64748b;
      }

      .riep-phase1-banner a {
        flex: 0 0 auto;
        text-decoration: none;
        padding: 9px 13px;
        border-radius: 999px;
        background: #172554;
        color: white;
        font-size: 12px;
        font-weight: 900;
      }

      @media (max-width: 640px) {
        .riep-phase1-banner {
          align-items: flex-start;
          flex-direction: column;
        }
      }
    `;

    document.head.appendChild(style);
  }

  function relabelLinks() {
    document.querySelectorAll("a").forEach(a => {
      const label = normalize(a.textContent);

      if (label === "who's running?" || label === "who’s running?") {
        a.textContent = "All Races";
        a.href = "running.html";
      }

      if (label === "meet the candidates") {
        a.textContent = "Compare Candidates";
        a.href = "meet.html";
      }

      if (label === "find my precinct") {
        if (page === "index.html") {
          a.textContent = "Find My Ballot";
          a.href = "ballot.html";
        } else {
          a.textContent = "Precinct & Turnout";
          a.href = "lookup.html";
        }
      }

      if (
        label === "see who's on my ballot" ||
        label === "see who’s on my ballot" ||
        label.includes("who's on my ballot") ||
        label.includes("who’s on my ballot")
      ) {
        a.textContent = "Find My Ballot";
        a.href = "ballot.html";
      }
    });
  }

  function insertBanner() {
    if (!["running.html", "meet.html", "lookup.html"].includes(page)) return;

    if (document.querySelector(".riep-phase1-banner")) return;

    const banner = document.createElement("div");
    banner.className = "riep-phase1-banner";

    banner.innerHTML = `
      <div>
        <strong>Looking for the fastest path?</strong><br>
        <span>
          Enter your address once to see both your House and Senate races together.
        </span>
      </div>

      <a href="ballot.html">
        Find My Ballot →
      </a>
    `;

    const main = document.querySelector("main");

    if (main) {
      main.insertBefore(banner, main.firstChild);
    } else {
      document.body.insertBefore(banner, document.body.firstChild);
    }
  }

  function simplifyHome() {
    if (page !== "index.html") return;

    document.querySelectorAll("a").forEach(a => {
      const label = normalize(a.textContent);

      if (label === "find my ballot") {
        a.href = "ballot.html";
        a.setAttribute(
          "aria-label",
          "Find my Rhode Island ballot by address"
        );
      }

      if (label === "compare candidates") {
        a.title =
          "Compare candidate priorities after selecting a race";
      }

      if (label === "all races") {
        a.title =
          "Browse every State House and State Senate race";
      }
    });
  }

  addStyles();
  relabelLinks();
  insertBanner();
  simplifyHome();
})();
