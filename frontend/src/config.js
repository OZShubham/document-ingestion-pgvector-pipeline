

// config.js - COMPLETE VERSION
export const config = {
  CLOUD_FUNCTION_URL: 'https://document-ingestion-pipeline-141241159430.us-central1.run.app',
  API_BASE_URL: import.meta.env.VITE_API_URL || 'https://rag-pipeline-backend-141241159430.europe-west1.run.app/api',
  GCS_BUCKET: import.meta.env.VITE_GCS_BUCKET || 'ingestion-docs',
  POLL_INTERVAL: 5000,
  MAX_FILE_SIZE_MB: 200,
  ALLOWED_FILE_TYPES: [
    '.pdf', '.docx', '.doc', '.xlsx', '.xls',
    '.txt', '.md', '.jpg', '.jpeg', '.png', '.webp'
  ]
};

// API Client
export class ApiClient {
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

  // Projects
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

  async getProjectAnalytics(projectId, userId) {
    return this.request(`/projects/${projectId}/analytics?user_id=${userId}`);
  }

  // Documents
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

  // Upload - DIRECT UPLOAD METHOD
  async uploadFile(file, projectId, userId, onProgress) {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('project_id', projectId);
    formData.append('user_id', userId);

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
          try {
            resolve(JSON.parse(xhr.response));
          } catch (e) {
            resolve({ success: true });
          }
        } else {
          reject(new Error(`Upload failed: ${xhr.status}`));
        }
      });

      xhr.addEventListener('error', () => {
        reject(new Error('Upload failed'));
      });

      xhr.open('POST', `${this.baseUrl}/upload/direct`);
      // Don't set Content-Type header - FormData will set it automatically with boundary
      xhr.send(formData);
    });
  }

  // Search
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

  // Members
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
}

// Export singleton instance
export const apiClient = new ApiClient(config.API_BASE_URL);
// Export singleton instance

