// import React, { useState, useEffect, useRef } from 'react';
// import { 
//   Upload, FileText, Search, CheckCircle, XCircle, Clock, 
//   AlertCircle, ChevronRight, Loader2, Database, Layers, 
//   Activity, Sparkles, GitBranch, 
//   Settings, Trash2, Eye, RefreshCw,
//   Users, Plus, FolderOpen, Zap, Brain,
//   BarChart2, UserPlus, X, LogOut
// } from 'lucide-react';

// // ============================================================================
// // CONFIGURATION
// // ============================================================================
// const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';
// const GCS_BUCKET = import.meta.env.VITE_GCS_BUCKET || 'your-bucket-name';

// // ============================================================================
// // API CLIENT
// // ============================================================================
// class ApiClient {
//   constructor(baseUrl) {
//     this.baseUrl = baseUrl;
//   }

//   async request(endpoint, options = {}) {
//     const url = `${this.baseUrl}${endpoint}`;
    
//     const config = {
//       headers: {
//         'Content-Type': 'application/json',
//         ...options.headers,
//       },
//       ...options,
//     };

//     try {
//       const response = await fetch(url, config);
      
//       if (!response.ok) {
//         const error = await response.json().catch(() => ({ error: 'Request failed' }));
//         throw new Error(error.error || error.detail || `HTTP error! status: ${response.status}`);
//       }
      
//       return await response.json();
//     } catch (error) {
//       console.error('API request failed:', error);
//       throw error;
//     }
//   }

//   async getProjects(userId) {
//     return this.request(`/projects?user_id=${userId}`);
//   }

//   async createProject(data) {
//     return this.request('/projects', {
//       method: 'POST',
//       body: JSON.stringify(data),
//     });
//   }

//   async deleteProject(projectId, userId) {
//     return this.request(`/projects/${projectId}?user_id=${userId}`, {
//       method: 'DELETE',
//     });
//   }

//   async getDocuments(projectId, userId) {
//     return this.request(`/documents?project_id=${projectId}&user_id=${userId}`);
//   }

//   async getDocumentDetails(documentId, projectId, userId) {
//     return this.request(`/documents/${documentId}?project_id=${projectId}&user_id=${userId}`);
//   }

//   async deleteDocument(documentId, projectId, userId) {
//     return this.request(`/documents/${documentId}?project_id=${projectId}&user_id=${userId}`, {
//       method: 'DELETE',
//     });
//   }

//   async getSignedUrl(filename, projectId, userId, contentType) {
//     return this.request('/upload/signed-url', {
//       method: 'POST',
//       body: JSON.stringify({ 
//         filename, 
//         project_id: projectId, 
//         user_id: userId,
//         content_type: contentType 
//       }),
//     });
//   }

//   async uploadToGCS(signedUrl, file, onProgress) {
//     return new Promise((resolve, reject) => {
//       const xhr = new XMLHttpRequest();
      
//       if (onProgress) {
//         xhr.upload.addEventListener('progress', (e) => {
//           if (e.lengthComputable) {
//             const progress = Math.round((e.loaded / e.total) * 100);
//             onProgress(progress);
//           }
//         });
//       }

//       xhr.addEventListener('load', () => {
//         if (xhr.status === 200) {
//           resolve(xhr.response);
//         } else {
//           reject(new Error(`Upload failed: ${xhr.status}`));
//         }
//       });

//       xhr.addEventListener('error', () => {
//         reject(new Error('Upload failed'));
//       });

//       xhr.open('PUT', signedUrl);
//       xhr.setRequestHeader('Content-Type', file.type);
//       xhr.send(file);
//     });
//   }

//   async searchDocuments(query, projectId, userId, k = 10) {
//     return this.request('/search', {
//       method: 'POST',
//       body: JSON.stringify({ 
//         query, 
//         project_id: projectId, 
//         user_id: userId,
//         k 
//       }),
//     });
//   }

//   async getProjectMembers(projectId, userId) {
//     return this.request(`/projects/${projectId}/members?user_id=${userId}`);
//   }

//   async inviteMember(projectId, email, role, userId) {
//     return this.request(`/projects/${projectId}/members`, {
//       method: 'POST',
//       body: JSON.stringify({ email, role, user_id: userId }),
//     });
//   }

//   async removeMember(projectId, memberUserId, userId) {
//     return this.request(`/projects/${projectId}/members/${memberUserId}?user_id=${userId}`, {
//       method: 'DELETE',
//     });
//   }

//   async getProjectAnalytics(projectId, userId) {
//     return this.request(`/projects/${projectId}/analytics?user_id=${userId}`);
//   }
// }

// const apiClient = new ApiClient(API_BASE_URL);

// // ============================================================================
// // MAIN APP COMPONENT
// // ============================================================================
// const App = () => {
//   const [user] = useState({ 
//     id: 'user-123', 
//     email: 'user@example.com', 
//     name: 'John Doe' 
//   });

//   const [projects, setProjects] = useState([]);
//   const [selectedProject, setSelectedProject] = useState(null);
//   const [documents, setDocuments] = useState([]);
//   const [projectMembers, setProjectMembers] = useState([]);
//   const [uploadQueue, setUploadQueue] = useState([]);
//   const [isUploading, setIsUploading] = useState(false);
//   const [searchQuery, setSearchQuery] = useState('');
//   const [searchResults, setSearchResults] = useState([]);
//   const [isSearching, setIsSearching] = useState(false);
//   const [activeView, setActiveView] = useState('projects');
//   const [selectedDoc, setSelectedDoc] = useState(null);
//   const [showCreateProject, setShowCreateProject] = useState(false);
//   const [showInviteModal, setShowInviteModal] = useState(false);
//   const [showDocModal, setShowDocModal] = useState(false);
//   const [notifications, setNotifications] = useState([]);
//   const fileInputRef = useRef(null);
//   const [realTimeUpdates, setRealTimeUpdates] = useState([]);
//   const [currentTab, setCurrentTab] = useState('upload');
//   const [analytics, setAnalytics] = useState(null);
//   const [isLoadingProjects, setIsLoadingProjects] = useState(false);

//   useEffect(() => {
//     loadProjects();
//   }, []);

//   useEffect(() => {
//     if (selectedProject) {
//       loadDocuments();
//       loadProjectMembers();
//       loadAnalytics();
      
//       const interval = setInterval(() => {
//         loadDocuments();
//       }, 5000);
      
//       return () => clearInterval(interval);
//     }
//   }, [selectedProject]);

//   // ============================================================================
//   // API FUNCTIONS
//   // ============================================================================

//   const loadProjects = async () => {
//     setIsLoadingProjects(true);
//     try {
//       const response = await apiClient.getProjects(user.id);
//       setProjects(response.projects || []);
//     } catch (error) {
//       addNotification('error', 'Failed to load projects');
//       console.error('Load projects error:', error);
//     } finally {
//       setIsLoadingProjects(false);
//     }
//   };

//   const loadDocuments = async () => {
//     if (!selectedProject) return;
    
//     try {
//       const response = await apiClient.getDocuments(selectedProject, user.id);
//       setDocuments(response.documents || []);
      
//       const processing = response.documents?.filter(d => d.status === 'processing') || [];
//       if (processing.length > 0) {
//         processing.forEach(doc => {
//           const exists = realTimeUpdates.some(u => u.docId === doc.id);
//           if (!exists) {
//             setRealTimeUpdates(prev => [{
//               id: Date.now() + Math.random(),
//               docId: doc.id,
//               message: `Processing "${doc.filename}"`,
//               timestamp: new Date().toISOString(),
//               type: 'processing'
//             }, ...prev.slice(0, 9)]);
//           }
//         });
//       }
//     } catch (error) {
//       addNotification('error', 'Failed to load documents');
//       console.error('Load documents error:', error);
//     }
//   };

//   const loadProjectMembers = async () => {
//     if (!selectedProject) return;
    
//     try {
//       const response = await apiClient.getProjectMembers(selectedProject, user.id);
//       setProjectMembers(response.members || []);
//     } catch (error) {
//       console.error('Failed to load members', error);
//     }
//   };

//   const loadAnalytics = async () => {
//     if (!selectedProject) return;
    
//     try {
//       const response = await apiClient.getProjectAnalytics(selectedProject, user.id);
//       setAnalytics(response);
//     } catch (error) {
//       console.error('Failed to load analytics', error);
//     }
//   };

//   const createProject = async (name, description) => {
//     try {
//       const newProject = await apiClient.createProject({
//         name,
//         description,
//         user_id: user.id,
//         user_email: user.email
//       });
      
//       setProjects(prev => [newProject, ...prev]);
//       setSelectedProject(newProject.id);
//       setActiveView('pipeline');
//       setShowCreateProject(false);
//       addNotification('success', `Project "${name}" created successfully`);
//     } catch (error) {
//       addNotification('error', 'Failed to create project');
//       console.error('Create project error:', error);
//     }
//   };

//   const deleteProject = async (projectId) => {
//     if (!window.confirm('Are you sure you want to delete this project?')) return;
    
//     try {
//       await apiClient.deleteProject(projectId, user.id);
//       setProjects(prev => prev.filter(p => p.id !== projectId));
//       if (selectedProject === projectId) {
//         setSelectedProject(null);
//         setActiveView('projects');
//       }
//       addNotification('success', 'Project deleted successfully');
//     } catch (error) {
//       addNotification('error', 'Failed to delete project');
//       console.error('Delete project error:', error);
//     }
//   };

//   const handleFileSelect = (files) => {
//     if (!selectedProject) {
//       addNotification('error', 'Please select a project first');
//       return;
//     }
    
//     const newFiles = Array.from(files).map(file => ({
//       id: Math.random().toString(36).substr(2, 9),
//       file,
//       status: 'queued',
//       progress: 0,
//       uploadedBy: user.email
//     }));
//     setUploadQueue(prev => [...prev, ...newFiles]);
//     addNotification('info', `${files.length} file(s) added to queue`);
//   };

//   const uploadToGCS = async (fileItem) => {
//     try {
//       setUploadQueue(prev => prev.map(f => 
//         f.id === fileItem.id ? { ...f, status: 'uploading', progress: 0 } : f
//       ));

