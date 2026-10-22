const inr = new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 });
const num = new Intl.NumberFormat("en-IN", { maximumFractionDigits: 1 });

export const formatINR = (v) => inr.format(v ?? 0);
export const formatNum = (v, digits = 1) =>
  new Intl.NumberFormat("en-IN", { maximumFractionDigits: digits }).format(v ?? 0);
export const formatKwh = (v) => `${num.format(v ?? 0)} kWh`;
export const formatPct = (v) => `${Math.round((v ?? 0) * 100)}%`;
export const formatDateShort = (iso) =>
  new Date(iso).toLocaleDateString("en-IN", { day: "numeric", month: "short" });
export const formatDateTime = (iso) =>
  new Date(iso).toLocaleString("en-IN", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
export const todayISO = () => {
  const d = new Date();
  return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
};
