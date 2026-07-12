<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>${title}</title>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/tofsjonas/sortable@4.1.7/sortable-base.min.css" />
  <script src="https://cdn.jsdelivr.net/gh/tofsjonas/sortable@4.1.7/dist/sortable.auto.min.js" defer></script>
  <style>
    * {
      box-sizing: border-box;
    }
    body {
      margin: 0;
      padding: 16px;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: #f5f5f5;
      color: #1f1f1f;
    }
    main {
      max-width: 1200px;
      margin: 0 auto;
    }
    h1, h2 {
      margin: 0 0 8px;
    }
    section {
      background: white;
      border: 1px solid #d7d7d7;
      padding: 10px 12px;
      margin-bottom: 12px;
    }
    .table-wrap {
      width: 100%;
      overflow-x: auto;
    }
    table {
      border-collapse: collapse;
      font-size: 14px;
      background: white;
    }
    .stats-table {
      width: auto;
      min-width: 320px;
    }
    .stats-table th {
      min-width: 240px;
    }
    .stats-table td.num {
      min-width: 120px;
    }
    .results-table {
      width: 100%;
    }
    .results-note {
      margin: 0 0 10px;
      color: #555;
      font-size: 13px;
    }
    .latex-macros {
      width: 100%;
      min-height: 260px;
      margin-top: 10px;
      padding: 8px;
      font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, monospace;
      font-size: 12px;
      white-space: pre;
    }
    th, td {
      border: 1px solid #e3e3e3;
      padding: 6px 8px;
      text-align: left;
      vertical-align: middle;
    }
    th {
      background: #f0f0f0;
      white-space: nowrap;
    }
    .sortable th {
      cursor: pointer;
      user-select: none;
    }
    .sortable th.no-sort {
      cursor: default;
    }
    td.num {
      text-align: right;
      white-space: nowrap;
      font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, monospace;
    }
    td.speedup-up {
      color: #1a7f37;
      font-weight: 600;
    }
    td.speedup-down {
      color: #c62828;
      font-weight: 600;
    }
    td.name {
      min-width: 180px;
    }
    td.pass-counts {
      min-width: 180px;
    }
    td.links {
      white-space: nowrap;
    }
    .mono {
      font-size: 11px;
      font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, monospace;
    }
    .links a {
      margin-right: 8px;
      color: #0b57d0;
      text-decoration: none;
    }
    .links a:hover {
      text-decoration: underline;
    }
    .plot {
      max-width: 520px;
    }
    .plots {
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
    }
    .plot img {
      display: block;
      width: 100%;
      height: auto;
      border: 1px solid #e3e3e3;
    }
    .plot-actions {
      margin-top: 6px;
    }
    .button {
      display: inline-block;
      padding: 4px 8px;
      border: 1px solid #c8c8c8;
      background: #f7f7f7;
      color: #1f1f1f;
      font-size: 12px;
      text-decoration: none;
    }
    .button:hover {
      background: #efefef;
    }
  </style>
</head>
<body>
  <main>
    <h1>${title}</h1>

    <section>
      <h2>Stats</h2>
      <table class="stats-table">
        <tbody>
        % for stat in stats:
          <tr>
            <th>${stat['label']}</th>
            <td class="num">${stat['value']}</td>
          </tr>
        % endfor
        </tbody>
      </table>
    </section>

    <section>
      <details>
        <summary>LaTeX Macros</summary>
        <textarea class="latex-macros" readonly spellcheck="false">${latex_macros}</textarea>
      </details>
    </section>

    <section>
      <div class="plots">
        <div class="plot">
          <img src="${speedup_cdf_path}" alt="Empirical CDF of render speedup" />
          <div class="plot-actions">
            <a class="button" href="${speedup_cdf_svg_path}" download>Download SVG</a>
          </div>
        </div>
        <div class="plot">
          <img src="${total_speedup_cdf_path}" alt="Empirical CDF of total speedup" />
          <div class="plot-actions">
            <a class="button" href="${total_speedup_cdf_svg_path}" download>Download SVG</a>
          </div>
        </div>
        <div class="plot">
          <img src="${runtime_scatter_path}" alt="Command count versus optimization time scatterplot" />
          <div class="plot-actions">
            <a class="button" href="${runtime_scatter_svg_path}" download>Download SVG</a>
          </div>
        </div>
        <div class="plot">
          <img src="${speedup_forest_path}" alt="Per-benchmark speedup confidence intervals" />
          <div class="plot-actions">
            <a class="button" href="${speedup_forest_svg_path}" download>Download SVG</a>
          </div>
        </div>
      </div>
    </section>

    <section>
      <h2>Results</h2>
      <p class="results-note">
        Baseline, Optimized, and Speedup are repeated-run point estimates from <code>report.json</code>:
        median of per-run geomeans for runtimes, and median of per-run speedups for the ratio.
        Speedup CI is a 95% bootstrap confidence interval over the per-run speedups.
      </p>
      <div class="table-wrap">
        <table class="results-table sortable">
          <thead>
            <tr>
              <th>Name</th>
              <th>#cmds</th>
              <th>Runs</th>
              <th>Opt Time</th>
              <th>Baseline Median</th>
              <th>Optimized Median</th>
              <th>Pixel Diff</th>
              <th>Speedup Median</th>
              <th>Speedup 95% CI</th>
              <th>Pass Counts</th>
              <th class="no-sort">Images</th>
            </tr>
          </thead>
          <tbody>
          % for row in results:
            <tr>
              <td class="name">${row['display_name']}</td>
              <td class="num">${row['num_cmds']}</td>
              <td class="num">${row['nanobench_run_count_display']}</td>
              <td class="num">${row['opt_time_display']}</td>
              <td class="num" title="${row['bl_rt_title']}">${row['bl_rt_display']}</td>
              <td class="num" title="${row['ee_rt_title']}">${row['ee_rt_display']}</td>
              <td class="num">${row['pixel_diff_display']}</td>
              <td class="num ${row['speedup_class']}" title="${row['speedup_title']}">${row['speedup_display']}</td>
              <td class="num" title="${row['speedup_ci_title']}">${row['speedup_ci_display']}</td>
              <td class="pass-counts mono">${row['pass_counts_display']}</td>
              <td class="links">
                <a href="png/${row['name']}.png">baseline</a>
                <a href="png/${row['name']}__ee.png">optimized</a>
                <a href="png/${row['name']}__diff.png">diff</a>
              </td>
            </tr>
          % endfor
          </tbody>
        </table>
      </div>
    </section>
  </main>
</body>
</html>
