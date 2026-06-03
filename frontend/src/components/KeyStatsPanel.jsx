import { useEffect, useState } from "react";
import axios from "axios";

const STATE_COLORS = {
  active: "bg-emerald-100 text-emerald-800 border-emerald-300",
  rate_limited: "bg-amber-100 text-amber-800 border-amber-300",
  quota_exceeded: "bg-orange-100 text-orange-800 border-orange-300",
  invalid: "bg-red-100 text-red-800 border-red-300",
};

const STATE_LABELS = {
  active: "Sẵn sàng",
  rate_limited: "Đang cooldown phút",
  quota_exceeded: "Hết quota ngày",
  invalid: "Key không hợp lệ",
};

export default function KeyStatsPanel() {
  const [stats, setStats] = useState(null);
  const [err, setErr] = useState("");

  const load = async () => {
    try {
      const { data } = await axios.get("/api/admin/keys/stats");
      setStats(data);
      setErr("");
    } catch (e) {
      setErr(e.response?.data?.detail || e.message);
    }
  };

  useEffect(() => {
    load();
    const t = setInterval(load, 5000);
    return () => clearInterval(t);
  }, []);

  if (err) {
    return (
      <div className="p-3 bg-red-50 border border-red-200 text-red-700 rounded-md text-sm">
        {err}
      </div>
    );
  }
  if (!stats) {
    return <div className="text-slate-500 text-sm">Đang tải trạng thái pool...</div>;
  }

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
        <Stat label="Tổng key" value={stats.total} />
        <Stat label="Sẵn sàng" value={stats.active} color="text-emerald-700" />
        <Stat label="Cooldown phút" value={stats.rate_limited} color="text-amber-700" />
        <Stat label="Hết quota ngày" value={stats.quota_exceeded} color="text-orange-700" />
        <Stat label="Key chết" value={stats.invalid} color="text-red-700" />
      </div>

      <div className="overflow-x-auto">
        <table className="min-w-full text-sm border border-slate-200 rounded">
          <thead className="bg-slate-100">
            <tr>
              <th className="px-3 py-2 text-left">#</th>
              <th className="px-3 py-2 text-left">Key</th>
              <th className="px-3 py-2 text-left">Trạng thái</th>
              <th className="px-3 py-2 text-right">Lượt dùng</th>
              <th className="px-3 py-2 text-right">Thành công</th>
              <th className="px-3 py-2 text-right">Lỗi</th>
              <th className="px-3 py-2 text-right">Cooldown còn (s)</th>
            </tr>
          </thead>
          <tbody>
            {stats.keys.map((k) => (
              <tr key={k.index} className="border-t border-slate-200">
                <td className="px-3 py-2">{k.index + 1}</td>
                <td className="px-3 py-2 font-mono text-xs">{k.preview}</td>
                <td className="px-3 py-2">
                  <span
                    className={`px-2 py-0.5 text-xs rounded border ${STATE_COLORS[k.state]}`}
                    title={k.last_error}
                  >
                    {STATE_LABELS[k.state] || k.state}
                  </span>
                </td>
                <td className="px-3 py-2 text-right">{k.used}</td>
                <td className="px-3 py-2 text-right text-emerald-700">{k.success}</td>
                <td className="px-3 py-2 text-right text-red-700">{k.errors}</td>
                <td className="px-3 py-2 text-right">
                  {k.cooldown_remaining > 0 ? k.cooldown_remaining.toFixed(0) : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <p className="text-xs text-slate-500">Tự refresh mỗi 5 giây.</p>
    </div>
  );
}

function Stat({ label, value, color = "text-slate-900" }) {
  return (
    <div className="bg-white border border-slate-200 rounded p-3">
      <div className="text-xs text-slate-500 uppercase">{label}</div>
      <div className={`text-2xl font-bold ${color}`}>{value}</div>
    </div>
  );
}
