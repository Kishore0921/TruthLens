import axios from 'axios';

const API_BASE = '/api/v1';

const client = axios.create({
  baseURL: API_BASE,
  headers: {
    'Accept': 'application/json',
  },
});

export const healthCheck = () => client.get('/health');

export const createInvestigation = (data) => client.post('/investigations', data);
export const getInvestigations = () => client.get('/investigations');
export const getInvestigation = (id) => client.get(`/investigations/${id}`);

export const uploadEvidence = (investigationId, file, onProgress) => {
  const formData = new FormData();
  formData.append('file', file);
  return client.post(`/investigations/${investigationId}/evidence`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: (progressEvent) => {
      if (onProgress && progressEvent.total) {
        const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total);
        onProgress(percent);
      }
    },
  });
};

export const getEvidence = (investigationId) => client.get(`/investigations/${investigationId}/evidence`);

export const startAnalysis = (investigationId) => client.post(`/investigations/${investigationId}/analyze`);
export const getAnalysisStatus = (investigationId) => client.get(`/investigations/${investigationId}/status`);
export const getFindings = (investigationId) => client.get(`/investigations/${investigationId}/findings`);
export const getCorrelations = (investigationId) => client.get(`/investigations/${investigationId}/correlations`);

export const getReport = (investigationId) => client.get(`/investigations/${investigationId}/report`);
export const getAssessment = (investigationId) => client.get(`/investigations/${investigationId}/assessment`);
export const downloadPdfReport = (investigationId) =>
  client.get(`/investigations/${investigationId}/report/pdf`, { responseType: 'blob' });

export const getDashboardStats = () => client.get('/dashboard/stats');
export const deleteEvidence = (evidenceId) => client.delete(`/evidence/${evidenceId}`);

// Settings & AI Provider Endpoints
export const getAIProviders = () => client.get('/settings/ai-providers');
export const updateAIProvider = (providerId, data) => client.put(`/settings/ai-providers/${providerId}`, data);
export const testAIProvider = (providerId) => client.post(`/settings/ai-providers/${providerId}/test`);
export const deleteAIProviderKey = (providerId) => client.delete(`/settings/ai-providers/${providerId}/key`);
export const extractReferenceFacts = (text) => client.post('/settings/extract-reference-facts', { text });

export const getEvidenceFileUrl = (evidenceId) => `${API_BASE}/evidence/${evidenceId}/file`;
export const getArtifactUrl = (evidenceId, filename) => `${API_BASE}/evidence/${evidenceId}/artifact/${filename}`;

export default client;
