import { useEffect, useState } from "react";
import {
  addGeminiKey,
  addKey,
  authCheck,
  clearAdminPassword,
  fetchGeminiStats,
  fetchProvider,
  fetchStats,
  getAdminPassword,
  removeGeminiKey,
  removeKey,
  replaceGeminiKeys,
  replaceKeys,
  resetGeminiKey,
  resetKey,
  setAdminPassword,
  testGeminiKeys,
  testKeys,
  updateProvider,
} from "../admin";

const STATE_COLORS = {
  active:         "bg-emerald-500/20 text-emerald-400 border-emerald-500/30",
  rate_limited:   "bg-amber-500/20 text-amber-400 border-amber-500/30",
  quota_exceeded: "bg-orange-500/20 text-orange-400 border-orange-500/30",
  invalid:        "bg-red-500/20 text-red-400 border-red-500/30",
};

const STATE_LABELS = {
  active:         "Sẵn sàng",
  rate_limited:   "Rate limit",
  quota_exceeded: "Hết quota",
  invalid:        "Không hợp lệ",
};

export default function AdminKeysTab() {
  const [authed, setAuthed] = useState(false);
  const [pw, setPw] = useState("");

  const [provider, setProvider] = useState(null);
  const [selectedProvider, setSelectedProvider] = useState("9router");
  const [selectedModel, setSelectedModel] = useState("");

  const [stats, setStats] = useState(null);
  const [bulkText, setBulkText] = useState("");
  const [testing, setTesting] = useState(false);
  const [testResults, setTestResults] = useState(null);

  const [geminiStats, setGeminiStats] = useState(null);
  const [geminiBulkText, setGeminiBulkText] = useState("");
  const [geminiTesting, setGeminiTesting] = useState(false);
  const [geminiTestResults, setGeminiTestResults] = useState(null);

  const [err, setErr] = useState("");
  const [notice, setNotice] = useState("");
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

    const loadAll = () => {
      fetchStats().then(setStats).catch(handleError);
      fetchGeminiStats().then(setGeminiStats).catch(handleError);
    };

    loadAll();
    fetchProvider()
      .then((data) => {
        setProvider(data);
        setSelectedProvider(data.provider || "9router");
        setSelectedModel(data.model);
      })
      .catch(handleError);

    const timer = setInterval(loadAll, 5000);
    return () => clearInterval(timer);
  }, [authed]);

  const handleProviderChange = (newProvider) => {
    setSelectedProvider(newProvider);
    if (provider?.providers) {
      const p = provider.providers.find((x) => x.id === newProvider);
      if (p?.models?.length) setSelectedModel(p.models[0].id);
    }
  };

  const availableModels = provider?.providers?.find((p) => p.id === selectedProvider)?.models || [];

  const parseBulk = (text) =>
    text.split(/[\n,]+/).map((v) => v.trim()).filter(Boolean);

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

  const handleProviderSave = async () => {
    setSaving(true); setErr(""); setNotice("");
    try {
      const data = await updateProvider(selectedProvider, selectedModel);
      setProvider(data);
      setNotice(`Đã chuyển sang ${selectedProvider} / ${selectedModel}.`);
    } catch (error) {
      setErr(error.response?.data?.detail || error.message);
    } finally { setSaving(false); }
  };

  const handleTest = async () => {
    const keys = parseBulk(bulkText);
    if (!keys.length) { setErr("Hãy nhập ít nhất một API key."); return; }
    setTesting(true); setErr(""); setTestResults(null);
    try { setTestResults(await testKeys(keys)); }
    catch (error) { setErr(error.response?.data?.detail || error.message); }
    finally { setTesting(false); }
  };

  const handleSaveAll = async () => {
    const keys = parseBulk(bulkText);
    if (!keys.length) { setErr("Cần ít nhất một API key."); return; }
    if (!confirm(`Thay toàn bộ pool 9router bằng ${keys.length} key này?`)) return;
    setSaving(true); setErr("");
    try {
      await replaceKeys(keys);
      setBulkText(""); setTestResults(null);
      setStats(await fetchStats());
    } catch (error) { setErr(error.response?.data?.detail || error.message); }
    finally { setSaving(false); }
  };

  const handleAdd = async () => {
    const keys = parseBulk(bulkText);
    if (keys.length !== 1) { setErr("Để thêm một key, ô nhập chỉ được chứa đúng một key."); return; }
    setSaving(true); setErr("");
    try {
      await addKey(keys[0]);
      setBulkText(""); setStats(await fetchStats());
    } catch (error) { setErr(error.response?.data?.detail || error.message); }
    finally { setSaving(false); }
  };

  const handleRemove = async (index) => {
    if (!confirm(`Xóa key 9router #${index + 1}?`)) return;
    try { await removeKey(index); setStats(await fetchStats()); }
    catch (error) { setErr(error.response?.data?.detail || error.message); }
  };

  const handleReset = async (index) => {
    try { await resetKey(index); setStats(await fetchStats()); }
    catch (error) { setErr(error.response?.data?.detail || error.message); }
  };

  const handleGeminiTest = async () => {
    const keys = parseBulk(geminiBulkText);
    if (!keys.length) { setErr("Hãy nhập ít nhất một Gemini API key."); return; }
    setGeminiTesting(true); setErr(""); setGeminiTestResults(null);
    try { setGeminiTestResults(await testGeminiKeys(keys)); }
    catch (error) { setErr(error.response?.data?.detail || error.message); }
    finally { setGeminiTesting(false); }
  };

  const handleGeminiSaveAll = async () => {
    const keys = parseBulk(geminiBulkText);
    if (!keys.length) { setErr("Cần ít nhất một Gemini API key."); return; }
    if (!confirm(`Thay toàn bộ Gemini pool bằng ${keys.length} key này?`)) return;
    setSaving(true); setErr("");
    try {
      await replaceGeminiKeys(keys);
      setGeminiBulkText(""); setGeminiTestResults(null);
      setGeminiStats(await fetchGeminiStats());
    } catch (error) { setErr(error.response?.data?.detail || error.message); }
    finally { setSaving(false); }
  };

  const handleGeminiAdd = async () => {
    const keys = parseBulk(geminiBulkText);
    if (keys.length !== 1) { setErr("Để thêm một key, ô nhập chỉ được chứa đúng một key."); return; }
    setSaving(true); setErr("");
    try {
      await addGeminiKey(keys[0]);
      setGeminiBulkText(""); setGeminiStats(await fetchGeminiStats());
    } catch (error) { setErr(error.response?.data?.detail || error.message); }
    finally { setSaving(false); }
  };

  const handleGeminiRemove = async (index) => {
    if (!confirm(`Xóa Gemini key #${index + 1}?`)) return;
    try { await removeGeminiKey(index); setGeminiStats(await fetchGeminiStats()); }
    catch (error) { setErr(error.response?.data?.detail || error.message); }
  };

  const handleGeminiReset = async (index) => {
    try { await resetGeminiKey(index); setGeminiStats(await fetchGeminiStats()); }
    catch (error) { setErr(error.response?.data?.detail || error.message); }
  };

  if (!authed) {
    return (
      <form onSubmit={handleLogin} className="mx-auto max-w-sm space-y-4">
        <div className="text-center mb-6">
          <div className="inline-flex h-14 w-14 items-center justify-center rounded-2xl bg-gold-400/15 text-gold-400 mb-3">
            <svg className="w-7 h-7" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8}
                d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
            </svg>
          </div>
          <h2 className="text-lg font-bold text-[#ece3d7]">Đăng nhập quản trị</h2>
          <p className="text-sm text-gold-700 mt-1">
            Nhập mật khẩu <code className="text-gold-400 bg-[#2f2620] px-1 rounded">ADMIN_PASSWORD</code>
          </p>
        </div>
        <input
          type="password"
          value={pw}
          onChange={(e) => setPw(e.target.value)}
          placeholder="Mật khẩu admin"
          className="w-full rounded-xl border border-[#43372d] bg-[#261e18] px-4 py-3 text-[#ece3d7]
            placeholder-gold-800 focus:border-gold-400 focus:outline-none focus:ring-1 focus:ring-gold-400/30"
          autoFocus
        />
        <button className="w-full rounded-xl bg-gold-500 py-2.5 text-sm font-semibold text-[#17120e] hover:bg-gold-400 shadow-lg shadow-gold-500/25">
          Đăng nhập
        </button>
        {err && <p className="text-sm text-red-400 text-center">{err}</p>}
      </form>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-base font-bold text-[#ece3d7]">Quản lý API Keys</h2>
          <p className="text-sm text-gold-700">9router + Google Gemini</p>
        </div>
        <button
          onClick={() => { clearAdminPassword(); setAuthed(false); }}
          className="flex items-center gap-1.5 text-sm text-gold-600 hover:text-[#ece3d7] rounded-lg border border-[#43372d] px-3 py-1.5"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
          </svg>
          Đăng xuất
        </button>
      </div>

      {err    && <StatusMsg color="red">{err}</StatusMsg>}
      {notice && <StatusMsg color="emerald">{notice}</StatusMsg>}

      {/* Provider config */}
      {provider && (
        <div className="space-y-4 rounded-xl border border-sky-500/20 bg-sky-500/10 p-4">
          <div className="text-xs font-semibold uppercase tracking-wider text-sky-400">
            Model OCR đang dùng
          </div>
          <div className="flex flex-wrap items-end gap-3">
            <label className="flex-1 min-w-40 text-sm font-medium text-[#ece3d7]">
              Provider
              <select
                value={selectedProvider}
                onChange={(e) => handleProviderChange(e.target.value)}
                className="mt-1.5 w-full rounded-xl border border-[#43372d] bg-[#261e18] px-3 py-2 text-[#ece3d7] focus:border-sky-500 focus:outline-none"
              >
                {(provider.providers || []).map((p) => (
                  <option key={p.id} value={p.id}>{p.name}</option>
                ))}
              </select>
            </label>
            <label className="flex-1 min-w-52 text-sm font-medium text-[#ece3d7]">
              Model
              <select
                value={selectedModel}
                onChange={(e) => setSelectedModel(e.target.value)}
                className="mt-1.5 w-full rounded-xl border border-[#43372d] bg-[#261e18] px-3 py-2 text-[#ece3d7] focus:border-sky-500 focus:outline-none"
              >
                {availableModels.map((model) => (
                  <option key={model.id} value={model.id}>
                    {model.name} ({model.id})
                  </option>
                ))}
              </select>
            </label>
            <button
              onClick={handleProviderSave}
              disabled={saving || (selectedProvider === provider.provider && selectedModel === provider.model)}
              className="rounded-xl bg-sky-600 px-4 py-2 text-sm font-semibold text-white hover:bg-sky-500 disabled:opacity-50"
            >
              Lưu
            </button>
          </div>
          <div className="text-xs text-sky-300/70">
            Hiện dùng: <span className="font-mono font-semibold text-sky-300">{provider.provider}</span>
            {" / "}
            <span className="font-mono font-semibold text-sky-300">{provider.model}</span>
          </div>
        </div>
      )}

      {/* ===== 9router section ===== */}
      <Section title="9router API Keys" subtitle={`OpenAI compatible · max 3 req/key · ${stats?.total ?? 0} key`} color="gold">
        <StatsGrid stats={stats} />

        <div className="space-y-3">
          <p className="text-sm text-gold-700">
            Mỗi key một dòng. Biến môi trường:{" "}
            <code className="text-gold-400 bg-[#2f2620] px-1 rounded text-xs">NINEROUTER_API_KEY</code>
          </p>
          <textarea
            value={bulkText}
            onChange={(e) => setBulkText(e.target.value)}
            placeholder={"sk-9router-key-1\nsk-9router-key-2"}
            rows={5}
            className="w-full rounded-xl border border-[#43372d] bg-[#211a15] p-3 font-mono text-xs text-[#ece3d7]
              placeholder-gold-800 focus:border-gold-400 focus:outline-none resize-none"
          />
          <div className="flex flex-wrap gap-2">
            <button onClick={handleTest} disabled={testing}
              className="flex items-center gap-2 rounded-xl bg-[#2f2620] px-4 py-2 text-sm font-semibold text-[#ece3d7] hover:bg-[#3d3228] disabled:opacity-50 border border-[#43372d]">
              {testing && <Spinner />}
              {testing ? "Đang kiểm tra..." : "Kiểm tra key"}
            </button>
            <button onClick={handleSaveAll} disabled={saving}
              className="rounded-xl bg-gold-500 px-4 py-2 text-sm font-semibold text-[#17120e] hover:bg-gold-400 disabled:opacity-50">
              Thay toàn bộ pool
            </button>
            <button onClick={handleAdd} disabled={saving}
              className="rounded-xl bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-500 disabled:opacity-50">
              Thêm một key
            </button>
          </div>
          <TestResultsBox results={testResults} />
        </div>

        <KeysTable stats={stats} onReset={handleReset} onRemove={handleRemove} />
        <p className="text-xs text-gold-800">File: <code>/app/data/keys.json</code></p>
      </Section>

      {/* ===== Gemini section ===== */}
      <Section title="Google Gemini API Keys" subtitle={`Vision API · max 10 req/key · ${geminiStats?.total ?? 0} key`} color="violet">
        <StatsGrid stats={geminiStats} />

        <div className="space-y-3">
          <p className="text-sm text-gold-700">
            Mỗi key một dòng (tối đa 10 key chạy song song). Biến môi trường:{" "}
            <code className="text-gold-400 bg-[#2f2620] px-1 rounded text-xs">GEMINI_API_KEY</code>
          </p>
          <textarea
            value={geminiBulkText}
            onChange={(e) => setGeminiBulkText(e.target.value)}
            placeholder={"AIzaSy...\nAIzaSy..."}
            rows={5}
            className="w-full rounded-xl border border-[#43372d] bg-[#211a15] p-3 font-mono text-xs text-[#ece3d7]
              placeholder-gold-800 focus:border-violet-500 focus:outline-none resize-none"
          />
          <div className="flex flex-wrap gap-2">
            <button onClick={handleGeminiTest} disabled={geminiTesting}
              className="flex items-center gap-2 rounded-xl bg-[#2f2620] px-4 py-2 text-sm font-semibold text-[#ece3d7] hover:bg-[#3d3228] disabled:opacity-50 border border-[#43372d]">
              {geminiTesting && <Spinner />}
              {geminiTesting ? "Đang kiểm tra..." : "Kiểm tra key"}
            </button>
            <button onClick={handleGeminiSaveAll} disabled={saving}
              className="rounded-xl bg-violet-600 px-4 py-2 text-sm font-semibold text-white hover:bg-violet-500 disabled:opacity-50">
              Thay toàn bộ pool
            </button>
            <button onClick={handleGeminiAdd} disabled={saving}
              className="rounded-xl bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-500 disabled:opacity-50">
              Thêm một key
            </button>
          </div>
          <TestResultsBox results={geminiTestResults} />
        </div>

        <KeysTable stats={geminiStats} onReset={handleGeminiReset} onRemove={handleGeminiRemove} />
        <p className="text-xs text-gold-800">File: <code>/app/data/gemini_keys.json</code></p>
      </Section>

      <p className="text-xs text-gold-800">
        Provider config: <code>/app/data/provider.json</code>
      </p>
    </div>
  );
}

