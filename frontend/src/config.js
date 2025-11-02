// API Configuration
export const config = {
  // Your Cloud Function URL
  CLOUD_FUNCTION_URL: 'https://document-ingestion-pipeline-141241159430.us-central1.run.app',
  
  // Your API endpoint (create this as a separate Cloud Function)
  API_BASE_URL: import.meta.env.VITE_API_URL || 'https://rag-pipeline-backend-141241159430.europe-west1.run.app/api',
  
  // GCS Bucket name
  GCS_BUCKET: import.meta.env.VITE_GCS_BUCKET || 'ingestion-docs',
  
  // Polling interval for document updates (ms)
  POLL_INTERVAL: 5000,
  
  // File upload settings
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
        throw new Error(`HTTP error! status: ${response.status}`);
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

  // Documents
  async getDocuments(projectId) {
    return this.request(`/documents?project_id=${projectId}`);
  }

  async deleteDocument(documentId, projectId) {
    return this.request(`/documents/${documentId}?project_id=${projectId}`, {
      method: 'DELETE',
    });
  }

  // Upload
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
        resolve(JSON.parse(xhr.response));
      } else {
        reject(new Error(`Upload failed: ${xhr.status}`));
      }
    });

    xhr.addEventListener('error', () => {
      reject(new Error('Upload failed'));
    });

    xhr.open('POST', `${this.baseUrl}/upload/direct`);
    xhr.send(formData);
  });
}
  
  async getSignedUrl(filename, projectId, contentType) {
    return this.request('/upload/signed-url', {
      method: 'POST',
      body: JSON.stringify({ filename, project_id: projectId, content_type: contentType }),
    });
  }

  async uploadToGCS(signedUrl, file) {
    const response = await fetch(signedUrl, {
      method: 'PUT',
      body: file,
      headers: { 'Content-Type': file.type },
    });

    if (!response.ok) {
      throw new Error('Upload failed');
    }

    return response;
  }

  // Search
  async searchDocuments(query, projectId, k = 10) {
    return this.request('/search', {
      method: 'POST',
      body: JSON.stringify({ query, project_id: projectId, k }),
    });
  }

  // Members
  async getProjectMembers(projectId) {
    return this.request(`/projects/${projectId}/members`);
  }

  async inviteMember(projectId, email, role) {
    return this.request(`/projects/${projectId}/members`, {
      method: 'POST',
      body: JSON.stringify({ email, role }),
    });
  }
}

// Export singleton instance
export const apiClient = new ApiClient(config.API_BASE_URL);
