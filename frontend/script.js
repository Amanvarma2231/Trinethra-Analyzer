/**
 * Trinethra Supervisor Feedback Analyzer - Frontend Core
 * Version: 2.1 (Professional Grade)
 */

const API_BASE_URL = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' 
    ? 'http://localhost:8005' 
    : 'https://trinethra-analyzer-backend.onrender.com'; // Adjust this to your actual backend URL if different
let currentAnalysisId = null;
let isAnalyzing = false;

// DOM Elements
const elements = {
    transcriptInput: document.getElementById('transcriptInput'),
    analyzeButton: document.getElementById('analyzeButton'),
    clearBtn: document.getElementById('clearBtn'),
    sampleBtn: document.getElementById('sampleBtn'),
    newAnalysisBtn: document.getElementById('newAnalysisBtn'),
    modelSelect: document.getElementById('modelSelect'),
    statusDot: document.getElementById('statusDot'),
    statusText: document.getElementById('statusText'),
    historyList: document.getElementById('historyList'),
    resultsContent: document.getElementById('resultsContent'),
    emptyState: document.getElementById('emptyState'),
    loadingState: document.getElementById('loadingState'),
    progressBar: document.getElementById('progressBar'),
    loadingMessage: document.getElementById('loadingMessage'),
    scoreValue: document.getElementById('scoreValue'),
    scoreCircle: document.getElementById('scoreCircle'),
    levelText: document.getElementById('levelText'),
    justificationText: document.getElementById('justificationText'),
    confidenceBadge: document.getElementById('confidenceBadge'),
    evidenceList: document.getElementById('evidenceList'),
    kpiList: document.getElementById('kpiList'),
    gapList: document.getElementById('gapList'),
    questionList: document.getElementById('questionList'),
    charCount: document.getElementById('charCount'),
    exportPdfBtn: document.getElementById('exportPdfBtn'),
    exportCsvBtn: document.getElementById('exportCsvBtn'),
    copyAnalysisBtn: document.getElementById('copyAnalysisBtn'),
    historySearch: document.getElementById('historySearch'),
    totalAnalyzed: document.getElementById('totalAnalyzed'),
    avgScore: document.getElementById('avgScore'),
    scoreStroke: document.getElementById('scoreStroke'),
    sentimentChart: document.getElementById('sentimentChart'),
    sentimentSummary: document.getElementById('sentimentSummary'),
    resultActions: document.getElementById('resultActions')
};

// --- Initialization ---

document.addEventListener('DOMContentLoaded', () => {
    checkHealth();
    loadHistory();
    loadStats();
    initCommandCenter();
    setupEventListeners();
    
    // Auto-refresh health every 30 seconds
    setInterval(checkHealth, 30000);
});

function setupEventListeners() {
    elements.analyzeButton.addEventListener('click', runAnalysis);
    elements.clearBtn.addEventListener('click', clearInput);
    elements.newAnalysisBtn.addEventListener('click', clearAll);
    elements.sampleBtn.addEventListener('click', loadSample);
    elements.transcriptInput.addEventListener('input', () => {
        updateCharCount();
        handleRealtimeInput();
    });
    elements.exportPdfBtn.addEventListener('click', exportPdf);
    elements.exportCsvBtn.addEventListener('click', exportCsv);
    elements.copyAnalysisBtn.addEventListener('click', copyResultsToClipboard);
    elements.historySearch.addEventListener('input', () => {
        loadHistory(elements.historySearch.value);
        updateTrendReport(elements.historySearch.value);
    });
    
    document.getElementById('themeToggle').addEventListener('click', toggleTheme);
    
    const voiceBtn = document.getElementById('voiceBtn');
    if (voiceBtn) voiceBtn.addEventListener('click', toggleDictation);
    
    document.getElementById('helpBtn').addEventListener('click', () => {
        showToast('Contact Developer: amanvarma@example.com', 'info');
    });
    
    // Keyboard shortcut: Ctrl+Enter
    elements.transcriptInput.addEventListener('keydown', (e) => {
        if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
            runAnalysis();
        }
    });
}

// --- API Functions ---

