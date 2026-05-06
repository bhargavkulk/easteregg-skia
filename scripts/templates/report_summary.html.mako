<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>${title}</title>
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
      max-width: 960px;
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
    .backend-links {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
    }
    .backend-link {
      display: inline-block;
      padding: 8px 12px;
      border: 1px solid #c8c8c8;
      background: #f7f7f7;
      color: #0b57d0;
      text-decoration: none;
    }
    .backend-link:hover {
      background: #efefef;
      text-decoration: underline;
    }
    .table-wrap {
      width: 100%;
      overflow-x: auto;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      background: white;
      font-size: 14px;
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
    td.num {
      text-align: right;
      white-space: nowrap;
      font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, monospace;
    }
  </style>
</head>
<body>
  <main>
    <h1>${title}</h1>

    <section>
      <h2>Backend Reports</h2>
      <div class="backend-links">
      % for backend in backends:
        <a class="backend-link" href="${backend['path']}">${backend['label']}</a>
      % endfor
      </div>
    </section>

    <section>
      <h2>Stats</h2>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Metric</th>
              % for backend in backends:
              <th>${backend['label']}</th>
              % endfor
            </tr>
          </thead>
          <tbody>
          % for row in stats:
            <tr>
              <th>${row['label']}</th>
              % for backend in backends:
              <td class="num">${row['values'][backend['label']]}</td>
              % endfor
            </tr>
          % endfor
          </tbody>
        </table>
      </div>
    </section>
  </main>
</body>
</html>
