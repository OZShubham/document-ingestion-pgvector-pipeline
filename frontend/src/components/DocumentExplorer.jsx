import React, { useState, useEffect } from 'react';
import {
  Search, Filter, X, Download, Trash2, Tag, CheckSquare,
  Square, MoreVertical, Calendar, User, FileType, Layers,
  ChevronDown, SlidersHorizontal, FileText, Eye, GitCompare,
  Package, AlertCircle, Loader2, ArrowUpDown, RefreshCw
} from 'lucide-react';

const DocumentExplorer = ({ projectId, userId, apiClient, onViewDetails }) => {
  const [documents, setDocuments] = useState([]);
  const [filteredDocuments, setFilteredDocuments] = useState([]);
  const [loading, setLoading] = useState(false);
  const [selectedDocs, setSelectedDocs] = useState(new Set());
  const [showFilters, setShowFilters] = useState(false);
  const [filterOptions, setFilterOptions] = useState(null);
  const [sortBy, setSortBy] = useState('created_at');
  const [sortOrder, setSortOrder] = useState('desc');
  
  // Filter states
  const [filters, setFilters] = useState({
    status: [],
    processing_method: [],
    file_type: [],
    uploaded_by: [],
    from_date: null,
    to_date: null,
    min_size_mb: null,
    max_size_mb: null,
    search_text: ''
  });

  useEffect(() => {
    loadDocuments();
    loadFilterOptions();
  }, [projectId]);

  useEffect(() => {
    applyFiltersAndSort();
  }, [documents, filters, sortBy, sortOrder]);

  const loadDocuments = async () => {
    try {
      setLoading(true);
      const response = await apiClient.request(
        `/documents?project_id=${projectId}&user_id=${userId}`
      );
      setDocuments(response.documents || []);
    } catch (error) {
      console.error('Failed to load documents:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadFilterOptions = async () => {
    try {
      const options = await apiClient.request(
        `/documents/filter-options?project_id=${projectId}&user_id=${userId}`
      );
      setFilterOptions(options);
    } catch (error) {
      console.error('Failed to load filter options:', error);
    }
  };

  const applyFiltersAndSort = () => {
    let filtered = [...documents];

    // Apply filters
    if (filters.status.length > 0) {
      filtered = filtered.filter(doc => filters.status.includes(doc.status));
    }
    
    if (filters.processing_method.length > 0) {
      filtered = filtered.filter(doc => 
        filters.processing_method.includes(doc.processing_method)
      );
    }
    
    if (filters.file_type.length > 0) {
      filtered = filtered.filter(doc => filters.file_type.includes(doc.mime_type));
    }
    
    if (filters.uploaded_by.length > 0) {
      filtered = filtered.filter(doc => 
        filters.uploaded_by.includes(doc.uploaded_by)
      );
    }
    
    if (filters.search_text) {
      const search = filters.search_text.toLowerCase();
      filtered = filtered.filter(doc =>
        doc.filename.toLowerCase().includes(search) ||
        (doc.error_message && doc.error_message.toLowerCase().includes(search))
      );
    }

    // Apply sorting
    filtered.sort((a, b) => {
      let aVal = a[sortBy];
      let bVal = b[sortBy];
      
      if (sortBy === 'file_size' || sortBy === 'page_count') {
        aVal = aVal || 0;
        bVal = bVal || 0;
      }
      
      if (sortBy === 'created_at') {
        aVal = new Date(aVal);
        bVal = new Date(bVal);
      }
      
      if (sortOrder === 'asc') {
        return aVal > bVal ? 1 : -1;
      } else {
        return aVal < bVal ? 1 : -1;
      }
    });

    setFilteredDocuments(filtered);
  };

  const toggleFilter = (filterType, value) => {
    setFilters(prev => {
      const current = prev[filterType];
      const updated = current.includes(value)
        ? current.filter(v => v !== value)
        : [...current, value];
      return { ...prev, [filterType]: updated };
    });
  };

  const clearFilters = () => {
    setFilters({
      status: [],
      processing_method: [],
      file_type: [],
      uploaded_by: [],
      from_date: null,
      to_date: null,
      min_size_mb: null,
      max_size_mb: null,
      search_text: ''
    });
  };

  const toggleSelectDoc = (docId) => {
    setSelectedDocs(prev => {
      const newSet = new Set(prev);
      if (newSet.has(docId)) {
        newSet.delete(docId);
      } else {
        newSet.add(docId);
      }
      return newSet;
    });
  };

  const toggleSelectAll = () => {
    if (selectedDocs.size === filteredDocuments.length) {
      setSelectedDocs(new Set());
    } else {
      setSelectedDocs(new Set(filteredDocuments.map(d => d.id)));
    }
  };

  const handleBatchOperation = async (operation) => {
    if (selectedDocs.size === 0) return;

    const confirmed = window.confirm(
      `${operation} ${selectedDocs.size} document(s)?`
    );
    
    if (!confirmed) return;

    try {
      let params = {};
      
      if (operation === 'tag') {
        const tag = prompt('Enter tag name:');
        if (!tag) return;
        params = { tag };
      }

      const result = await apiClient.request(`/documents/batch?project_id=${projectId}`, {
        method: 'POST',
        body: JSON.stringify({
          operation,
          document_ids: Array.from(selectedDocs),
          user_id: userId,
          params
        })
      });

      alert(`Success: ${result.success}/${result.total}`);
      
      if (operation === 'delete') {
        loadDocuments();
      }
      
      if (operation === 'export' && result.export_data) {
        downloadJSON(result.export_data, 'documents-export.json');
      }

      setSelectedDocs(new Set());
    } catch (error) {
      alert(`Operation failed: ${error.message}`);
    }
  };

  const downloadJSON = (data, filename) => {
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  };

  const formatFileSize = (bytes) => {
    if (!bytes) return '0 B';
    const mb = bytes / (1024 * 1024);
    if (mb >= 1) return `${mb.toFixed(2)} MB`;
    const kb = bytes / 1024;
    return `${kb.toFixed(2)} KB`;
  };

  const getStatusBadge = (status) => {
    const styles = {
      completed: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
      processing: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
      failed: 'bg-red-500/20 text-red-400 border-red-500/30',
      pending: 'bg-slate-500/20 text-slate-400 border-slate-500/30'
    };
    return styles[status] || styles.pending;
  };

  return (
    <div className="space-y-6">
      {/* Header with Actions */}
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div className="flex items-center gap-3 flex-1 min-w-0">
          {/* Search */}
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <input
              type="text"
              value={filters.search_text}
              onChange={(e) => setFilters(prev => ({ ...prev, search_text: e.target.value }))}
              placeholder="Search documents..."
              className="w-full pl-10 pr-4 py-2 bg-slate-800/50 border border-slate-700/50 rounded-xl focus:outline-none focus:border-purple-500/50 transition-all"
            />
          </div>

          {/* Filter Button */}
          <button
            onClick={() => setShowFilters(!showFilters)}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl font-medium transition-all ${
              showFilters
                ? 'bg-purple-500/20 text-purple-400 border border-purple-500/30'
                : 'bg-slate-800/50 hover:bg-slate-800 border border-slate-700/50'
            }`}
          >
            <SlidersHorizontal className="w-4 h-4" />
            <span className="hidden sm:inline">Filters</span>
            {(filters.status.length > 0 || filters.processing_method.length > 0 || 
              filters.file_type.length > 0) && (
              <span className="px-2 py-0.5 bg-purple-500 rounded-full text-xs">
                {filters.status.length + filters.processing_method.length + filters.file_type.length}
              </span>
            )}
          </button>

          {/* Sort */}
          <div className="relative">
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              className="px-4 py-2 bg-slate-800/50 border border-slate-700/50 rounded-xl focus:outline-none appearance-none pr-10"
            >
              <option value="created_at">Date</option>
              <option value="filename">Name</option>
              <option value="file_size">Size</option>
              <option value="page_count">Pages</option>
              <option value="status">Status</option>
            </select>
            <ArrowUpDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
          </div>

          <button
            onClick={() => setSortOrder(prev => prev === 'asc' ? 'desc' : 'asc')}
            className="p-2 bg-slate-800/50 hover:bg-slate-800 border border-slate-700/50 rounded-xl transition-all"
            title={`Sort ${sortOrder === 'asc' ? 'Descending' : 'Ascending'}`}
          >
            {sortOrder === 'asc' ? '↑' : '↓'}
          </button>

          <button
            onClick={loadDocuments}
            className="p-2 bg-slate-800/50 hover:bg-slate-800 border border-slate-700/50 rounded-xl transition-all"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>

        {/* Batch Actions */}
        {selectedDocs.size > 0 && (
          <div className="flex items-center gap-2">
            <span className="text-sm text-slate-400">{selectedDocs.size} selected</span>
            <button
              onClick={() => handleBatchOperation('tag')}
              className="flex items-center gap-1 px-3 py-2 bg-cyan-500/20 hover:bg-cyan-500/30 border border-cyan-500/30 rounded-xl text-sm transition-all"
            >
              <Tag className="w-4 h-4" />
              Tag
            </button>
            <button
              onClick={() => handleBatchOperation('export')}
              className="flex items-center gap-1 px-3 py-2 bg-blue-500/20 hover:bg-blue-500/30 border border-blue-500/30 rounded-xl text-sm transition-all"
            >
              <Download className="w-4 h-4" />
              Export
            </button>
            <button
              onClick={() => handleBatchOperation('delete')}
              className="flex items-center gap-1 px-3 py-2 bg-red-500/20 hover:bg-red-500/30 border border-red-500/30 rounded-xl text-sm transition-all"
            >
              <Trash2 className="w-4 h-4" />
              Delete
            </button>
            <button
              onClick={() => setSelectedDocs(new Set())}
              className="p-2 hover:bg-slate-800 rounded-xl transition-all"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        )}
      </div>

      {/* Filters Panel */}
      {showFilters && filterOptions && (
        <div className="bg-slate-900/50 backdrop-blur-xl border border-slate-800/50 rounded-2xl p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-bold">Advanced Filters</h3>
            <button
              onClick={clearFilters}
              className="text-sm text-purple-400 hover:text-purple-300 transition-colors"
            >
              Clear All
            </button>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
            {/* Status Filter */}
            {filterOptions.statuses.length > 0 && (
              <div>
                <label className="text-sm font-medium mb-2 block">Status</label>
                <div className="space-y-2">
                  {filterOptions.statuses.map(status => (
                    <label key={status} className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={filters.status.includes(status)}
                        onChange={() => toggleFilter('status', status)}
                        className="rounded border-slate-600"
                      />
                      <span className="text-sm capitalize">{status}</span>
                    </label>
                  ))}
                </div>
              </div>
            )}

            {/* Processing Method Filter */}
            {filterOptions.processing_methods.length > 0 && (
              <div>
                <label className="text-sm font-medium mb-2 block">Processing Method</label>
                <div className="space-y-2">
                  {filterOptions.processing_methods.map(method => (
                    <label key={method} className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={filters.processing_method.includes(method)}
                        onChange={() => toggleFilter('processing_method', method)}
                        className="rounded border-slate-600"
                      />
                      <span className="text-sm">{method}</span>
                    </label>
                  ))}
                </div>
              </div>
            )}

            {/* File Type Filter */}
            {filterOptions.file_types.length > 0 && (
              <div>
                <label className="text-sm font-medium mb-2 block">File Type</label>
                <div className="space-y-2 max-h-40 overflow-y-auto">
                  {filterOptions.file_types.map(type => (
                    <label key={type} className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={filters.file_type.includes(type)}
                        onChange={() => toggleFilter('file_type', type)}
                        className="rounded border-slate-600"
                      />
                      <span className="text-sm truncate">{type}</span>
                    </label>
                  ))}
                </div>
              </div>
            )}

            {/* Uploader Filter */}
            {filterOptions.uploaders.length > 0 && (
              <div>
                <label className="text-sm font-medium mb-2 block">Uploaded By</label>
                <div className="space-y-2 max-h-40 overflow-y-auto">
                  {filterOptions.uploaders.map(uploader => (
                    <label key={uploader} className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={filters.uploaded_by.includes(uploader)}
                        onChange={() => toggleFilter('uploaded_by', uploader)}
                        className="rounded border-slate-600"
                      />
                      <span className="text-sm truncate">{uploader}</span>
                    </label>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Active Filters */}
      {(filters.status.length > 0 || filters.processing_method.length > 0 || 
        filters.file_type.length > 0 || filters.uploaded_by.length > 0) && (
        <div className="flex flex-wrap gap-2">
          {filters.status.map(status => (
            <span key={status} className="flex items-center gap-1 px-3 py-1 bg-purple-500/20 border border-purple-500/30 rounded-lg text-sm">
              Status: {status}
              <button onClick={() => toggleFilter('status', status)} className="ml-1 hover:text-purple-300">
                <X className="w-3 h-3" />
              </button>
            </span>
          ))}
          {filters.processing_method.map(method => (
            <span key={method} className="flex items-center gap-1 px-3 py-1 bg-cyan-500/20 border border-cyan-500/30 rounded-lg text-sm">
              Method: {method}
              <button onClick={() => toggleFilter('processing_method', method)} className="ml-1 hover:text-cyan-300">
                <X className="w-3 h-3" />
              </button>
            </span>
          ))}
          {filters.file_type.map(type => (
            <span key={type} className="flex items-center gap-1 px-3 py-1 bg-blue-500/20 border border-blue-500/30 rounded-lg text-sm">
              Type: {type.split('/')[1]}
              <button onClick={() => toggleFilter('file_type', type)} className="ml-1 hover:text-blue-300">
                <X className="w-3 h-3" />
              </button>
            </span>
          ))}
        </div>
      )}

      {/* Documents List */}
      <div className="bg-slate-900/50 backdrop-blur-xl border border-slate-800/50 rounded-2xl overflow-hidden">
        {/* Table Header */}
        <div className="bg-slate-800/30 border-b border-slate-700/50 px-4 py-3 flex items-center gap-4">
          <button
            onClick={toggleSelectAll}
            className="p-1 hover:bg-slate-700/50 rounded transition-all"
          >
            {selectedDocs.size === filteredDocuments.length && filteredDocuments.length > 0 ? (
              <CheckSquare className="w-5 h-5 text-purple-400" />
            ) : (
              <Square className="w-5 h-5 text-slate-400" />
            )}
          </button>
          <div className="flex-1 grid grid-cols-12 gap-4 text-sm font-medium text-slate-400">
            <div className="col-span-4">Document</div>
            <div className="col-span-2 hidden md:block">Size</div>
            <div className="col-span-2 hidden lg:block">Method</div>
            <div className="col-span-2 hidden xl:block">Uploaded</div>
            <div className="col-span-2">Status</div>
          </div>
          <div className="w-20 text-center text-sm font-medium text-slate-400">Actions</div>
        </div>

        {/* Documents */}
        <div className="divide-y divide-slate-700/50">
          {loading ? (
            <div className="py-12 text-center">
              <Loader2 className="w-8 h-8 animate-spin text-purple-400 mx-auto mb-3" />
              <p className="text-slate-400">Loading documents...</p>
            </div>
          ) : filteredDocuments.length === 0 ? (
            <div className="py-12 text-center">
              <FileText className="w-12 h-12 text-slate-600 mx-auto mb-3" />
              <p className="text-slate-400 mb-2">No documents found</p>
              <button
                onClick={clearFilters}
                className="text-sm text-purple-400 hover:text-purple-300"
              >
                Clear filters
              </button>
            </div>
          ) : (
            filteredDocuments.map(doc => (
              <div
                key={doc.id}
                className={`px-4 py-3 flex items-center gap-4 hover:bg-slate-800/30 transition-all ${
                  selectedDocs.has(doc.id) ? 'bg-purple-500/5' : ''
                }`}
              >
                {/* Checkbox */}
                <button
                  onClick={() => toggleSelectDoc(doc.id)}
                  className="p-1 hover:bg-slate-700/50 rounded transition-all"
                >
                  {selectedDocs.has(doc.id) ? (
                    <CheckSquare className="w-5 h-5 text-purple-400" />
                  ) : (
                    <Square className="w-5 h-5 text-slate-400" />
                  )}
                </button>

                {/* Document Info */}
                <div className="flex-1 grid grid-cols-12 gap-4 items-center min-w-0">
                  {/* Filename */}
                  <div className="col-span-4 flex items-center gap-3 min-w-0">
                    <div className="p-2 bg-purple-500/10 rounded-lg flex-shrink-0">
                      <FileText className="w-5 h-5 text-purple-400" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="font-medium truncate">{doc.filename}</p>
                      <div className="flex items-center gap-2 text-xs text-slate-400">
                        {doc.page_count && <span>{doc.page_count} pages</span>}
                        {doc.chunk_count > 0 && <span>• {doc.chunk_count} chunks</span>}
                      </div>
                    </div>
                  </div>

                  {/* Size */}
                  <div className="col-span-2 hidden md:block">
                    <p className="text-sm text-slate-300">{formatFileSize(doc.file_size)}</p>
                  </div>

                  {/* Method */}
                  <div className="col-span-2 hidden lg:block">
                    <span className="px-2 py-1 bg-slate-700/50 rounded text-xs font-medium">
                      {doc.processing_method}
                    </span>
                  </div>

                  {/* Uploaded */}
                  <div className="col-span-2 hidden xl:block">
                    <p className="text-xs text-slate-400 truncate">{doc.uploaded_by}</p>
                    <p className="text-xs text-slate-500">
                      {new Date(doc.created_at).toLocaleDateString()}
                    </p>
                  </div>

                  {/* Status */}
                  <div className="col-span-2">
                    <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-lg text-xs font-medium border ${getStatusBadge(doc.status)}`}>
                      {doc.status}
                    </span>
                  </div>
                </div>

                {/* Actions */}
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => onViewDetails(doc.id)}
                    className="p-2 hover:bg-slate-700/50 rounded-lg transition-all"
                    title="View Details"
                  >
                    <Eye className="w-4 h-4" />
                  </button>
                  <div className="relative group">
                    <button className="p-2 hover:bg-slate-700/50 rounded-lg transition-all">
                      <MoreVertical className="w-4 h-4" />
                    </button>
                    <div className="absolute right-0 top-full mt-1 bg-slate-800 border border-slate-700 rounded-xl shadow-xl opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all z-10 w-40">
                      <button
                        onClick={() => onViewDetails(doc.id)}
                        className="w-full px-4 py-2 text-left text-sm hover:bg-slate-700/50 first:rounded-t-xl transition-all flex items-center gap-2"
                      >
                        <Eye className="w-4 h-4" />
                        View Details
                      </button>
                      <button
                        onClick={() => {
                          setSelectedDocs(new Set([doc.id]));
                          handleBatchOperation('export');
                        }}
                        className="w-full px-4 py-2 text-left text-sm hover:bg-slate-700/50 transition-all flex items-center gap-2"
                      >
                        <Download className="w-4 h-4" />
                        Export
                      </button>
                      <button
                        onClick={() => {
                          if (window.confirm(`Delete ${doc.filename}?`)) {
                            setSelectedDocs(new Set([doc.id]));
                            handleBatchOperation('delete');
                          }
                        }}
                        className="w-full px-4 py-2 text-left text-sm hover:bg-slate-700/50 last:rounded-b-xl transition-all text-red-400 flex items-center gap-2"
                      >
                        <Trash2 className="w-4 h-4" />
                        Delete
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>

        {/* Footer */}
        {filteredDocuments.length > 0 && (
          <div className="bg-slate-800/30 border-t border-slate-700/50 px-4 py-3 text-sm text-slate-400">
            Showing {filteredDocuments.length} of {documents.length} documents
          </div>
        )}
      </div>
    </div>
  );
};

export default DocumentExplorer;