//       const { signed_url, gcs_uri } = await apiClient.getSignedUrl(
//         fileItem.file.name,
//         selectedProject,
//         user.id,
//         fileItem.file.type
//       );

//       await apiClient.uploadToGCS(signed_url, fileItem.file, (progress) => {
//         setUploadQueue(prev => prev.map(f => 
//           f.id === fileItem.id ? { ...f, progress } : f
//         ));
//       });

//       setUploadQueue(prev => prev.map(f => 
//         f.id === fileItem.id ? { ...f, status: 'processing', progress: 100 } : f
//       ));

//       addNotification('success', `${fileItem.file.name} uploaded - Cloud Function triggered`);
      
//       setRealTimeUpdates(prev => [{
//         id: Date.now(),
//         message: `Processing "${fileItem.file.name}" via Cloud Function`,
//         timestamp: new Date().toISOString(),
//         type: 'processing'
//       }, ...prev.slice(0, 9)]);

//       setTimeout(() => {
//         setUploadQueue(prev => prev.filter(f => f.id !== fileItem.id));
//         loadDocuments();
//       }, 3000);

//     } catch (error) {
//       console.error('Upload error:', error);
//       setUploadQueue(prev => prev.map(f => 
//         f.id === fileItem.id ? { ...f, status: 'failed', progress: 0, error: error.message } : f
//       ));
//       addNotification('error', `Failed to upload ${fileItem.file.name}: ${error.message}`);
//     }
//   };

//   const startUpload = async () => {
//     if (!selectedProject) {
//       addNotification('error', 'Please select a project first');
//       return;
//     }

//     setIsUploading(true);
//     const queued = uploadQueue.filter(f => f.status === 'queued');
    
//     for (const fileItem of queued) {
//       await uploadToGCS(fileItem);
//     }
    
//     setIsUploading(false);
//   };

//   const handleSearch = async () => {
//     if (!searchQuery.trim()) {
//       addNotification('error', 'Please enter a search query');
//       return;
//     }
    
//     if (!selectedProject) {
//       addNotification('error', 'Please select a project first');
//       return;
//     }

//     setIsSearching(true);

//     try {
//       const response = await apiClient.searchDocuments(
//         searchQuery,
//         selectedProject,
//         user.id,
//         10
//       );
      
//       setSearchResults(response.results || []);
      
//       if (response.results && response.results.length === 0) {
//         addNotification('info', 'No results found');
//       } else {
//         addNotification('success', `Found ${response.results.length} results`);
//       }
//     } catch (error) {
//       addNotification('error', 'Search failed');
//       console.error('Search error:', error);
//     } finally {
//       setIsSearching(false);
//     }
//   };

//   const deleteDocument = async (docId) => {
//     if (!window.confirm('Are you sure you want to delete this document?')) return;
    
//     try {
//       await apiClient.deleteDocument(docId, selectedProject, user.id);
//       setDocuments(prev => prev.filter(d => d.id !== docId));
//       addNotification('success', 'Document deleted successfully');
//     } catch (error) {
//       addNotification('error', 'Failed to delete document');
//       console.error('Delete document error:', error);
//     }
//   };

//   const viewDocumentDetails = async (docId) => {
//     try {
//       const details = await apiClient.getDocumentDetails(docId, selectedProject, user.id);
//       setSelectedDoc(details);
//       setShowDocModal(true);
//     } catch (error) {
//       addNotification('error', 'Failed to load document details');
//       console.error('Document details error:', error);
//     }
//   };

//   const inviteMember = async (email, role = 'member') => {
//     try {
//       await apiClient.inviteMember(selectedProject, email, role, user.id);
//       addNotification('success', `Invitation sent to ${email}`);
//       setShowInviteModal(false);
//       loadProjectMembers();
//     } catch (error) {
//       addNotification('error', 'Failed to invite member');
//       console.error('Invite member error:', error);
//     }
//   };

//   // ============================================================================
//   // UTILITY FUNCTIONS
//   // ============================================================================

//   const addNotification = (type, message) => {
//     const id = Date.now();
//     setNotifications(prev => [...prev, { id, type, message }]);
//     setTimeout(() => {
//       setNotifications(prev => prev.filter(n => n.id !== id));
//     }, 5000);
//   };

//   const formatBytes = (bytes) => {
//     if (!bytes) return '0 B';
//     const k = 1024;
//     const sizes = ['B', 'KB', 'MB', 'GB'];
//     const i = Math.floor(Math.log(bytes) / Math.log(k));
//     return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
//   };

//   const formatTime = (ms) => {
//     if (!ms) return 'N/A';
//     if (ms < 1000) return `${ms}ms`;
//     return `${(ms / 1000).toFixed(1)}s`;
//   };

//   const getStatusConfig = (status) => {
//     const configs = {
//       completed: { icon: CheckCircle, color: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20', label: 'Completed' },
//       processing: { icon: Loader2, color: 'text-blue-400 bg-blue-500/10 border-blue-500/20', label: 'Processing', spin: true },
//       failed: { icon: XCircle, color: 'text-red-400 bg-red-500/10 border-red-500/20', label: 'Failed' },
//       uploading: { icon: Upload, color: 'text-purple-400 bg-purple-500/10 border-purple-500/20', label: 'Uploading' },
//       queued: { icon: Clock, color: 'text-slate-400 bg-slate-500/10 border-slate-500/20', label: 'Queued' }
//     };
//     return configs[status] || configs.queued;
//   };

//   const StatusBadge = ({ status }) => {
//     const config = getStatusConfig(status);
//     const Icon = config.icon;
//     return (
//       <div className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg border ${config.color}`}>
//         <Icon className={`w-3.5 h-3.5 ${config.spin ? 'animate-spin' : ''}`} />
//         <span className="text-xs font-medium">{config.label}</span>
//       </div>
//     );
//   };

//   // ============================================================================
//   // RENDER
//   // ============================================================================

//   return (
//     <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 text-white">
//       {/* Background Effects */}
//       <div className="fixed inset-0 overflow-hidden pointer-events-none">
//         <div className="absolute top-1/4 -left-48 w-96 h-96 bg-blue-500/5 rounded-full blur-3xl animate-pulse" />
//         <div className="absolute bottom-1/4 -right-48 w-96 h-96 bg-purple-500/5 rounded-full blur-3xl animate-pulse" style={{ animationDelay: '1s' }} />
//       </div>

//       {/* Notifications */}
//       <div className="fixed top-4 right-4 z-50 space-y-2 max-w-md">
//         {notifications.map(n => (
//           <div key={n.id} className="bg-slate-900/95 backdrop-blur-xl border border-slate-700/50 rounded-xl px-4 py-3 shadow-2xl animate-slide-in">
//             <div className="flex items-center gap-3">
//               {n.type === 'success' ? <CheckCircle className="w-5 h-5 text-emerald-400" /> : 
//                n.type === 'error' ? <XCircle className="w-5 h-5 text-red-400" /> : 
//                <AlertCircle className="w-5 h-5 text-blue-400" />}
//               <span className="text-sm">{n.message}</span>
//             </div>
//           </div>
//         ))}
//       </div>

//       {/* Header */}
//       <header className="relative border-b border-slate-800/50 bg-slate-900/30 backdrop-blur-xl sticky top-0 z-40">
//         <div className="max-w-7xl mx-auto px-6 py-4">
//           <div className="flex items-center justify-between">
//             <div className="flex items-center gap-4">
//               <div className="relative">
//                 <div className="absolute inset-0 bg-gradient-to-r from-blue-500 to-purple-600 rounded-2xl blur-lg opacity-50" />
//                 <div className="relative bg-gradient-to-br from-blue-500 via-purple-500 to-pink-500 p-3 rounded-2xl">
//                   <Database className="w-7 h-7" />
//                 </div>
//               </div>
//               <div>
//                 <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-400 via-purple-400 to-pink-400 bg-clip-text text-transparent">
//                   DocuMind AI
//                 </h1>
//                 <p className="text-xs text-slate-400">Collaborative Document Pipeline</p>
//               </div>
//             </div>
            
//             <div className="flex items-center gap-3">
//               <div className="hidden md:flex items-center gap-2 px-3 py-2 bg-slate-800/50 rounded-lg">
//                 <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-500 rounded-full flex items-center justify-center text-sm font-bold">
//                   {user.name.charAt(0)}
//                 </div>
//                 <span className="text-sm">{user.name}</span>
//               </div>
//               <button className="p-2 hover:bg-slate-800/50 rounded-lg transition-all">
//                 <Settings className="w-5 h-5" />
//               </button>
//             </div>
//           </div>
//         </div>
//       </header>

//       <div className="max-w-7xl mx-auto px-6 py-8 relative">
//         {/* Projects View */}
//         {activeView === 'projects' && (
//           <div className="space-y-6">
//             <div className="flex items-center justify-between mb-6">
//               <div>
//                 <h2 className="text-3xl font-bold mb-2">Your Projects</h2>
//                 <p className="text-slate-400">Create projects and collaborate with your team</p>
//               </div>
//               <button
//                 onClick={() => setShowCreateProject(true)}
//                 className="flex items-center gap-2 bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 px-6 py-3 rounded-xl font-medium transition-all duration-300 shadow-lg shadow-blue-500/25"
//               >
//                 <Plus className="w-5 h-5" />
//                 New Project
//               </button>
//             </div>

//             {isLoadingProjects ? (
//               <div className="flex flex-col items-center justify-center py-20">
//                 <Loader2 className="w-12 h-12 animate-spin text-blue-400 mb-4" />
//                 <p className="text-slate-400">Loading projects...</p>
//               </div>
//             ) : projects.length > 0 ? (
//               <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
//                 {projects.map(project => (
//                   <div
//                     key={project.id}
//                     onClick={() => {
//                       setSelectedProject(project.id);
//                       setActiveView('pipeline');
//                     }}
//                     className="group cursor-pointer bg-slate-900/50 backdrop-blur-xl border border-slate-800/50 hover:border-slate-700 rounded-2xl p-6 transition-all duration-300 hover:shadow-xl hover:shadow-blue-500/10 hover:scale-[1.02]"
//                   >
//                     <div className="flex items-start justify-between mb-4">
//                       <div className="p-3 bg-gradient-to-br from-blue-500/20 to-purple-500/20 rounded-xl group-hover:scale-110 transition-transform">
//                         <FolderOpen className="w-6 h-6 text-blue-400" />
//                       </div>
//                       <div className="flex items-center gap-2 text-slate-400">
//                         <Users className="w-4 h-4" />
//                         <span className="text-sm">{project.members_count}</span>
//                       </div>
//                     </div>