async function checkHealth() {
    try {
        const response = await fetch(`${API_BASE_URL}/health`);
        const data = await response.json();
        
        if (data.ollama === 'connected') {
            elements.statusDot.className = 'dot online';
            elements.statusText.textContent = `Ollama Online (${data.current_model})`;
            elements.analyzeButton.disabled = false;
        } else {
            elements.statusDot.className = 'dot';
            elements.statusText.textContent = 'Ollama Offline';
            elements.analyzeButton.disabled = true;
        }
    } catch (e) {
        elements.statusDot.className = 'dot';
        elements.statusText.textContent = 'Backend Offline';
        elements.analyzeButton.disabled = true;
    }
}

async function loadHistory(filter = '') {
    try {
        const response = await fetch(`${API_BASE_URL}/history`);
        let history = await response.json();
        
        if (filter) {
            const query = filter.toLowerCase();
            history = history.filter(item => 
                item.transcript.toLowerCase().includes(query) || 
                item.score.toString().includes(query)
            );
        }

        elements.historyList.innerHTML = '';
        if (history.length === 0) {
            elements.historyList.innerHTML = `<div class="text-dim" style="font-size: 0.8rem; text-align: center; padding: 1rem;">${filter ? 'No matches found' : 'No history yet'}</div>`;
            return;
        }
        
        history.forEach(item => {
            const date = new Date(item.timestamp).toLocaleDateString();
            const div = document.createElement('div');
            div.className = 'history-item fade-in';
            div.innerHTML = `
                <div class="score-tag" style="color: ${getScoreColor(item.score)}">${item.score}</div>
                <div class="meta">${date}</div>
                <div style="font-size: 0.8rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; color: var(--text-dim);">
                    ${item.transcript.substring(0, 40)}...
                </div>
            `;
            div.onclick = () => loadResult(item.id);
            elements.historyList.appendChild(div);
        });
    } catch (e) {
        console.error('Failed to load history:', e);
    }
}

async function loadStats() {
    try {
        const response = await fetch(`${API_BASE_URL}/stats`);
        const data = await response.json();
        
        animateCounter(elements.totalAnalyzed, parseInt(elements.totalAnalyzed.textContent) || 0, data.total || 0);
        animateCounter(elements.avgScore, parseFloat(elements.avgScore.textContent) || 0, data.avg_score || 0, 1);
    } catch (e) {
        console.error('Failed to load stats:', e);
    }
}

function animateCounter(el, start, end, decimals = 0) {
    const duration = 1000;
    const startTime = performance.now();
    
    function update(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        const current = start + (end - start) * progress;
        
        el.textContent = current.toFixed(decimals);
        
        if (progress < 1) {
            requestAnimationFrame(update);
        }
    }
    
    requestAnimationFrame(update);
}

async function runAnalysis() {
    if (isAnalyzing) return;
    
    const transcript = elements.transcriptInput.value.trim();
    if (transcript.length < 50) {
        showToast('Transcript too short (min 50 chars)', 'error');
        return;
    }

    isAnalyzing = true;
    showState('loading');
    updateProgress(0, 'Starting analysis engine...');
    
    try {
        const model = elements.modelSelect.value;
        const response = await fetch(`${API_BASE_URL}/analyze/stream`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ transcript, model })
        });

        const reader = response.body.getReader();
        const decoder = new TextDecoder();

        while (true) {
            const { value, done } = await reader.read();
            if (done) break;
            
            const chunk = decoder.decode(value);
            const lines = chunk.split('\n');
            
            for (const line of lines) {
                if (!line) continue;
                try {
                    const data = JSON.parse(line);
                    if (data.type === 'progress') {
                        updateProgress(data.progress, data.message);
                    } else if (data.type === 'complete') {
                        currentAnalysisId = data.id;
                        renderResults(data.data);
                        loadHistory(); 
                        loadStats();
                    }
                } catch (e) {
                    console.warn('Failed to parse chunk:', line);
                }
            }
        }
    } catch (e) {
        showToast(`Analysis failed: ${e.message}`, 'error');
        showState('empty');
    } finally {
        isAnalyzing = false;
    }
}

