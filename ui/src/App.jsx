import React, { useState } from 'react';
import { analyzePrompt } from './api';
import './App.css';

function App() {
  const [prompt, setPrompt] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  const handleAnalyze = async () => {
    // Validation
    if (!prompt.trim()) {
      setError('Please enter a prompt to analyze');
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await analyzePrompt(prompt);
      setResult(response);
    } catch (err) {
      setError(err.message || 'Failed to analyze prompt. Is the backend running?');
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    // Ctrl/Cmd + Enter to submit
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      handleAnalyze();
    }
  };

  // Compute risk level from findings
  const getRiskLevel = (findings) => {
    if (!findings || findings.length === 0) return 'Low';
    
    const hasBlockerOrError = findings.some(f => 
      f.severity.toUpperCase() === 'BLOCKER' || f.severity.toUpperCase() === 'ERROR'
    );
    if (hasBlockerOrError) return 'High';
    
    const hasWarning = findings.some(f => f.severity.toUpperCase() === 'WARNING');
    if (hasWarning) return 'Medium';
    
    return 'Low';
  };

  // Group findings by severity
  const groupFindingsBySeverity = (findings) => {
    const groups = {
      BLOCKER: [],
      ERROR: [],
      WARNING: [],
      INFO: []
    };

    findings.forEach(finding => {
      const severity = finding.severity.toUpperCase();
      if (groups[severity]) {
        groups[severity].push(finding);
      }
    });

    return groups;
  };

  const riskLevel = result ? getRiskLevel(result.devspec_findings) : null;
  const groupedFindings = result ? groupFindingsBySeverity(result.devspec_findings) : null;

  // Generate security summary
  const getSecuritySummary = (findings) => {
    if (!findings || findings.length === 0) {
      return 'No security issues detected. The prompt appears safe to use.';
    }

    const blockerCount = findings.filter(f => f.severity.toUpperCase() === 'BLOCKER').length;
    const errorCount = findings.filter(f => f.severity.toUpperCase() === 'ERROR').length;
    const warningCount = findings.filter(f => f.severity.toUpperCase() === 'WARNING').length;

    if (blockerCount > 0) {
      const issues = [];
      findings.filter(f => f.severity.toUpperCase() === 'BLOCKER')
        .slice(0, 3)
        .forEach(f => {
          if (f.code.includes('PLAINTEXT_PASSWORD')) issues.push('plaintext passwords');
          else if (f.code.includes('HARDCODED_SECRET')) issues.push('hardcoded secrets');
          else if (f.code.includes('ADMIN_BACKDOOR')) issues.push('admin backdoors');
          else if (f.code.includes('HTTP_FOR_AUTH')) issues.push('insecure HTTP authentication');
          else if (f.code.includes('DEBUG_EXPOSES')) issues.push('debug endpoint exposure');
          else if (f.code.includes('NO_AUTH')) issues.push('missing authentication');
        });
      const issueText = issues.length > 0 ? ` including ${issues.join(', ')}` : '';
      return `Multiple critical issues detected${issueText}. Immediate attention required before implementation.`;
    }

    if (errorCount > 0) {
      return `${errorCount} significant security issue${errorCount > 1 ? 's' : ''} detected that should be addressed before proceeding.`;
    }

    if (warningCount > 0) {
      return `${warningCount} potential security concern${warningCount > 1 ? 's' : ''} identified. Review recommended.`;
    }

    return 'Minor issues detected. Review the findings below.';
  };

  return (
    <div className="app">
      <header className="header">
        <h1>🛡️ AI Safety Orchestrator</h1>
        <p className="subtitle">Analyze developer prompts for security issues</p>
      </header>

      <main className="main-container">
        {/* Left Column - Input */}
        <div className="left-column">
          <div className="panel">
            <h2>Original Prompt</h2>
            <textarea
              className="prompt-input"
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Enter prompt here…"
              disabled={loading}
            />
            
            <button
              className="analyze-button"
              onClick={handleAnalyze}
              disabled={loading}
            >
              {loading ? (
                <>
                  <span className="spinner"></span>
                  Analyzing...
                </>
              ) : (
                'Analyze Prompt'
              )}
            </button>

            <div className="api-info">
              <small>Backend: POST /api/analyze</small>
            </div>
          </div>
        </div>

        {/* Right Column - Results */}
        <div className="right-column">
          {error && (
            <div className="error-banner">
              <strong>Error:</strong> {error}
            </div>
          )}

          {result && (
            <>
              {/* 1. Risk Level Badge */}
              <div className={`risk-badge risk-${riskLevel.toLowerCase()}`}>
                <span className="risk-label">Risk Level:</span>
                <span className="risk-value">{riskLevel}</span>
              </div>

              {/* 2. Security Analysis Summary */}
              <div className="panel summary-panel">
                <h2>Security Analysis Summary</h2>
                <div className="summary-text">
                  {getSecuritySummary(result.devspec_findings)}
                </div>
              </div>

              {/* 3. Issues Found - Combined Box */}
              <div className="panel issues-panel">
                <h2>Issues Found</h2>
                
                {result.devspec_findings.length === 0 && (!result.guidance || result.guidance.length === 0) ? (
                  <div className="no-issues">
                    ✅ No security issues detected! The prompt is safe to use.
                  </div>
                ) : (
                  <div className="combined-issues-container">
                    {/* Detected Issues Subsection */}
                    {result.devspec_findings.length > 0 && (
                      <div className="issues-subsection">
                        <h3 className="subsection-title">Detected Issues</h3>
                        <div className="issues-container">
                          {['BLOCKER', 'ERROR', 'WARNING', 'INFO'].map(severity => {
                            const findings = groupedFindings[severity];
                            if (findings.length === 0) return null;

                            return (
                              <div key={severity} className="severity-group">
                                <div className={`severity-header severity-${severity.toLowerCase()}`}>
                                  <span className="severity-icon">
                                    {severity === 'BLOCKER' && '🔴'}
                                    {severity === 'ERROR' && '🟠'}
                                    {severity === 'WARNING' && '🟡'}
                                    {severity === 'INFO' && '🟢'}
                                  </span>
                                  <span className="severity-label">{severity}</span>
                                  <span className="severity-count">({findings.length})</span>
                                </div>
                                
                                <div className="findings-list">
                                  {findings.map((finding, idx) => (
                                    <div key={idx} className="finding-item">
                                      <div className="finding-code">{finding.code}</div>
                                      <div className="finding-message">{finding.message}</div>
                                      <div className="finding-suggestion">
                                        <strong>💡 Suggestion:</strong> {finding.suggestion}
                                      </div>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    )}

                    {/* Additional Guidance Subsection */}
                    {result.guidance && result.guidance.length > 0 && (
                      <div className="issues-subsection">
                        <h3 className="subsection-title">Additional Guidance</h3>
                        <div className="guidance-list">
                          {result.guidance.map((item, idx) => (
                            <div key={idx} className="guidance-item">
                              <div className="guidance-title">💡 {item.title}</div>
                              <div className="guidance-detail">{item.detail}</div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* 4. Curated Prompt - At the end */}
              <div className="panel curated-panel">
                <h2>Curated Prompt</h2>
                <div className="curated-prompt">
                  {result.final_curated_prompt}
                </div>
              </div>
            </>
          )}

          {!result && !error && (
            <div className="placeholder">
              <div className="placeholder-icon">🔍</div>
              <p>Enter a prompt and click "Analyze Prompt" to see results</p>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}

export default App;