//                     <h3 className="text-xl font-bold mb-2">{project.name}</h3>
//                     <p className="text-sm text-slate-400 mb-4 line-clamp-2">{project.description || 'No description'}</p>

//                     <div className="grid grid-cols-2 gap-4 pt-4 border-t border-slate-800/50">
//                       <div>
//                         <p className="text-xs text-slate-500 mb-1">Documents</p>
//                         <p className="text-lg font-bold">{project.doc_count || 0}</p>
//                       </div>
//                       <div>
//                         <p className="text-xs text-slate-500 mb-1">Storage</p>
//                         <p className="text-lg font-bold">{project.storage_used || 0} GB</p>
//                       </div>
//                     </div>
//                   </div>
//                 ))}
//               </div>
//             ) : (
//               <div className="text-center py-20">
//                 <div className="inline-flex p-6 bg-slate-800/30 rounded-3xl mb-6">
//                   <FolderOpen className="w-16 h-16 text-slate-600" />
//                 </div>
//                 <h3 className="text-2xl font-bold mb-3">No projects yet</h3>
//                 <p className="text-slate-400 mb-6">Create your first project to get started with document processing</p>
//                 <button
//                   onClick={() => setShowCreateProject(true)}
//                   className="inline-flex items-center gap-2 bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 px-6 py-3 rounded-xl font-medium transition-all shadow-lg"
//                 >
//                   <Plus className="w-5 h-5" />
//                   Create First Project
//                 </button>
//               </div>
//             )}
//           </div>
//         )}

//         {/* Pipeline View */}
//         {activeView === 'pipeline' && selectedProject && (
//           <div className="space-y-6">
//             <button
//               onClick={() => setActiveView('projects')}
//               className="flex items-center gap-2 text-slate-400 hover:text-white transition-colors mb-4"
//             >
//               <ChevronRight className="w-4 h-4 rotate-180" />
//               Back to Projects
//             </button>

//             {/* Project Header */}
//             <div className="bg-slate-900/50 backdrop-blur-xl border border-slate-800/50 rounded-2xl p-6">
//               <div className="flex items-center justify-between mb-4">
//                 <div>
//                   <h2 className="text-2xl font-bold mb-2">
//                     {projects.find(p => p.id === selectedProject)?.name}
//                   </h2>
//                   <p className="text-slate-400 text-sm">
//                     {projects.find(p => p.id === selectedProject)?.description || 'No description'}
//                   </p>
//                 </div>
//                 <div className="flex gap-2">
//                   <button
//                     onClick={() => setShowInviteModal(true)}
//                     className="flex items-center gap-2 px-4 py-2 bg-slate-800/50 hover:bg-slate-800 border border-slate-700/50 rounded-xl transition-all"
//                   >
//                     <UserPlus className="w-4 h-4" />
//                     Invite
//                   </button>
//                   <button
//                     onClick={() => loadDocuments()}
//                     className="flex items-center gap-2 px-4 py-2 bg-slate-800/50 hover:bg-slate-800 border border-slate-700/50 rounded-xl transition-all"
//                   >
//                     <RefreshCw className="w-4 h-4" />
//                   </button>
//                 </div>
//               </div>

//               {/* Analytics Cards */}
//               {analytics && (
//                 <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-4">
//                   <div className="bg-slate-800/30 rounded-xl p-4">
//                     <p className="text-xs text-slate-400 mb-1">Total Docs</p>
//                     <p className="text-2xl font-bold">{analytics.total_documents}</p>
//                   </div>
//                   <div className="bg-slate-800/30 rounded-xl p-4">
//                     <p className="text-xs text-slate-400 mb-1">Completed</p>
//                     <p className="text-2xl font-bold text-emerald-400">{analytics.completed_documents}</p>
//                   </div>
//                   <div className="bg-slate-800/30 rounded-xl p-4">
//                     <p className="text-xs text-slate-400 mb-1">Processing</p>
//                     <p className="text-2xl font-bold text-blue-400">{analytics.processing_documents}</p>
//                   </div>
//                   <div className="bg-slate-800/30 rounded-xl p-4">
//                     <p className="text-xs text-slate-400 mb-1">Storage</p>
//                     <p className="text-2xl font-bold">{analytics.total_storage_gb} GB</p>
//                   </div>
//                 </div>
//               )}

//               {/* Team Members */}
//               {projectMembers.length > 0 && (
//                 <div className="flex items-center gap-2 mt-4 pt-4 border-t border-slate-800/50">
//                   <span className="text-sm text-slate-400">Team:</span>
//                   <div className="flex -space-x-2">
//                     {projectMembers.slice(0, 5).map((member, i) => (
//                       <div
//                         key={i}
//                         className="w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-500 rounded-full flex items-center justify-center text-xs font-bold border-2 border-slate-900"
//                         title={member.email}
//                       >
//                         {member.email.charAt(0).toUpperCase()}
//                       </div>
//                     ))}
//                     {projectMembers.length > 5 && (
//                       <div className="w-8 h-8 bg-slate-800 rounded-full flex items-center justify-center text-xs border-2 border-slate-900">
//                         +{projectMembers.length - 5}
//                       </div>
//                     )}
//                   </div>
//                 </div>
//               )}
//             </div>

//             {/* Navigation Tabs */}
//             <div className="flex gap-2 bg-slate-900/30 p-1.5 rounded-2xl border border-slate-800/50">
//               {[
//                 { id: 'upload', label: 'Upload', icon: Upload },
//                 { id: 'documents', label: 'Documents', icon: FileText },
//                 { id: 'search', label: 'Search', icon: Search }
//               ].map(tab => (
//                 <button
//                   key={tab.id}
//                   onClick={() => setCurrentTab(tab.id)}
//                   className={`flex-1 flex items-center justify-center gap-2 px-6 py-3 rounded-xl font-medium transition-all ${
//                     currentTab === tab.id
//                       ? 'bg-gradient-to-r from-blue-500 to-purple-600 shadow-lg'
//                       : 'hover:bg-slate-800/50 text-slate-400'
//                   }`}
//                 >
//                   <tab.icon className="w-4 h-4" />
//                   {tab.label}
//                 </button>
//               ))}
//             </div>

//             {/* Upload Tab */}
//             {currentTab === 'upload' && (
//               <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
//                 <div className="lg:col-span-2">
//                   <div className="relative group">
//                     <div className="absolute inset-0 bg-gradient-to-r from-blue-500/20 to-purple-500/20 rounded-3xl blur-2xl opacity-0 group-hover:opacity-100 transition-opacity" />
//                     <div className="relative bg-slate-900/50 backdrop-blur-xl border-2 border-dashed border-slate-700/50 hover:border-blue-500/50 rounded-3xl p-12 transition-all">
//                       <input
//                         ref={fileInputRef}
//                         type="file"
//                         multiple
//                         onChange={(e) => handleFileSelect(e.target.files)}
//                         className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
//                         accept=".pdf,.docx,.doc,.xlsx,.xls,.txt,.md,.jpg,.jpeg,.png,.webp"
//                       />
                      
//                       <div className="text-center">
//                         <div className="inline-flex p-6 bg-gradient-to-r from-blue-500/20 to-purple-500/20 rounded-3xl mb-6">
//                           <Upload className="w-16 h-16 text-blue-400" />
//                         </div>
//                         <h3 className="text-2xl font-bold mb-3">Upload Documents</h3>
//                         <p className="text-slate-400 mb-4">Drop files here or click to browse</p>
//                         <div className="flex flex-wrap justify-center gap-2 text-xs text-slate-500">
//                           <span className="px-2 py-1 bg-slate-800/50 rounded">PDF</span>
//                           <span className="px-2 py-1 bg-slate-800/50 rounded">DOCX</span>
//                           <span className="px-2 py-1 bg-slate-800/50 rounded">XLSX</span>
//                           <span className="px-2 py-1 bg-slate-800/50 rounded">Images</span>
//                         </div>
//                       </div>
//                     </div>
//                   </div>

//                   {/* Upload Queue */}
//                   {uploadQueue.length > 0 && (
//                     <div className="mt-6 bg-slate-900/50 backdrop-blur-xl border border-slate-800/50 rounded-2xl p-6">
//                       <div className="flex items-center justify-between mb-4">
//                         <h3 className="font-bold">Upload Queue ({uploadQueue.length})</h3>
//                         <button
//                           onClick={startUpload}
//                           disabled={isUploading || uploadQueue.filter(f => f.status === 'queued').length === 0}
//                           className="flex items-center gap-2 bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 disabled:opacity-50 disabled:cursor-not-allowed px-4 py-2 rounded-xl font-medium transition-all"
//                         >
//                           {isUploading ? (
//                             <>
//                               <Loader2 className="w-4 h-4 animate-spin" />
//                               Uploading...
//                             </>
//                           ) : (
//                             <>
//                               <Upload className="w-4 h-4" />
//                               Start Upload
//                             </>
//                           )}
//                         </button>
//                       </div>

