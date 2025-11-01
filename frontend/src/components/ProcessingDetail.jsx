import React, { useState, useEffect, useRef } from 'react';
import {
  Workflow, CheckCircle, XCircle, Loader2, Clock, Zap,
  FileText, Layers, Database, Eye, ChevronDown, ChevronRight,
  Activity, Cpu, HardDrive, Brain, Sparkles, Tag, Hash,
  Copy, Download, Search, Filter
} from 'lucide-react';

const ProcessingDetail = ({ documentId, projectId, userId, apiClient, onClose }) => {
  const [document, setDocument] = useState(null);
  const [timeline, setTimeline] = useState([]);
  const [chunks, setChunks] = useState([]);
  const [insights, setInsights] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('timeline');
  const [expandedChunks, setExpandedChunks] = useState(new Set());
  const [chunksPage, setChunksPage] = useState(1);
  const [chunksPagination, setChunksPagination] = useState(null);
  const wsRef = useRef(null);
  const [liveUpdates, setLiveUpdates] = useState([]);

  useEffect(() => {
    loadDocumentDetails();
    connectWebSocket();
    
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [documentId]);

  useEffect(() => {
    if (activeTab === 'chunks') {
      loadChunks();
    } else if (activeTab === 'insights') {
      loadInsights();
    }
  }, [activeTab, chunksPage]);

  const connectWebSocket = () => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/api/ws/${projectId}`;
    
    const ws = new WebSocket(wsUrl);
    
    ws.onopen = () => {
      console.log('WebSocket connected');
      ws.send(JSON.stringify({ type: 'auth', user_id: userId }));
    };
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      if (data.type === 'document_update' && data.document_id === documentId) {
        setLiveUpdates(prev => [data, ...prev.slice(0, 9)]);
        loadDocumentDetails(); // Refresh details
      }
    };
    
    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
    
    ws.onclose = () => {
      console.log('WebSocket disconnected');
    };
    
    wsRef.current = ws;
  };

  const loadDocumentDetails = async () => {
    try {
      setLoading(true);
      
      // Load document
      const docData = await apiClient.request(
        `/documents/${documentId}?project_id=${projectId}&user_id=${userId}`
      );
      setDocument(docData);
      
      // Load timeline
      const timelineData = await apiClient.request(
        `/documents/${documentId}/processing-timeline?project_id=${projectId}&user_id=${userId}`
      );
      setTimeline(timelineData.timeline || []);
      
    } catch (error) {
      console.error('Failed to load document details:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadChunks = async () => {
    try {
      const data = await apiClient.request(
        `/documents/${documentId}/chunks?project_id=${projectId}&user_id=${userId}&page=${chunksPage}&limit=20`
      );
      setChunks(data.chunks || []);
      setChunksPagination(data.pagination);
    } catch (error) {
      console.error('Failed to load chunks:', error);
    }
  };

  const loadInsights = async () => {
    try {
      const data = await apiClient.request(
        `/documents/${documentId}/insights?project_id=${projectId}&user_id=${userId}`
      );
      setInsights(data);
    } catch (error) {
      console.error('Failed to load insights:', error);
    }
  };

  const toggleChunk = (chunkId) => {
    setExpandedChunks(prev => {
      const newSet = new Set(prev);
      if (newSet.has(chunkId)) {
        newSet.delete(chunkId);
      } else {
        newSet.add(chunkId);
      }
      return newSet;
    });
  };

  const getStageIcon = (stage) => {
    const icons = {
      'extraction': FileText,
      'chunking': Layers,
      'embedding': Brain,
      'storage': Database,
      'pipeline': Workflow
    };
    return icons[stage] || Activity;
  };

  const getStatusColor = (status) => {
    const colors = {
      'started': 'text-blue-400 bg-blue-500/10',
      'completed': 'text-emerald-400 bg-emerald-500/10',
      'failed': 'text-red-400 bg-red-500/10',
      'warning': 'text-yellow-400 bg-yellow-500/10'
    };
    return colors[status] || 'text-slate-400 bg-slate-500/10';
  };

  const formatDuration = (ms) => {
    if (!ms) return 'N/A';
    if (ms < 1000) return `${ms}ms`;
    return `${(ms / 1000).toFixed(2)}s`;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="w-12 h-12 animate-spin text-emerald-400" />
      </div>
    );
  }

  if (!document) {
    return (
      <div className="text-center py-12">
        <FileText className="w-12 h-12 text-slate-600 mx-auto mb-4" />
        <p className="text-slate-400">Document not found</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-slate-900/50 backdrop-blur-xl border border-slate-800/50 rounded-2xl p-6">
        <div className="flex items-start justify-between mb-4">
          <div className="flex items-start gap-4">
            <div className="p-3 bg-emerald-500/10 rounded-xl">
              <FileText className="w-8 h-8 text-emerald-400" />
            </div>
            <div>
              <h2 className="text-2xl font-bold mb-2">{document.filename}</h2>
              <div className="flex items-center gap-3 flex-wrap">
                <span className={`px-3 py-1 rounded-lg text-sm font-medium ${getStatusColor(document.status)}`}>
                  {document.status}
                </span>
                <span className="text-sm text-slate-400">
                  {(document.file_size / (1024 * 1024)).toFixed(2)} MB
                </span>
                {document.page_count && (
                  <span className="text-sm text-slate-400">{document.page_count} pages</span>
                )}
                <span className="text-sm text-slate-400">{document.processing_method}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Quick Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-4">
          <div className="bg-slate-800/30 rounded-lg p-3">
            <p className="text-xs text-slate-400 mb-1">Processing Time</p>
            <p className="text-lg font-bold">{formatDuration(document.processing_time_ms)}</p>
          </div>
          <div className="bg-slate-800/30 rounded-lg p-3">
            <p className="text-xs text-slate-400 mb-1">Chunks Created</p>
            <p className="text-lg font-bold text-purple-400">{document.chunk_count || 0}</p>
          </div>
          <div className="bg-slate-800/30 rounded-lg p-3">
            <p className="text-xs text-slate-400 mb-1">Uploaded By</p>
            <p className="text-sm font-medium truncate">{document.uploaded_by}</p>
          </div>
          <div className="bg-slate-800/30 rounded-lg p-3">
            <p className="text-xs text-slate-400 mb-1">Upload Time</p>
            <p className="text-sm font-medium">
              {new Date(document.created_at).toLocaleString()}
            </p>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 bg-slate-900/30 p-1.5 rounded-2xl border border-slate-800/50">
        {[
          { id: 'timeline', label: 'Processing Timeline', icon: Activity },
          { id: 'chunks', label: 'Chunks', icon: Layers },
          { id: 'insights', label: 'Insights', icon: Brain },
          { id: 'metadata', label: 'Metadata', icon: Tag }
        ].map(tab => {
          const Icon = tab.icon;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex-1 flex items-center justify-center gap-2 px-4 py-3 rounded-xl font-medium transition-all ${
                activeTab === tab.id
                  ? 'bg-gradient-to-r from-emerald-500 to-cyan-600 shadow-lg'
                  : 'hover:bg-slate-800/50 text-slate-400'
              }`}
            >
              <Icon className="w-4 h-4" />
              <span className="hidden md:inline">{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* Timeline Tab */}
      {activeTab === 'timeline' && (
        <div className="bg-slate-900/50 backdrop-blur-xl border border-slate-800/50 rounded-2xl p-6">
          <h3 className="text-xl font-bold mb-6 flex items-center gap-2">
            <Workflow className="w-6 h-6 text-emerald-400" />
            Processing Pipeline
          </h3>

          <div className="space-y-4">
            {timeline.map((stage, index) => {
              const StageIcon = getStageIcon(stage.stage);
              const isLast = index === timeline.length - 1;
              
              return (
                <div key={index} className="relative">
                  {!isLast && (
                    <div className="absolute left-6 top-12 bottom-0 w-0.5 bg-slate-700/50" />
                  )}
                  
                  <div className="flex gap-4">
                    <div className={`relative z-10 p-3 rounded-xl ${getStatusColor(stage.status)}`}>
                      <StageIcon className="w-6 h-6" />
                    </div>
                    
                    <div className="flex-1 bg-slate-800/30 rounded-xl p-4 border border-slate-700/30">
                      <div className="flex items-start justify-between mb-2">
                        <div>
                          <h4 className="font-bold text-lg capitalize">{stage.stage}</h4>
                          <p className="text-sm text-slate-400">
                            {new Date(stage.timestamp).toLocaleString()}
                          </p>
                        </div>
                        <div className="flex items-center gap-3">
                          {stage.duration_ms && (
                            <span className="px-3 py-1 bg-slate-700/50 rounded-lg text-sm font-medium">
                              {formatDuration(stage.duration_ms)}
                            </span>
                          )}
                          <span className={`px-3 py-1 rounded-lg text-sm font-medium ${getStatusColor(stage.status)}`}>
                            {stage.status}
                          </span>
                        </div>
                      </div>

                      {stage.metadata && Object.keys(stage.metadata).length > 0 && (
                        <div className="mt-3 pt-3 border-t border-slate-700/30">
                          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                            {Object.entries(stage.metadata).map(([key, value]) => (
                              <div key={key} className="text-sm">
                                <span className="text-slate-400">{key}: </span>
                                <span className="text-slate-200 font-medium">
                                  {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                                </span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {stage.error_details && (
                        <div className="mt-3 p-3 bg-red-500/10 border border-red-500/20 rounded-lg">
                          <p className="text-sm text-red-300">{stage.error_details}</p>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          {timeline.length === 0 && (
            <div className="text-center py-12">
              <Activity className="w-12 h-12 text-slate-600 mx-auto mb-4" />
              <p className="text-slate-400">No processing logs available</p>
            </div>
          )}
        </div>
      )}

      {/* Chunks Tab */}
      {activeTab === 'chunks' && (
        <div className="bg-slate-900/50 backdrop-blur-xl border border-slate-800/50 rounded-2xl p-6">
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-xl font-bold flex items-center gap-2">
              <Layers className="w-6 h-6 text-purple-400" />
              Document Chunks ({chunksPagination?.total || 0})
            </h3>
            
            {chunksPagination && chunksPagination.pages > 1 && (
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setChunksPage(p => Math.max(1, p - 1))}
                  disabled={chunksPage === 1}
                  className="px-3 py-1 bg-slate-800/50 hover:bg-slate-800 disabled:opacity-50 rounded-lg transition-all"
                >
                  Previous
                </button>
                <span className="text-sm text-slate-400">
                  Page {chunksPage} of {chunksPagination.pages}
                </span>
                <button
                  onClick={() => setChunksPage(p => Math.min(chunksPagination.pages, p + 1))}
                  disabled={chunksPage === chunksPagination.pages}
                  className="px-3 py-1 bg-slate-800/50 hover:bg-slate-800 disabled:opacity-50 rounded-lg transition-all"
                >
                  Next
                </button>
              </div>
            )}
          </div>

          <div className="space-y-3">
            {chunks.map((chunk, index) => {
              const isExpanded = expandedChunks.has(chunk.id);
              
              return (
                <div key={chunk.id} className="bg-slate-800/30 rounded-xl border border-slate-700/30 overflow-hidden">
                  <button
                    onClick={() => toggleChunk(chunk.id)}
                    className="w-full p-4 flex items-center justify-between hover:bg-slate-800/50 transition-all"
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 bg-purple-500/20 rounded-lg flex items-center justify-center text-sm font-bold text-purple-400">
                        {chunk.index}
                      </div>
                      <div className="text-left">
                        <p className="font-medium text-sm">Chunk {chunk.index}</p>
                        <p className="text-xs text-slate-400">
                          {chunk.token_count} tokens • {chunk.method}
                        </p>
                      </div>
                    </div>
                    
                    <div className="flex items-center gap-2">
                      {chunk.has_embedding && (
                        <span className="px-2 py-1 bg-emerald-500/20 border border-emerald-500/30 rounded text-xs text-emerald-400">
                          Indexed
                        </span>
                      )}
                      {isExpanded ? (
                        <ChevronDown className="w-5 h-5 text-slate-400" />
                      ) : (
                        <ChevronRight className="w-5 h-5 text-slate-400" />
                      )}
                    </div>
                  </button>

                  {isExpanded && (
                    <div className="p-4 border-t border-slate-700/30 bg-slate-900/30">
                      <div className="prose prose-invert prose-sm max-w-none">
                        <p className="text-sm text-slate-300 whitespace-pre-wrap leading-relaxed">
                          {chunk.full_content || chunk.preview}
                        </p>
                      </div>
                      
                      <div className="flex items-center gap-2 mt-4 pt-4 border-t border-slate-700/30">
                        <button
                          onClick={() => navigator.clipboard.writeText(chunk.full_content || chunk.preview)}
                          className="flex items-center gap-1 px-3 py-1 bg-slate-700/50 hover:bg-slate-700 rounded-lg text-xs transition-all"
                        >
                          <Copy className="w-3 h-3" />
                          Copy
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {chunks.length === 0 && (
            <div className="text-center py-12">
              <Layers className="w-12 h-12 text-slate-600 mx-auto mb-4" />
              <p className="text-slate-400">No chunks found</p>
            </div>
          )}
        </div>
      )}

      {/* Insights Tab */}
      {activeTab === 'insights' && (
        <div className="bg-slate-900/50 backdrop-blur-xl border border-slate-800/50 rounded-2xl p-6">
          <h3 className="text-xl font-bold mb-6 flex items-center gap-2">
            <Brain className="w-6 h-6 text-pink-400" />
            AI-Generated Insights
          </h3>

          {insights ? (
            <div className="space-y-6">
              {/* Summary */}
              <div className="bg-slate-800/30 rounded-xl p-5 border border-slate-700/30">
                <h4 className="font-bold mb-3 flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-pink-400" />
                  Summary
                </h4>
                <p className="text-slate-300 leading-relaxed">{insights.summary}</p>
              </div>

              {/* Topics */}
              {insights.topics && insights.topics.length > 0 && (
                <div className="bg-slate-800/30 rounded-xl p-5 border border-slate-700/30">
                  <h4 className="font-bold mb-3 flex items-center gap-2">
                    <Tag className="w-4 h-4 text-purple-400" />
                    Key Topics
                  </h4>
                  <div className="flex flex-wrap gap-2">
                    {insights.topics.map((topic, i) => (
                      <span key={i} className="px-3 py-1 bg-purple-500/20 border border-purple-500/30 rounded-lg text-sm text-purple-300">
                        {topic}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Keywords */}
              {insights.keywords && insights.keywords.length > 0 && (
                <div className="bg-slate-800/30 rounded-xl p-5 border border-slate-700/30">
                  <h4 className="font-bold mb-3 flex items-center gap-2">
                    <Hash className="w-4 h-4 text-cyan-400" />
                    Important Keywords
                  </h4>
                  <div className="flex flex-wrap gap-2">
                    {insights.keywords.map((keyword, i) => (
                      <span key={i} className="px-3 py-1 bg-cyan-500/20 border border-cyan-500/30 rounded-lg text-sm text-cyan-300">
                        {keyword}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="text-center py-12">
              <Loader2 className="w-12 h-12 animate-spin text-pink-400 mx-auto mb-4" />
              <p className="text-slate-400">Generating insights...</p>
            </div>
          )}
        </div>
      )}

      {/* Metadata Tab */}
      {activeTab === 'metadata' && (
        <div className="bg-slate-900/50 backdrop-blur-xl border border-slate-800/50 rounded-2xl p-6">
          <h3 className="text-xl font-bold mb-6 flex items-center gap-2">
            <Tag className="w-6 h-6 text-orange-400" />
            Document Metadata
          </h3>

          <div className="grid md:grid-cols-2 gap-4">
            <div className="bg-slate-800/30 rounded-xl p-4">
              <p className="text-xs text-slate-400 mb-1">Document ID</p>
              <p className="font-mono text-sm break-all">{document.id}</p>
            </div>
            <div className="bg-slate-800/30 rounded-xl p-4">
              <p className="text-xs text-slate-400 mb-1">MIME Type</p>
              <p className="font-medium">{document.mime_type}</p>
            </div>
            <div className="bg-slate-800/30 rounded-xl p-4">
              <p className="text-xs text-slate-400 mb-1">GCS URI</p>
              <p className="font-mono text-sm break-all">{document.gcs_uri}</p>
            </div>
            <div className="bg-slate-800/30 rounded-xl p-4">
              <p className="text-xs text-slate-400 mb-1">Created At</p>
              <p className="font-medium">{new Date(document.created_at).toLocaleString()}</p>
            </div>
            {document.updated_at && (
              <div className="bg-slate-800/30 rounded-xl p-4">
                <p className="text-xs text-slate-400 mb-1">Last Updated</p>
                <p className="font-medium">{new Date(document.updated_at).toLocaleString()}</p>
              </div>
            )}
            {document.metadata && Object.keys(document.metadata).length > 0 && (
              <div className="md:col-span-2 bg-slate-800/30 rounded-xl p-4">
                <p className="text-xs text-slate-400 mb-3">Additional Metadata</p>
                <pre className="text-xs bg-slate-900/50 p-3 rounded-lg overflow-auto max-h-60">
                  {JSON.stringify(document.metadata, null, 2)}
                </pre>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Live Updates Panel */}
      {liveUpdates.length > 0 && (
        <div className="bg-slate-900/50 backdrop-blur-xl border border-blue-500/20 rounded-2xl p-6">
          <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
            <Activity className="w-5 h-5 text-blue-400" />
            Live Updates
          </h3>
          <div className="space-y-2">
            {liveUpdates.map((update, index) => (
              <div key={index} className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">{update.status}</span>
                  <span className="text-xs text-slate-400">
                    {new Date(update.timestamp).toLocaleTimeString()}
                  </span>
                </div>
                {update.data && (
                  <p className="text-xs text-slate-400 mt-1">
                    {JSON.stringify(update.data)}
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default ProcessingDetail;