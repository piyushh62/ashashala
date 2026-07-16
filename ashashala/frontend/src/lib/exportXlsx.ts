import * as XLSX from "xlsx";

/**
 * Export an array of plain row objects to a downloaded .xlsx file. Column order
 * follows the keys of the first row (or an explicit `headers` map for nicer
 * labels). Kept UI-agnostic so any Admin/Teacher/School screen can reuse it.
 */
export function exportRowsToXlsx<T extends Record<string, unknown>>(
  rows: T[],
  options: {
    filename: string;
    sheetName?: string;
    /** Optional ordered map of row key -> column header label. */
    headers?: Partial<Record<keyof T, string>>;
  },
): void {
  const { filename, sheetName = "Sheet1", headers } = options;

  const keys = headers
    ? (Object.keys(headers) as (keyof T)[])
    : rows.length
      ? (Object.keys(rows[0]) as (keyof T)[])
      : [];

  const aoa: unknown[][] = [
    keys.map((k) => (headers?.[k] ?? String(k)) as string),
    ...rows.map((row) => keys.map((k) => row[k] ?? "")),
  ];

  const worksheet = XLSX.utils.aoa_to_sheet(aoa);
  const workbook = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(workbook, worksheet, sheetName);

  const name = filename.endsWith(".xlsx") ? filename : `${filename}.xlsx`;
  XLSX.writeFile(workbook, name);
}
