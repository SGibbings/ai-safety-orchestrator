/**
 * API Client for AI Safety Orchestrator Backend
 * Dynamically detects backend URL for GitHub Codespaces compatibility
 */

// Dynamically determine backend URL based on current environment
// Works in both local development and GitHub Codespaces
function getBackendURL() {
  // Get the current origin (e.g., https://xxx-3000.app.github.dev or http://localhost:3000)
  const currentOrigin = window.location.origin;
  
  // Replace the frontend port with the backend port (8000)
  // This works for both Codespaces forwarded ports and localhost
  const backendURL = currentOrigin.replace(/:(3000|5173)/, ':8000');
  
  console.log('[API Client] Backend URL:', backendURL);
  return backendURL;
}

const API_BASE_URL = getBackendURL();

/**
 * Analyze a developer prompt for security issues
 * @param {string} prompt - The developer prompt to analyze
 * @returns {Promise<AnalysisResponse>}
 */
export async function analyzePrompt(prompt) {
  const response = await fetch(`${API_BASE_URL}/api/analyze`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ prompt }),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`API Error (${response.status}): ${errorText}`);
  }

  return response.json();
}

/**
 * Check if the backend is healthy
 * @returns {Promise<boolean>}
 */
export async function checkHealth() {
  try {
    const response = await fetch(`${API_BASE_URL}/health`);
    return response.ok;
  } catch (error) {
    return false;
  }
}