//                       <div className="space-y-3">
//                         {uploadQueue.map(file => (
//                           <div key={file.id} className="bg-slate-800/30 rounded-xl p-4">
//                             <div className="flex items-center justify-between mb-2">
//                               <div className="flex items-center gap-3">
//                                 <FileText className="w-5 h-5 text-blue-400" />
//                                 <div>
//                                   <p className="font-medium text-sm">{file.file.name}</p>
//                                   <p className="text-xs text-slate-400">{formatBytes(file.file.size)}</p>
//                                 </div>
//                               </div>
//                               <StatusBadge status={file.status} />
//                             </div>
//                             {(file.status === 'uploading' || file.status === 'processing') && (
//                               <div className="mt-2">
//                                 <div className="w-full bg-slate-700/30 rounded-full h-2">
//                                   <div 
//                                     className="bg-gradient-to-r from-blue-500 to-purple-600 h-2 rounded-full transition-all duration-300"
//                                     style={{ width: `${file.progress}%` }}
//                                   />
//                                 </div>
//                                 <p className="text-xs text-slate-400 mt-1">{file.progress}%</p>
//                               </div>
//                             )}
//                             {file.status === 'failed' && file.error && (
//                               <p className="text-xs text-red-400 mt-2">{file.error}</p>
//                             )}
//                           </div>
//                         ))}
//                       </div>
//                     </div>
//                   )}
//                 </div>

//                 {/* Real-time Updates */}
//                 <div className="lg:col-span-1">
//                   <div className="bg-slate-900/50 backdrop-blur-xl border border-slate-800/50 rounded-2xl p-6 sticky top-24">
//                     <div className="flex items-center gap-2 mb-4">
//                       <Activity className="w-5 h-5 text-blue-400" />
//                       <h3 className="font-bold">Activity Feed</h3>
//                     </div>

//                     <div className="space-y-3 max-h-96 overflow-y-auto">
//                       {realTimeUpdates.length > 0 ? (
//                         realTimeUpdates.map(update => (
//                           <div key={update.id} className="bg-slate-800/30 rounded-xl p-3">
//                             <div className="flex items-start gap-2">
//                               <Sparkles className="w-4 h-4 text-purple-400 mt-0.5" />
//                               <div>
//                                 <p className="text-sm">{update.message}</p>
//                                 <p className="text-xs text-slate-500 mt-1">
//                                   {new Date(update.timestamp).toLocaleTimeString()}
//                                 </p>
//                               </div>
//                             </div>
//                           </div>
//                         ))
//                       ) : (
//                         <div className="text-center py-8 text-slate-500">
//                           <Activity className="w-8 h-8 mx-auto mb-2 opacity-50" />
//                           <p className="text-sm">No recent activity</p>
//                         </div>
//                       )}
//                     </div>
//                   </div>
//                 </div>
//               </div>
//             )}

//             {/* Documents Tab */}
//             {currentTab === 'documents' && (
//               <div className="bg-slate-900/50 backdrop-blur-xl border border-slate-800/50 rounded-2xl p-6">
//                 <div className="flex items-center justify-between mb-6">
//                   <h3 className="text-xl font-bold">Documents ({documents.length})</h3>
//                   <button
//                     onClick={() => loadDocuments()}
//                     className="flex items-center gap-2 px-4 py-2 bg-slate-800/50 hover:bg-slate-800 border border-slate-700/50 rounded-xl transition-all"
//                   >
//                     <RefreshCw className="w-4 h-4" />
//                     Refresh
//                   </button>
//                 </div>

//                 {documents.length > 0 ? (
//                   <div className="space-y-3">
//                     {documents.map(doc => (
//                       <div key={doc.id} className="bg-slate-800/30 rounded-xl p-4 hover:bg-slate-800/50 transition-all">
//                         <div className="flex items-center justify-between">
//                           <div className="flex items-center gap-4 flex-1">
//                             <div className="p-2 bg-blue-500/10 rounded-lg">
//                               <FileText className="w-6 h-6 text-blue-400" />
//                             </div>
//                             <div className="flex-1">
//                               <h4 className="font-medium mb-1">{doc.filename}</h4>
//                               <div className="flex items-center gap-4 text-xs text-slate-400">
//                                 <span>{formatBytes(doc.file_size)}</span>
//                                 {doc.page_count && <span>{doc.page_count} pages</span>}
//                                 <span>{doc.processing_method}</span>
//                                 {doc.processing_time_ms && <span>{formatTime(doc.processing_time_ms)}</span>}
//                               </div>
//                             </div>
//                           </div>
                          
//                           <div className="flex items-center gap-3">
//                             <StatusBadge status={doc.status} />
//                             <button
//                               onClick={() => viewDocumentDetails(doc.id)}
//                               className="p-2 hover:bg-slate-700/50 rounded-lg transition-all"
//                             >
//                               <Eye className="w-4 h-4" />
//                             </button>
//                             <button
//                               onClick={() => deleteDocument(doc.id)}
//                               className="p-2 hover:bg-red-500/10 rounded-lg transition-all text-red-400"
//                             >
//                               <Trash2 className="w-4 h-4" />
//                             </button>
//                           </div>
//                         </div>

//                         {doc.error_message && (
//                           <div className="mt-3 p-3 bg-red-500/10 border border-red-500/20 rounded-lg">
//                             <p className="text-xs text-red-400">{doc.error_message}</p>
//                           </div>
//                         )}
//                       </div>
//                     ))}
//                   </div>
//                 ) : (
//                   <div className="text-center py-12 text-slate-500">
//                     <FileText className="w-12 h-12 mx-auto mb-3 opacity-50" />
//                     <p>No documents yet. Upload some files to get started.</p>
//                   </div>
//                 )}
//               </div>
//             )}

//             {/* Search Tab */}
//             {currentTab === 'search' && (
//               <div className="space-y-6">
//                 <div className="bg-slate-900/50 backdrop-blur-xl border border-slate-800/50 rounded-2xl p-6">
//                   <h3 className="text-xl font-bold mb-4">Semantic Search</h3>
//                   <div className="flex gap-3">
//                     <input
//                       type="text"
//                       value={searchQuery}
//                       onChange={(e) => setSearchQuery(e.target.value)}
//                       onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
//                       placeholder="Search across all documents..."
//                       className="flex-1 px-4 py-3 bg-slate-800/50 border border-slate-700/50 rounded-xl focus:outline-none focus:border-blue-500/50 transition-all"
//                     />
//                     <button
//                       onClick={handleSearch}
//                       disabled={isSearching}
//                       className="flex items-center gap-2 bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 disabled:opacity-50 px-6 py-3 rounded-xl font-medium transition-all"
//                     >
//                       {isSearching ? (
//                         <>
//                           <Loader2 className="w-4 h-4 animate-spin" />
//                           Searching...
//                         </>
//                       ) : (
//                         <>
//                           <Search className="w-4 h-4" />
//                           Search
//                         </>
//                       )}
//                     </button>
//                   </div>
//                 </div>

//                 {searchResults.length > 0 && (
//                   <div className="bg-slate-900/50 backdrop-blur-xl border border-slate-800/50 rounded-2xl p-6">
//                     <h4 className="font-bold mb-4">Results ({searchResults.length})</h4>
//                     <div className="space-y-4">
//                       {searchResults.map((result, index) => (
//                         <div key={index} className="bg-slate-800/30 rounded-xl p-4">
//                           <div className="flex items-start justify-between mb-2">
//                             <div className="flex items-center gap-2">
//                               <FileText className="w-4 h-4 text-blue-400" />
//                               <span className="font-medium text-sm">{result.filename}</span>
//                             </div>
//                             <span className="text-xs text-slate-500">
//                               Page {result.page} • Chunk {result.chunk_index}
//                             </span>
//                           </div>
//                           <p className="text-sm text-slate-300 leading-relaxed">{result.content}</p>
//                           {result.metadata && (
//                             <div className="mt-2 flex gap-2">
//                               <span className="text-xs px-2 py-1 bg-slate-700/50 rounded">
//                                 {result.processing_method}
//                               </span>
//                             </div>
//                           )}
//                         </div>
//                       ))}
//                     </div>
//                   </div>
//                 )}
//               </div>
//             )}
//           </div>
//         )}
//       </div>

//       {/* Create Project Modal */}
//       {showCreateProject && (
//         <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
//           <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 max-w-md w-full">
//             <h3 className="text-xl font-bold mb-4">Create New Project</h3>
//             <form onSubmit={(e) => {
//               e.preventDefault();
//               const formData = new FormData(e.target);
//               createProject(formData.get('name'), formData.get('description'));
//             }}>
//               <div className="space-y-4">
//                 <div>
//                   <label className="block text-sm font-medium mb-2">Project Name</label>
//                   <input
//                     type="text"
//                     name="name"
//                     required
//                     className="w-full px-4 py-2 bg-slate-800/50 border border-slate-700/50 rounded-xl focus:outline-none focus:border-blue-500/50"
//                     placeholder="My Project"
//                   />
//                 </div>
//                 <div>
//                   <label className="block text-sm font-medium mb-2">Description (optional)</label>
//                   <textarea
//                     name="description"
//                     rows="3"
//                     className="w-full px-4 py-2 bg-slate-800/50 border border-slate-700/50 rounded-xl focus:outline-none focus:border-blue-500/50"
//                     placeholder="What is this project about?"
//                   />
//                 </div>
//               </div>
//               <div className="flex gap-3 mt-6">
//                 <button
//                   type="button"
//                   onClick={() => setShowCreateProject(false)}
//                   className="flex-1 px-4 py-2 bg-slate-800/50 hover:bg-slate-800 rounded-xl transition-all"
//                 >
//                   Cancel
//                 </button>
//                 <button
//                   type="submit"
//                   className="flex-1 px-4 py-2 bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 rounded-xl transition-all"
//                 >
//                   Create
//                 </button>
//               </div>
//             </form>
//           </div>
//         </div>
//       )}

