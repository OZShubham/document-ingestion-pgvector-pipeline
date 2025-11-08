import React, { useState, useEffect } from 'react';
import { 
  Folder, Users, HardDrive, Clock, 
  Trash2, FileText, Plus
} from 'lucide-react';

const ProjectsList = ({ userId, apiClient, onSelectProject, setShowCreateProject }) => {
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadProjects();
  }, []);

  const loadProjects = async () => {
    try {
      setLoading(true);
      const response = await apiClient.request(`/projects?user_id=${userId}`);
      setProjects(response.projects || []);
      setError(null);
    } catch (error) {
      console.error('Failed to load projects:', error);
      setError('Failed to load projects. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteProject = async (projectId, projectName) => {
    const confirmed = window.confirm(
      `Are you sure you want to delete project "${projectName}"? This action cannot be undone.`
    );

    if (!confirmed) return;

    try {
      await apiClient.request(`/projects/${projectId}?user_id=${userId}`, {
        method: 'DELETE'
      });
      
      setProjects(projects.filter(p => p.id !== projectId));
      
    } catch (error) {
      console.error('Failed to delete project:', error);
      alert('Failed to delete project. Please try again.');
    }
  };

  if (loading) {
    return (
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

        <div className="flex items-center justify-center h-96">
          <div className="text-center">
            <div className="w-12 h-12 border-4 border-purple-400 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
            <p className="text-slate-400">Loading projects...</p>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
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

        <div className="text-center py-12">
          <p className="text-red-400 mb-4">{error}</p>
          <button 
            onClick={loadProjects}
            className="px-4 py-2 bg-slate-800 hover:bg-slate-700 rounded-lg transition-colors"
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  if (projects.length === 0) {
    return (
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

        <div className="text-center py-12">
          <Folder className="w-12 h-12 text-slate-600 mx-auto mb-4" />
          <p className="text-slate-400 mb-4">No projects found</p>
          <button
            onClick={() => setShowCreateProject(true)}
            className="inline-flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 rounded-xl font-medium transition-colors"
          >
            Create New Project
          </button>
        </div>
      </div>
    );
  }

  return (
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

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {projects.map(project => (
          <div 
            key={project.id}
            className="bg-slate-800/50 backdrop-blur-xl border border-slate-700/50 rounded-2xl overflow-hidden hover:border-slate-600/50 transition-all"
          >
            {/* Project Header */}
            <div className="p-6">
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <button 
                    onClick={() => onSelectProject(project.id)}
                    className="text-xl font-bold hover:text-purple-400 transition-colors truncate block text-left w-full"
                  >
                    {project.name}
                  </button>
                  <p className="text-slate-400 text-sm truncate">
                    {project.description || 'No description'}
                  </p>
                </div>
                
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => handleDeleteProject(project.id, project.name)}
                    className="p-2 hover:bg-red-500/10 rounded-lg transition-all text-red-400"
                    title="Delete Project"
                  >
                    <Trash2 className="w-5 h-5" />
                  </button>
                </div>
              </div>
            </div>

            {/* Project Stats */}
            <div className="border-t border-slate-700/50 px-6 py-4">
              <div className="grid grid-cols-3 gap-4">
                <div className="text-center">
                  <div className="flex items-center justify-center gap-1 text-slate-400 mb-1">
                    <FileText className="w-4 h-4" />
                    <span className="text-xs">Docs</span>
                  </div>
                  <p className="font-bold">{project.doc_count}</p>
                </div>
                
                {/* <div className="text-center">
                  {/* <div className="flex items-center justify-center gap-1 text-slate-400 mb-1">
                    <HardDrive className="w-4 h-4" />
                    <span className="text-xs">Storage</span>
                  </div> 
                  <p className="font-bold">{project.storage_used} GB</p>
                </div> */}
                
                <div className="text-center">
                  <div className="flex items-center justify-center gap-1 text-slate-400 mb-1">
                    <Users className="w-4 h-4" />
                    <span className="text-xs">Members</span>
                  </div>
                  <p className="font-bold">{project.members_count}</p>
                </div>
              </div>
            </div>

            {/* Project Footer */}
            <div className="border-t border-slate-700/50 px-6 py-3">
              <div className="flex items-center gap-2 text-xs text-slate-400">
                <Clock className="w-4 h-4" />
                <span>Created {new Date(project.created_at).toLocaleDateString()}</span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default ProjectsList;