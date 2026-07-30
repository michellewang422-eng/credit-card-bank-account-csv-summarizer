// Lightweight CSV line splitter for preview purposes only (headers + row count).
// Handles quoted fields, escaped quotes ("") and commas inside quotes.
// Bank-specific parsing/categorization stays in the Python engine, not here.
function parseCsvLine(line) {
  const fields = []
  let current = ''
  let inQuotes = false

  for (let i = 0; i < line.length; i++) {
    const char = line[i]
    if (inQuotes) {
      if (char === '"') {
        if (line[i + 1] === '"') {
          current += '"'
          i++
        } else {
          inQuotes = false
        }
      } else {
        current += char
      }
    } else if (char === '"') {
      inQuotes = true
    } else if (char === ',') {
      fields.push(current)
      current = ''
    } else {
      current += char
    }
  }
  fields.push(current)
  return fields
}

function summarizeCsvText(fileName, text) {
  const lines = text.split(/\r\n|\n/).filter(line => line.length > 0)
  const [headerLine = '', ...dataLines] = lines
  return {
    fileName,
    headers: headerLine ? parseCsvLine(headerLine) : [],
    rowCount: dataLines.length,
  }
}

export function readCsvFile(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(summarizeCsvText(file.name, reader.result))
    reader.onerror = () => reject(reader.error)
    reader.readAsText(file)
  })
}
