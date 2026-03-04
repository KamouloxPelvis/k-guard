import api from './api';

/**
 * Triggers a Trivy vulnerability scan via the K-Guard backend.
 * The 'api' instance automatically injects the JWT token and handles the /api prefix.
 */
export const triggerScan = async (image: string) => {
  try {
    // Perform a POST request to initiate the asynchronous scanning process
    const { data } = await api.post('/scan/scan', { image });
    return data;

  } catch (error: any) {
    // Log security-related errors with context for debugging
    console.error("🚨 K-Guard Scan Error:", error.response?.data || error.message);
    
    // Return a consistent error object to prevent UI crashes in the SecurityView
    return { 
      status: 'error', 
      message: error.response?.data?.detail || error.message 
    };
  }
};