//       {/* Invite Member Modal */}
//       {showInviteModal && (
//         <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
//           <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 max-w-md w-full">
//             <h3 className="text-xl font-bold mb-4">Invite Team Member</h3>
//             <form onSubmit={(e) => {
//               e.preventDefault();
//               const formData = new FormData(e.target);
//               inviteMember(formData.get('email'), formData.get('role'));
//             }}>
//               <div className="space-y-4">
//                 <div>
//                   <label className="block text-sm font-medium mb-2">Email Address</label>
//                   <input
//                     type="email"
//                     name="email"
//                     required
//                     className="w-full px-4 py-2 bg-slate-800/50 border border-slate-700/50 rounded-xl focus:outline-none focus:border-blue-500/50"
//                     placeholder="colleague@example.com"
//                   />
//                 </div>
//                 <div>
//                   <label className="block text-sm font-medium mb-2">Role</label>
//                   <select
//                     name="role"
//                     className="w-full px-4 py-2 bg-slate-800/50 border border-slate-700/50 rounded-xl focus:outline-none focus:border-blue-500/50"
//                   >
//                     <option value="member">Member</option>
//                     <option value="admin">Admin</option>
//                   </select>
//                 </div>
//               </div>
//               <div className="flex gap-3 mt-6">
//                 <button
//                   type="button"
//                   onClick={() => setShowInviteModal(false)}
//                   className="flex-1 px-4 py-2 bg-slate-800/50 hover:bg-slate-800 rounded-xl transition-all"
//                 >
//                   Cancel
//                 </button>
//                 <button
//                   type="submit"
//                   className="flex-1 px-4 py-2 bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 rounded-xl transition-all"
//                 >
//                   Send Invite
//                 </button>
//               </div>
//             </form>
//           </div>
//         </div>
//       )}

//       {/* Document Details Modal */}
//       {showDocModal && selectedDoc && (
//         <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
//           <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 max-w-3xl w-full max-h-[80vh] overflow-y-auto">
//             <div className="flex items-start justify-between mb-6">
//               <div>
//                 <h3 className="text-2xl font-bold mb-2">{selectedDoc.filename}</h3>
//                 <div className="flex items-center gap-3">
//                   <StatusBadge status={selectedDoc.status} />
//                   <span className="text-sm text-slate-400">{formatBytes(selectedDoc.file_size)}</span>
//                   {selectedDoc.page_count && (
//                     <span className="text-sm text-slate-400">{selectedDoc.page_count} pages</span>
//                   )}
//                 </div>
//               </div>
//               <button
//                 onClick={() => setShowDocModal(false)}
//                 className="p-2 hover:bg-slate-800 rounded-lg transition-all"
//               >
//                 <X className="w-5 h-5" />
//               </button>
//             </div>

//             <div className="space-y-6">
//               {/* Metadata */}
//               <div className="bg-slate-800/30 rounded-xl p-4">
//                 <h4 className="font-bold mb-3">Details</h4>
//                 <div className="grid grid-cols-2 gap-4 text-sm">
//                   <div>
//                     <p className="text-slate-400 mb-1">Processing Method</p>
//                     <p className="font-medium">{selectedDoc.processing_method}</p>
//                   </div>
//                   <div>
//                     <p className="text-slate-400 mb-1">Chunks</p>
//                     <p className="font-medium">{selectedDoc.chunk_count}</p>
//                   </div>
//                   <div>
//                     <p className="text-slate-400 mb-1">Uploaded By</p>
//                     <p className="font-medium">{selectedDoc.uploaded_by}</p>
//                   </div>
//                   <div>
//                     <p className="text-slate-400 mb-1">Upload Time</p>
//                     <p className="font-medium">
//                       {selectedDoc.created_at ? new Date(selectedDoc.created_at).toLocaleString() : 'N/A'}
//                     </p>
//                   </div>
//                 </div>
//               </div>

//               {/* Processing Logs */}
//               {selectedDoc.processing_logs && selectedDoc.processing_logs.length > 0 && (
//                 <div className="bg-slate-800/30 rounded-xl p-4">
//                   <h4 className="font-bold mb-3">Processing Logs</h4>
//                   <div className="space-y-2">
//                     {selectedDoc.processing_logs.map((log, index) => (
//                       <div key={index} className="flex items-start gap-3 text-sm">
//                         <div className="w-24 text-slate-400 flex-shrink-0">
//                           {new Date(log.timestamp).toLocaleTimeString()}
//                         </div>
//                         <div className="flex-1">
//                           <div className="flex items-center gap-2 mb-1">
//                             <span className="font-medium">{log.stage}</span>
//                             <StatusBadge status={log.status} />
//                           </div>
//                           {log.duration_ms && (
//                             <p className="text-slate-400 text-xs">{formatTime(log.duration_ms)}</p>
//                           )}
//                           {log.error_details && (
//                             <p className="text-red-400 text-xs mt-1">{log.error_details}</p>
//                           )}
//                         </div>
//                       </div>
//                     ))}
//                   </div>
//                 </div>
//               )}

//               {selectedDoc.error_message && (
//                 <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-4">
//                   <h4 className="font-bold text-red-400 mb-2">Error</h4>
//                   <p className="text-sm text-red-300">{selectedDoc.error_message}</p>
//                 </div>
//               )}
//             </div>
//           </div>
//         </div>
//       )}
//     </div>
//   );
// };

// export default App;

import React, { useState, useEffect, useRef } from 'react';
import { 
  Upload, FileText, Search, CheckCircle, XCircle, Clock, 
  AlertCircle, ChevronRight, Loader2, Database, 
  Activity, Sparkles, Settings, Trash2, Eye, RefreshCw,
  Users, Plus, FolderOpen, UserPlus, X, BarChart2, MessageSquare
} from 'lucide-react';

// Import all new components
import ChatInterface from './components/ChatInterface';
import Dashboard from './components/Dashboard';
import ProcessingDetail from './components/ProcessingDetail';
import LiveStatusIndicator from './components/LiveStatusIndicator';
import DocumentExplorer from './components/DocumentExplorer';
import MobileNav from './components/MobileNav';

// ============================================================================
// CONFIGURATION
// ============================================================================
// const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';
const API_BASE_URL = import.meta.env.VITE_API_URL || 'https://rag-pipeline-ui-141241159430.europe-west1.run.app/api';

// ============================================================================
// API CLIENT
// ============================================================================
class ApiClient {
  constructor(baseUrl) {
    this.baseUrl = baseUrl;
  }

