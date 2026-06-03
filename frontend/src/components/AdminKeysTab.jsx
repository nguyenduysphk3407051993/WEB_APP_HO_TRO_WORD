import { useEffect, useState } from "react";
import {
  addKey,
  authCheck,
  clearAdminPassword,
  fetchStats,
  getAdminPassword,
  removeKey,
  replaceKeys,
  resetKey,
  setAdminPassword,
  testKeys,
} from "../admin";

const STATE_COLORS = {
  active: "bg-emerald-100 text-emerald-800 border-emerald-300",
  rate_limited: "bg-amber-100 text-amber-800 border-amber-300",
  quota_exceeded: "bg-orange-100 text-orange-800 border-orange-300",
  invalid: "bg-red-100 text-red-800 border-red-300",
};

const STATE_LABELS = {
  active: "Sẵn sàng",
  rate_limited: "Cooldown phút",
  quota_exceeded: "Hết quota ngày",
  invalid: "Key không hợp lệ",
};

export default function AdminKeysTab() {
  const [authed, setAuthed] = useState(false);
  const [pw, setPw] = useState("");
  const [stats, setStats] = useState(null);
  const [err, setErr] = useState("");
  const [bulkText, setBulkText] = useState("");
  const [testing, setTesting] = useState(false);
  const [testResults, setTestResults] = useState(null);
  const [saving, setSaving] = useState(false);

  // Auto auth nếu sessionStorage còn password
  useEffect(() => {
    const stored = getAdminPassword();
    if (stored) {
      authCheck()
        .then(() => setAuthed(true))
        .catch(() => clearAdminPassword());
    }
  }, []);

  // Refresh stats định kỳ khi đã auth
  useEffect(() => {
    if (!authed) return;
    const load = () =>
      fetchStats()
        .then(setStats)
        .catch((e) => {
          if (e.response?.status === 401) {
            clearAdminPassword();
            setAuthed(false);
          } else {
            setErr(e.response?.data?.detail || e.message);
          }
        });
    load();
    const t = setInterval(load, 5000);
    return () => clearInterval(t);
  }, [authed]);

  const handleLogin = async (e) => {
    e?.preventDefault();
    setErr("");
    setAdminPassword(pw);
    try {
      await authCheck();
      setAuthed(true);
    } catch (e) {
      clearAdminPassword();
      setErr(e.response?.data?.detail || "Sai mật khẩu.");
    }
  };

  const handleLogout = () => {
    clearAdminPassword();
    setAuthed(false);
    setPw("");
    setStats(null);
  };

  const parseBulk = () =>
    bulkText
      .split(/[\n,]+/)
      .map((s) => s.trim())
      .filter(Boolean);

  const handleTest = async () => {
    setErr("");
    setTestResults(null);
    const keys = parseBulk();
    if (!keys.length) {
      setErr("Hãy paste ít nhất 1 key vào ô bên trên.");
      return;
    }
    setTesting(true);
    try {
      const res = await testKeys(keys);
      setTestResults(res);
    } catch (e) {
      setErr(e.response?.data?.detail || e.message);
    } finally {
      setTesting(false);
    }
  };

  const handleSaveAll = async () => {
    setErr("");
    const keys = parseBulk();
    if (!keys.length) {
      setErr("Cần ít nhất 1 key.");
      return;
    }
    if (!confirm(`Thay toàn bộ pool bằng ${keys.length} key này? (Pool cũ sẽ bị xoá)`)) return;
    setSaving(true);
    try {
      await replaceKeys(keys);
      setBulkText("");
      setTestResults(null);
    } catch (e) {
      setErr(e.response?.data?.detail || e.message);
    } finally {
      setSaving(false);
    }
  };

  const handleAdd = async () => {
    setErr("");
    const keys = parseBulk();
    if (keys.length !== 1) {
      setErr("Để thêm 1 key, ô textarea chỉ chứa 1 key.");
      return;
    }
    setSaving(true);
    try {
      await addKey(keys[0]);
      setBulkText("");
    } catch (e) {
      setErr(e.response?.data?.detail || e.message);
    } finally {
      setSaving(false);
    }
  };

  const handleRemove = async (index) => {
    if (!confirm(`Xoá key #${index + 1}?`)) return;
    try {
      await removeKey(index);
    } catch (e) {
      setErr(e.response?.data?.detail || e.message);
    }
  };

  const handleResetKey = async (index) => {
    try {
      await resetKey(index);
    } catch (e) {
      setErr(e.response?.data?.detail || e.message);
    }
  };

  if (!authed) {
    return (
      <form onSubmit={handleLogin} className="max-w-md mx-auto space-y-4">
        <h2 className="text-lg font-semibold">Mật khẩu Admin</h2>
        <p className="text-sm text-slate-600">
          Cần mật khẩu để xem/sửa danh sách API keys. Mật khẩu này đặt qua biến môi
          trường <code className="bg-slate-100 px-1 rounded">ADMIN_PASSWORD</code> trong file <code>.env</code>.
        </p>
        <input
          type="password"
          value={pw}
          onChange={(e) => setPw(e.target.value)}
          placeholder="Mật khẩu admin"
          className="w-full border border-slate-300 rounded px-3 py-2"
          autoFocus
        />
        <button
          type="submit"
          className="w-full bg-indigo-600 text-white py-2 rounded hover:bg-indigo-700"
        >
          Đăng nhập
        </button>
        {err && <p className="text-red-600 text-sm">{err}</p>}
      </form>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-lg font-semibold">Quản lý Gemini API Keys</h2>
        <button onClick={handleLogout} className="text-sm text-slate-600 hover:text-slate-900 underline">
          Đăng xuất
        </button>
      </div>

      {err && (
        <div className="p-3 bg-red-50 border border-red-200 text-red-700 rounded-md text-sm">
          {err}
        </div>
      )}

      {/* Stats summary */}
      {stats && (
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
          <Stat label="Tổng key" value={stats.total} />
          <Stat label="Sẵn sàng" value={stats.active} color="text-emerald-700" />
          <Stat label="Cooldown phút" value={stats.rate_limited} color="text-amber-700" />
          <Stat label="Hết quota ngày" value={stats.quota_exceeded} color="text-orange-700" />
          <Stat label="Key chết" value={stats.invalid} color="text-red-700" />
        </div>
      )}

      {/* Bulk paste */}
      <div className="bg-white border border-slate-200 rounded p-4 space-y-3">
        <h3 className="font-semibold text-slate-800">Paste API keys</h3>
        <p className="text-sm text-slate-600">
          Mỗi key trên 1 dòng, hoặc phân cách bằng dấu phẩy. Hỗ trợ paste nhiều key một lúc.
        </p>
        <textarea
          value={bulkText}
          onChange={(e) => setBulkText(e.target.value)}
          placeholder={"AIzaSy_KEY_1\nAIzaSy_KEY_2\nAIzaSy_KEY_3\n..."}
          rows={8}
          className="w-full p-3 border border-slate-300 rounded font-mono text-xs"
        />
        <div className="flex flex-wrap gap-2">
          <button
            onClick={handleTest}
            disabled={testing}
            className="px-4 py-2 bg-slate-800 text-white rounded hover:bg-slate-700 disabled:opacity-50 text-sm"
          >
            {testing ? "Đang test..." : "Test keys (không lưu)"}
          </button>
          <button
            onClick={handleSaveAll}
            disabled={saving}
            className="px-4 py-2 bg-indigo-600 text-white rounded hover:bg-indigo-700 disabled:opacity-50 text-sm"
          >
            {saving ? "Đang lưu..." : "Thay toàn bộ pool"}
          </button>
          <button
            onClick={handleAdd}
            disabled={saving}
            className="px-4 py-2 bg-emerald-600 text-white rounded hover:bg-emerald-700 disabled:opacity-50 text-sm"
          >
            Thêm 1 key vào pool
          </button>
        </div>

        {testResults && (
          <div className="mt-3 space-y-1 text-sm">
            <p>
              Kết quả test: <strong>{testResults.ok}/{testResults.total}</strong> key hoạt động.
            </p>
            <ul className="bg-slate-50 border border-slate-200 rounded p-2 max-h-48 overflow-auto text-xs space-y-1">
              {testResults.results.map((r, i) => (
                <li key={i} className={r.ok ? "text-emerald-700" : "text-red-700"}>
                  {r.ok ? "✓" : "✗"} <span className="font-mono">{r.preview}</span> — {r.message}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {/* Bảng pool */}
      {stats && stats.keys.length > 0 && (
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm border border-slate-200 rounded bg-white">
            <thead className="bg-slate-100">
              <tr>
                <th className="px-3 py-2 text-left">#</th>
                <th className="px-3 py-2 text-left">Key</th>
                <th className="px-3 py-2 text-left">Trạng thái</th>
                <th className="px-3 py-2 text-right">Dùng</th>
                <th className="px-3 py-2 text-right">OK</th>
                <th className="px-3 py-2 text-right">Lỗi</th>
                <th className="px-3 py-2 text-right">CD (s)</th>
                <th className="px-3 py-2 text-center">Hành động</th>
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
                      {STATE_LABELS[k.state]}
                    </span>
                  </td>
                  <td className="px-3 py-2 text-right">{k.used}</td>
                  <td className="px-3 py-2 text-right text-emerald-700">{k.success}</td>
                  <td className="px-3 py-2 text-right text-red-700">{k.errors}</td>
                  <td className="px-3 py-2 text-right">
                    {k.cooldown_remaining > 0 ? k.cooldown_remaining.toFixed(0) : "—"}
                  </td>
                  <td className="px-3 py-2 text-center space-x-2">
                    <button
                      onClick={() => handleResetKey(k.index)}
                      className="text-xs text-indigo-600 hover:underline"
                      title="Đưa về trạng thái active"
                    >
                      Reset
                    </button>
                    <button
                      onClick={() => handleRemove(k.index)}
                      className="text-xs text-red-600 hover:underline"
                    >
                      Xoá
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {stats && stats.keys.length === 0 && (
        <p className="text-amber-700 bg-amber-50 border border-amber-200 p-3 rounded text-sm">
          Pool trống — paste keys vào ô trên và bấm "Thay toàn bộ pool" để bắt đầu.
        </p>
      )}

      <p className="text-xs text-slate-500">Stats refresh mỗi 5 giây. Keys lưu vào /app/data/keys.json (mount volume).</p>
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
