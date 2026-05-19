#!/usr/bin/env node
/**
 * AceIQ Health — Eval Runner (Node.js direct mode)
 *
 * Runs the full evaluation pipeline without requiring a Python runtime,
 * database, or LLM API key. Implements:
 *   - SPL XML parsing
 *   - PII redaction & prescribing-intent detection (same regex as Python)
 *   - TF-IDF retrieval with stemming + section-name indexing
 *   - All 6 eval metrics from the project brief
 *
 * Usage:  node eval/run_eval.js
 */

'use strict';

const fs   = require('fs');
const path = require('path');

const ROOT           = path.resolve(__dirname, '..');
const SAMPLE_DIR     = path.join(ROOT, 'sample_data');
const QUESTIONS_FILE = path.join(__dirname, 'questions.json');

// ── XML Parsing ──────────────────────────────────────────────────────────────

function parseXML(xmlContent, externalId) {
  const titleMatch = xmlContent.match(/<title>([\s\S]*?)<\/title>/);
  const nameMatch  = xmlContent.match(/<name>([\s\S]*?)<\/name>/);
  const title      = (titleMatch && titleMatch[1] || '').trim();
  const drugName   = (nameMatch  && nameMatch[1]  || '').trim();

  const sections = [];
  let   order    = 0;
  const secRe    = /<section[^>]*displayName="([^"]*)"[^>]*>[\s\S]*?<text>([\s\S]*?)<\/text>[\s\S]*?<\/section>/g;
  let   m;

  while ((m = secRe.exec(xmlContent)) !== null) {
    const displayName = m[1].trim();
    const text        = m[2].trim();
    if (text) {
      sections.push({
        section: displayName,
        sectionOrder: order++,
        text,
        drugName,
        title,
        externalId,
      });
    }
  }
  return { title, drugName, externalId, sections };
}

// ── Guardrails (identical patterns to backend/services/guardrails.py) ────────

const PII_RULES = [
  { label: 'EMAIL',   re: /[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}/g },
  { label: 'PHONE',   re: /(?<!\d)(?:\+?\d{1,3}[\s-]?)?\(?\d{2,4}\)?[\s-]?\d{3,4}[\s-]?\d{3,4}(?!\d)/g },
  { label: 'AADHAAR', re: /\b\d{4}\s?\d{4}\s?\d{4}\b/g },
  { label: 'PAN',     re: /\b[A-Z]{5}\d{4}[A-Z]\b/g },
  { label: 'MRN',     re: /\bMRN[:\s#-]*\d{4,10}\b/gi },
  { label: 'DOB',     re: /\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b/g },
];

const NAME_RE = /\b(patient|mr|mrs|ms|dr|doctor|named?|called)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})\b/gi;

const PRESCRIBING_RES = [
  /\bwhat (?:should|do) (?:i|we) (?:prescribe|give|order|recommend)\b/i,
  /\bbest (?:drug|antibiotic|medication|treatment) for\b/i,
  /\b(?:can|should) i (?:start|give|switch|stop)\b/i,
  /\bdiagnose|diagnosis for\b/i,
  /\bmy patient (?:has|is|with)\b/i,
];

const REFUSAL_MSG = (
  "This appears to be a prescribing-decision question. AceIQ Health is a " +
  "reference tool, not a clinical decision-support system. Try rephrasing as " +
  "a label-lookup question, e.g. 'What does the metformin label say about renal dosing?'"
);

function redactPII(text) {
  let out = text;
  for (const { label, re } of PII_RULES) {
    out = out.replace(new RegExp(re.source, re.flags), '[REDACTED:' + label + ']');
  }
  out = out.replace(NAME_RE, function(_, trigger) { return trigger + ' [REDACTED:NAME]'; });
  return out;
}

function isPrescribingIntent(text) {
  return PRESCRIBING_RES.some(function(re) { return re.test(text); });
}

// ── TF-IDF Retrieval with stemming + section-name indexing ───────────────────

/**
 * Minimal suffix stemmer to collapse morphological variants so that
 * query term "contraindication" matches doc term "contraindicated", etc.
 *
 * Applies the most common medical-label inflection rules in order of
 * specificity (longest suffix first to avoid over-stripping).
 */
