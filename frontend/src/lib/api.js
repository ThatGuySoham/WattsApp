// Thin fetch wrapper. Every call throws ApiError with a readable message; callers
// must catch and render it (toast / inline error) — never swallow.
const BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL;

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

function readDetail(body) {
  if (!body) return null;
  if (typeof body.detail === "string") return body.detail;
  if (Array.isArray(body.detail)) {
    return body.detail.map((d) => `${(d.loc || []).slice(1).join(".")}: ${d.msg}`).join("; ");
  }
  return null;
}

async function request(path, { method = "GET", body } = {}) {
  if (!BASE_URL) {
    throw new ApiError("NEXT_PUBLIC_API_BASE_URL is not set. Add it to frontend/.env.local.", 0);
  }
  let res;
  try {
    res = await fetch(`${BASE_URL}${path}`, {
      method,
      headers: body ? { "Content-Type": "application/json" } : undefined,
      body: body ? JSON.stringify(body) : undefined,
      cache: "no-store",
    });
  } catch {
    throw new ApiError(`Cannot reach WattsApp API at ${BASE_URL}. Is the backend running?`, 0);
  }
  if (res.status === 204) return null;
  let data = null;
  try {
    data = await res.json();
  } catch {
    // non-JSON body; handled below
  }
  if (!res.ok) {
    throw new ApiError(readDetail(data) || `Request failed (${res.status} ${res.statusText})`, res.status);
  }
  return data;
}

export const api = {
  households: () => request("/households"),
  tariffs: () => request("/tariffs"),
  appliances: (hid) => request(`/households/${hid}/appliances`),
  createAppliance: (hid, data) => request(`/households/${hid}/appliances`, { method: "POST", body: data }),
  deleteAppliance: (aid) => request(`/appliances/${aid}`, { method: "DELETE" }),
  logUsage: (aid, data) => request(`/appliances/${aid}/usage-logs`, { method: "POST", body: data }),
  usageHistory: (hid, days = 30) => request(`/households/${hid}/usage-history?days=${days}`),
  modelReport: (hid) => request(`/households/${hid}/model`),
  train: (hid) => request(`/households/${hid}/train`, { method: "POST" }),
  predict: (body) => request("/predict", { method: "POST", body }),
};
