const API_BASE_URL = "https://api.example.com";
const DEFAULT_HEADERS = { accept: "application/json" };

export function summarize(items) {
  const names = items.map((item) => item.name);
  return names;
}