function stem(word) {
  if (word.length < 4) return word;
  // Verb/noun inflection rules — order matters (longest match first)
  const rules = [
    ['ications', ''],   // contraindications → contraindicat
    ['ication',  ''],   // contraindication  → contraindicat
    ['icated',   ''],   // contraindicated   → contraindicat
    ['tions',    ''],   // interactions → interact
    ['tion',     ''],   // interaction  → interact
    ['ations',   ''],   // indications  → indicat
    ['ation',    ''],   // indication   → indicat
    ['ings',     ''],   // warnings     → warn
    ['ing',      ''],   // dosing       → dos
    ['ated',     ''],   // indicated    → indic
    ['ies',      'y'],  // applies → apply
    ['ied',      'y'],  // applied → apply
    ['ers',      'r'],  // inhibitors → inhibitor (keep er)
    ['es',       ''],   // doses → dos
    ['ed',       ''],   // indicated → indicat
    ['er',       ''],   // inhibitor (already handled)
    ['ly',       ''],   // clinically → clinical
    ['s',        ''],   // reactions → reaction
  ];
  for (const [suffix, replacement] of rules) {
    if (word.endsWith(suffix) && word.length - suffix.length + replacement.length >= 3) {
      return word.slice(0, word.length - suffix.length) + replacement;
    }
  }
  return word;
}

function tokenize(text) {
  return text
    .toLowerCase()
    .replace(/[^\w\s]/g, ' ')
    .split(/\s+/)
    .filter(function(t) { return t.length > 2; })
    .map(stem);
}

/**
 * Build a TF-IDF index over all chunks.
 * We index "section_name + space + text" so queries using section keywords
 * (e.g. "contraindication", "drug interactions") score against the right chunk.
 */
function buildIndex(chunks) {
  var N  = chunks.length;
  var df = {};

  for (var i = 0; i < chunks.length; i++) {
    var c        = chunks[i];
    var fullText = c.section + ' ' + c.text;
    var terms    = Array.from(new Set(tokenize(fullText)));
    for (var j = 0; j < terms.length; j++) {
      df[terms[j]] = (df[terms[j]] || 0) + 1;
    }
  }

  var idf = {};
  for (var term in df) {
    idf[term] = Math.log((N + 1) / (df[term] + 1)) + 1;
  }

  var vectors = chunks.map(function(c) {
    var fullText = c.section + ' ' + c.text;
    var tokens   = tokenize(fullText);
    var tf       = {};
    for (var k = 0; k < tokens.length; k++) {
      tf[tokens[k]] = (tf[tokens[k]] || 0) + 1;
    }
    var vec = {};
    for (var t in tf) {
      vec[t] = (tf[t] / tokens.length) * (idf[t] || 1);
    }
    return { chunk: c, vec: vec };
  });

  return { vectors: vectors, idf: idf };
}

function cosine(a, b) {
  var dot = 0, na = 0, nb = 0;
  for (var t in a) { dot += a[t] * (b[t] || 0); na += a[t] * a[t]; }
  for (var t2 in b) nb += b[t2] * b[t2];
  return (na === 0 || nb === 0) ? 0 : dot / Math.sqrt(na * nb);
}

function buildQueryVec(question, idf) {
  var tokens = tokenize(question);
  var tf     = {};
  for (var i = 0; i < tokens.length; i++) tf[tokens[i]] = (tf[tokens[i]] || 0) + 1;
  var vec = {};
  for (var t in tf) vec[t] = (tf[t] / tokens.length) * (idf[t] || Math.log(2));
  return vec;
}

function retrieve(question, index, topK) {
  topK = topK || 3;
  var qv     = buildQueryVec(question, index.idf);
  var scored = index.vectors.map(function(entry) {
    return { chunk: entry.chunk, score: cosine(qv, entry.vec) };
  });
  scored.sort(function(a, b) { return b.score - a.score; });
  return scored.slice(0, topK).map(function(s) { return s.chunk; });
}

// ── Eval pipeline ─────────────────────────────────────────────────────────────

function runQuestion(q, index) {
  var t0       = Date.now();
  var redacted = redactPII(q.question);
  var refused  = isPrescribingIntent(redacted);

  if (refused) {
    return {
      id:            q.id,
      refused:       true,
      answer:        REFUSAL_MSG,
      citations:     [],
      verifierScore: null,
      latencyMs:     Date.now() - t0,
    };
  }

  var chunks = retrieve(redacted, index, 3);
  var answer = chunks.map(function(c) { return '[' + c.section + '] ' + c.text; }).join('\n\n')
             + '\n\nSource: drug labels and provided excerpts only.';

  return {
    id:            q.id,
    refused:       false,
    answer:        answer,
    citations:     chunks.map(function(c) {
      return {
        drugName:   c.drugName,
        section:    c.section,
        externalId: c.externalId,
        excerpt:    c.text.slice(0, 500),
      };
    }),
    verifierScore: null,
    latencyMs:     Date.now() - t0,
  };
}

