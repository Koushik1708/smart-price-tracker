import React, { useState, useEffect, useCallback } from 'react';
import apiClient from '../apiClient';

export default function AdminPanel({ showToast }) {
  const [activeTab, setActiveTab] = useState('users'); // users, products, queues, dlq, diagnostics, audit
  const [loading, setLoading] = useState(false);

  // States
  const [users, setUsers] = useState([]);
  const [userQuery, setUserQuery] = useState('');
  const [userPagination, setUserPagination] = useState({ current_page: 1, total_pages: 1 });

  const [products, setProducts] = useState([]);
  const [productQuery, setProductQuery] = useState('');
  const [productStatus, setProductStatus] = useState('');
  const [productPagination, setProductPagination] = useState({ current_page: 1, total_pages: 1 });

  const [queueInfo, setQueueInfo] = useState(null);
  const [workerInfo, setWorkerInfo] = useState(null);
  const [redisInfo, setRedisInfo] = useState(null);

  const [failedJobs, setFailedJobs] = useState([]);
  const [failedPagination, setFailedPagination] = useState({ current_page: 1, total_pages: 1 });

  const [diagnostics, setDiagnostics] = useState(null);
  const [runtimeConfig, setRuntimeConfig] = useState(null);
  const [systemStats, setSystemStats] = useState(null);

  const [auditLogs, setAuditLogs] = useState([]);
  const [auditActionFilter, setAuditActionFilter] = useState('');
  const [auditPagination, setAuditPagination] = useState({ current_page: 1, total_pages: 1 });

  // 1. Fetch Users
  const fetchUsers = useCallback((page = 1) => {
    setLoading(true);
    apiClient.get(`/admin/users?q=${userQuery}&page=${page}`)
      .then(res => {
        setUsers(res.data.users || []);
        setUserPagination(res.data.pagination || { current_page: 1, total_pages: 1 });
      })
      .catch(err => {
        console.error("Failed to fetch admin users:", err);
        showToast && showToast("Failed to load user list", "error");
      })
      .finally(() => setLoading(false));
  }, [userQuery, showToast]);

  // 2. Fetch Products
  const fetchProducts = useCallback((page = 1) => {
    setLoading(true);
    apiClient.get(`/admin/products?q=${productQuery}&status_filter=${productStatus}&page=${page}`)
      .then(res => {
        setProducts(res.data.products || []);
        setProductPagination(res.data.pagination || { current_page: 1, total_pages: 1 });
      })
      .catch(err => console.error("Failed to fetch admin products:", err))
      .finally(() => setLoading(false));
  }, [productQuery, productStatus]);

  // 3. Fetch Queues & Workers
  const fetchQueueAndWorkers = useCallback(() => {
    setLoading(true);
    Promise.all([
      apiClient.get('/admin/queues'),
      apiClient.get('/admin/workers'),
      apiClient.get('/admin/redis')
    ]).then(([qRes, wRes, rRes]) => {
      setQueueInfo(qRes.data);
      setWorkerInfo(wRes.data);
      setRedisInfo(rRes.data);
    }).catch(err => console.error("Failed queue/worker diagnostics:", err))
      .finally(() => setLoading(false));
  }, []);

  // 4. Fetch Failed Jobs
  const fetchFailedJobs = useCallback((page = 1) => {
    setLoading(true);
    apiClient.get(`/admin/failed-jobs?page=${page}`)
      .then(res => {
        setFailedJobs(res.data.failed_jobs || []);
        setFailedPagination(res.data.pagination || { current_page: 1, total_pages: 1 });
      })
      .catch(err => console.error("Failed to fetch DLQ:", err))
      .finally(() => setLoading(false));
  }, []);

  // 5. Fetch Diagnostics & Config
  const fetchDiagnostics = useCallback(() => {
    setLoading(true);
    Promise.all([
      apiClient.get('/admin/diagnostics'),
      apiClient.get('/admin/config'),
      apiClient.get('/admin/stats')
    ]).then(([dRes, cRes, sRes]) => {
      setDiagnostics(dRes.data);
      setRuntimeConfig(cRes.data);
      setSystemStats(sRes.data);
    }).catch(err => console.error("Failed system diagnostics:", err))
      .finally(() => setLoading(false));
  }, []);

  // 6. Fetch Audit Logs
  const fetchAuditLogs = useCallback((page = 1) => {
    setLoading(true);
    apiClient.get(`/admin/audit-logs?action=${auditActionFilter}&page=${page}`)
      .then(res => {
        setAuditLogs(res.data.audit_logs || []);
        setAuditPagination(res.data.pagination || { current_page: 1, total_pages: 1 });
      })
      .catch(err => console.error("Failed audit logs:", err))
      .finally(() => setLoading(false));
  }, [auditActionFilter]);

  useEffect(() => {
    if (activeTab === 'users') fetchUsers(1);
    else if (activeTab === 'products') fetchProducts(1);
    else if (activeTab === 'queues') fetchQueueAndWorkers();
    else if (activeTab === 'dlq') fetchFailedJobs(1);
    else if (activeTab === 'diagnostics') fetchDiagnostics();
    else if (activeTab === 'audit') fetchAuditLogs(1);
  }, [activeTab, fetchUsers, fetchProducts, fetchQueueAndWorkers, fetchFailedJobs, fetchDiagnostics, fetchAuditLogs]);

  // Admin Actions
  const handleToggleAdminRole = (userId, currentIsAdmin) => {
    apiClient.post(`/admin/users/${userId}/role?is_admin=${!currentIsAdmin}`)
      .then(() => {
        showToast && showToast(`User ${userId} admin role updated`, 'success');
        fetchUsers(userPagination.current_page);
      })
      .catch(err => showToast && showToast("Failed to update role", 'error'));
  };

  const handleAdminRetryProduct = (productId) => {
    apiClient.post(`/admin/products/${productId}/retry`)
      .then(() => {
        showToast && showToast(`Scrape retry queued for product ${productId}`, 'success');
        if (activeTab === 'products') fetchProducts(productPagination.current_page);
        else if (activeTab === 'dlq') fetchFailedJobs(failedPagination.current_page);
      })
      .catch(() => showToast && showToast("Failed to queue retry", 'error'));
  };

  const handleAdminDeleteProduct = (productId) => {
    if (!window.confirm("Are you sure you want to delete this product system-wide?")) return;
    apiClient.delete(`/admin/products/${productId}`)
      .then(() => {
        showToast && showToast(`Product ${productId} deleted`, 'success');
        fetchProducts(productPagination.current_page);
      })
      .catch(() => showToast && showToast("Failed to delete product", 'error'));
  };

  // Shared table class helpers
  const tableWrapper = "overflow-x-auto border border-slate-200 dark:border-slate-700/60 rounded-xl";
  const tableBase = "w-full text-left text-sm border-collapse";
  const thead = "bg-slate-50 dark:bg-slate-700/40 border-b border-slate-200 dark:border-slate-700/60 text-slate-600 dark:text-slate-400 font-bold";
  const tbody = "divide-y divide-slate-100 dark:divide-slate-700/40";
  const trHover = "hover:bg-slate-50 dark:hover:bg-slate-700/30 transition-colors";
  const inputClass = "p-2 border border-slate-200 dark:border-slate-700 rounded-lg text-sm bg-white dark:bg-slate-900/80 text-slate-800 dark:text-slate-200 placeholder-slate-400 dark:placeholder-slate-500 outline-none focus:ring-2 focus:ring-indigo-500 transition-colors";
  const btnSecondary = "bg-slate-100 dark:bg-slate-700 hover:bg-slate-200 dark:hover:bg-slate-600 px-4 py-2 rounded-lg text-sm font-semibold text-slate-700 dark:text-slate-300 transition-colors";

  return (
    <div className="bg-white dark:bg-slate-800/90 rounded-2xl shadow-sm border border-slate-200 dark:border-slate-700/80 p-6 transition-colors">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between border-b border-slate-100 dark:border-slate-700/60 pb-5 mb-6 gap-4">
        <div>
          <h2 className="text-2xl font-bold text-slate-900 dark:text-slate-50 m-0">Enterprise Administration Panel</h2>
          <p className="text-sm text-slate-500 dark:text-slate-400 m-0 mt-1">System governance, queue monitoring, worker health, and audit trails</p>
        </div>
        <div className="flex items-center gap-2 bg-indigo-50 dark:bg-indigo-950/60 border border-indigo-100 dark:border-indigo-900/50 text-indigo-700 dark:text-indigo-400 font-bold px-3 py-1.5 rounded-lg text-xs">
          🛡️ Authenticated as Admin
        </div>
      </div>

      {/* Sub Tabs */}
      <div className="flex flex-wrap border-b border-slate-200 dark:border-slate-700 mb-6 gap-2">
        {[
          { id: 'users', label: '👥 User Management' },
          { id: 'products', label: '📦 Global Products' },
          { id: 'queues', label: '⚙️ Workers & Queues' },
          { id: 'dlq', label: '⚠️ Failed Jobs (DLQ)' },
          { id: 'diagnostics', label: '📊 System Diagnostics' },
          { id: 'audit', label: '📜 Audit Logs' }
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-4 py-2.5 text-sm font-semibold rounded-t-lg transition-colors ${
              activeTab === tab.id
                ? 'bg-indigo-600 dark:bg-indigo-500 text-white border-b-2 border-indigo-700 dark:border-indigo-400'
                : 'bg-slate-50 dark:bg-slate-700/40 text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700 hover:text-slate-900 dark:hover:text-slate-200'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {loading && (
        <div className="flex justify-center items-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600 dark:border-indigo-400"></div>
        </div>
      )}

      {/* Tab 1: User Management */}
      {activeTab === 'users' && !loading && (
        <div>
          <div className="flex gap-2 mb-4">
            <input
              type="text"
              placeholder="Search users by name or email..."
              value={userQuery}
              onChange={e => setUserQuery(e.target.value)}
              className={`${inputClass} flex-1`}
            />
            <button onClick={() => fetchUsers(1)} className={btnSecondary}>Search</button>
          </div>
          <div className={tableWrapper}>
            <table className={tableBase}>
              <thead className={thead}>
                <tr>
                  <th className="p-3">ID</th>
                  <th className="p-3">Name</th>
                  <th className="p-3">Email</th>
                  <th className="p-3">Role</th>
                  <th className="p-3">Tracked Products</th>
                  <th className="p-3 font-right">Actions</th>
                </tr>
              </thead>
              <tbody className={tbody}>
                {users.map(u => (
                  <tr key={u.id} className={trHover}>
                    <td className="p-3 font-semibold text-slate-700 dark:text-slate-300">#{u.id}</td>
                    <td className="p-3 font-bold text-slate-900 dark:text-slate-100">{u.name}</td>
                    <td className="p-3 text-slate-600 dark:text-slate-400">{u.email}</td>
                    <td className="p-3">
                      {u.is_admin ? (
                        <span className="bg-indigo-100 dark:bg-indigo-950/60 text-indigo-700 dark:text-indigo-400 text-xs px-2.5 py-1 rounded-full font-bold">Admin</span>
                      ) : (
                        <span className="bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-400 text-xs px-2.5 py-1 rounded-full">User</span>
                      )}
                    </td>
                    <td className="p-3 text-slate-700 dark:text-slate-300 font-semibold">{u.product_count}</td>
                    <td className="p-3 text-right">
                      <button
                        onClick={() => handleToggleAdminRole(u.id, u.is_admin)}
                        className="text-xs bg-slate-100 dark:bg-slate-700 hover:bg-slate-200 dark:hover:bg-slate-600 border border-slate-200 dark:border-slate-600 font-semibold px-2.5 py-1 rounded text-slate-700 dark:text-slate-300 transition-colors"
                      >
                        {u.is_admin ? 'Demote User' : 'Promote Admin'}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Tab 2: Global Products */}
      {activeTab === 'products' && !loading && (
        <div>
          <div className="flex gap-2 mb-4">
            <input
              type="text"
              placeholder="Search product title or brand..."
              value={productQuery}
              onChange={e => setProductQuery(e.target.value)}
              className={`${inputClass} flex-1`}
            />
            <select
              value={productStatus}
              onChange={e => setProductStatus(e.target.value)}
              className={inputClass}
            >
              <option value="">All Statuses</option>
              <option value="SUCCESS">SUCCESS</option>
              <option value="PENDING">PENDING</option>
              <option value="FAILED">FAILED</option>
            </select>
            <button onClick={() => fetchProducts(1)} className={btnSecondary}>Filter</button>
          </div>
          <div className={tableWrapper}>
            <table className={tableBase}>
              <thead className={thead}>
                <tr>
                  <th className="p-3">ID</th>
                  <th className="p-3">User ID</th>
                  <th className="p-3">Platform</th>
                  <th className="p-3">Title</th>
                  <th className="p-3">Status</th>
                  <th className="p-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className={tbody}>
                {products.map(p => (
                  <tr key={p.id} className={trHover}>
                    <td className="p-3 font-semibold text-slate-700 dark:text-slate-300">#{p.id}</td>
                    <td className="p-3 text-slate-600 dark:text-slate-400">User #{p.user_id}</td>
                    <td className="p-3 capitalize font-bold text-slate-800 dark:text-slate-200">{p.platform}</td>
                    <td className="p-3 text-slate-900 dark:text-slate-100 font-medium truncate max-w-xs">{p.title}</td>
                    <td className="p-3">
                      <span className={`text-xs px-2.5 py-1 rounded-full font-bold ${
                        p.status === 'SUCCESS' ? 'bg-emerald-100 dark:bg-emerald-950/50 text-emerald-700 dark:text-emerald-400' :
                        p.status === 'FAILED' ? 'bg-rose-100 dark:bg-rose-950/50 text-rose-700 dark:text-rose-400' : 'bg-amber-100 dark:bg-amber-950/50 text-amber-700 dark:text-amber-400'
                      }`}>
                        {p.status}
                      </span>
                    </td>
                    <td className="p-3 text-right space-x-2">
                      <button
                        onClick={() => handleAdminRetryProduct(p.id)}
                        className="text-xs bg-indigo-50 dark:bg-indigo-950/60 text-indigo-700 dark:text-indigo-400 border border-indigo-200 dark:border-indigo-900/50 font-semibold px-2 py-1 rounded transition-colors"
                      >
                        Force Retry
                      </button>
                      <button
                        onClick={() => handleAdminDeleteProduct(p.id)}
                        className="text-xs bg-rose-50 dark:bg-rose-950/50 text-rose-700 dark:text-rose-400 border border-rose-200 dark:border-rose-900/50 font-semibold px-2 py-1 rounded transition-colors"
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Tab 3: Workers & Queues */}
      {activeTab === 'queues' && !loading && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="bg-slate-50 dark:bg-slate-700/30 p-5 rounded-xl border border-slate-200 dark:border-slate-700/50">
            <h3 className="text-sm font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-3">Celery Workers</h3>
            <div className="text-3xl font-extrabold text-indigo-600 dark:text-indigo-400 mb-1">{workerInfo?.status || 'Unknown'}</div>
            <p className="text-xs text-slate-600 dark:text-slate-400 m-0">Concurrency: {workerInfo?.concurrency || 4} workers</p>
          </div>
          <div className="bg-slate-50 dark:bg-slate-700/30 p-5 rounded-xl border border-slate-200 dark:border-slate-700/50">
            <h3 className="text-sm font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-3">Queue Status</h3>
            <div className="text-3xl font-extrabold text-emerald-600 dark:text-emerald-400 mb-1">{queueInfo?.depth || 0} jobs</div>
            <p className="text-xs text-slate-600 dark:text-slate-400 m-0">Limit: {queueInfo?.queue_limit || 1000} items max</p>
          </div>
          <div className="bg-slate-50 dark:bg-slate-700/30 p-5 rounded-xl border border-slate-200 dark:border-slate-700/50">
            <h3 className="text-sm font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-3">Redis Broker</h3>
            <div className="text-3xl font-extrabold text-slate-800 dark:text-slate-100 mb-1">{redisInfo?.status || 'Connected'}</div>
            <p className="text-xs text-slate-600 dark:text-slate-400 m-0">Used Memory: {redisInfo?.used_memory_human || 'N/A'}</p>
          </div>
        </div>
      )}

      {/* Tab 4: Failed Jobs / DLQ */}
      {activeTab === 'dlq' && !loading && (
        <div>
          <div className={tableWrapper}>
            <table className={tableBase}>
              <thead className={thead}>
                <tr>
                  <th className="p-3">Product ID</th>
                  <th className="p-3">Title</th>
                  <th className="p-3">Retry Count</th>
                  <th className="p-3">Failure Reason</th>
                  <th className="p-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className={tbody}>
                {failedJobs.map(f => (
                  <tr key={f.id} className={trHover}>
                    <td className="p-3 font-semibold text-slate-700 dark:text-slate-300">#{f.id}</td>
                    <td className="p-3 font-bold text-slate-900 dark:text-slate-100 truncate max-w-xs">{f.title}</td>
                    <td className="p-3 text-slate-600 dark:text-slate-400">{f.retry_count}</td>
                    <td className="p-3 text-rose-600 dark:text-rose-400 font-medium text-xs truncate max-w-xs">{f.last_failure_reason || 'Unknown'}</td>
                    <td className="p-3 text-right">
                      <button
                        onClick={() => handleAdminRetryProduct(f.id)}
                        className="text-xs bg-indigo-600 dark:bg-indigo-500 text-white font-bold px-3 py-1.5 rounded hover:bg-indigo-700 dark:hover:bg-indigo-600 transition-colors"
                      >
                        Requeue Scrape
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Tab 5: System Diagnostics & Config */}
      {activeTab === 'diagnostics' && !loading && (
        <div className="space-y-6">
          {systemStats && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-indigo-50 dark:bg-indigo-950/40 p-4 rounded-xl border border-indigo-100 dark:border-indigo-900/50 text-center">
                <div className="text-xs text-indigo-700 dark:text-indigo-400 font-bold uppercase">Total Users</div>
                <div className="text-2xl font-extrabold text-indigo-900 dark:text-indigo-300">{systemStats.total_users}</div>
              </div>
              <div className="bg-slate-50 dark:bg-slate-700/30 p-4 rounded-xl border border-slate-200 dark:border-slate-700/50 text-center">
                <div className="text-xs text-slate-500 dark:text-slate-400 font-bold uppercase">Total Products</div>
                <div className="text-2xl font-extrabold text-slate-900 dark:text-slate-100">{systemStats.total_products}</div>
              </div>
              <div className="bg-emerald-50 dark:bg-emerald-950/40 p-4 rounded-xl border border-emerald-100 dark:border-emerald-900/50 text-center">
                <div className="text-xs text-emerald-700 dark:text-emerald-400 font-bold uppercase">Successful Scrapes</div>
                <div className="text-2xl font-extrabold text-emerald-900 dark:text-emerald-300">{systemStats.successful_products}</div>
              </div>
              <div className="bg-rose-50 dark:bg-rose-950/40 p-4 rounded-xl border border-rose-100 dark:border-rose-900/50 text-center">
                <div className="text-xs text-rose-700 dark:text-rose-400 font-bold uppercase">Active Alerts</div>
                <div className="text-2xl font-extrabold text-rose-900 dark:text-rose-300">{systemStats.active_alerts}</div>
              </div>
            </div>
          )}
          {runtimeConfig && (
            <div className="bg-slate-900 dark:bg-slate-950 text-slate-100 p-5 rounded-xl text-xs font-mono overflow-x-auto border border-slate-700/50">
              <h3 className="text-sm font-bold text-indigo-400 mb-3 font-sans">Runtime Configuration Settings</h3>
              <pre>{JSON.stringify(runtimeConfig, null, 2)}</pre>
            </div>
          )}
        </div>
      )}

      {/* Tab 6: Audit Logs */}
      {activeTab === 'audit' && !loading && (
        <div>
          <div className="flex gap-2 mb-4">
            <select
              value={auditActionFilter}
              onChange={e => setAuditActionFilter(e.target.value)}
              className={inputClass}
            >
              <option value="">All Actions</option>
              <option value="LOGIN">LOGIN</option>
              <option value="LOGOUT">LOGOUT</option>
              <option value="FAILED_LOGIN">FAILED_LOGIN</option>
              <option value="PRODUCT_TRACKED">PRODUCT_TRACKED</option>
              <option value="PRODUCT_DELETED">PRODUCT_DELETED</option>
              <option value="ALERT_CREATED">ALERT_CREATED</option>
              <option value="ADMIN_ACTION">ADMIN_ACTION</option>
              <option value="SECURITY_EVENT">SECURITY_EVENT</option>
            </select>
            <button onClick={() => fetchAuditLogs(1)} className={btnSecondary}>Filter Logs</button>
          </div>
          <div className={tableWrapper}>
            <table className={`${tableBase} font-mono`}>
              <thead className={`${thead} font-sans text-sm`}>
                <tr>
                  <th className="p-3">Timestamp</th>
                  <th className="p-3">Trace ID</th>
                  <th className="p-3">User ID</th>
                  <th className="p-3">Action</th>
                  <th className="p-3">Outcome</th>
                  <th className="p-3">Details</th>
                </tr>
              </thead>
              <tbody className={tbody}>
                {auditLogs.map(a => (
                  <tr key={a.id} className={trHover}>
                    <td className="p-3 text-slate-500 dark:text-slate-400 whitespace-nowrap text-xs">{new Date(a.timestamp).toLocaleString()}</td>
                    <td className="p-3 font-semibold text-indigo-600 dark:text-indigo-400 truncate max-w-[120px] text-xs">{a.trace_id || 'N/A'}</td>
                    <td className="p-3 text-slate-700 dark:text-slate-300 text-xs">{a.user_id ? `#${a.user_id}` : 'Guest/Anon'}</td>
                    <td className="p-3 font-bold text-slate-900 dark:text-slate-100 text-xs">{a.action}</td>
                    <td className="p-3 text-xs">
                      <span className={`px-2 py-0.5 rounded font-bold ${
                        a.outcome === 'SUCCESS' ? 'bg-emerald-100 dark:bg-emerald-950/50 text-emerald-700 dark:text-emerald-400' :
                        a.outcome === 'BLOCKED' ? 'bg-amber-100 dark:bg-amber-950/50 text-amber-700 dark:text-amber-400' : 'bg-rose-100 dark:bg-rose-950/50 text-rose-700 dark:text-rose-400'
                      }`}>
                        {a.outcome}
                      </span>
                    </td>
                    <td className="p-3 text-slate-600 dark:text-slate-400 truncate max-w-xs text-xs">{a.details || '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
