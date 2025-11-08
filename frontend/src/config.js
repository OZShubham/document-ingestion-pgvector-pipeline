// // config.js - CORRECTED VERSION
// export const config = {
//   CLOUD_FUNCTION_URL: 'https://document-ingestion-pipeline-141241159430.us-central1.run.app',
//   API_BASE_URL: import.meta.env.VITE_API_URL || 'https://rag-pipeline-backend-141241159430.europe-west1.run.app/api',
//   GCS_BUCKET: import.meta.env.VITE_GCS_BUCKET || 'ingestion-docs',
//   POLL_INTERVAL: 5000,
//   MAX_FILE_SIZE_MB: 200,
//   ALLOWED_FILE_TYPES: [
//     '.pdf', '.docx', '.doc', '.xlsx', '.xls',
//     '.txt', '.md', '.jpg', '.jpeg', '.png', '.webp'
//   ]
// };

// // Helper to get WebSocket URL
// export const getWebSocketUrl = (path) => {
//   const baseUrl = config.API_BASE_URL;
//   const url = new URL(baseUrl);
//   const protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
//   const host = url.host;
//   return `${protocol}//${host}${path}`;
// };

// // API Client
// export class ApiClient {
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

//   // Projects
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

//   async getProjectAnalytics(projectId, userId) {
//     return this.request(`/projects/${projectId}/analytics?user_id=${userId}`);
//   }

//   // Documents
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

//   // FIXED: Correct endpoint path
//   async getDocumentFilterOptions(projectId, userId) {
//     return this.request(`/documents/filter-options?project_id=${projectId}&user_id=${userId}`);
//   }

//   // Processing timeline
//   async getProcessingTimeline(documentId, projectId, userId) {
//     return this.request(`/documents/${documentId}/processing-timeline?project_id=${projectId}&user_id=${userId}`);
//   }

//   // Document chunks
//   async getDocumentChunks(documentId, projectId, userId, page = 1, limit = 20) {
//     return this.request(`/documents/${documentId}/chunks?project_id=${projectId}&user_id=${userId}&page=${page}&limit=${limit}`);
//   }

//   // Document insights
//   async getDocumentInsights(documentId, projectId, userId) {
//     return this.request(`/documents/${documentId}/insights?project_id=${projectId}&user_id=${userId}`);
//   }

//   // Upload - DIRECT UPLOAD METHOD
//   async uploadFile(file, projectId, userId, onProgress) {
//     const formData = new FormData();
//     formData.append('file', file);
//     formData.append('project_id', projectId);
//     formData.append('user_id', userId);

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
//           try {
//             resolve(JSON.parse(xhr.response));
//           } catch (e) {
//             resolve({ success: true });
//           }
//         } else {
//           reject(new Error(`Upload failed: ${xhr.status}`));
//         }
//       });

//       xhr.addEventListener('error', () => {
//         reject(new Error('Upload failed'));
//       });

//       xhr.open('POST', `${this.baseUrl}/upload/direct`);
//       xhr.send(formData);
//     });
//   }

//   // Search
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

//   // Members
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

//   // Chat
//   async sendChatMessage(projectId, userId, message, conversationId = null) {
//     return this.request('/chat', {
//       method: 'POST',
//       body: JSON.stringify({
//         query: message,
//         project_id: projectId,
//         user_id: userId,
//         conversation_id: conversationId
//       }),
//     });
//   }

//   async getChatHistory(projectId, userId, conversationId = null) {
//     const params = new URLSearchParams({
//       project_id: projectId,
//       user_id: userId
//     });
//     if (conversationId) {
//       params.append('conversation_id', conversationId);
//     }
//     return this.request(`/chat/history?${params.toString()}`);
//   }
// }

// // Export singleton instance
// export const apiClient = new ApiClient(config.API_BASE_URL);

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

// Helper to get WebSocket URL
export const getWebSocketUrl = (path) => {
  const baseUrl = config.API_BASE_URL;
  const url = new URL(baseUrl);
  const protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
  const host = url.host;
  return `${protocol}//${host}${path}`;
};