function Section({ title, subtitle, color, children }) {
  const borders = {
    gold:   "border-gold-500/20 bg-gold-500/5",
    violet: "border-violet-500/20 bg-violet-500/5",
  };
  return (
    <div className={`rounded-xl border p-4 space-y-4 ${borders[color] ?? "border-[#43372d] bg-[#261e18]/30"}`}>
      <div>
        <h3 className="font-semibold text-[#ece3d7]">{title}</h3>
        <p className="text-xs text-gold-700 mt-0.5">{subtitle}</p>
      </div>
      {children}
    </div>
  );
}

function StatsGrid({ stats }) {
  if (!stats) return null;
  return (
    <div className="grid grid-cols-2 gap-2 sm:grid-cols-5">
      <StatCard label="Tổng key"     value={stats.total} />
      <StatCard label="Sẵn sàng"     value={stats.active}         color="text-emerald-400" />
      <StatCard label="Rate limit"   value={stats.rate_limited}   color="text-amber-400" />
      <StatCard label="Hết quota"    value={stats.quota_exceeded} color="text-orange-400" />
      <StatCard label="Không hợp lệ" value={stats.invalid}        color="text-red-400" />
    </div>
  );
}

function KeysTable({ stats, onReset, onRemove }) {
  if (!stats?.keys?.length) {
    return stats ? (
      <StatusMsg color="amber">Pool đang trống. Hãy thêm API key để OCR hoạt động.</StatusMsg>
    ) : null;
  }
  return (
    <div className="overflow-x-auto rounded-xl border border-[#43372d]">
      <table className="min-w-full text-sm bg-[#261e18]/60">
        <thead>
          <tr className="border-b border-[#43372d] bg-[#261e18]">
            {["#", "Key", "Trạng thái", "Dùng", "OK", "Lỗi", "Cooldown", ""].map((label) => (
              <th key={label} className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gold-700">
                {label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-[#43372d]/50">
          {stats.keys.map((key) => (
            <tr key={key.index} className="hover:bg-[#2f2620]/50">
              <td className="px-4 py-3 text-gold-600">{key.index + 1}</td>
              <td className="px-4 py-3 font-mono text-xs text-[#ece3d7]">{key.preview}</td>
              <td className="px-4 py-3">
                <span className={`rounded-lg border px-2 py-0.5 text-xs font-medium ${STATE_COLORS[key.state]}`} title={key.last_error}>
                  {STATE_LABELS[key.state]}
                </span>
              </td>
              <td className="px-4 py-3 text-[#ece3d7]">{key.used}</td>
              <td className="px-4 py-3 text-emerald-400">{key.success}</td>
              <td className="px-4 py-3 text-red-400">{key.errors}</td>
              <td className="px-4 py-3 text-gold-600">
                {key.cooldown_remaining > 0 ? `${key.cooldown_remaining.toFixed(0)}s` : "—"}
              </td>
              <td className="px-4 py-3">
                <div className="flex gap-3">
                  <button onClick={() => onReset(key.index)} className="text-xs text-gold-400 hover:text-gold-300 font-medium">Reset</button>
                  <button onClick={() => onRemove(key.index)} className="text-xs text-red-400 hover:text-red-300 font-medium">Xóa</button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function TestResultsBox({ results }) {
  if (!results) return null;
  return (
    <div className="rounded-xl border border-[#43372d] bg-[#211a15] p-3 space-y-2">
      <p className="text-sm font-semibold text-[#ece3d7]">
        {results.ok}/{results.total} key hoạt động
      </p>
      {results.results.map((result, index) => (
        <div key={index} className={`text-xs font-mono ${result.ok ? "text-emerald-400" : "text-red-400"}`}>
          <code>{result.preview}</code>: {result.message}
        </div>
      ))}
    </div>
  );
}

function Spinner() {
  return <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-gold-400 border-t-transparent" />;
}

function StatusMsg({ color, children }) {
  const styles = {
    red:     "border-red-500/20 bg-red-500/10 text-red-300",
    emerald: "border-emerald-500/20 bg-emerald-500/10 text-emerald-300",
    amber:   "border-amber-500/20 bg-amber-500/10 text-amber-300",
  };
  return <div className={`rounded-xl border p-3 text-sm ${styles[color]}`}>{children}</div>;
}

function StatCard({ label, value, color = "text-[#ece3d7]" }) {
  return (
    <div className="rounded-xl border border-[#43372d] bg-[#261e18] p-3">
      <div className="text-[10px] uppercase tracking-wider text-gold-700 font-semibold">{label}</div>
      <div className={`text-2xl font-bold mt-1 ${color}`}>{value}</div>
    </div>
  );
}