// ── Metrics ───────────────────────────────────────────────────────────────────

function computeMetrics(questions, results) {
  var resMap   = {};
  for (var i = 0; i < results.length; i++) resMap[results[i].id] = results[i];

  var answerQs = questions.filter(function(q) { return !q.should_refuse; });

  // 1. Drug match
  var drugMatches = answerQs.filter(function(q) {
    var r   = resMap[q.id];
    if (!r || r.refused) return false;
    var exp = (q.expected_drug || '').toLowerCase();
    if (!exp) return true;
    return r.citations.some(function(c) {
      return (c.drugName || '').toLowerCase().indexOf(exp) !== -1;
    });
  }).length;

  // 2. Section match
  var sectionMatches = answerQs.filter(function(q) {
    var r = resMap[q.id];
    if (!r || r.refused) return false;
    if (!q.expected_sections.length) return true;
    var cited = {};
    r.citations.forEach(function(c) { cited[c.section] = true; });
    return q.expected_sections.some(function(s) { return cited[s]; });
  }).length;

  // 3. Must-mention coverage
  var coverages = answerQs.map(function(q) {
    var r = resMap[q.id];
    if (!r || r.refused || !q.must_mention.length) return 1.0;
    var al    = r.answer.toLowerCase();
    var found = q.must_mention.filter(function(t) { return al.indexOf(t.toLowerCase()) !== -1; }).length;
    return found / q.must_mention.length;
  });
  var avgCoverage = coverages.reduce(function(a, b) { return a + b; }, 0) / coverages.length;

  // 4. Refusal correctness
  var refusalCorrect = questions.filter(function(q) {
    var r = resMap[q.id];
    return r && r.refused === q.should_refuse;
  }).length;

  // 5. Verifier (N/A without LLM)
  var avgVerifier = null;

  // 6. Latency
  var avgLatency = results.reduce(function(a, r) { return a + r.latencyMs; }, 0) / results.length;

  return {
    drugMatchPct:    drugMatches / answerQs.length,
    sectionMatchPct: sectionMatches / answerQs.length,
    avgCoverage:     avgCoverage,
    refusalPct:      refusalCorrect / questions.length,
    avgVerifier:     avgVerifier,
    avgLatency:      avgLatency,
    details: {
      drugMatches:    drugMatches,
      sectionMatches: sectionMatches,
      refusalCorrect: refusalCorrect,
      total:          questions.length,
      answerTotal:    answerQs.length,
    },
  };
}

// ── Printing ──────────────────────────────────────────────────────────────────

function pct(v)  { return (v * 100).toFixed(1) + '%'; }

function passLabel(val, target, higherBetter) {
  if (higherBetter === undefined) higherBetter = true;
  var ok = higherBetter ? val >= target : val <= target;
  return ok ? '✅ PASS' : '❌ FAIL';
}

function printMetrics(m) {
  var LINE = '='.repeat(66);
  console.log('\n' + LINE);
  console.log('  METRICS RESULTS');
  console.log(LINE);
  console.log('  ' + 'Metric'.padEnd(32) + ' ' + 'Result'.padStart(10) + '  ' + 'Target'.padStart(8) + '  Status');
  console.log('  ' + '-'.repeat(60));

  var rows = [
    ['Retrieval drug match',   pct(m.drugMatchPct),    '>=90%',  passLabel(m.drugMatchPct,    0.90)],
    ['Section match',          pct(m.sectionMatchPct), '>=80%',  passLabel(m.sectionMatchPct, 0.80)],
    ['Must-mention coverage',  pct(m.avgCoverage),     '>=75%',  passLabel(m.avgCoverage,     0.75)],
    ['Refusal correctness',    pct(m.refusalPct),      '100%',   passLabel(m.refusalPct,      1.00)],
    ['Avg verifier score',
     m.avgVerifier != null ? m.avgVerifier.toFixed(3) : '    N/A',
     '>=0.75',
     m.avgVerifier != null ? passLabel(m.avgVerifier, 0.75) : '⚠️  N/A (no LLM)'],
    ['Avg latency (ms)',       m.avgLatency.toFixed(0), '<=3000', passLabel(m.avgLatency, 3000, false)],
  ];

  for (var i = 0; i < rows.length; i++) {
    var r = rows[i];
    console.log('  ' + r[0].padEnd(32) + ' ' + r[1].padStart(10) + '  ' + r[2].padStart(8) + '  ' + r[3]);
  }
  console.log(LINE);

  var hardPass = (
    m.drugMatchPct    >= 0.90 &&
    m.sectionMatchPct >= 0.80 &&
    m.avgCoverage     >= 0.75 &&
    m.refusalPct      >= 1.00 &&
    m.avgLatency      <= 3000
  );

  if (hardPass) {
    console.log('\n  🎉 All hard targets met — v1 acceptance criteria PASSED\n');
  } else {
    console.log('\n  ⚠️  One or more targets not met — see failures above\n');
  }
  return hardPass;
}

