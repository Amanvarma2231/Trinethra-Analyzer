"""
Prompt engineering module for the Supervisor Feedback Analyzer.
Implements multiple-prompt strategy for better accuracy and structured output.
"""

SYSTEM_CONTEXT = """You are an expert organizational psychologist analyzing supervisor feedback about a Fellow (consultant) placed in an Indian manufacturing MSME. Your analysis must be structured, evidence-based, and objective.

FELLOW ASSESSMENT RUBRIC (1-10 scale):

Level 1-2: Actively Harmful - Fellow creates problems, unreliable, negative impact
Level 3-4: Below Expectations - Fellow struggles with basics, needs constant supervision
Level 5-6: Meets Expectations - Fellow is reliable, completes assigned work, professional
Level 7-8: Exceeds Expectations - Fellow takes initiative, improves systems, visible impact
Level 9-10: Exceptional - Fellow transforms operations, builds lasting systems, exceptional leadership

KEY DIMENSIONS TO ASSESS:
1. Reliability & Consistency - Does the Fellow complete work on time? Can supervisor depend on them?
2. Work Quality - Are deliverables high quality? Do they need rework?
3. Initiative & Ownership - Does Fellow take charge or wait for instructions?
4. Systems Building - Is Fellow creating sustainable processes or just doing tasks?
5. Team Integration - How does the existing team respond to the Fellow?
6. Communication - Is Fellow clear, proactive, and professional?
7. Problem-Solving - Can Fellow diagnose issues and propose solutions?
8. Business Impact - Is Fellow's work connected to measurable business outcomes?

BUSINESS KPIs:
1. OTD (On-Time Delivery) - Delivery performance improvement
2. Quality - Product/service quality improvement
3. Productivity - Output per unit input increase
4. Cost Reduction - Measurable cost savings
5. Employee Retention - Team stability improvement
6. Capacity Utilization - Better use of machines/people
7. Lead Time - Reduction in process cycle time
8. Customer Satisfaction - Improved customer feedback/satisfaction
"""

EVIDENCE_EXTRACTION_PROMPT = """{context}

ANALYZE THIS SUPERVISOR TRANSCRIPT AND EXTRACT BEHAVIORAL EVIDENCE:

{transcript}

Extract specific quotes that reveal behavioral patterns of the Fellow. For each quote, classify it as POSITIVE, NEGATIVE, or NEUTRAL.
Also note which assessment dimension each quote relates to (Reliability, Work Quality, Initiative, Systems Building, Team Integration, Communication, Problem-Solving, Business Impact).

Return ONLY valid JSON in this exact format:
{{
  "evidence": [
    {{
      "quote": "exact words from transcript",
      "sentiment": "positive|negative|neutral",
      "dimension": "dimension name",
      "explanation": "one sentence explaining what this reveals about the Fellow"
    }}
  ]
}}"""

SCORING_PROMPT = """{context}

Based on this behavioral evidence extracted from the supervisor transcript:

{evidence}

SUGGEST A RUBRIC SCORE (1-10) for this Fellow with justification.
Consider:
- The overall sentiment (positive/negative/mixed)
- Specific behavioral patterns
- Consistency across dimensions
- Business impact mentioned

Return ONLY valid JSON:
{{
  "score": <number 1-10>,
  "confidence": "<low|medium|high>",
  "justification": "<2-3 sentences citing specific evidence>",
  "level_description": "<e.g., 'Meets Expectations', 'Exceeds Expectations'>"
}}"""

KPI_MAPPING_PROMPT = """{context}

Based on the supervisor transcript and evidence:

{evidence}

FULL TRANSCRIPT:
{transcript}

Identify which of the 8 business KPIs the Fellow's work connects to. For each KPI you identify, explain the connection with evidence.

8 KPIs: OTD (On-Time Delivery), Quality, Productivity, Cost Reduction, Employee Retention, Capacity Utilization, Lead Time, Customer Satisfaction

Return ONLY valid JSON:
{{
  "kpi_mappings": [
    {{
      "kpi": "KPI name",
      "connection": "How the Fellow's work relates to this KPI based on transcript evidence",
      "strength": "strong|moderate|weak"
    }}
  ]
}}"""

GAP_ANALYSIS_PROMPT = """{context}

CURRENT EVIDENCE FROM TRANSCRIPT:
{evidence}

RUBRIC DIMENSIONS THAT SHOULD BE ASSESSED:
1. Reliability & Consistency
2. Work Quality
3. Initiative & Ownership
4. Systems Building
5. Team Integration
6. Communication
7. Problem-Solving
8. Business Impact

Identify which dimensions are NOT adequately covered in the transcript. For each gap, note what information is missing and why it matters.

Return ONLY valid JSON:
{{
  "gaps": [
    {{
      "dimension": "dimension name",
      "missing_information": "What specifically is missing",
      "importance": "Why this matters for Fellow assessment"
    }}
  ]
}}"""

FOLLOWUP_QUESTIONS_PROMPT = """{context}

GAPS IDENTIFIED IN CURRENT ASSESSMENT:
{gaps}

Generate 3-5 specific follow-up questions the psychology intern should ask in the next supervisor call. Each question should:
- Target a specific gap
- Be open-ended
- Encourage detailed behavioral examples
- Not be leading or suggestive

Return ONLY valid JSON:
{{
  "followup_questions": [
    {{
      "question": "The question text",
      "targets_gap": "Which gap/dimension this addresses",
      "purpose": "What we hope to learn from this question"
    }}
  ]
}}"""