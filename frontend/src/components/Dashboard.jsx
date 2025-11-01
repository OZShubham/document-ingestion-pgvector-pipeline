import React, { useState, useEffect } from 'react';
import {
  BarChart, Bar, LineChart, Line, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from 'recharts';
import {
  TrendingUp, TrendingDown, FileText, CheckCircle, XCircle,
  Clock, Database, Layers, Activity, Zap, Users, HardDrive,
  AlertCircle, Package, Cpu, ArrowUpRight, ArrowDownRight
} from 'lucide-react';

const Dashboard = ({ projectId, userId, apiClient }) => {
  const [analytics, setAnalytics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [timeRange, setTimeRange] = useState(30);

  useEffect(() => {
    loadAnalytics();
  }, [projectId, timeRange]);

  const loadAnalytics = async () => {
    try {
      setLoading(true);
      const data = await apiClient.request(
        `/projects/${projectId}/analytics/detailed?user_id=${userId}&days=${timeRange}`
      );
      setAnalytics(data);
    } catch (error) {
      console.error('Failed to load analytics:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <Activity className="w-12 h-12 animate-pulse text-purple-400 mx-auto mb-4" />
          <p className="text-slate-400">Loading analytics...</p>
        </div>
      </div>
    );
  }

  if (!analytics) {
    return (
      <div className="text-center py-12">
        <AlertCircle className="w-12 h-12 text-slate-600 mx-auto mb-4" />
        <p className="text-slate-400">No analytics data available</p>
      </div>
    );
  }

  const COLORS = {
    primary: '#3b82f6',
    success: '#10b981',
    warning: '#f59e0b',
    danger: '#ef4444',
    purple: '#a855f7',
    pink: '#ec4899',
    cyan: '#06b6d4'
  };

  const MetricCard = ({ icon: Icon, label, value, change, trend, color = 'blue' }) => (
    <div className="bg-slate-800/30 rounded-xl p-6 border border-slate-700/30 hover:border-slate-600/50 transition-all">
      <div className="flex items-start justify-between mb-4">
        <div className={`p-3 bg-${color}-500/10 rounded-xl`}>
          <Icon className={`w-6 h-6 text-${color}-400`} />
        </div>
        {change !== undefined && (
          <div className={`flex items-center gap-1 text-xs font-medium ${
            trend === 'up' ? 'text-emerald-400' : trend === 'down' ? 'text-red-400' : 'text-slate-400'
          }`}>
            {trend === 'up' ? <ArrowUpRight className="w-3 h-3" /> : 
             trend === 'down' ? <ArrowDownRight className="w-3 h-3" /> : null}
            {change}%
          </div>
        )}
      </div>
      <div>
        <p className="text-3xl font-bold mb-1">{value}</p>
        <p className="text-sm text-slate-400">{label}</p>
      </div>
    </div>
  );

  return (
    <div className="space-y-6">
      {/* Time Range Selector */}
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">Analytics Dashboard</h2>
        <div className="flex gap-2">
          {[7, 30, 90].map(days => (
            <button
              key={days}
              onClick={() => setTimeRange(days)}
              className={`px-4 py-2 rounded-xl font-medium transition-all ${
                timeRange === days
                  ? 'bg-gradient-to-r from-purple-500 to-pink-600 shadow-lg'
                  : 'bg-slate-800/30 hover:bg-slate-800/50 text-slate-400'
              }`}
            >
              {days}d
            </button>
          ))}
        </div>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <MetricCard
          icon={FileText}
          label="Total Documents"
          value={analytics.overview.total_documents}
          color="blue"
        />
        <MetricCard
          icon={CheckCircle}
          label="Success Rate"
          value={`${analytics.overview.success_rate}%`}
          change={analytics.overview.success_rate}
          trend={analytics.overview.success_rate >= 90 ? 'up' : analytics.overview.success_rate >= 70 ? 'neutral' : 'down'}
          color="emerald"
        />
        <MetricCard
          icon={HardDrive}
          label="Storage Used"
          value={`${analytics.overview.total_storage_gb} GB`}
          color="purple"
        />
        <MetricCard
          icon={Layers}
          label="Total Vectors"
          value={analytics.vector_store.total_vectors.toLocaleString()}
          color="pink"
        />
      </div>

      {/* Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Upload Timeline */}
        <div className="bg-slate-900/50 backdrop-blur-xl border border-slate-800/50 rounded-2xl p-6">
          <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
            <Activity className="w-5 h-5 text-purple-400" />
            Upload Activity
          </h3>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={[...analytics.timeline].reverse()}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis 
                dataKey="date" 
                stroke="#94a3b8"
                fontSize={12}
                tickFormatter={(date) => new Date(date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
              />
              <YAxis stroke="#94a3b8" fontSize={12} />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#1e293b',
                  border: '1px solid #334155',
                  borderRadius: '8px'
                }}
              />
              <Legend />
              <Line type="monotone" dataKey="uploads" stroke={COLORS.primary} name="Uploads" strokeWidth={2} />
              <Line type="monotone" dataKey="successful" stroke={COLORS.success} name="Successful" strokeWidth={2} />
              <Line type="monotone" dataKey="failed" stroke={COLORS.danger} name="Failed" strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Processing Methods */}
        <div className="bg-slate-900/50 backdrop-blur-xl border border-slate-800/50 rounded-2xl p-6">
          <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
            <Zap className="w-5 h-5 text-emerald-400" />
            Processing Methods
          </h3>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={analytics.processing_methods}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={({ method, count }) => `${method}: ${count}`}
                outerRadius={100}
                fill="#8884d8"
                dataKey="count"
              >
                {analytics.processing_methods.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={Object.values(COLORS)[index % Object.values(COLORS).length]} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{
                  backgroundColor: '#1e293b',
                  border: '1px solid #334155',
                  borderRadius: '8px'
                }}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>

        {/* File Types Distribution */}
        <div className="bg-slate-900/50 backdrop-blur-xl border border-slate-800/50 rounded-2xl p-6">
          <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
            <Package className="w-5 h-5 text-orange-400" />
            File Types
          </h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={analytics.file_types.slice(0, 6)}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis 
                dataKey="type" 
                stroke="#94a3b8"
                fontSize={11}
                angle={-45}
                textAnchor="end"
                height={80}
              />
              <YAxis stroke="#94a3b8" fontSize={12} />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#1e293b',
                  border: '1px solid #334155',
                  borderRadius: '8px'
                }}
              />
              <Bar dataKey="count" fill={COLORS.purple} name="Documents" />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Processing Performance */}
        <div className="bg-slate-900/50 backdrop-blur-xl border border-slate-800/50 rounded-2xl p-6">
          <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
            <Cpu className="w-5 h-5 text-cyan-400" />
            Stage Performance
          </h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={analytics.performance}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis 
                dataKey="stage" 
                stroke="#94a3b8"
                fontSize={11}
                angle={-45}
                textAnchor="end"
                height={80}
              />
              <YAxis stroke="#94a3b8" fontSize={12} />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#1e293b',
                  border: '1px solid #334155',
                  borderRadius: '8px'
                }}
                formatter={(value) => `${value}ms`}
              />
              <Bar dataKey="avg_duration_ms" fill={COLORS.cyan} name="Avg Duration (ms)" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Top Uploaders & Vector Stats */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Top Uploaders */}
        <div className="bg-slate-900/50 backdrop-blur-xl border border-slate-800/50 rounded-2xl p-6">
          <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
            <Users className="w-5 h-5 text-blue-400" />
            Top Contributors
          </h3>
          <div className="space-y-3">
            {analytics.top_uploaders.slice(0, 5).map((uploader, index) => (
              <div key={index} className="flex items-center justify-between p-3 bg-slate-800/30 rounded-lg">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center font-bold">
                    {index + 1}
                  </div>
                  <div>
                    <p className="font-medium">{uploader.user}</p>
                    <p className="text-xs text-slate-400">{uploader.upload_count} uploads</p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="font-bold text-purple-400">{uploader.total_uploaded_mb} MB</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Vector Store Stats */}
        <div className="bg-slate-900/50 backdrop-blur-xl border border-slate-800/50 rounded-2xl p-6">
          <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
            <Database className="w-5 h-5 text-pink-400" />
            Vector Store
          </h3>
          <div className="space-y-4">
            <div className="flex items-center justify-between p-4 bg-slate-800/30 rounded-lg">
              <span className="text-slate-400">Total Vectors</span>
              <span className="font-bold text-xl text-pink-400">
                {analytics.vector_store.total_vectors.toLocaleString()}
              </span>
            </div>
            <div className="flex items-center justify-between p-4 bg-slate-800/30 rounded-lg">
              <span className="text-slate-400">Documents Indexed</span>
              <span className="font-bold text-xl text-purple-400">
                {analytics.vector_store.documents_with_vectors}
              </span>
            </div>
            <div className="flex items-center justify-between p-4 bg-slate-800/30 rounded-lg">
              <span className="text-slate-400">Avg Chunk Size</span>
              <span className="font-bold text-xl text-blue-400">
                {Math.round(analytics.vector_store.avg_chunk_size)} chars
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Recent Activity */}
      <div className="bg-slate-900/50 backdrop-blur-xl border border-slate-800/50 rounded-2xl p-6">
        <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
          <Clock className="w-5 h-5 text-emerald-400" />
          Recent Activity
        </h3>
        <div className="space-y-2">
          {analytics.recent_activity.slice(0, 10).map((activity, index) => (
            <div key={index} className="flex items-center justify-between p-3 bg-slate-800/30 rounded-lg hover:bg-slate-800/50 transition-all">
              <div className="flex items-center gap-3 flex-1 min-w-0">
                <FileText className="w-4 h-4 text-blue-400 flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="font-medium truncate">{activity.filename}</p>
                  <p className="text-xs text-slate-400">
                    {activity.uploaded_by} • {new Date(activity.created_at).toLocaleString()}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                {activity.status === 'completed' && (
                  <CheckCircle className="w-4 h-4 text-emerald-400" />
                )}
                {activity.status === 'failed' && (
                  <XCircle className="w-4 h-4 text-red-400" />
                )}
                {activity.status === 'processing' && (
                  <Clock className="w-4 h-4 text-blue-400" />
                )}
                {activity.processing_duration_seconds && (
                  <span className="text-xs text-slate-400">
                    {activity.processing_duration_seconds}s
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Errors (if any) */}
      {analytics.errors.length > 0 && (
        <div className="bg-slate-900/50 backdrop-blur-xl border border-red-500/20 rounded-2xl p-6">
          <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
            <AlertCircle className="w-5 h-5 text-red-400" />
            Recent Errors
          </h3>
          <div className="space-y-2">
            {analytics.errors.map((error, index) => (
              <div key={index} className="p-3 bg-red-500/10 border border-red-500/20 rounded-lg">
                <div className="flex items-start justify-between gap-2">
                  <p className="text-sm text-red-300 flex-1">{error.message}</p>
                  <div className="text-right flex-shrink-0">
                    <p className="text-xs font-bold text-red-400">{error.occurrences}x</p>
                    <p className="text-xs text-slate-500">
                      {new Date(error.last_occurrence).toLocaleDateString()}
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default Dashboard;