import { useEffect, useState } from "react";
import {
  addKey,
  authCheck,
  clearAdminPassword,
  fetchProvider,
  fetchStats,
  getAdminPassword,
  removeKey,
  replaceKeys,
  resetKey,
  setAdminPassword,
  testKeys,
  updateProvider,
} from "../admin";

const STATE_COLORS = {
  active: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30",
  rate_limited: "bg-amber-500/20 text-amber-400 border-amber-500/30",
  quota_exceeded: "bg-orange-500/20 text-orange-400 border-orange-500/30",
  invalid: "bg-red-500/20 text-red-400 border-red-500/30",
};

const STATE_LABELS = {
  active: "Sẵn sàng",
  rate_limited: "Rate limit",
  quota_exceeded: "Hết quota",
  invalid: "Không hợp lệ",
};

export default function AdminKeysTab() {
  const [authed, setAuthed] = useState(false);
  const [pw, setPw] = useState("");
  const [stats, setStats] = useState(null);
  const [provider, setProvider] = useState(null);
  const [selectedModel, setSelectedModel] = useState("");
  const [err, setErr] = useState("");
  const [notice, setNotice] = useState("");
  const [bulkText, setBulkText] = useState("");
  const [testing, setTesting] = useState(false);
  const [testResults, setTestResults] = useState(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    const stored = getAdminPassword();
    if (!stored) return;
    authCheck()
      .then(() => setAuthed(true))
      .catch(() => clearAdminPassword());
  }, []);

  useEffect(() => {
    if (!authed) return;

    const handleError = (error) => {
      if (error.response?.status === 401) {
        clearAdminPassword();
        setAuthed(false);
      } else {
        setErr(error.response?.data?.detail || error.message);
      }
    };
    const loadStats = () => fetchStats().then(setStats).catch(handleError);

    loadStats();
    fetchProvider()
      .then((data) => {
        setProvider(data);
        setSelectedModel(data.model);
      })
      .catch(handleError);

    const timer = setInterval(loadStats, 5000);
    return () => clearInterval(timer);
  }, [authed]);

  const parseBulk = () =>
    bulkText.split(/[\n,]+/).map((v) => v.trim()).filter(Boolean);

  const handleLogin = async (e) => {
    e.preventDefault();
    setErr("");
    setAdminPassword(pw);
    try {
      await authCheck();
      setAuthed(true);
    } catch (error) {
      clearAdminPassword();
      setErr(error.response?.data?.detail || "Sai mật khẩu.");
    }
  };

  const handleModelSave = async () => {
    setSaving(true); setErr(""); setNotice("");
    try {
      const data = await updateProvider(selectedModel);
      setProvider(data);
      setNotice(`Đã chuyển model OCR sang ${data.model}.`);
    } catch (error) {
      setErr(error.response?.data?.detail || error.message);
    } finally { setSaving(false); }
  };

  const handleTest = async () => {
    const keys = parseBulk();
    if (!keys.length) { setErr("Hãy nhập ít nhất một API key."); return; }
    setTesting(true); setErr(""); setTestResults(null);
    try { setTestResults(await testKeys(keys)); }
    catch (error) { setErr(error.response?.data?.detail || error.message); }
    finally { setTesting(false); }
  };

  const handleSaveAll = async () => {
    const keys = parseBulk();
    if (!keys.length) { setErr("Cần ít nhất một API key."); return; }
    if (!confirm(`Thay toàn bộ pool bằng ${keys.length} key này?`)) return;
    setSaving(true); setErr("");
    try {
      await replaceKeys(keys);
      setBulkText(""); setTestResults(null);
      setStats(await fetchStats());
    } catch (error) { setErr(error.response?.data?.detail || error.message); }
    finally { setSaving(false); }
  };

  const handleAdd = async () => {
    const keys = parseBulk();
    if (keys.length !== 1) { setErr("Để thêm một key, ô nhập chỉ được chứa đúng một key."); return; }
    setSaving(true); setErr("");
    try {
      await addKey(keys[0]);
      setBulkText(""); setStats(await fetchStats());
    } catch (error) { setErr(error.response?.data?.detail || error.message); }
    finally { setSaving(false); }
  };

  const handleRemove = async (index) => {
    if (!confirm(`Xóa key #${index + 1}?`)) return;
    try { await removeKey(index); setStats(await fetchStats()); }
    catch (error) { setErr(error.response?.data?.detail || error.message); }
  };

  const handleReset = async (index) => {
    try { await resetKey(index); setStats(await fetchStats()); }
    catch (error) { setErr(error.response?.data?.detail || error.message); }
  };

  if (!authed) {
    return (
      <form onSubmit={handleLogin} className="mx-auto max-w-sm space-y-4">
        <div className="text-center mb-6">
          <div className="inline-flex h-14 w-14 items-center justify-center rounded-2xl bg-indigo-500/15 text-indigo-400 mb-3">
            <svg className="w-7 h-7" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8}
                d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
            </svg>
          </div>
          <h2 className="text-lg font-bold text-slate-200">Đăng nhập quản trị</h2>
          <p className="text-sm text-slate-500 mt-1">
            Nhập mật khẩu <code className="text-slate-400 bg-slate-800 px-1 rounded">ADMIN_PASSWORD</code>
          </p>
        </div>

        <input
          type="password"
          value={pw}
          onChange={(e) => setPw(e.target.value)}
          placeholder="Mật khẩu admin"
          className="w-full rounded-xl border border-slate-700 bg-slate-800 px-4 py-3 text-slate-200
            placeholder-slate-600 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500/50"
          autoFocus
        />
        <button className="w-full rounded-xl bg-indigo-600 py-2.5 text-sm font-semibold text-white hover:bg-indigo-500 shadow-lg shadow-indigo-600/25">
          Đăng nhập
        </button>
        {err && (
          <p className="text-sm text-red-400 text-center">{err}</p>
        )}
      </form>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-base font-bold text-slate-200">Kết nối 9router</h2>
          <p className="text-sm text-slate-500">API tương thích OpenAI Chat Completions</p>
        </div>
        <button
          onClick={() => { clearAdminPassword(); setAuthed(false); }}
          className="flex items-center gap-1.5 text-sm text-slate-400 hover:text-slate-200 rounded-lg border border-slate-700 px-3 py-1.5"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
          </svg>
          Đăng xuất
        </button>
      </div>

      {err && <StatusMsg color="red">{err}</StatusMsg>}
      {notice && <StatusMsg color="emerald">{notice}</StatusMsg>}

      {/* Provider config */}
      {provider && (
        <div className="space-y-4 rounded-xl border border-sky-500/20 bg-sky-500/10 p-4">
          <div>
            <div className="text-xs font-semibold uppercase tracking-wider text-sky-400 mb-1">HTTP endpoint</div>
            <code className="text-sm text-sky-300 font-mono">{provider.base_url}/chat/completions</code>
          </div>
          <div className="flex flex-wrap items-end gap-3">
            <label className="flex-1 min-w-52 text-sm font-medium text-slate-300">
              Model OCR
              <select
                value={selectedModel}
                onChange={(e) => setSelectedModel(e.target.value)}
                className="mt-1.5 w-full rounded-xl border border-slate-600 bg-slate-800 px-3 py-2 text-slate-200 focus:border-indigo-500 focus:outline-none"
              >
                {provider.models.map((model) => (
                  <option key={model.id} value={model.id}>
                    {model.name} ({model.id})
                  </option>
                ))}
              </select>
            </label>
            <button
              onClick={handleModelSave}
              disabled={saving || selectedModel === provider.model}
              className="rounded-xl bg-sky-600 px-4 py-2 text-sm font-semibold text-white hover:bg-sky-500 disabled:opacity-50"
            >
              Lưu model
            </button>
          </div>
        </div>
      )}

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
          <StatCard label="Tổng key" value={stats.total} />
          <StatCard label="Sẵn sàng" value={stats.active} color="text-emerald-400" />
          <StatCard label="Rate limit" value={stats.rate_limited} color="text-amber-400" />
          <StatCard label="Hết quota" value={stats.quota_exceeded} color="text-orange-400" />
          <StatCard label="Không hợp lệ" value={stats.invalid} color="text-red-400" />
        </div>
      )}

      {/* Key manager */}
      <div className="space-y-4 rounded-xl border border-slate-700 bg-slate-800/60 p-4">
        <div>
          <h3 className="font-semibold text-slate-200">9router API Keys</h3>
          <p className="text-sm text-slate-500 mt-0.5">
            Mỗi key một dòng. Biến môi trường: <code className="text-slate-400 bg-slate-800 px-1 rounded text-xs">NINEROUTER_API_KEY</code>
          </p>
        </div>
        <textarea
          value={bulkText}
          onChange={(e) => setBulkText(e.target.value)}
          placeholder={"sk-9router-key-1\nsk-9router-key-2"}
          rows={6}
          className="w-full rounded-xl border border-slate-700 bg-slate-900 p-3 font-mono text-xs text-slate-300
            placeholder-slate-600 focus:border-indigo-500 focus:outline-none resize-none"
        />
        <div className="flex flex-wrap gap-2">
          <button
            onClick={handleTest}
            disabled={testing}
            className="flex items-center gap-2 rounded-xl bg-slate-700 px-4 py-2 text-sm font-semibold text-slate-200 hover:bg-slate-600 disabled:opacity-50"
          >
            {testing && <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-slate-400 border-t-transparent" />}
            {testing ? "Đang kiểm tra..." : "Kiểm tra key"}
          </button>
          <button
            onClick={handleSaveAll}
            disabled={saving}
            className="rounded-xl bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-500 disabled:opacity-50"
          >
            Thay toàn bộ pool
          </button>
          <button
            onClick={handleAdd}
            disabled={saving}
            className="rounded-xl bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-500 disabled:opacity-50"
          >
            Thêm một key
          </button>
        </div>

        {testResults && (
          <div className="rounded-xl border border-slate-700 bg-slate-900 p-3 space-y-2">
            <p className="text-sm font-semibold text-slate-200">
              {testResults.ok}/{testResults.total} key hoạt động
            </p>
            {testResults.results.map((result, index) => (
              <div key={index} className={`text-xs font-mono ${result.ok ? "text-emerald-400" : "text-red-400"}`}>
                <code>{result.preview}</code>: {result.message}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Keys table */}
      {stats?.keys?.length > 0 ? (
        <div className="overflow-x-auto rounded-xl border border-slate-700">
          <table className="min-w-full text-sm bg-slate-800/60">
            <thead>
              <tr className="border-b border-slate-700 bg-slate-800">
                {["#", "Key", "Trạng thái", "Dùng", "OK", "Lỗi", "Cooldown", ""].map((label) => (
                  <th key={label} className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-400">
                    {label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700/50">
              {stats.keys.map((key) => (
                <tr key={key.index} className="hover:bg-slate-800/50">
                  <td className="px-4 py-3 text-slate-400">{key.index + 1}</td>
                  <td className="px-4 py-3 font-mono text-xs text-slate-300">{key.preview}</td>
                  <td className="px-4 py-3">
                    <span className={`rounded-lg border px-2 py-0.5 text-xs font-medium ${STATE_COLORS[key.state]}`} title={key.last_error}>
                      {STATE_LABELS[key.state]}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-slate-300">{key.used}</td>
                  <td className="px-4 py-3 text-emerald-400">{key.success}</td>
                  <td className="px-4 py-3 text-red-400">{key.errors}</td>
                  <td className="px-4 py-3 text-slate-400">
                    {key.cooldown_remaining > 0 ? `${key.cooldown_remaining.toFixed(0)}s` : "—"}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex gap-3">
                      <button onClick={() => handleReset(key.index)} className="text-xs text-indigo-400 hover:text-indigo-300 font-medium">
                        Reset
                      </button>
                      <button onClick={() => handleRemove(key.index)} className="text-xs text-red-400 hover:text-red-300 font-medium">
                        Xóa
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        stats && <StatusMsg color="amber">Pool đang trống. Hãy thêm API key để OCR hoạt động.</StatusMsg>
      )}

      <p className="text-xs text-slate-600">
        Keys: <code>/app/data/keys.json</code> · Model: <code>/app/data/provider.json</code>
      </p>
    </div>
  );
}

function StatusMsg({ color, children }) {
  const styles = {
    red: "border-red-500/20 bg-red-500/10 text-red-300",
    emerald: "border-emerald-500/20 bg-emerald-500/10 text-emerald-300",
    amber: "border-amber-500/20 bg-amber-500/10 text-amber-300",
  };
  return <div className={`rounded-xl border p-3 text-sm ${styles[color]}`}>{children}</div>;
}

function StatCard({ label, value, color = "text-slate-200" }) {
  return (
    <div className="rounded-xl border border-slate-700 bg-slate-800 p-3">
      <div className="text-[10px] uppercase tracking-wider text-slate-500 font-semibold">{label}</div>
      <div className={`text-2xl font-bold mt-1 ${color}`}>{value}</div>
    </div>
  );
}
