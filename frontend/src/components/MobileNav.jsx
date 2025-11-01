import React, { useState } from 'react';
import {
  Menu, X, Home, FileText, MessageSquare, Search, BarChart2,
  Upload, Settings, LogOut, ChevronRight
} from 'lucide-react';

const MobileNav = ({ activeView, onNavigate, projects, selectedProject, onSelectProject, user }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [showProjects, setShowProjects] = useState(false);

  const menuItems = [
    { id: 'projects', label: 'Projects', icon: Home },
    { id: 'dashboard', label: 'Dashboard', icon: BarChart2 },
    { id: 'upload', label: 'Upload', icon: Upload },
    { id: 'documents', label: 'Documents', icon: FileText },
    { id: 'chat', label: 'Chat', icon: MessageSquare },
    { id: 'search', label: 'Search', icon: Search }
  ];

  const handleNavigate = (view) => {
    onNavigate(view);
    setIsOpen(false);
  };

  return (
    <>
      {/* Mobile Menu Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="lg:hidden fixed top-4 right-4 z-50 p-3 bg-slate-900 border border-slate-800 rounded-xl shadow-xl"
      >
        {isOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
      </button>

      {/* Mobile Menu Overlay */}
      {isOpen && (
        <div
          className="lg:hidden fixed inset-0 bg-black/50 backdrop-blur-sm z-40"
          onClick={() => setIsOpen(false)}
        />
      )}

      {/* Mobile Menu Panel */}
      <div
        className={`lg:hidden fixed top-0 right-0 h-full w-80 bg-slate-900 border-l border-slate-800 z-40 transform transition-transform duration-300 ${
          isOpen ? 'translate-x-0' : 'translate-x-full'
        }`}
      >
        <div className="flex flex-col h-full">
          {/* Header */}
          <div className="p-6 border-b border-slate-800">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center font-bold">
                {user.name.charAt(0)}
              </div>
              <div>
                <p className="font-bold">{user.name}</p>
                <p className="text-xs text-slate-400">{user.email}</p>
              </div>
            </div>

            {/* Current Project */}
            {selectedProject && (
              <button
                onClick={() => setShowProjects(!showProjects)}
                className="w-full p-3 bg-slate-800/50 rounded-xl flex items-center justify-between"
              >
                <span className="text-sm font-medium truncate">
                  {projects.find(p => p.id === selectedProject)?.name || 'Select Project'}
                </span>
                <ChevronRight className={`w-4 h-4 transition-transform ${showProjects ? 'rotate-90' : ''}`} />
              </button>
            )}

            {/* Projects List */}
            {showProjects && (
              <div className="mt-2 space-y-1 max-h-60 overflow-y-auto">
                {projects.map(project => (
                  <button
                    key={project.id}
                    onClick={() => {
                      onSelectProject(project.id);
                      setShowProjects(false);
                    }}
                    className={`w-full p-2 text-left text-sm rounded-lg transition-all ${
                      selectedProject === project.id
                        ? 'bg-purple-500/20 text-purple-400'
                        : 'hover:bg-slate-800/50'
                    }`}
                  >
                    {project.name}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Navigation */}
          <div className="flex-1 overflow-y-auto p-4 space-y-1">
            {menuItems.map(item => {
              const Icon = item.icon;
              const isActive = activeView === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => handleNavigate(item.id)}
                  className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl font-medium transition-all ${
                    isActive
                      ? 'bg-gradient-to-r from-purple-500/20 to-pink-500/20 border border-purple-500/30 text-purple-400'
                      : 'hover:bg-slate-800/50'
                  }`}
                >
                  <Icon className="w-5 h-5" />
                  {item.label}
                </button>
              );
            })}
          </div>

          {/* Footer */}
          <div className="p-4 border-t border-slate-800 space-y-2">
            <button className="w-full flex items-center gap-3 px-4 py-3 rounded-xl hover:bg-slate-800/50 transition-all">
              <Settings className="w-5 h-5" />
              Settings
            </button>
            <button className="w-full flex items-center gap-3 px-4 py-3 rounded-xl hover:bg-slate-800/50 transition-all text-red-400">
              <LogOut className="w-5 h-5" />
              Sign Out
            </button>
          </div>
        </div>
      </div>
    </>
  );
};

export default MobileNav;