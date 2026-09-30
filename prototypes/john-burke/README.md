# John Burke candidate profile preview

Open [index.html](index.html) in a browser. It is one standalone file, including the portrait supplied for this prototype, so a local web server is not needed.

This is a static design preview. It is not linked from the live site. The race and finance navigation points to the site's general pages until exact candidate routes are wired during integration.

Content comes from the repository's `data/candidate_research_2026_with_endorsements.json`, `data/race_data.json`, `data/candidate_finance_2026.json`, and `data/outside_ratings_2026.json`. The user supplied the portrait, phone, and legislative email. Finance figures reflect Q2 2026, and outside ratings retain their original reporting periods and attributions. The endorsements, primary/precinct history, bill-level record, and social listening areas are explicitly placeholders.

To integrate, move or adapt the HTML and styles into the site's page structure, connect the race and finance links to Burke-specific routes, and replace the static snapshot with verified data loading. The embedded image makes the preview portable; a production version can use a separately optimized asset.
