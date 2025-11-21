import React, { useState, useEffect, useRef } from 'react';
import { analyzePrompt } from './api';
import './App.css';

// Helper function to convert SEC_* codes to human-readable titles
const getFriendlyIssueName = (code) => {
  const friendlyNames = {
    'SEC_HARDCODED_SECRET': 'Hardcoded Secrets',
    'SEC_PLAINTEXT_PASSWORDS': 'Plaintext Password Storage',
    'SEC_WEAK_HASH_MD5': 'Weak Cryptographic Hash (MD5)',
    'SEC_WEAK_HASH_SHA1': 'Weak Cryptographic Hash (SHA1)',
    'SEC_NO_TLS_FOR_AUTH': 'Missing TLS/HTTPS for Authentication',
    'SEC_HTTP_FOR_AUTH': 'HTTP Used for Authentication',
    'SEC_NO_AUTH_INTERNAL': 'Missing Authentication',
    'SEC_ADMIN_BACKDOOR': 'Admin Backdoor Access',
    'SEC_DEBUG_EXPOSES_SECRETS': 'Debug Endpoint Exposes Secrets',
    'SEC_MISSING_INPUT_VALIDATION': 'Missing Input Validation',
    'SEC_SQL_INJECTION_RISK': 'SQL Injection Risk',
    'SEC_INSECURE_JWT_STORAGE': 'Insecure JWT Storage',
    'SEC_WEAK_SESSION': 'Weak Session Management',
    'SEC_NO_RATE_LIMITING': 'Missing Rate Limiting',
    'SEC_CORS_MISCONFIGURATION': 'CORS Misconfiguration',
    'SEC_SENSITIVE_DATA_LOG': 'Sensitive Data in Logs'
  };
  
  return friendlyNames[code] || code.replace(/^SEC_/, '').replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
};

// Risk level descriptions
const RISK_DESCRIPTIONS = {
  'High': 'Critical or multiple severe security issues detected. Unsafe for production use without changes.',
  'Medium': 'Some important security concerns identified. Should be reviewed and mitigated before production.',
  'Low': 'No major security issues detected. Still review before production, but overall safer.'
};

// Spec quality level based on score
const getSpecQualityLevel = (score) => {
  if (score === null || score === undefined) return null;
  if (score >= 70) return 'Good';
  if (score >= 40) return 'Fair';
  return 'Poor';
};