// ── Main ──────────────────────────────────────────────────────────────────────

function main() {
  var LINE = '='.repeat(66);
  console.log('\n' + LINE);
  console.log(' AceIQ Health — Eval Suite (Node.js direct mode)');
  console.log(' Pipeline: XML parse → TF-IDF+stem retrieval → guardrails → metrics');
  console.log(LINE);

  var xmlFiles = fs.readdirSync(SAMPLE_DIR).filter(function(f) { return f.endsWith('.xml'); });
  if (!xmlFiles.length) { console.error('No XML files in sample_data/'); process.exit(1); }

  var allChunks = [];
  for (var fi = 0; fi < xmlFiles.length; fi++) {
    var f       = xmlFiles[fi];
    var content = fs.readFileSync(path.join(SAMPLE_DIR, f), 'utf8');
    var label   = parseXML(content, path.basename(f, '.xml'));
    allChunks.push.apply(allChunks, label.sections);
    console.log('  Loaded ' + label.drugName + ': ' + label.sections.length + ' sections');
  }
  console.log('  Total chunks in index: ' + allChunks.length + '\n');

  var index     = buildIndex(allChunks);
  var questions = JSON.parse(fs.readFileSync(QUESTIONS_FILE, 'utf8'));

  console.log('  Running ' + questions.length + ' questions...\n');
  var results = [];

  for (var qi = 0; qi < questions.length; qi++) {
    var q     = questions[qi];
    var label2 = q.question.length > 72 ? q.question.slice(0, 72) + '...' : q.question;
    process.stdout.write('  [' + q.id + '] ' + label2 + '\n');
    var r = runQuestion(q, index);
    results.push(r);
    var status = r.refused
      ? 'REFUSED'
      : ('OK (' + r.latencyMs + 'ms, ' + r.citations.length + ' citations, sections: ['
         + r.citations.map(function(c) { return c.section; }).join(', ') + '])');
    console.log('       ' + status);
  }

  var metrics = computeMetrics(questions, results);
  printMetrics(metrics);

  // Per-question detail
  console.log('  Per-question detail:');
  console.log('  ' + 'ID'.padEnd(4) + ' ' + 'Refused'.padEnd(8) + ' ' + 'Drug'.padEnd(6)
    + ' ' + 'Sec'.padEnd(5) + ' ' + 'Coverage'.padEnd(10) + ' Latency');
  console.log('  ' + '-'.repeat(48));

  var answerQs2 = questions.filter(function(q2) { return !q2.should_refuse; });
  var resMap2   = {};
  for (var ri = 0; ri < results.length; ri++) resMap2[results[ri].id] = results[ri];

  for (var qi2 = 0; qi2 < questions.length; qi2++) {
    var q2  = questions[qi2];
    var r2  = resMap2[q2.id];
    if (!r2) continue;

    var drugOk = q2.should_refuse ? ' -' : (r2.citations.some(function(c) {
      return (c.drugName || '').toLowerCase().indexOf((q2.expected_drug || '').toLowerCase()) !== -1;
    }) ? '✅' : '❌');

    var secOk = q2.should_refuse ? ' -' : (!q2.expected_sections.length ? '✅' :
      (r2.citations.some(function(c) { return q2.expected_sections.indexOf(c.section) !== -1; }) ? '✅' : '❌'));

    var cov;
    if (q2.should_refuse) {
      cov = ' -';
    } else if (!q2.must_mention.length) {
      cov = '100%';
    } else {
      var al2 = r2.answer.toLowerCase();
      var n2  = q2.must_mention.filter(function(t) { return al2.indexOf(t.toLowerCase()) !== -1; }).length;
      cov     = (n2 / q2.must_mention.length * 100).toFixed(0) + '%';
    }

    console.log('  ' + q2.id.padEnd(4) + ' ' + String(r2.refused).padEnd(8) + ' '
      + drugOk.padEnd(6) + ' ' + secOk.padEnd(5) + ' ' + cov.padEnd(10) + ' ' + r2.latencyMs + 'ms');
  }
  console.log('');
}

main();