async function loadResult(id) {
    showState('loading');
    updateProgress(50, 'Loading from database...');
    
    try {
        // Find in history or fetch from server
        const response = await fetch(`${API_BASE_URL}/history`);
        const history = await response.json();
        const item = history.find(i => i.id === id);
        
        if (item) {
            elements.transcriptInput.value = item.transcript;
            updateCharCount();
            currentAnalysisId = item.id;
            renderResults(item.results);
        }
    } catch (e) {
        showToast('Failed to load result', 'error');
        showState('empty');
    }
}

async function exportPdf() {
    if (!currentAnalysisId) return;
    window.open(`${API_BASE_URL}/export/${currentAnalysisId}`, '_blank');
}

async function exportCsv() {
    window.open(`${API_BASE_URL}/export/csv`, '_blank');
    showToast('CSV Export Started', 'success');
}

function copyResultsToClipboard() {
    const score = elements.scoreValue.textContent;
    const level = elements.levelText.textContent;
    const justification = elements.justificationText.textContent;
    
    const text = `TRINETHRA ANALYSIS REPORT\n=========================\nScore: ${score}/10\nLevel: ${level}\n\nJustification: ${justification}\n\nGenerated via Trinethra AI`;
    
    navigator.clipboard.writeText(text).then(() => {
        showToast('Report copied to clipboard!', 'success');
    });
}

// --- Dictation Logic ---
let isDictating = false;
let recognition;

if ('webkitSpeechRecognition' in window) {
    recognition = new webkitSpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;

    recognition.onresult = (event) => {
        let interimTranscript = '';
        for (let i = event.resultIndex; i < event.results.length; ++i) {
            if (event.results[i].isFinal) {
                elements.transcriptInput.value += event.results[i][0].transcript + ' ';
            } else {
                interimTranscript += event.results[i][0].transcript;
            }
        }
        updateCharCount();
    };

    recognition.onend = () => {
        isDictating = false;
        document.getElementById('voiceBtn').innerHTML = '🎤 Start Dictation';
        document.getElementById('voiceBtn').classList.remove('btn-danger');
    };
}

function toggleDictation() {
    if (!recognition) {
        showToast('Speech recognition not supported in this browser.', 'error');
        return;
    }

    if (isDictating) {
        recognition.stop();
    } else {
        recognition.start();
        isDictating = true;
        document.getElementById('voiceBtn').innerHTML = '🛑 Stop Dictation';
        document.getElementById('voiceBtn').classList.add('btn-danger');
        showToast('Listening...', 'success');
    }
}