  async request(endpoint, options = {}) {
    const url = `${this.baseUrl}${endpoint}`;
    
    const config = {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    };

    try {
      const response = await fetch(url, config);
      
      if (!response.ok) {
        const error = await response.json().catch(() => ({ error: 'Request failed' }));
        throw new Error(error.error || error.detail || `HTTP error! status: ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error('API request failed:', error);
      throw error;
    }
  }

  async getProjects(userId) {
    return this.request(`/projects?user_id=${userId}`);
  }

  async createProject(data) {
    return this.request('/projects', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async deleteProject(projectId, userId) {
    return this.request(`/projects/${projectId}?user_id=${userId}`, {
      method: 'DELETE',
    });
  }

  async getDocuments(projectId, userId) {
    return this.request(`/documents?project_id=${projectId}&user_id=${userId}`);
  }

  async getDocumentDetails(documentId, projectId, userId) {
    return this.request(`/documents/${documentId}?project_id=${projectId}&user_id=${userId}`);
  }

  async deleteDocument(documentId, projectId, userId) {
    return this.request(`/documents/${documentId}?project_id=${projectId}&user_id=${userId}`, {
      method: 'DELETE',
    });
  }

  async getSignedUrl(filename, projectId, userId, contentType) {
    return this.request('/upload/signed-url', {
      method: 'POST',
      body: JSON.stringify({ 
        filename, 
        project_id: projectId, 
        user_id: userId,
        content_type: contentType 
      }),
    });
  }

  async uploadToGCS(signedUrl, file, onProgress) {
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      
      if (onProgress) {
        xhr.upload.addEventListener('progress', (e) => {
          if (e.lengthComputable) {
            const progress = Math.round((e.loaded / e.total) * 100);
            onProgress(progress);
          }
        });
      }

      xhr.addEventListener('load', () => {
        if (xhr.status === 200) {
          resolve(xhr.response);
        } else {
          reject(new Error(`Upload failed: ${xhr.status}`));
        }
      });

      xhr.addEventListener('error', () => {
        reject(new Error('Upload failed'));
      });

      xhr.open('PUT', signedUrl);
      xhr.setRequestHeader('Content-Type', file.type);
      xhr.send(file);
    });
  }

  async searchDocuments(query, projectId, userId, k = 10) {
    return this.request('/search', {
      method: 'POST',
      body: JSON.stringify({ 
        query, 
        project_id: projectId, 
        user_id: userId,
        k 
      }),
    });
  }

  async getProjectMembers(projectId, userId) {
    return this.request(`/projects/${projectId}/members?user_id=${userId}`);
  }

  async inviteMember(projectId, email, role, userId) {
    return this.request(`/projects/${projectId}/members`, {
      method: 'POST',
      body: JSON.stringify({ email, role, user_id: userId }),
    });
  }

  async removeMember(projectId, memberUserId, userId) {
    return this.request(`/projects/${projectId}/members/${memberUserId}?user_id=${userId}`, {
      method: 'DELETE',
    });
  }

  async getProjectAnalytics(projectId, userId) {
    return this.request(`/projects/${projectId}/analytics?user_id=${userId}`);
  }
}

const apiClient = new ApiClient(API_BASE_URL);

// ============================================================================
// MAIN APP COMPONENT
// ============================================================================
const App = () => {
  const [user] = useState({ 
    id: 'user-123', 
    email: 'user@example.com', 
    name: 'John Doe' 
  });

  const [projects, setProjects] = useState([]);
  const [selectedProject, setSelectedProject] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [projectMembers, setProjectMembers] = useState([]);
  const [uploadQueue, setUploadQueue] = useState([]);
  const [isUploading, setIsUploading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [isSearching, setIsSearching] = useState(false);
  const [activeView, setActiveView] = useState('projects');
  const [showCreateProject, setShowCreateProject] = useState(false);
  const [showInviteModal, setShowInviteModal] = useState(false);
  const [notifications, setNotifications] = useState([]);
  const fileInputRef = useRef(null);
  const [realTimeUpdates, setRealTimeUpdates] = useState([]);
  const [currentTab, setCurrentTab] = useState('dashboard');
  const [analytics, setAnalytics] = useState(null);
  const [isLoadingProjects, setIsLoadingProjects] = useState(false);
  
  // New states for integrated components
  const [showProcessingDetail, setShowProcessingDetail] = useState(false);
  const [detailDocumentId, setDetailDocumentId] = useState(null);

  useEffect(() => {
    loadProjects();
  }, []);

  useEffect(() => {
    if (selectedProject) {
      loadDocuments();
      loadProjectMembers();
      loadAnalytics();
      
      const interval = setInterval(() => {
        loadDocuments();
      }, 5000);
      
      return () => clearInterval(interval);
    }
  }, [selectedProject]);

  // ============================================================================
  // API FUNCTIONS
  // ============================================================================

  const loadProjects = async () => {
    setIsLoadingProjects(true);
    try {
      const response = await apiClient.getProjects(user.id);
      setProjects(response.projects || []);
    } catch (error) {
      addNotification('error', 'Failed to load projects');
      console.error('Load projects error:', error);
    } finally {
      setIsLoadingProjects(false);
    }
  };

  const loadDocuments = async () => {
    if (!selectedProject) return;
    
    try {
      const response = await apiClient.getDocuments(selectedProject, user.id);
      setDocuments(response.documents || []);
      
      const processing = response.documents?.filter(d => d.status === 'processing') || [];
      if (processing.length > 0) {
        processing.forEach(doc => {
          const exists = realTimeUpdates.some(u => u.docId === doc.id);
          if (!exists) {
            setRealTimeUpdates(prev => [{
              id: Date.now() + Math.random(),
              docId: doc.id,
              message: `Processing "${doc.filename}"`,
              timestamp: new Date().toISOString(),
              type: 'processing'
            }, ...prev.slice(0, 9)]);
          }
        });
      }
    } catch (error) {
      addNotification('error', 'Failed to load documents');
      console.error('Load documents error:', error);
    }
  };

  const loadProjectMembers = async () => {
    if (!selectedProject) return;
    
    try {
      const response = await apiClient.getProjectMembers(selectedProject, user.id);
      setProjectMembers(response.members || []);
    } catch (error) {
      console.error('Failed to load members', error);
    }
  };

  const loadAnalytics = async () => {
    if (!selectedProject) return;
    
    try {
      const response = await apiClient.getProjectAnalytics(selectedProject, user.id);
      setAnalytics(response);
    } catch (error) {
      console.error('Failed to load analytics', error);
    }
  };

  const createProject = async (name, description) => {
    try {
      const newProject = await apiClient.createProject({
        name,
        description,
        user_id: user.id,
        user_email: user.email
      });
      
      setProjects(prev => [newProject, ...prev]);
      setSelectedProject(newProject.id);
      setActiveView('pipeline');
      setShowCreateProject(false);
      addNotification('success', `Project "${name}" created successfully`);
    } catch (error) {
      addNotification('error', 'Failed to create project');
      console.error('Create project error:', error);
    }
  };

  const deleteProject = async (projectId) => {
    if (!window.confirm('Are you sure you want to delete this project?')) return;
    
    try {
      await apiClient.deleteProject(projectId, user.id);
      setProjects(prev => prev.filter(p => p.id !== projectId));
      if (selectedProject === projectId) {
        setSelectedProject(null);
        setActiveView('projects');
      }
      addNotification('success', 'Project deleted successfully');
    } catch (error) {
      addNotification('error', 'Failed to delete project');
      console.error('Delete project error:', error);
    }
  };

  const handleFileSelect = (files) => {
    if (!selectedProject) {
      addNotification('error', 'Please select a project first');
      return;
    }
    
    const newFiles = Array.from(files).map(file => ({
      id: Math.random().toString(36).substr(2, 9),
      file,
      status: 'queued',
      progress: 0,
      uploadedBy: user.email
    }));
    setUploadQueue(prev => [...prev, ...newFiles]);
    addNotification('info', `${files.length} file(s) added to queue`);
  };

  const uploadToGCS = async (fileItem) => {
    try {
      setUploadQueue(prev => prev.map(f => 
        f.id === fileItem.id ? { ...f, status: 'uploading', progress: 0 } : f
      ));

      const { signed_url } = await apiClient.getSignedUrl(
        fileItem.file.name,
        selectedProject,
        user.id,
        fileItem.file.type
      );

      await apiClient.uploadToGCS(signed_url, fileItem.file, (progress) => {
        setUploadQueue(prev => prev.map(f => 
          f.id === fileItem.id ? { ...f, progress } : f
        ));
      });

      setUploadQueue(prev => prev.map(f => 
        f.id === fileItem.id ? { ...f, status: 'processing', progress: 100 } : f
      ));

      addNotification('success', `${fileItem.file.name} uploaded - Cloud Function triggered`);
      
      setRealTimeUpdates(prev => [{
        id: Date.now(),
        message: `Processing "${fileItem.file.name}" via Cloud Function`,
        timestamp: new Date().toISOString(),
        type: 'processing'
      }, ...prev.slice(0, 9)]);

      setTimeout(() => {
        setUploadQueue(prev => prev.filter(f => f.id !== fileItem.id));
        loadDocuments();
      }, 3000);

    } catch (error) {
      console.error('Upload error:', error);
      setUploadQueue(prev => prev.map(f => 
        f.id === fileItem.id ? { ...f, status: 'failed', progress: 0, error: error.message } : f
      ));
      addNotification('error', `Failed to upload ${fileItem.file.name}: ${error.message}`);
    }
  };

  const startUpload = async () => {
    if (!selectedProject) {
      addNotification('error', 'Please select a project first');
      return;
    }

    setIsUploading(true);
    const queued = uploadQueue.filter(f => f.status === 'queued');
    
    for (const fileItem of queued) {
      await uploadToGCS(fileItem);
    }
    
    setIsUploading(false);
  };

  const handleSearch = async () => {
    if (!searchQuery.trim()) {
      addNotification('error', 'Please enter a search query');
      return;
    }
    
    if (!selectedProject) {
      addNotification('error', 'Please select a project first');
      return;
    }

    setIsSearching(true);

    try {
      const response = await apiClient.searchDocuments(
        searchQuery,
        selectedProject,
        user.id,
        10
      );
      
      setSearchResults(response.results || []);
      
      if (response.results && response.results.length === 0) {
        addNotification('info', 'No results found');
      } else {
        addNotification('success', `Found ${response.results.length} results`);
      }
    } catch (error) {
      addNotification('error', 'Search failed');
      console.error('Search error:', error);
    } finally {
      setIsSearching(false);
    }
  };

  const deleteDocument = async (docId) => {
    if (!window.confirm('Are you sure you want to delete this document?')) return;
    
    try {
      await apiClient.deleteDocument(docId, selectedProject, user.id);
      setDocuments(prev => prev.filter(d => d.id !== docId));
      addNotification('success', 'Document deleted successfully');
    } catch (error) {
      addNotification('error', 'Failed to delete document');
      console.error('Delete document error:', error);
    }
  };

  const viewDocumentDetails = async (docId) => {
    setDetailDocumentId(docId);
    setShowProcessingDetail(true);
  };

  const inviteMember = async (email, role = 'member') => {
    try {
      await apiClient.inviteMember(selectedProject, email, role, user.id);
      addNotification('success', `Invitation sent to ${email}`);
      setShowInviteModal(false);
      loadProjectMembers();
    } catch (error) {
      addNotification('error', 'Failed to invite member');
      console.error('Invite member error:', error);
    }
  };

  const addNotification = (type, message) => {
    const id = Date.now();
    setNotifications(prev => [...prev, { id, type, message }]);
    setTimeout(() => {
      setNotifications(prev => prev.filter(n => n.id !== id));
    }, 5000);
  };

  const formatBytes = (bytes) => {
    if (!bytes) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  };

  const getStatusConfig = (status) => {
    const configs = {
      completed: { icon: CheckCircle, color: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20', label: 'Completed' },
      processing: { icon: Loader2, color: 'text-blue-400 bg-blue-500/10 border-blue-500/20', label: 'Processing', spin: true },
      failed: { icon: XCircle, color: 'text-red-400 bg-red-500/10 border-red-500/20', label: 'Failed' },
      uploading: { icon: Upload, color: 'text-purple-400 bg-purple-500/10 border-purple-500/20', label: 'Uploading' },
      queued: { icon: Clock, color: 'text-slate-400 bg-slate-500/10 border-slate-500/20', label: 'Queued' }
    };
    return configs[status] || configs.queued;
  };

  const StatusBadge = ({ status }) => {
    const config = getStatusConfig(status);
    const Icon = config.icon;
    return (
      <div className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg border ${config.color}`}>
        <Icon className={`w-3.5 h-3.5 ${config.spin ? 'animate-spin' : ''}`} />
        <span className="text-xs font-medium">{config.label}</span>
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 text-white">
      {/* Mobile Navigation */}
      <MobileNav
        activeView={activeView}
        onNavigate={setActiveView}
        projects={projects}
        selectedProject={selectedProject}
        onSelectProject={(projectId) => {
          setSelectedProject(projectId);
          setActiveView('pipeline');
        }}
        user={user}
      />

      {/* Background Effects */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 -left-48 w-96 h-96 bg-blue-500/5 rounded-full blur-3xl animate-pulse" />
        <div className="absolute bottom-1/4 -right-48 w-96 h-96 bg-purple-500/5 rounded-full blur-3xl animate-pulse" style={{ animationDelay: '1s' }} />
      </div>

      {/* Notifications */}
      <div className="fixed top-4 right-4 z-50 space-y-2 max-w-md">
        {notifications.map(n => (
          <div key={n.id} className="bg-slate-900/95 backdrop-blur-xl border border-slate-700/50 rounded-xl px-4 py-3 shadow-2xl animate-slide-in">
            <div className="flex items-center gap-3">
              {n.type === 'success' ? <CheckCircle className="w-5 h-5 text-emerald-400" /> : 
               n.type === 'error' ? <XCircle className="w-5 h-5 text-red-400" /> : 
               <AlertCircle className="w-5 h-5 text-blue-400" />}
              <span className="text-sm">{n.message}</span>
            </div>
          </div>
        ))}
      </div>

      {/* Header */}
      <header className="relative border-b border-slate-800/50 bg-slate-900/30 backdrop-blur-xl sticky top-0 z-30">
        <div className="max-w-7xl mx-auto px-6 py-4 pr-20 lg:pr-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="relative">
                <div className="absolute inset-0 bg-gradient-to-r from-blue-500 to-purple-600 rounded-2xl blur-lg opacity-50" />
                <div className="relative bg-gradient-to-br from-blue-500 via-purple-500 to-pink-500 p-3 rounded-2xl">
                  <Database className="w-7 h-7" />
                </div>
              </div>
              <div>
                <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-400 via-purple-400 to-pink-400 bg-clip-text text-transparent">
                  DocuMind AI
                </h1>
                <p className="text-xs text-slate-400">Collaborative Document Pipeline</p>
              </div>
            </div>
            
            <div className="hidden lg:flex items-center gap-3">
              <div className="flex items-center gap-2 px-3 py-2 bg-slate-800/50 rounded-lg">
                <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-500 rounded-full flex items-center justify-center text-sm font-bold">
                  {user.name.charAt(0)}
                </div>
                <span className="text-sm">{user.name}</span>
              </div>
              <button className="p-2 hover:bg-slate-800/50 rounded-lg transition-all">
                <Settings className="w-5 h-5" />
              </button>
            </div>
          </div>
        </div>
      </header>

  <div className="max-w-7xl mx-auto px-6 py-8 relative section-gap">
        {/* Projects View */}
        {activeView === 'projects' && (
          <div className="space-y-6">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h2 className="text-3xl font-bold mb-2">Your Projects</h2>
                <p className="text-slate-400">Create projects and collaborate with your team</p>
              </div>
              <button
                onClick={() => setShowCreateProject(true)}
                className="flex items-center gap-2 bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 px-6 py-3 rounded-xl font-medium transition-all duration-300 shadow-lg shadow-blue-500/25"
              >
                <Plus className="w-5 h-5" />
                New Project
              </button>
            </div>

            {isLoadingProjects ? (
              <div className="flex flex-col items-center justify-center py-20">
                <Loader2 className="w-12 h-12 animate-spin text-blue-400 mb-4" />
                <p className="text-slate-400">Loading projects...</p>
              </div>
            ) : projects.length > 0 ? (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {projects.map(project => (
                  <div
                    key={project.id}
                    onClick={() => {
                      setSelectedProject(project.id);
                      setActiveView('pipeline');
                    }}
                    className="group cursor-pointer bg-slate-900/50 backdrop-blur-xl border border-slate-800/50 hover:border-slate-700 rounded-2xl p-6 transition-all duration-300 hover:shadow-xl hover:shadow-blue-500/10 hover:scale-[1.02]"
                  >
                    <div className="flex items-start justify-between mb-4">
                      <div className="p-3 bg-gradient-to-br from-blue-500/20 to-purple-500/20 rounded-xl group-hover:scale-110 transition-transform">
                        <FolderOpen className="w-6 h-6 text-blue-400" />
                      </div>
                      <div className="flex items-center gap-2 text-slate-400">
                        <Users className="w-4 h-4" />
                        <span className="text-sm">{project.members_count}</span>
                      </div>
                    </div>

                    <h3 className="text-xl font-bold mb-2">{project.name}</h3>
                    <p className="text-sm text-slate-400 mb-4 line-clamp-2">{project.description || 'No description'}</p>

                    <div className="grid grid-cols-2 gap-4 pt-4 border-t border-slate-800/50">
                      <div>
                        <p className="text-xs text-slate-500 mb-1">Documents</p>
                        <p className="text-lg font-bold">{project.doc_count || 0}</p>
                      </div>
                      <div>
                        <p className="text-xs text-slate-500 mb-1">Storage</p>
                        <p className="text-lg font-bold">{project.storage_used || 0} GB</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-20">
                <div className="inline-flex p-6 bg-slate-800/30 rounded-3xl mb-6">
                  <FolderOpen className="w-16 h-16 text-slate-600" />
                </div>
                <h3 className="text-2xl font-bold mb-3">No projects yet</h3>
                <p className="text-slate-400 mb-6">Create your first project to get started with document processing</p>
                <button
                  onClick={() => setShowCreateProject(true)}
                  className="inline-flex items-center gap-2 bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 px-6 py-3 rounded-xl font-medium transition-all shadow-lg"
                >
                  <Plus className="w-5 h-5" />
                  Create First Project
                </button>
              </div>
            )}
          </div>
        )}

        {/* Pipeline View */}
        {activeView === 'pipeline' && selectedProject && (
          <div className="space-y-6">
            <button
              onClick={() => setActiveView('projects')}
              className="flex items-center gap-2 text-slate-400 hover:text-white transition-colors mb-4"
            >
              <ChevronRight className="w-4 h-4 rotate-180" />
              Back to Projects
            </button>

            {/* Project Header with Live Status */}
            <div className="bg-slate-900/50 backdrop-blur-xl border border-slate-800/50 rounded-2xl ui-card">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h2 className="text-2xl font-bold mb-2">
                    {projects.find(p => p.id === selectedProject)?.name}
                  </h2>
                  <p className="text-slate-400 text-sm">
                    {projects.find(p => p.id === selectedProject)?.description || 'No description'}
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  <LiveStatusIndicator
                    projectId={selectedProject}
                    userId={user.id}
                    onUpdate={(data) => {
                      if (data.type === 'document_update') {
                        addNotification('info', `Document ${data.status}: ${data.data?.filename || 'Unknown'}`);
                        loadDocuments();
                      }
                    }}
                  />
                  <button
                    onClick={() => setShowInviteModal(true)}
                    className="flex items-center gap-2 px-4 py-2 bg-slate-800/50 hover:bg-slate-800 border border-slate-700/50 rounded-xl transition-all"
                  >
                    <UserPlus className="w-4 h-4" />
                    Invite
                  </button>
                  <button
                    onClick={() => loadDocuments()}
                    className="flex items-center gap-2 px-4 py-2 bg-slate-800/50 hover:bg-slate-800 border border-slate-700/50 rounded-xl transition-all"
                  >
                    <RefreshCw className="w-4 h-4" />
                  </button>
                </div>
              </div>

              {/* Analytics Cards */}
              {analytics && (
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-4">
                  <div className="bg-slate-800/30 rounded-xl p-4">
                    <p className="text-xs text-slate-400 mb-1">Total Docs</p>
                    <p className="text-2xl font-bold">{analytics.total_documents}</p>
                  </div>
                  <div className="bg-slate-800/30 rounded-xl p-4">
                    <p className="text-xs text-slate-400 mb-1">Completed</p>
                    <p className="text-2xl font-bold text-emerald-400">{analytics.completed_documents}</p>
                  </div>
                  <div className="bg-slate-800/30 rounded-xl p-4">
                    <p className="text-xs text-slate-400 mb-1">Processing</p>
                    <p className="text-2xl font-bold text-blue-400">{analytics.processing_documents}</p>
                  </div>
                  <div className="bg-slate-800/30 rounded-xl p-4">
                    <p className="text-xs text-slate-400 mb-1">Storage</p>
                    <p className="text-2xl font-bold">{analytics.total_storage_gb} GB</p>
                  </div>
                </div>
              )}

              {/* Team Members */}
              {projectMembers.length > 0 && (
                <div className="flex items-center gap-2 mt-4 pt-4 border-t border-slate-800/50">
                  <span className="text-sm text-slate-400">Team:</span>
                  <div className="flex -space-x-2">
                    {projectMembers.slice(0, 5).map((member, i) => (
                      <div
                        key={i}
                        className="w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-500 rounded-full flex items-center justify-center text-xs font-bold border-2 border-slate-900"
                        title={member.email}
                      >
                        {member.email.charAt(0).toUpperCase()}
                      </div>
                    ))}
                    {projectMembers.length > 5 && (
                      <div className="w-8 h-8 bg-slate-800 rounded-full flex items-center justify-center text-xs border-2 border-slate-900">
                        +{projectMembers.length - 5}
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>

            {/* Navigation Tabs */}
            <div className="flex gap-2 bg-slate-900/30 p-1.5 rounded-2xl border border-slate-800/50 overflow-x-auto">
              {[
                { id: 'dashboard', label: 'Dashboard', icon: BarChart2 },
                { id: 'upload', label: 'Upload', icon: Upload },
                { id: 'documents', label: 'Documents', icon: FileText },
                { id: 'search', label: 'Search', icon: Search },
                { id: 'chat', label: 'Chat', icon: MessageSquare }
              ].map(tab => (
                <button
                  key={tab.id}
                  onClick={() => setCurrentTab(tab.id)}
                  className={`flex items-center justify-center gap-2 px-4 py-3 rounded-xl font-medium transition-all whitespace-nowrap ${
                    currentTab === tab.id
                      ? 'bg-gradient-to-r from-blue-500 to-purple-600 shadow-lg'
                      : 'hover:bg-slate-800/50 text-slate-400'
                  }`}
                >
                  <tab.icon className="w-4 h-4" />
                  <span className="hidden sm:inline">{tab.label}</span>
                </button>
              ))}
            </div>

            {/* Dashboard Tab */}
            {currentTab === 'dashboard' && (
              <Dashboard 
                projectId={selectedProject}
                userId={user.id}
                apiClient={apiClient}
              />
            )}

            {/* Upload Tab */}
            {currentTab === 'upload' && (
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <div className="lg:col-span-2">
                  <div className="relative group">
                    <div className="absolute inset-0 bg-gradient-to-r from-blue-500/20 to-purple-500/20 rounded-3xl blur-2xl opacity-0 group-hover:opacity-100 transition-opacity" />
                    <div className="relative bg-slate-900/50 backdrop-blur-xl border-2 border-dashed border-slate-700/50 hover:border-blue-500/50 rounded-3xl p-12 transition-all">
                      <input
                        ref={fileInputRef}
                        type="file"
                        multiple
                        onChange={(e) => handleFileSelect(e.target.files)}
                        className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                        accept=".pdf,.docx,.doc,.xlsx,.xls,.txt,.md,.jpg,.jpeg,.png,.webp"
                      />
                      
                      <div className="text-center">
                        <div className="inline-flex p-6 bg-gradient-to-r from-blue-500/20 to-purple-500/20 rounded-3xl mb-6">
                          <Upload className="w-16 h-16 text-blue-400" />
                        </div>
                        <h3 className="text-2xl font-bold mb-3">Upload Documents</h3>
                        <p className="text-slate-400 mb-4">Drop files here or click to browse</p>
                        <div className="flex flex-wrap justify-center gap-2 text-xs text-slate-500">
                          <span className="px-2 py-1 bg-slate-800/50 rounded">PDF</span>
                          <span className="px-2 py-1 bg-slate-800/50 rounded">DOCX</span>
                          <span className="px-2 py-1 bg-slate-800/50 rounded">XLSX</span>
                          <span className="px-2 py-1 bg-slate-800/50 rounded">Images</span>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Upload Queue */}
                  {uploadQueue.length > 0 && (
                    <div className="mt-6 bg-slate-900/50 backdrop-blur-xl border border-slate-800/50 rounded-2xl ui-card">
                      <div className="flex items-center justify-between mb-4">
                        <h3 className="font-bold">Upload Queue ({uploadQueue.length})</h3>
                        <button
                          onClick={startUpload}
                          disabled={isUploading || uploadQueue.filter(f => f.status === 'queued').length === 0}
                          className="flex items-center gap-2 bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 disabled:opacity-50 disabled:cursor-not-allowed px-4 py-2 rounded-xl font-medium transition-all"
                        >
                          {isUploading ? (
                            <>
                              <Loader2 className="w-4 h-4 animate-spin" />
                              Uploading...
                            </>
                          ) : (
                            <>
                              <Upload className="w-4 h-4" />
                              Start Upload
                            </>
                          )}
                        </button>
                      </div>

                      <div className="space-y-3">
                        {uploadQueue.map(file => (
                          <div key={file.id} className="bg-slate-800/30 rounded-xl p-4">
                            <div className="flex items-center justify-between mb-2">
                              <div className="flex items-center gap-3">
                                <FileText className="w-5 h-5 text-blue-400" />
                                <div>
                                  <p className="font-medium text-sm">{file.file.name}</p>
                                  <p className="text-xs text-slate-400">{formatBytes(file.file.size)}</p>
                                </div>
                              </div>
                              <StatusBadge status={file.status} />
                            </div>
                            {(file.status === 'uploading' || file.status === 'processing') && (
                              <div className="mt-2">
                                <div className="w-full bg-slate-700/30 rounded-full h-2">
                                  <div 
                                    className="bg-gradient-to-r from-blue-500 to-purple-600 h-2 rounded-full transition-all duration-300"
                                    style={{ width: `${file.progress}%` }}
                                  />
                                </div>
                                <p className="text-xs text-slate-400 mt-1">{file.progress}%</p>
                              </div>
                            )}
                            {file.status === 'failed' && file.error && (
                              <p className="text-xs text-red-400 mt-2">{file.error}</p>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                {/* Real-time Updates */}
                <div className="lg:col-span-1">
                  <div className="bg-slate-900/50 backdrop-blur-xl border border-slate-800/50 rounded-2xl ui-card sticky top-24">
                    <div className="flex items-center gap-2 mb-4">
                      <Activity className="w-5 h-5 text-blue-400" />
                      <h3 className="font-bold">Activity Feed</h3>
                    </div>

                    <div className="space-y-3 max-h-96 overflow-y-auto">
                      {realTimeUpdates.length > 0 ? (
                        realTimeUpdates.map(update => (
                          <div key={update.id} className="bg-slate-800/30 rounded-xl p-3">
                            <div className="flex items-start gap-2">
                              <Sparkles className="w-4 h-4 text-purple-400 mt-0.5" />
                              <div>
                                <p className="text-sm">{update.message}</p>
                                <p className="text-xs text-slate-500 mt-1">
                                  {new Date(update.timestamp).toLocaleTimeString()}
                                </p>
                              </div>
                            </div>
                          </div>
                        ))
                      ) : (
                        <div className="text-center py-8 text-slate-500">
                          <Activity className="w-8 h-8 mx-auto mb-2 opacity-50" />
                          <p className="text-sm">No recent activity</p>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Documents Tab - Using Enhanced Document Explorer */}
            {currentTab === 'documents' && (
              <DocumentExplorer
                projectId={selectedProject}
                userId={user.id}
                apiClient={apiClient}
                onViewDetails={viewDocumentDetails}
              />
            )}

            {/* Search Tab */}
            {currentTab === 'search' && (
              <div className="space-y-6">
                <div className="bg-slate-900/50 backdrop-blur-xl border border-slate-800/50 rounded-2xl p-6">
                  <h3 className="text-xl font-bold mb-4">Semantic Search</h3>
                  <div className="flex gap-3">
                    <input
                      type="text"
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
                      placeholder="Search across all documents..."
                      className="flex-1 px-4 py-3 bg-slate-800/50 border border-slate-700/50 rounded-xl focus:outline-none focus:border-blue-500/50 transition-all"
                    />
                    <button
                      onClick={handleSearch}
                      disabled={isSearching}
                      className="flex items-center gap-2 bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 disabled:opacity-50 px-6 py-3 rounded-xl font-medium transition-all"
                    >
                      {isSearching ? (
                        <>
                          <Loader2 className="w-4 h-4 animate-spin" />
                          Searching...
                        </>
                      ) : (
                        <>
                          <Search className="w-4 h-4" />
                          Search
                        </>
                      )}
                    </button>
                  </div>
                </div>

                {searchResults.length > 0 && (
                  <div className="bg-slate-900/50 backdrop-blur-xl border border-slate-800/50 rounded-2xl p-6">
                    <h4 className="font-bold mb-4">Results ({searchResults.length})</h4>
                    <div className="space-y-4">
                      {searchResults.map((result, index) => (
                        <div key={index} className="bg-slate-800/30 rounded-xl p-4">
                          <div className="flex items-start justify-between mb-2">
                            <div className="flex items-center gap-2">
                              <FileText className="w-4 h-4 text-blue-400" />
                              <span className="font-medium text-sm">{result.filename}</span>
                            </div>
                            <span className="text-xs text-slate-500">
                              Page {result.page} • Chunk {result.chunk_index}
                            </span>
                          </div>
                          <p className="text-sm text-slate-300 leading-relaxed">{result.content}</p>
                          {result.metadata && (
                            <div className="mt-2 flex gap-2">
                              <span className="text-xs px-2 py-1 bg-slate-700/50 rounded">
                                {result.processing_method}
                              </span>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Chat Tab */}
            {currentTab === 'chat' && (
              <ChatInterface 
                projectId={selectedProject}
                userId={user.id}
                apiClient={apiClient}
              />
            )}
          </div>
        )}
      </div>

      {/* Create Project Modal */}
      {showCreateProject && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 max-w-md w-full">
            <h3 className="text-xl font-bold mb-4">Create New Project</h3>
            <form onSubmit={(e) => {
              e.preventDefault();
              const formData = new FormData(e.target);
              createProject(formData.get('name'), formData.get('description'));
            }}>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium mb-2">Project Name</label>
                  <input
                    type="text"
                    name="name"
                    required
                    className="w-full px-4 py-2 bg-slate-800/50 border border-slate-700/50 rounded-xl focus:outline-none focus:border-blue-500/50"
                    placeholder="My Project"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-2">Description (optional)</label>
                  <textarea
                    name="description"
                    rows="3"
                    className="w-full px-4 py-2 bg-slate-800/50 border border-slate-700/50 rounded-xl focus:outline-none focus:border-blue-500/50"
                    placeholder="What is this project about?"
                  />
                </div>
              </div>
              <div className="flex gap-3 mt-6">
                <button
                  type="button"
                  onClick={() => setShowCreateProject(false)}
                  className="flex-1 px-4 py-2 bg-slate-800/50 hover:bg-slate-800 rounded-xl transition-all"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="flex-1 px-4 py-2 bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 rounded-xl transition-all"
                >
                  Create
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Invite Member Modal */}
      {showInviteModal && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 max-w-md w-full">
            <h3 className="text-xl font-bold mb-4">Invite Team Member</h3>
            <form onSubmit={(e) => {
              e.preventDefault();
              const formData = new FormData(e.target);
              inviteMember(formData.get('email'), formData.get('role'));
            }}>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium mb-2">Email Address</label>
                  <input
                    type="email"
                    name="email"
                    required
                    className="w-full px-4 py-2 bg-slate-800/50 border border-slate-700/50 rounded-xl focus:outline-none focus:border-blue-500/50"
                    placeholder="colleague@example.com"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-2">Role</label>
                  <select
                    name="role"
                    className="w-full px-4 py-2 bg-slate-800/50 border border-slate-700/50 rounded-xl focus:outline-none focus:border-blue-500/50"
                  >
                    <option value="member">Member</option>
                    <option value="admin">Admin</option>
                  </select>
                </div>
              </div>
              <div className="flex gap-3 mt-6">
                <button
                  type="button"
                  onClick={() => setShowInviteModal(false)}
                  className="flex-1 px-4 py-2 bg-slate-800/50 hover:bg-slate-800 rounded-xl transition-all"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="flex-1 px-4 py-2 bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 rounded-xl transition-all"
                >
                  Send Invite
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Processing Detail Modal */}
      {showProcessingDetail && detailDocumentId && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4 overflow-y-auto">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-6xl max-h-[90vh] overflow-y-auto">
            <div className="sticky top-0 bg-slate-900 border-b border-slate-800 px-6 py-4 flex items-center justify-between z-10">
              <h2 className="text-xl font-bold">Document Details</h2>
              <button
                onClick={() => {
                  setShowProcessingDetail(false);
                  setDetailDocumentId(null);
                }}
                className="p-2 hover:bg-slate-800 rounded-lg transition-all"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="p-6">
              <ProcessingDetail
                documentId={detailDocumentId}
                projectId={selectedProject}
                userId={user.id}
                apiClient={apiClient}
                onClose={() => {
                  setShowProcessingDetail(false);
                  setDetailDocumentId(null);
                }}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default App;