// API Client - COMPLETE VERSION
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

    // Remove Content-Type for FormData
    if (options.body instanceof FormData) {
      delete config.headers['Content-Type'];
    }

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

  // ============================================================================
  // PROJECTS
  // ============================================================================
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

  // ADDED: Detailed analytics for Dashboard component
  async getDetailedAnalytics(projectId, userId, days = 30) {
    return this.request(`/projects/${projectId}/analytics/detailed?user_id=${userId}&days=${days}`);
  }

  // ============================================================================
  // DOCUMENTS
  // ============================================================================
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

  // ============================================================================
  // PROCESSING DETAILS (for ProcessingDetail component)
  // ============================================================================
  async getProcessingTimeline(documentId, projectId, userId) {
    return this.request(`/documents/${documentId}/processing-timeline?project_id=${projectId}&user_id=${userId}`);
  }

  async getDocumentChunks(documentId, projectId, userId, page = 1, limit = 20) {
    return this.request(`/documents/${documentId}/chunks?project_id=${projectId}&user_id=${userId}&page=${page}&limit=${limit}`);
  }

  async getDocumentInsights(documentId, projectId, userId) {
    return this.request(`/documents/${documentId}/insights?project_id=${projectId}&user_id=${userId}`);
  }

  // ============================================================================
  // FILTERING & BATCH (for DocumentExplorer component)
  // ============================================================================
  async getFilterOptions(projectId, userId) {
    return this.request(`/documents/filter-options?project_id=${projectId}&user_id=${userId}`);
  }

  async filterDocuments(projectId, userId, filters) {
    return this.request(`/documents/filter?project_id=${projectId}&user_id=${userId}`, {
      method: 'POST',
      body: JSON.stringify(filters)
    });
  }

  async batchOperation(projectId, operation, documentIds, userId, params = null) {
    return this.request(`/documents/batch?project_id=${projectId}`, {
      method: 'POST',
      body: JSON.stringify({
        operation,
        document_ids: documentIds,
        user_id: userId,
        params
      })
    });
  }

  async compareDocuments(projectId, userId, documentIds) {
    const docIdsParam = documentIds.map(id => `document_ids=${id}`).join('&');
    return this.request(`/documents/compare?project_id=${projectId}&user_id=${userId}&${docIdsParam}`);
  }

  // ============================================================================
  // UPLOAD - DIRECT UPLOAD
  // ============================================================================
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
            reject(new Error('Invalid response from server'));
          }
        } else {
          try {
            const error = JSON.parse(xhr.response);
            reject(new Error(error.detail || `Upload failed: ${xhr.status}`));
          } catch (e) {
            reject(new Error(`Upload failed: ${xhr.status}`));
          }
        }
      });

      xhr.addEventListener('error', () => {
        reject(new Error('Upload failed: Network error'));
      });

      xhr.addEventListener('abort', () => {
        reject(new Error('Upload cancelled'));
      });

      xhr.open('POST', `${this.baseUrl}/upload/direct`);
      xhr.send(formData);
    });
  }

  // ============================================================================
  // SEARCH
  // ============================================================================
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

  // ============================================================================
  // CHAT
  // ============================================================================
  async chat(query, projectId, userId, conversationId = null, k = 5, temperature = 0.7) {
    return this.request('/chat', {
      method: 'POST',
      body: JSON.stringify({
        query,
        project_id: projectId,
        user_id: userId,
        conversation_id: conversationId,
        k,
        temperature
      })
    });
  }

  // Alternative method name for backward compatibility
  async sendChatMessage(projectId, userId, message, conversationId = null) {
    return this.chat(message, projectId, userId, conversationId);
  }

  async getChatHistory(projectId, userId, conversationId = null) {
    const params = new URLSearchParams({
      project_id: projectId,
      user_id: userId
    });
    if (conversationId) {
      params.append('conversation_id', conversationId);
    }
    return this.request(`/chat/history?${params.toString()}`);
  }

  // ============================================================================
  // MEMBERS
  // ============================================================================
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

  // ============================================================================
  // UTILITIES
  // ============================================================================
  async checkStorageHealth(userId) {
    return this.request(`/storage/health?user_id=${userId}`);
  }
}

// Export singleton instance
export const apiClient = new ApiClient(config.API_BASE_URL);