function renderResults(results) {
    elements.resultsContent.classList.remove('hidden');
    elements.emptyState.classList.add('hidden');
    elements.resultActions.classList.remove('hidden');

    // 1. Animated Score Gauge
    const score = results.scoring.score;
    elements.scoreValue.textContent = score;
    const dashArray = `${score * 10}, 100`;
    elements.scoreStroke.setAttribute('stroke-dasharray', dashArray);
    elements.scoreStroke.setAttribute('stroke', getScoreColor(score));

    elements.levelText.textContent = results.scoring.level_description;
    elements.justificationText.textContent = results.scoring.justification;
    
    const confidence = results.scoring.confidence;
    elements.confidenceBadge.textContent = `Confidence: ${confidence.toUpperCase()}`;
    elements.confidenceBadge.className = `confidence-badge ${confidence}`;

    // 2. Sentiment Donut Chart
    const stats = results.sentiment_stats || {positive: 50, negative: 30, neutral: 20};
    const pos = stats.positive;
    const neg = stats.negative;
    const neu = stats.neutral;
    
    elements.sentimentChart.style.background = `conic-gradient(
        var(--success) 0deg ${pos * 3.6}deg,
        var(--warning) ${pos * 3.6}deg ${(pos + neu) * 3.6}deg,
        var(--error) ${(pos + neu) * 3.6}deg 360deg
    )`;
    elements.sentimentSummary.innerHTML = `
        <span style="color: var(--success)">● ${pos}% Pos</span> &nbsp;
        <span style="color: var(--warning)">● ${neu}% Neu</span> &nbsp;
        <span style="color: var(--error)">● ${neg}% Neg</span>
    `;

    // 3. Evidence with Smart Highlighting
    elements.evidenceList.innerHTML = '';
    results.evidence.evidence.forEach(item => {
        const div = document.createElement('div');
        div.className = 'evidence-item';
        div.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 5px;">
                <span class="sentiment-tag ${item.sentiment}">${item.sentiment.toUpperCase()}</span>
                <span style="font-size: 0.7rem; color: var(--text-dim); font-weight: 600;">${item.dimension.toUpperCase()}</span>
            </div>
            <div class="quote">"${item.quote}"</div>
            <div class="explanation">${item.explanation}</div>
        `;
        div.onclick = () => highlightInTranscript(item.quote);
        elements.evidenceList.appendChild(div);
    });

    // 4. KPI Mapping
    elements.kpiList.innerHTML = '';
    results.kpi_mapping.kpi_mappings.forEach(item => {
        const div = document.createElement('div');
        div.className = 'kpi-card';
        div.innerHTML = `
            <div class="kpi-name">${item.kpi}</div>
            <div class="kpi-evidence">${item.evidence}</div>
        `;
        elements.kpiList.appendChild(div);
    });

    // Gaps
    elements.gapList.innerHTML = '';
    (results.gap_analysis.gaps || []).forEach(item => {
        const div = document.createElement('div');
        div.style.marginBottom = '10px';
        div.style.fontSize = '0.85rem';
        div.innerHTML = `
            <span style="color: var(--warning);">⚠️ ${item.dimension}:</span> 
            <span class="text-dim">${item.missing_information}</span>
        `;
        elements.gapList.appendChild(div);
    });

    // Questions
    elements.questionList.innerHTML = '';
    (results.followup_questions.followup_questions || []).forEach(item => {
        const div = document.createElement('div');
        div.style.padding = '10px';
        div.style.background = 'rgba(255,255,255,0.03)';
        div.style.borderRadius = '6px';
        div.style.marginBottom = '8px';
        div.style.fontSize = '0.85rem';
        div.innerHTML = `
            <div style="font-weight: 600; margin-bottom: 4px;">Q: ${item.question}</div>
            <div style="font-size: 0.7rem; color: var(--text-dim);">Goal: ${item.purpose}</div>
        `;
        elements.questionList.appendChild(div);
    });
}

// --- Utilities ---

function showState(state) {
    elements.emptyState.classList.add('hidden');
    elements.loadingState.classList.add('hidden');
    elements.resultsContent.classList.add('hidden');
    elements.resultActions.classList.add('hidden');
    
    if (state === 'loading') elements.loadingState.classList.remove('hidden');
    else if (state === 'results') {
        elements.resultsContent.classList.remove('hidden');
        elements.resultActions.classList.remove('hidden');
    }
    else elements.emptyState.classList.remove('hidden');
}

function updateProgress(val, msg) {
    elements.progressBar.style.width = `${val}%`;
    elements.loadingMessage.textContent = msg;
}

function updateCharCount() {
    const len = elements.transcriptInput.value.length;
    elements.charCount.textContent = `${len} characters`;
}

function clearInput() {
    elements.transcriptInput.value = '';
    updateCharCount();
}

function clearAll() {
    clearInput();
    showState('empty');
    currentAnalysisId = null;
}

function highlightInTranscript(quote) {
    const transcript = elements.transcriptInput.value;
    const index = transcript.toLowerCase().indexOf(quote.toLowerCase());
    
    if (index !== -1) {
        elements.transcriptInput.focus();
        elements.transcriptInput.setSelectionRange(index, index + quote.length);
        
        // Scroll to the selection
        const lineHeight = 24; // approx
        const linesBefore = transcript.substring(0, index).split('\n').length;
        elements.transcriptInput.scrollTop = (linesBefore - 5) * lineHeight;
        
        showToast('Highlighted in transcript', 'success');
    } else {
        showToast('Quote not found in original text', 'warning');
    }
}

async function loadSample() {
    try {
        const response = await fetch('./data/sample-transcripts.json');
        const samples = await response.json();
        
        // Pick a random sample or cycle through them
        const randomIndex = Math.floor(Math.random() * samples.length);
        const sample = samples[randomIndex];
        
        elements.transcriptInput.value = sample.transcript;
        updateCharCount();
        showToast(`Loaded sample for ${sample.fellow_name}`, 'success');
    } catch (e) {
        console.error('Failed to load sample data:', e);
        // Fallback to hardcoded sample
        elements.transcriptInput.value = `Interviewer: Good morning Mr. Khan... (fallback sample)`;
        updateCharCount();
    }
}

function getScoreColor(score) {
    if (score >= 7) return 'var(--success)';
    if (score >= 4) return 'var(--warning)';
    return 'var(--danger)';
}

function showToast(msg, type = 'info') {
    const toast = document.getElementById('toast');
    const div = document.createElement('div');
    div.style.padding = '1rem 2rem';
    div.style.background = type === 'error' ? 'var(--danger)' : type === 'success' ? 'var(--success)' : 'var(--bg-accent)';
    div.style.color = 'white';
    div.style.borderRadius = '8px';
    div.style.marginBottom = '10px';
    div.style.boxShadow = '0 10px 30px rgba(0,0,0,0.5)';
    div.style.animation = 'slideIn 0.3s ease';
    div.textContent = msg;
    
    toast.appendChild(div);
    setTimeout(() => {
        div.style.opacity = '0';
        div.style.transform = 'translateY(20px)';
        div.style.transition = 'all 0.5s ease';
        setTimeout(() => div.remove(), 500);
    }, 3000);
}

function initCommandCenter() {
    const greeting = document.getElementById('welcomeGreeting');
    const hour = new Date().getHours();
    let text = "Ready to Analyze";
    if (hour < 12) text = "Good Morning! Ready to Analyze?";
    else if (hour < 18) text = "Good Afternoon! Ready to Analyze?";
    else text = "Good Evening! Ready to Analyze?";
    if (greeting) greeting.textContent = text;

    // Pro-Tips Rotation
    const tips = [
        "Encourage supervisors to mention specific numbers for accurate KPI mapping.",
        "Clear, structured transcripts yield 25% better sentiment analysis.",
        "Identify specific training gaps by asking about technical skills directly.",
        "High-confidence results come from transcripts longer than 500 characters."
    ];
    const tipEl = document.getElementById('proTipText');
    if (tipEl) tipEl.textContent = `"${tips[Math.floor(Math.random() * tips.length)]}"`;
    
    // Resume Last Logic
    const resumeBtn = document.getElementById('resumeLastBtn');
    if (resumeBtn) {
        resumeBtn.onclick = async () => {
            try {
                const response = await fetch(`${API_BASE_URL}/history?limit=1`);
                const history = await response.json();
                if (history.length > 0) loadResult(history[0].id);
                else showToast('No history found to resume', 'error');
            } catch (e) {
                showToast('Unable to connect to history', 'error');
            }
        };
    }
}

function toggleTheme() {
    const isLight = document.body.classList.toggle('light-mode');
    const icon = document.getElementById('themeIcon');
    if (isLight) {
        icon.innerHTML = '<path d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364-6.364l-.707.707M6.343 17.657l-.707.707m0-11.314l.707.707m11.314 11.314l.707.707M12 8a4 4 0 1 1 0 8 4 4 0 0 1 0-8z"></path>';
        showToast('Switched to Normal Light Theme', 'info');
    } else {
        icon.innerHTML = '<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path>';
        showToast('Switched to Professional Dark Theme', 'info');
    }
}

function updateAIBubble(text) {
    const bubble = document.getElementById('aiBubble');
    const textEl = document.getElementById('bubbleText');
    
    if (text.length < 20) {
        bubble.classList.add('hidden');
        return;
    }

    const insights = [
        { key: 'training', msg: "I detect a training gap. Consider asking about technical SOPs." },
        { key: 'good', msg: "Great positive reinforcement! This will boost morale." },
        { key: 'data', msg: "You're focusing on data. Good for objective mapping!" },
        { key: 'slow', msg: "The conversation seems focused on delays. Flag this as a bottleneck." }
    ];

    const match = insights.find(i => text.toLowerCase().includes(i.key));
    if (match) {
        bubble.classList.remove('hidden');
        textEl.textContent = match.msg;
    }
}

async function updateTrendReport(query) {
    const trendCard = document.getElementById('trendCard');
    const trendContent = document.getElementById('trendContent');
    const sparkline = document.getElementById('trendSparkline');
    
    if (!query || query.length < 3) {
        trendCard.classList.add('hidden');
        return;
    }

    try {
        const response = await fetch(`${API_BASE_URL}/history?search=${query}`);
        const items = await response.json();
        
        if (items.length < 2) {
            trendCard.classList.add('hidden');
            return;
        }

        const scores = items.map(i => i.score).reverse();
        const latest = scores[scores.length - 1];
        const prev = scores[scores.length - 2];
        const diff = latest - prev;
        
        trendCard.classList.remove('hidden');
        trendContent.innerHTML = `
            <div style="margin-bottom: 4px;">
                Insights for <strong>${query}</strong>: 
                <span class="trend-badge ${diff >= 0 ? 'trend-up' : 'trend-down'}">
                    ${diff >= 0 ? '↑' : '↓'} ${Math.abs(diff).toFixed(1)}
                </span>
            </div>
        `;

        drawSparkline(sparkline, scores);
    } catch (e) {
        console.error('Trend calculation failed', e);
    }
}

function drawSparkline(svg, data) {
    const max = 10;
    const width = 100;
    const height = 30;
    const step = width / (data.length - 1);
    
    let pathData = `M 0 ${height - (data[0] / max * height)}`;
    data.forEach((val, i) => {
        pathData += ` L ${i * step} ${height - (val / max * height)}`;
    });
    
    svg.innerHTML = `<path d="${pathData}" />`;
}

// --- Real-time Logic ---
let realtimeDebounce;
let autoSaveTimeout;

function handleRealtimeInput() {
    clearTimeout(realtimeDebounce);
    clearTimeout(autoSaveTimeout);

    realtimeDebounce = setTimeout(() => {
        const text = elements.transcriptInput.value;
        
        // 1. Instant Fellow Recognition
        const fellowMatch = text.match(/(Fellow|Mr\.|Ms\.)\s+([A-Z][a-z]+)/);
        if (fellowMatch) {
            const name = fellowMatch[2];
            document.getElementById('statusText').textContent = `Identifying: ${name}...`;
            updateTrendReport(name);
        }

    // 2. Fast Sentiment Estimation & AI Thought Bubble
    updateLiveTone(text);
    updateAIBubble(text);
    }, 500);

    autoSaveTimeout = setTimeout(saveDraft, 3000);
}

function updateLiveTone(text) {
    const posWords = ['good', 'excellent', 'great', 'consistent', 'improved', 'helped', 'efficiency', 'positive', 'happy'];
    const negWords = ['bad', 'poor', 'issue', 'problem', 'delay', 'gap', 'slow', 'negative', 'angry'];
    
    let score = 50; // Neutral
    const words = text.toLowerCase().split(/\s+/);
    
    words.forEach(w => {
        if (posWords.includes(w)) score += 5;
        if (negWords.includes(w)) score -= 5;
    });

    score = Math.max(10, Math.min(90, score));
    const meter = document.getElementById('liveMeterBar');
    if (meter) {
        meter.style.width = `${score}%`;
        meter.style.background = score > 60 ? 'var(--success)' : score < 40 ? 'var(--danger)' : 'var(--warning)';
    }
}

function saveDraft() {
    const text = elements.transcriptInput.value;
    if (text.length > 10) {
        localStorage.setItem('trinethra_draft', text);
        const status = document.getElementById('autoSaveStatus');
        if (status) {
            status.textContent = 'Draft Saved';
            setTimeout(() => status.textContent = '', 2000);
        }
    }
}

// Load draft on startup
document.addEventListener('DOMContentLoaded', () => {
    const draft = localStorage.getItem('trinethra_draft');
    if (draft && elements.transcriptInput) {
        elements.transcriptInput.value = draft;
        updateCharCount();
        handleRealtimeInput();
    }
});