function App() {
  const [prompt, setPrompt] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);
  const [stage, setStage] = useState('idle'); // 'idle' | 'running_spec' | 'running_security' | 'finalizing' | 'done' | 'error'
  const [showSpecKitDetails, setShowSpecKitDetails] = useState(false);
  const requestInFlight = useRef(false);

  const handleAnalyze = async () => {
    // Validation
    if (!prompt.trim()) {
      setError('Please enter a prompt to analyze');
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);
    setStage('running_spec');
    requestInFlight.current = true;

    try {
      // Start the API request
      const responsePromise = analyzePrompt(prompt);
      
      // Simulate pipeline stages for better UX
      // Stage 1: spec-kit (500-800ms)
      setTimeout(() => {
        if (requestInFlight.current && stage !== 'done' && stage !== 'error') {
          setStage('running_security');
        }
      }, 650);
      
      // Stage 2: security analysis (additional 500-800ms)
      setTimeout(() => {
        if (requestInFlight.current && stage !== 'done' && stage !== 'error') {
          setStage('finalizing');
        }
      }, 1300);
      
      // Wait for actual response
      const response = await responsePromise;
      requestInFlight.current = false;
      setResult(response);
      setStage('done');
    } catch (err) {
      requestInFlight.current = false;
      setError(err.message || 'Failed to analyze prompt. Is the backend running?');
      setStage('error');
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

  // Use risk level from API (which accounts for minimal spec exemption and threshold logic)
  // Don't recalculate client-side as it won't match the backend's sophisticated logic
  const riskLevel = result ? result.risk_level : null;

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
      <main className="main-container">
        {/* Left Column - Header + Input */}
        <div className="left-column">
          <header className="header">
            <h1>SpecAlign</h1>
            <p className="subtitle">Analyze developer prompts for security issues</p>
          </header>

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

          {/* Pipeline Stage Indicator */}
          {(loading || stage === 'done' || stage === 'error') && (
            <div className="panel pipeline-panel">
              <h2>Analysis Pipeline</h2>
              <div className="pipeline-stages">
                {/* Stage 1: Spec-kit */}
                <div className={`pipeline-stage ${
                  stage === 'running_spec' ? 'active' : 
                  ['running_security', 'finalizing', 'done'].includes(stage) ? 'completed' : 
                  stage === 'error' && ['idle', 'running_spec'].includes(stage) ? 'error' : 
                  'pending'
                }`}>
                  <div className="stage-icon">
                    {stage === 'running_spec' && <span className="spinner-small"></span>}
                    {['running_security', 'finalizing', 'done'].includes(stage) && (
                      result?.spec_kit_success === false ? 
                        <span className="icon-warning">⚠</span> : 
                        <span className="icon-check">✓</span>
                    )}
                    {stage === 'pending' && <span className="icon-pending">○</span>}
                  </div>
                  <div className="stage-content">
                    <div className="stage-title">Spec-kit Analysis</div>
                    <div className="stage-subtitle">Workflow & spec validation</div>
                  </div>
                </div>

                {/* Stage 2: Security Analysis */}
                <div className={`pipeline-stage ${
                  stage === 'running_security' ? 'active' : 
                  ['finalizing', 'done'].includes(stage) ? 'completed' : 
                  'pending'
                }`}>
                  <div className="stage-icon">
                    {stage === 'running_security' && <span className="spinner-small"></span>}
                    {['finalizing', 'done'].includes(stage) && <span className="icon-check">✓</span>}
                    {['idle', 'running_spec'].includes(stage) && <span className="icon-pending">○</span>}
                  </div>
                  <div className="stage-content">
                    <div className="stage-title">Security Analysis</div>
                    <div className="stage-subtitle">Dev-spec-kit rules engine</div>
                  </div>
                </div>

                {/* Stage 3: Finalizing */}
                <div className={`pipeline-stage ${
                  stage === 'finalizing' ? 'active' : 
                  stage === 'done' ? 'completed' : 
                  'pending'
                }`}>
                  <div className="stage-icon">
                    {stage === 'finalizing' && <span className="spinner-small"></span>}
                    {stage === 'done' && <span className="icon-check">✓</span>}
                    {!['finalizing', 'done'].includes(stage) && <span className="icon-pending">○</span>}
                  </div>
                  <div className="stage-content">
                    <div className="stage-title">Finalizing</div>
                    <div className="stage-subtitle">Risk assessment & curation</div>
                  </div>
                </div>
              </div>

              {stage === 'done' && (
                <div className="pipeline-complete">
                  <span className="complete-icon">✓</span> Analysis complete
                </div>
              )}
              {stage === 'error' && (
                <div className="pipeline-error">
                  <span className="error-icon">✕</span> Analysis failed
                </div>
              )}
            </div>
          )}
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
              {/* 1. Risk Level Badge and Spec Quality Score */}
              <div className="analysis-header">
                <div className="risk-section">
                  <div className={`risk-badge risk-${riskLevel.toLowerCase()}`}>
                    <span className="risk-label">Risk Level:</span>
                    <span className="risk-value">{riskLevel}</span>
                  </div>
                  <p className="risk-description">{RISK_DESCRIPTIONS[riskLevel] || ''}</p>
                </div>

                {/* Spec Quality Score (if available) */}
                {result.spec_quality_score !== null && result.spec_quality_score !== undefined && (
                  <div className="quality-section">
                    <div className="quality-score-container">
                      <div className="quality-label">Spec Quality</div>
                      <div className={`quality-score quality-${getSpecQualityLevel(result.spec_quality_score)?.toLowerCase()}`}>
                        <span className="score-value">{result.spec_quality_score}</span>
                        <span className="score-max">/100</span>
                      </div>
                      <div className="quality-level">{getSpecQualityLevel(result.spec_quality_score)}</div>
                    </div>
                    <p className="quality-description">
                      Measures how complete and well-structured the spec is (based on Spec Kit).
                    </p>
                  </div>
                )}
              </div>

              {/* 2. Spec Breakdown (if structure available) */}
              {result.spec_kit_structure && (
                <div className="panel spec-breakdown-panel">
                  <div className="panel-header">
                    <h2>Spec Breakdown</h2>
                    <span className="panel-subtitle">Structured view of your project spec</span>
                  </div>
                  
                  <div className="spec-breakdown-content">
                    {/* Features */}
                    {result.spec_kit_structure.features && result.spec_kit_structure.features.length > 0 && (
                      <div className="spec-category">
                        <div className="category-label">Features & Requirements</div>
                        <div className="category-items">
                          {result.spec_kit_structure.features.map((item, idx) => (
                            <span key={idx} className="spec-chip">{item}</span>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Entities */}
                    {result.spec_kit_structure.entities && result.spec_kit_structure.entities.length > 0 && (
                      <div className="spec-category">
                        <div className="category-label">Data Models & Entities</div>
                        <div className="category-items">
                          {result.spec_kit_structure.entities.map((item, idx) => (
                            <span key={idx} className="spec-chip">{item}</span>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Flows */}
                    {result.spec_kit_structure.flows && result.spec_kit_structure.flows.length > 0 && (
                      <div className="spec-category">
                        <div className="category-label">User Flows & Workflows</div>
                        <div className="category-items">
                          {result.spec_kit_structure.flows.map((item, idx) => (
                            <span key={idx} className="spec-chip">{item}</span>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Configuration */}
                    {result.spec_kit_structure.configuration && result.spec_kit_structure.configuration.length > 0 && (
                      <div className="spec-category">
                        <div className="category-label">Configuration</div>
                        <div className="category-items">
                          {result.spec_kit_structure.configuration.map((item, idx) => (
                            <span key={idx} className="spec-chip">{item}</span>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Error Handling */}
                    {result.spec_kit_structure.error_handling && result.spec_kit_structure.error_handling.length > 0 && (
                      <div className="spec-category">
                        <div className="category-label">Error Handling</div>
                        <div className="category-items">
                          {result.spec_kit_structure.error_handling.map((item, idx) => (
                            <span key={idx} className="spec-chip">{item}</span>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Testing */}
                    {result.spec_kit_structure.testing && result.spec_kit_structure.testing.length > 0 && (
                      <div className="spec-category">
                        <div className="category-label">Testing Strategy</div>
                        <div className="category-items">
                          {result.spec_kit_structure.testing.map((item, idx) => (
                            <span key={idx} className="spec-chip">{item}</span>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Logging */}
                    {result.spec_kit_structure.logging && result.spec_kit_structure.logging.length > 0 && (
                      <div className="spec-category">
                        <div className="category-label">Logging & Monitoring</div>
                        <div className="category-items">
                          {result.spec_kit_structure.logging.map((item, idx) => (
                            <span key={idx} className="spec-chip">{item}</span>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Authentication */}
                    {result.spec_kit_structure.authentication && result.spec_kit_structure.authentication.length > 0 && (
                      <div className="spec-category">
                        <div className="category-label">Authentication & Authorization</div>
                        <div className="category-items">
                          {result.spec_kit_structure.authentication.map((item, idx) => (
                            <span key={idx} className="spec-chip">{item}</span>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Data Storage */}
                    {result.spec_kit_structure.data_storage && result.spec_kit_structure.data_storage.length > 0 && (
                      <div className="spec-category">
                        <div className="category-label">Data Storage</div>
                        <div className="category-items">
                          {result.spec_kit_structure.data_storage.map((item, idx) => (
                            <span key={idx} className="spec-chip">{item}</span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* 3. Spec Quality Warnings (if warnings exist) */}
              {result.spec_quality_warnings && result.spec_quality_warnings.length > 0 && (
                <div className="panel spec-quality-panel">
                  <div className="panel-header">
                    <h2>Missing or Weak Areas</h2>
                    <span className="panel-subtitle">Potential gaps in your project spec</span>
                  </div>
                  
                  <div className="quality-warnings">
                    <div className="quality-notice">
                      <span className="notice-icon">⚠</span>
                      <div className="notice-text">
                        These are spec quality observations, not security issues.
                        Consider addressing them to improve project clarity.
                      </div>
                    </div>
                    
                    <div className="warnings-list">
                      {result.spec_quality_warnings.map((warning, idx) => (
                        <div key={idx} className="warning-item">
                          <span className="warning-bullet">•</span>
                          <span className="warning-text">{warning}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {/* 4. Security Analysis - Merged Panel */}
              <div className="panel security-analysis-panel">
                <div className="panel-header">
                  <h2>Security Analysis</h2>
                  <span className="panel-subtitle">
                    {result.devspec_findings.length === 0 
                      ? 'No issues detected'
                      : `${result.devspec_findings.length} issue${result.devspec_findings.length !== 1 ? 's' : ''} found`}
                  </span>
                </div>

                {result.devspec_findings.length === 0 ? (
                  <div className="no-issues">
                    <span className="success-icon">✓</span>
                    <div className="no-issues-text">
                      <strong>No security issues detected.</strong>
                      <p>The prompt appears safe to use.</p>
                    </div>
                  </div>
                ) : (
                  <>
                    {/* Security Summary */}
                    <div className="security-summary">
                      {getSecuritySummary(result.devspec_findings)}
                    </div>

                    {/* Findings grouped by severity */}
                    <div className="security-findings">
                      {['BLOCKER', 'ERROR', 'WARNING', 'INFO'].map(severity => {
                        const findings = groupedFindings[severity];
                        if (findings.length === 0) return null;

                        const severityLabels = {
                          'BLOCKER': 'Blockers',
                          'ERROR': 'Errors',
                          'WARNING': 'Warnings',
                          'INFO': 'Info'
                        };

                        return (
                          <div key={severity} className="severity-group">
                            <div className={`severity-header severity-${severity.toLowerCase()}`}>
                              <span className="severity-label">{severityLabels[severity]}</span>
                              <span className="severity-count">{findings.length}</span>
                            </div>
                            
                            <div className="findings-list">
                              {findings.map((finding, idx) => (
                                <div key={idx} className={`finding-item finding-${severity.toLowerCase()}`}>
                                  <div className="finding-header">
                                    <div className="finding-title">{getFriendlyIssueName(finding.code)}</div>
                                    <div className="finding-code">{finding.code}</div>
                                  </div>
                                  <div className="finding-message">{finding.message}</div>
                                  {finding.suggestion && (
                                    <div className="finding-suggestion">
                                      <span className="suggestion-label">Recommendation:</span> {finding.suggestion}
                                    </div>
                                  )}
                                </div>
                              ))}
                            </div>
                          </div>
                        );
                      })}
                    </div>

                    {/* Additional Guidance (if present) */}
                    {result.guidance && result.guidance.length > 0 && (
                      <div className="additional-guidance">
                        <div className="guidance-header">Additional Guidance</div>
                        <div className="guidance-list">
                          {result.guidance.map((item, idx) => (
                            <div key={idx} className="guidance-item">
                              <div className="guidance-title">{item.title}</div>
                              <div className="guidance-detail">{item.detail}</div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </>
                )}
              </div>

              {/* 6. Spec-kit Analysis (if enabled) */}
              {result.spec_kit_enabled && (
                <div className="panel spec-kit-panel">
                  <div className="spec-kit-header">
                    <h2>Spec-kit Analysis</h2>
                    {result.spec_kit_success ? (
                      <span className="badge badge-success">Success</span>
                    ) : (
                      <span className="badge badge-warning">Failed</span>
                    )}
                  </div>
                  
                  <div className="spec-kit-notice">
                    <span className="notice-icon">ℹ</span>
                    <div className="notice-text">
                      Spec-kit provides workflow and spec-driven development insights. 
                      Security decisions (risk level, findings) are determined by the security analyzer.
                    </div>
                  </div>

                  {result.spec_kit_success ? (
                    <div className="spec-kit-content">
                      {result.spec_kit_summary && (
                        <div className="spec-kit-summary">
                          <strong>Summary:</strong> {result.spec_kit_summary}
                        </div>
                      )}
                      
                      {result.spec_kit_raw_output && (
                        <div className="spec-kit-details">
                          <button 
                            className="details-toggle"
                            onClick={() => setShowSpecKitDetails(!showSpecKitDetails)}
                          >
                            {showSpecKitDetails ? '▼' : '▶'} View raw output
                          </button>
                          {showSpecKitDetails && (
                            <pre className="spec-kit-raw">
                              {typeof result.spec_kit_raw_output === 'string' 
                                ? result.spec_kit_raw_output 
                                : JSON.stringify(result.spec_kit_raw_output, null, 2)}
                            </pre>
                          )}
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="spec-kit-failure">
                      <span className="failure-icon">⚠</span>
                      <div className="failure-text">
                        Spec-kit run failed. Fallback to security analysis only. 
                        The security analyzer has completed successfully.
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* 7. Curated Prompt - At the end */}
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
              <p>Enter a prompt and click "Analyze Prompt" to see results</p>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}

export default App;
