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
  active: "bg-emerald-100 text-emerald-800 border-emerald-300",
  rate_limited: "bg-amber-100 text-amber-800 border-amber-300",
  quota_exceeded: "bg-orange-100 text-orange-800 border-orange-300",
  invalid: "bg-red-100 text-red-800 border-red-300",
};

const STATE_LABELS = {
  active: "Sẵn sàng",
  rate_limited: "Giới hạn tốc độ",
  quota_exceeded: "Hết quota",
  invalid: "Key không hợp lệ",
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
    bulkText
      .split(/[\n,]+/)
      .map((value) => value.trim())
      .filter(Boolean);

  const handleLogin = async (event) => {
    event.preventDefault();
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
    setSaving(true);
    setErr("");
    setNotice("");
    try {
      const data = await updateProvider(selectedModel);
      setProvider(data);
      setNotice(`Đã chuyển model OCR sang ${data.model}.`);
    } catch (error) {
      setErr(error.response?.data?.detail || error.message);
    } finally {
      setSaving(false);
    }
  };

  const handleTest = async () => {
    const keys = parseBulk();
    if (!keys.length) {
      setErr("Hãy nhập ít nhất một API key.");
      return;
    }
    setTesting(true);
    setErr("");
    setTestResults(null);
    try {
      setTestResults(await testKeys(keys));
    } catch (error) {
      setErr(error.response?.data?.detail || error.message);
    } finally {
      setTesting(false);
    }
  };

  const handleSaveAll = async () => {
    const keys = parseBulk();
    if (!keys.length) {
      setErr("Cần ít nhất một API key.");
      return;
    }
    if (!confirm(`Thay toàn bộ pool bằng ${keys.length} key này?`)) return;
    setSaving(true);
    setErr("");
    try {
      await replaceKeys(keys);
      setBulkText("");
      setTestResults(null);
      setStats(await fetchStats());
    } catch (error) {
      setErr(error.response?.data?.detail || error.message);
    } finally {
      setSaving(false);
    }
  };

  const handleAdd = async () => {
    const keys = parseBulk();
    if (keys.length !== 1) {
      setErr("Để thêm một key, ô nhập chỉ được chứa đúng một key.");
      return;
    }
    setSaving(true);
    setErr("");
    try {
      await addKey(keys[0]);
      setBulkText("");
      setStats(await fetchStats());
    } catch (error) {
      setErr(error.response?.data?.detail || error.message);
    } finally {
      setSaving(false);
    }
  };

  const handleRemove = async (index) => {
    if (!confirm(`Xóa key #${index + 1}?`)) return;
    try {
      await removeKey(index);
      setStats(await fetchStats());
    } catch (error) {
      setErr(error.response?.data?.detail || error.message);
    }
  };

  const handleReset = async (index) => {
    try {
      await resetKey(index);
      setStats(await fetchStats());
    } catch (error) {
      setErr(error.response?.data?.detail || error.message);
    }
  };

  if (!authed) {
    return (
      <form onSubmit={handleLogin} className="mx-auto max-w-md space-y-4">
        <h2 className="text-lg font-semibold">Đăng nhập quản trị</h2>
        <p className="text-sm text-slate-600">
          Nhập mật khẩu được cấu hình bằng <code>ADMIN_PASSWORD</code> để quản lý
          kết nối 9router.
        </p>
        <input
          type="password"
          value={pw}
          onChange={(event) => setPw(event.target.value)}
          placeholder="Mật khẩu admin"
          className="w-full rounded border border-slate-300 px-3 py-2"
          autoFocus
        />
        <button className="w-full rounded bg-indigo-600 py-2 text-white hover:bg-indigo-700">
          Đăng nhập
        </button>
        {err && <p className="text-sm text-red-600">{err}</p>}
      </form>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold">Kết nối 9router</h2>
          <p className="text-sm text-slate-500">
            API tương thích OpenAI Chat Completions, hỗ trợ đầu vào ảnh.
          </p>
        </div>
        <button
          onClick={() => {
            clearAdminPassword();
            setAuthed(false);
          }}
          className="text-sm text-slate-600 underline"
        >
          Đăng xuất
        </button>
      </div>

      {err && <Message color="red">{err}</Message>}
      {notice && <Message color="emerald">{notice}</Message>}

      {provider && (
        <div className="space-y-4 rounded-lg border border-cyan-200 bg-cyan-50 p-4">
          <div>
            <div className="text-xs font-semibold uppercase text-cyan-700">HTTP endpoint</div>
            <code className="text-sm text-cyan-950">{provider.base_url}/chat/completions</code>
          </div>
          <div className="flex flex-wrap items-end gap-3">
            <label className="min-w-72 flex-1 text-sm font-medium text-slate-700">
              Model OCR
              <select
                value={selectedModel}
                onChange={(event) => setSelectedModel(event.target.value)}
                className="mt-1 w-full rounded border border-slate-300 bg-white px-3 py-2"
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
              className="rounded bg-cyan-700 px-4 py-2 text-sm text-white disabled:opacity-50"
            >
              Lưu model
            </button>
          </div>
        </div>
      )}

      {stats && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
          <Stat label="Tổng key" value={stats.total} />
          <Stat label="Sẵn sàng" value={stats.active} color="text-emerald-700" />
          <Stat label="Rate limit" value={stats.rate_limited} color="text-amber-700" />
          <Stat label="Hết quota" value={stats.quota_exceeded} color="text-orange-700" />
          <Stat label="Không hợp lệ" value={stats.invalid} color="text-red-700" />
        </div>
      )}

      <div className="space-y-3 rounded-lg border border-slate-200 bg-white p-4">
        <h3 className="font-semibold">9router API keys</h3>
        <p className="text-sm text-slate-600">
          Mỗi key một dòng. Có thể nhập một key từ biến <code>NINEROUTER_API_KEY</code>
          hoặc quản lý nhiều key tại đây.
        </p>
        <textarea
          value={bulkText}
          onChange={(event) => setBulkText(event.target.value)}
          placeholder={"sk-9router-key-1\nsk-9router-key-2"}
          rows={6}
          className="w-full rounded border border-slate-300 p-3 font-mono text-xs"
        />
        <div className="flex flex-wrap gap-2">
          <button
            onClick={handleTest}
            disabled={testing}
            className="rounded bg-slate-800 px-4 py-2 text-sm text-white disabled:opacity-50"
          >
            {testing ? "Đang gửi HTTP request..." : "Kiểm tra key"}
          </button>
          <button
            onClick={handleSaveAll}
            disabled={saving}
            className="rounded bg-indigo-600 px-4 py-2 text-sm text-white disabled:opacity-50"
          >
            Thay toàn bộ pool
          </button>
          <button
            onClick={handleAdd}
            disabled={saving}
            className="rounded bg-emerald-600 px-4 py-2 text-sm text-white disabled:opacity-50"
          >
            Thêm một key
          </button>
        </div>
        {testResults && (
          <div className="space-y-2 text-sm">
            <strong>{testResults.ok}/{testResults.total} key hoạt động</strong>
            {testResults.results.map((result, index) => (
              <div
                key={index}
                className={result.ok ? "text-emerald-700" : "text-red-700"}
              >
                <code>{result.preview}</code>: {result.message}
              </div>
            ))}
          </div>
        )}
      </div>

      {stats?.keys?.length > 0 ? (
        <div className="overflow-x-auto">
          <table className="min-w-full rounded border border-slate-200 bg-white text-sm">
            <thead className="bg-slate-100">
              <tr>
                {["#", "Key", "Trạng thái", "Dùng", "OK", "Lỗi", "Cooldown", "Hành động"].map(
                  (label) => (
                    <th key={label} className="px-3 py-2 text-left">{label}</th>
                  ),
                )}
              </tr>
            </thead>
            <tbody>
              {stats.keys.map((key) => (
                <tr key={key.index} className="border-t border-slate-200">
                  <td className="px-3 py-2">{key.index + 1}</td>
                  <td className="px-3 py-2 font-mono text-xs">{key.preview}</td>
                  <td className="px-3 py-2">
                    <span
                      className={`rounded border px-2 py-0.5 text-xs ${STATE_COLORS[key.state]}`}
                      title={key.last_error}
                    >
                      {STATE_LABELS[key.state]}
                    </span>
                  </td>
                  <td className="px-3 py-2">{key.used}</td>
                  <td className="px-3 py-2 text-emerald-700">{key.success}</td>
                  <td className="px-3 py-2 text-red-700">{key.errors}</td>
                  <td className="px-3 py-2">
                    {key.cooldown_remaining > 0 ? `${key.cooldown_remaining.toFixed(0)}s` : "-"}
                  </td>
                  <td className="space-x-2 px-3 py-2">
                    <button onClick={() => handleReset(key.index)} className="text-indigo-600">
                      Reset
                    </button>
                    <button onClick={() => handleRemove(key.index)} className="text-red-600">
                      Xóa
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <Message color="amber">Pool đang trống. Hãy thêm API key để OCR hoạt động.</Message>
      )}

      <p className="text-xs text-slate-500">
        Keys lưu tại <code>/app/data/keys.json</code>; model lưu tại{" "}
        <code>/app/data/provider.json</code>.
      </p>
    </div>
  );
}

function Message({ color, children }) {
  const styles = {
    red: "border-red-200 bg-red-50 text-red-700",
    emerald: "border-emerald-200 bg-emerald-50 text-emerald-700",
    amber: "border-amber-200 bg-amber-50 text-amber-800",
  };
  return <div className={`rounded border p-3 text-sm ${styles[color]}`}>{children}</div>;
}

function Stat({ label, value, color = "text-slate-900" }) {
  return (
    <div className="rounded border border-slate-200 bg-white p-3">
      <div className="text-xs uppercase text-slate-500">{label}</div>
      <div className={`text-2xl font-bold ${color}`}>{value}</div>
    </div>
  );
}
