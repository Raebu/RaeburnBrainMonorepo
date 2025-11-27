// client/nextjs-frontend/components/ResultsTable.js
import React from 'react';

/**
 * A table component to display scraped data results.
 *
 * @param {Object} props
 * @param {Array<Object>} props.data - An array of objects representing the scraped data.
 *                                  Each object should have consistent keys (e.g., name, title, company).
 * @param {Array<string>} props.columns - An array of column names/keys to display.
 *                                      Order determines column order.
 *                                      E.g., ['name', 'title', 'company']
 * @param {Object} props.columnLabels - An optional object mapping column keys to user-friendly labels.
 *                                    E.g., { name: 'Full Name', title: 'Job Title' }
 *                                    If not provided, the key itself is used as the header.
 */
export default function ResultsTable({ data = [], columns = [], columnLabels = {} }) {
  // Don't render the table if there's no data or columns
  if (!data.length || !columns.length) {
    return (
      <div className="card p-8 text-center text-muted">
        <p>No data available to display.</p>
        {data.length === 0 && columns.length > 0 && <p>It seems the scraping job hasn't returned any results yet.</p>}
        {columns.length === 0 && data.length > 0 && <p>Column configuration is missing.</p>}
      </div>
    );
  }

  return (
    <div className="card overflow-hidden"> {/* Use card class for styling and overflow-hidden for clean borders */}
      <div className="overflow-x-auto"> {/* Allow horizontal scrolling on small screens */}
        <table className="min-w-full divide-y divide-color-border"> {/* Use full width and border between rows */}
          <thead className="bg-muted"> {/* Use muted background for header */}
            <tr>
              {columns.map((columnKey) => (
                <th
                  key={columnKey}
                  scope="col"
                  className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-muted-foreground" // Style header cells
                >
                  {/* Use provided label or fallback to the key */}
                  {columnLabels[columnKey] || columnKey}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="bg-secondary divide-y divide-color-border"> {/* Body background and row dividers */}
            {data.map((row, rowIndex) => (
              <tr key={rowIndex} className={rowIndex % 2 === 0 ? 'bg-secondary' : 'bg-muted'}> {/* Zebra striping */}
                {columns.map((columnKey) => (
                  <td
                    key={`${rowIndex}-${columnKey}`} // Unique key for each cell
                    className="px-6 py-4 whitespace-nowrap text-sm text-primary max-w-xs truncate" // Style data cells, truncate long text
                  >
                    {/* Display the cell data or a placeholder if null/undefined */}
                    {row[columnKey] ?? '-'}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
