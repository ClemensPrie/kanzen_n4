import json
import os
import shutil
import struct
import zlib
from pathlib import Path

# --- CONFIGURATION ---
DATA_FILE = 'data.json'
OUTPUT_DIR = 'dist'
APP_TITLE = 'Grammar App (N4)'
APP_SHORT_NAME = 'N4 Grammar'
APP_THEME_COLOR = '#2c3e50'

# --- UTILITY: Generate minimal PNG icons (no external deps) ---
def _png_chunk(chunk_type, data):
    c = chunk_type + data
    return struct.pack('>I', len(data)) + c + struct.pack('>I', zlib.crc32(c) & 0xffffffff)

def create_png(width, height, r, g, b):
    """Create a minimal solid-color PNG."""
    sig = b'\x89PNG\r\n\x1a\n'
    ihdr = _png_chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0))
    raw_data = b''
    for y in range(height):
        raw_data += b'\x00'  # filter byte
        raw_data += bytes([r, g, b]) * width
    idat = _png_chunk(b'IDAT', zlib.compress(raw_data))
    iend = _png_chunk(b'IEND', b'')
    return sig + ihdr + idat + iend


def build_app():
    print(f"Building {APP_TITLE}...")

    # 1. Load the JSON data (strip trailing non-JSON content)
    if not os.path.exists(DATA_FILE):
        print(f"Error: Could not find {DATA_FILE}")
        return

    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        raw = f.read()
    end = raw.rfind(']')
    if end > 0 and end < len(raw) - 1:
        raw = raw[:end + 1]
    data = json.loads(raw)
    print(f"  Loaded {len(data)} chapters")

    # 2. Clean and recreate the output directory
    if os.path.exists(OUTPUT_DIR):
        shutil.rmtree(OUTPUT_DIR)
    os.makedirs(OUTPUT_DIR)

    # 3. Generate icons if they don't exist on disk
    icon_192_path = os.path.join(OUTPUT_DIR, 'icon-192.png')
    icon_512_path = os.path.join(OUTPUT_DIR, 'icon-512.png')
    for src in ['icon-192.png', 'icon-512.png']:
        if os.path.exists(src):
            shutil.copyfile(src, os.path.join(OUTPUT_DIR, src))
            print(f"  Copied {src}")
        else:
            # Generate minimal PNG icon
            sz = 192 if '192' in src else 512
            png_data = create_png(sz, sz, 44, 62, 80)
            dst = os.path.join(OUTPUT_DIR, src)
            with open(dst, 'wb') as f:
                f.write(png_data)
            print(f"  Generated {src}")

    # 4. Generate the manifest.json
    manifest = {
        "name": APP_TITLE,
        "short_name": APP_SHORT_NAME,
        "description": "JLPT N4 grammar study app based on the Kanzen Master textbook",
        "start_url": ".",
        "display": "standalone",
        "background_color": "#ffffff",
        "theme_color": APP_THEME_COLOR,
        "lang": "ja",
        "icons": [
            { "src": "icon-192.png", "sizes": "192x192", "type": "image/png" },
            { "src": "icon-512.png", "sizes": "512x512", "type": "image/png" }
        ]
    }
    with open(os.path.join(OUTPUT_DIR, 'manifest.json'), 'w', encoding='utf-8') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    # 5. Generate the Service Worker
    sw_code = """const CACHE_NAME = 'grammar-app-v2';
const urlsToCache = [
    './',
    './index.html',
    './manifest.json',
    './data.json',
    './icon-192.png',
    './icon-512.png'
];

self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => cache.addAll(urlsToCache))
            .catch(err => console.error('SW install failed:', err))
    );
});

self.addEventListener('activate', event => {
    event.waitUntil(
        caches.keys().then(keys =>
            Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
        )
    );
});

self.addEventListener('fetch', event => {
    event.respondWith(
        caches.match(event.request)
            .then(response => response || fetch(event.request))
            .catch(() => caches.match('./index.html'))
    );
});"""
    with open(os.path.join(OUTPUT_DIR, 'sw.js'), 'w', encoding='utf-8') as f:
        f.write(sw_code)

    # 6. Copy data.json
    shutil.copyfile(DATA_FILE, os.path.join(OUTPUT_DIR, DATA_FILE))

    # 7. Generate index.html
    html_code = generate_html()
    with open(os.path.join(OUTPUT_DIR, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(html_code)

    print(f"Build successful! Output saved to '{OUTPUT_DIR}/'")
    print("Push the 'dist' folder to your GitHub Pages branch.")


# --- HTML TEMPLATE (regular string — NOT an f-string) ---
def generate_html():
    return HTML_TEMPLATE.replace('__APP_TITLE__', APP_TITLE)


HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>__APP_TITLE__</title>
    <link rel="manifest" href="./manifest.json">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="default">
    <meta name="apple-mobile-web-app-title" content="__APP_TITLE__">
    <link rel="apple-touch-icon" href="icon-192.png">
    <style>
        :root { --primary: #2c3e50; --primary-light: #3498db; --bg: #f9f9f9; --text: #333; --border: #ddd; }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Hiragino Kaku Gothic ProN', 'Noto Sans JP', sans-serif; }
        body { display: flex; height: 100vh; background: var(--bg); color: var(--text); }

        /* Sidebar */
        nav { width: 260px; background: var(--primary); color: white; overflow-y: auto; padding: 16px; flex-shrink: 0; }
        nav h1 { font-size: 1.1em; margin-bottom: 6px; padding-bottom: 8px; border-bottom: 1px solid rgba(255,255,255,0.2); }
        nav h2 { font-size: 0.95em; margin: 12px 0 6px; opacity: 0.85; }
        nav ul { list-style: none; padding-left: 8px; margin-bottom: 10px; }
        nav li { margin: 2px 0; }
        nav a { color: #ecf0f1; text-decoration: none; display: block; padding: 4px 8px; border-radius: 4px; font-size: 0.9em; }
        nav a:hover { background: rgba(255,255,255,0.1); }
        nav a.active { background: var(--primary-light); font-weight: bold; }
        #menu-toggle { display: none; background: none; border: none; color: white; font-size: 1.5em; cursor: pointer; padding: 4px 8px; }

        /* Main */
        main { flex: 1; padding: 24px; overflow-y: auto; }
        .content-box { background: white; padding: 24px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); max-width: 800px; margin: 0 auto; }

        /* Breadcrumbs */
        .breadcrumbs { font-size: 0.85em; color: #888; margin-bottom: 12px; padding: 0 4px; max-width: 800px; margin-left: auto; margin-right: auto; }
        .breadcrumbs a { color: var(--primary-light); text-decoration: none; }
        .breadcrumbs a:hover { text-decoration: underline; }
        .breadcrumbs span { color: #888; }

        /* Typography */
        ruby { ruby-align: center; }
        rt { font-size: 0.7em; }
        h1 { font-size: 1.6em; margin-bottom: 16px; color: var(--primary); }
        h2 { font-size: 1.3em; margin: 20px 0 10px; color: #34495e; }
        h3 { font-size: 1.1em; margin: 16px 0 8px; color: #555; }
        p, li { line-height: 1.7; }
        .grammar-example { background: #f1f2f6; padding: 10px 14px; border-left: 4px solid var(--primary-light); margin: 8px 0; border-radius: 0 4px 4px 0; }
        .formula { background: #e8f8f5; padding: 8px 12px; border-radius: 4px; font-weight: bold; margin: 10px 0; font-size: 0.95em; }

        /* Conjugation table */
        .conj-table { width: 100%; border-collapse: collapse; margin: 12px 0; font-size: 0.9em; }
        .conj-table th, .conj-table td { border: 1px solid var(--border); padding: 6px 10px; text-align: center; }
        .conj-table th { background: var(--primary); color: white; }
        .conj-table td { background: #fff; }
        .conj-table input { width: 100%; border: 1px solid var(--border); border-radius: 3px; padding: 4px 6px; text-align: center; font-size: 0.95em; }
        .conj-table .prefilled { background: #f0f0f0; color: #666; }
        .conj-table .blank-cell { background: #fffde7; }

        /* Exercises */
        .exercise-block { margin-bottom: 24px; border-bottom: 1px solid #eee; padding-bottom: 20px; }
        .exercise-block:last-child { border-bottom: none; }
        .exercise-instruction { font-weight: bold; margin-bottom: 10px; color: #555; }
        .question-block { margin-bottom: 16px; padding: 10px 12px; border-radius: 6px; background: #fafafa; }
        .question-block p { margin-bottom: 4px; }
        .question-number { font-weight: bold; color: var(--primary-light); margin-right: 6px; }
        .options { margin: 6px 0 4px 16px; }
        .options label { display: flex; align-items: baseline; gap: 6px; cursor: pointer; padding: 3px 0; font-size: 0.95em; }
        .options label:hover { color: var(--primary-light); }
        input[type="text"] { padding: 5px 8px; border: 1px solid var(--border); border-radius: 4px; font-size: 0.95em; width: 120px; }
        input[type="text"]:focus { border-color: var(--primary-light); outline: none; box-shadow: 0 0 0 2px rgba(52,152,219,0.2); }
        .blank-input { width: 80px; margin: 0 2px; }
        .feedback { margin-top: 4px; font-size: 0.85em; min-height: 1.2em; }
        .correct { color: #27ae60; font-weight: bold; }
        .incorrect { color: #e74c3c; font-weight: bold; }

        /* Reading comprehension */
        .reading-passage { background: #f1f2f6; padding: 14px; border-radius: 6px; margin: 12px 0; line-height: 1.8; font-size: 0.95em; }

        /* Buttons */
        .btn-group { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 16px; }
        button { background: var(--primary-light); color: white; border: none; padding: 8px 18px; border-radius: 5px; cursor: pointer; font-size: 0.95em; transition: background 0.15s; }
        button:hover { background: #2980b9; }
        .btn-secondary { background: #7f8c8d; }
        .btn-secondary:hover { background: #636e72; }
        .btn-success { background: #27ae60; }
        .btn-success:hover { background: #219a52; }
        .btn-warning { background: #f39c12; }
        .btn-warning:hover { background: #d68910; }

        /* Quiz score */
        .quiz-score { background: #eafaf1; border: 2px solid #27ae60; border-radius: 8px; padding: 16px; margin-top: 16px; text-align: center; }
        .quiz-score h3 { font-size: 1.4em; margin: 0 0 8px; color: var(--primary); }
        .quiz-score .pct { font-size: 2em; font-weight: bold; color: #27ae60; }
        .quiz-score .pct.low { color: #e74c3c; }
        .quiz-score .pct.mid { color: #f39c12; }

        /* Grammar point links */
        .gp-list { list-style: none; padding: 0; }
        .gp-list li { margin: 4px 0; }
        .gp-list a { display: block; padding: 8px 12px; background: #f1f2f6; border-radius: 5px; color: var(--text); text-decoration: none; border-left: 3px solid var(--primary-light); }
        .gp-list a:hover { background: #e2e6ea; }

        /* Back link */
        .back-link { display: inline-block; margin-top: 16px; color: var(--primary-light); text-decoration: none; font-size: 0.9em; }
        .back-link:hover { text-decoration: underline; }

        /* Theme toggle */
        .theme-toggle { position: fixed; bottom: 16px; right: 16px; z-index: 100; background: var(--primary); color: white; border: none; border-radius: 50%; width: 40px; height: 40px; cursor: pointer; font-size: 1.1em; box-shadow: 0 2px 6px rgba(0,0,0,0.2); }

        /* Responsive */
        @media (max-width: 768px) {
            body { flex-direction: column; }
            nav { width: 100%; height: auto; max-height: 48px; overflow: hidden; padding: 8px 16px; transition: max-height 0.3s; }
            nav.open { max-height: 80vh; overflow-y: auto; }
            nav h1 { display: inline; font-size: 1em; border-bottom: none; }
            #menu-toggle { display: inline-block; float: right; }
            main { padding: 12px; }
            .content-box { padding: 16px; }
        }
        @media (prefers-color-scheme: dark) {
            :root { --bg: #1a1a2e; --text: #e0e0e0; --primary: #16213e; --border: #333; }
            .content-box { background: #222; }
            .grammar-example { background: #2a2a3e; }
            .formula { background: #1a3a2e; }
            .question-block { background: #2a2a3e; }
            .gp-list a { background: #2a2a3e; color: #e0e0e0; }
            .reading-passage { background: #2a2a3e; }
            .conj-table td { background: #222; }
            .conj-table .prefilled { background: #333; color: #aaa; }
            .conj-table .blank-cell { background: #2a2a1e; }
            .quiz-score { background: #1a3a2e; }
            input[type="text"] { background: #333; color: #e0e0e0; border-color: #555; }
        }
    </style>
</head>
<body>
    <nav id="nav-bar">
        <div style="display:flex;align-items:center;justify-content:space-between;">
            <h1>__APP_TITLE__</h1>
            <button id="menu-toggle" aria-label="Toggle menu">&#9776;</button>
        </div>
        <div id="nav-links"></div>
    </nav>
    <main>
        <div id="breadcrumbs" class="breadcrumbs"></div>
        <div id="app-root" class="content-box">
            <p>Loading data...</p>
        </div>
    </main>
    <button class="theme-toggle" id="theme-toggle" aria-label="Toggle dark mode">&#9790;</button>
    <script>
    // ===== CONFIG =====
    var APP_TITLE = '__APP_TITLE__';

    // ===== STATE =====
    var data = [];
    var quizMode = false;
    var root = document.getElementById('app-root');
    var navLinks = document.getElementById('nav-links');
    var bcEl = document.getElementById('breadcrumbs');

    // ===== DATA HELPERS =====
    function getItems(chapter) { return chapter.lessons || chapter.sections || []; }
    function getItemId(item) { return item.lesson_id || item.section_id; }
    function getItem(chapter, itemId) {
        return getItems(chapter).find(function(it) { return getItemId(it) === itemId; });
    }
    function getCorrectAnswer(q) {
        return q.correct_answer !== undefined ? q.correct_answer : q.answer;
    }
    function isPart2(chapter) { return !!chapter.lessons; }

    // ===== ROUTER =====
    function getRoute() {
        var hash = window.location.hash.slice(1);
        if (!hash) return { type: 'home' };
        var parts = hash.split('/');
        if (parts.length === 1) return { type: 'chapter', id: parts[0] };
        if (parts.length === 2) return { type: 'item', chapterId: parts[0], itemId: parts[1] };
        if (parts.length === 3 && parts[2] === 'exercises')
            return { type: 'exercises', chapterId: parts[0], itemId: parts[1] };
        if (parts.length === 4 && parts[2] === 'grammar')
            return { type: 'grammar', chapterId: parts[0], itemId: parts[1], gpId: parts[3] };
        return { type: 'notfound' };
    }

    function navigate(hash) {
        window.location.hash = hash;
    }

    window.addEventListener('hashchange', function() {
        renderPage();
        updateActiveNav();
    });

    // ===== NAVIGATION =====
    function renderNav() {
        navLinks.innerHTML = '';
        data.forEach(function(chapter) {
            var h2 = document.createElement('h2');
            h2.textContent = chapter.chapter_title || chapter.title || 'Chapter';
            navLinks.appendChild(h2);
            var ul = document.createElement('ul');
            var items = getItems(chapter);
            items.forEach(function(item) {
                var li = document.createElement('li');
                var a = document.createElement('a');
                a.href = '#' + chapter.chapter_id + '/' + getItemId(item);
                a.textContent = item.title || 'Lesson';
                li.appendChild(a);
                ul.appendChild(li);
            });
            navLinks.appendChild(ul);
        });
    }

    function updateActiveNav() {
        var hash = window.location.hash;
        document.querySelectorAll('#nav-links a').forEach(function(a) {
            if (a.getAttribute('href') === hash) {
                a.classList.add('active');
            } else {
                a.classList.remove('active');
            }
        });
    }

    // Hamburger toggle
    document.getElementById('menu-toggle').addEventListener('click', function() {
        document.getElementById('nav-bar').classList.toggle('open');
    });

    // Close sidebar on nav click (mobile)
    document.addEventListener('click', function(e) {
        var nav = document.getElementById('nav-bar');
        if (nav.classList.contains('open') && e.target.tagName === 'A' && e.target.href) {
            nav.classList.remove('open');
        }
    });

    // ===== BREADCRUMBS =====
    function renderBreadcrumbs(crumbs) {
        if (!crumbs || crumbs.length === 0) {
            bcEl.innerHTML = '';
            return;
        }
        var html = '';
        crumbs.forEach(function(crumb, i) {
            if (i > 0) html += ' &gt; ';
            if (crumb.url) {
                html += '<a href="' + crumb.url + '">' + escapeHtml(crumb.label) + '</a>';
            } else {
                html += '<span>' + escapeHtml(crumb.label) + '</span>';
            }
        });
        bcEl.innerHTML = html;
    }

    function escapeHtml(s) {
        if (!s) return '';
        return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
    }

    // ===== PAGE RENDERER =====
    function renderPage() {
        var route = getRoute();
        updateActiveNav();

        if (route.type === 'home') { renderHome(); return; }
        if (route.type === 'chapter') { renderChapter(route); return; }
        if (route.type === 'item') { renderItem(route); return; }
        if (route.type === 'grammar') { renderGrammar(route); return; }
        if (route.type === 'exercises') { renderExercises(route); return; }
        notFound();
    }

    function renderHome() {
        root.innerHTML = '<h1>Welcome!</h1><p>Select a chapter or lesson from the sidebar to start studying.</p>';
        renderBreadcrumbs([]);
    }

    function renderChapter(route) {
        var chapter = data.find(function(c) { return c.chapter_id === route.id; });
        if (!chapter) return notFound();
        var p2 = isPart2(chapter);
        var pType = p2 ? 'lesson' : 'section';
        var items = getItems(chapter);
        var html = '<h1>' + escapeHtml(chapter.chapter_title) + '</h1><p>' + items.length + ' ' + pType + '(s). Select one from the sidebar.</p>';
        root.innerHTML = html;
        renderBreadcrumbs([{ label: chapter.chapter_title }]);
    }

    function renderItem(route) {
        var chapter = data.find(function(c) { return c.chapter_id === route.chapterId; });
        if (!chapter) return notFound();
        var item = getItem(chapter, route.itemId);
        if (!item) return notFound();
        var p2 = isPart2(chapter);

        var html = '<h1>' + escapeHtml(item.title) + '</h1>';

        // Conjugation table (on Part 1 sections, shown inline as reference)
        if (item.conjugation_table && item.conjugation_table.length > 0) {
            html += renderConjugationTable(item.conjugation_table);
        }

        // Grammar points (Parts 2/3)
        if (item.grammar_points && item.grammar_points.length > 0) {
            html += '<h2>Grammar Points</h2><ul class="gp-list">';
            item.grammar_points.forEach(function(gp) {
                html += '<li><a href="#' + route.chapterId + '/' + route.itemId + '/grammar/' + gp.point_id + '">' + escapeHtml(gp.title) + '</a></li>';
            });
            html += '</ul>';
        }

        // Exercises
        if (item.exercises && item.exercises.length > 0) {
            if (p2) {
                // Part 2: exercises button (they have their own page)
                html += '<br><button onclick="navigate(\'' + route.chapterId + '/' + route.itemId + '/exercises\')">Go to Exercises</button>';
            } else {
                // Part 1/3: exercises shown inline
                html += '<h2>Exercises</h2>';
                html += renderAllExercises(item.exercises, route.chapterId, route.itemId);
            }
        }

        root.innerHTML = html;
        renderBreadcrumbs([
            { label: chapter.chapter_title, url: '#' + route.chapterId },
            { label: item.title }
        ]);
    }

    function renderGrammar(route) {
        var chapter = data.find(function(c) { return c.chapter_id === route.chapterId; });
        if (!chapter) return notFound();
        var item = getItem(chapter, route.itemId);
        if (!item) return notFound();
        if (!item.grammar_points) return notFound();
        var gp = item.grammar_points.find(function(g) { return g.point_id === route.gpId; });
        if (!gp) return notFound();

        var html = '<h1>' + escapeHtml(item.title) + '</h1>';
        html += '<h2>' + escapeHtml(gp.title) + '</h2>';
        if (gp.explanation) html += '<p>' + gp.explanation + '</p>';
        if (gp.formula) html += '<div class="formula">' + gp.formula + '</div>';
        if (gp.examples && gp.examples.length > 0) {
            html += '<h3>Examples</h3>';
            gp.examples.forEach(function(ex) {
                html += '<div class="grammar-example">' + (ex.text || '') + '</div>';
            });
        }
        if (gp.conjugation_table && gp.conjugation_table.length > 0) {
            html += renderConjugationTable(gp.conjugation_table);
        }
        html += '<div class="btn-group">';
        html += '<a href="#' + route.chapterId + '/' + route.itemId + '" class="back-link">&larr; Back to ' + escapeHtml(item.title) + '</a>';
        html += '</div>';
        root.innerHTML = html;

        renderBreadcrumbs([
            { label: chapter.chapter_title, url: '#' + route.chapterId },
            { label: item.title, url: '#' + route.chapterId + '/' + route.itemId },
            { label: gp.title }
        ]);
    }

    // ===== CONJUGATION TABLE RENDERER =====
    function renderConjugationTable(rows) {
        if (!rows || rows.length === 0) return '';
        var keys = Object.keys(rows[0]);
        var html = '<table class="conj-table"><thead><tr>';
        keys.forEach(function(k) {
            html += '<th>' + escapeHtml(k.replace(/_/g, ' ')) + '</th>';
        });
        html += '</tr></thead><tbody>';
        rows.forEach(function(row) {
            html += '<tr>';
            keys.forEach(function(k) {
                html += '<td>' + escapeHtml(row[k] || '') + '</td>';
            });
            html += '</tr>';
        });
        html += '</tbody></table>';
        return html;
    }

    // ===== EXERCISE RENDERERS =====
    function renderAllExercises(exercises, chapterId, itemId) {
        if (!exercises || exercises.length === 0) return '<p>No exercises available.</p>';
        // Restore saved answers
        var saved = loadProgress(chapterId, itemId);
        var html = '';
        exercises.forEach(function(ex, idx) {
            html += '<div class="exercise-block" id="ex-block-' + idx + '">';
            html += '<div class="exercise-instruction">' + escapeHtml(ex.instruction || 'Exercise ' + (idx + 1)) + '</div>';
            // Reading passage
            if (ex.exercise_type === 'reading_comprehension' && ex.reading_text) {
                html += '<div class="reading-passage">' + ex.reading_text + '</div>';
            }
            html += '<div id="ex-' + idx + '">';
            html += renderExerciseQuestions(ex, idx, saved ? saved[idx] : null);
            html += '</div></div>';
        });
        html += '<div class="btn-group">';
        html += '<button onclick="checkAnswers()">Check Answers</button> ';
        html += '<button class="btn-secondary" onclick="quizModeToggle()">Quiz Mode</button> ';
        html += '<button class="btn-secondary" onclick="clearAnswers()">Clear Answers</button>';
        html += '</div>';
        html += '<div id="quiz-result"></div>';
        return html;
    }

    function renderExerciseQuestions(ex, idx, savedData) {
        var html = '';
        var qs = ex.questions || [];
        qs.forEach(function(q, qIdx) {
            var uid = idx + '-' + qIdx;
            var qKey = q.id || qIdx;
            var savedVal = savedData ? savedData[qKey] : null;
            // For array answers, savedVal might be an array too
            var savedAnswer = savedVal ? (savedVal.answer || savedVal) : null;

            html += '<div class="question-block" id="q-' + uid + '">';
            html += '<p><span class="question-number">' + escapeHtml(String(q.id || (qIdx + 1))) + '.</span> ' + q.sentence + '</p>';

            if (ex.exercise_type === 'multiple_choice' || ex.exercise_type === 'multiple_choice_star') {
                html += renderMCOptions(uid, q.options || [], savedAnswer);
            } else if (ex.exercise_type === 'reading_comprehension') {
                html += renderMCOptions(uid, q.options || [], savedAnswer);
            } else if (ex.exercise_type === 'fill_in_the_blank') {
                html += renderFillBlank(uid, q, ex, savedAnswer);
            } else if (ex.exercise_type === 'transformation') {
                var savedStr = (typeof savedAnswer === 'string') ? savedAnswer : '';
                html += '<p>Answer: <input type="text" id="input-' + uid + '" placeholder="Type answer" value="' + escapeHtml(savedStr) + '"></p>';
            } else if (ex.exercise_type === 'conjugation_table_fill') {
                html += renderConjTableFill(uid, q, savedAnswer);
            } else {
                html += '<p><em>Exercise type not yet supported.</em></p>';
            }

            html += '<div id="fb-' + uid + '" class="feedback"></div>';
            html += '</div>';
        });
        return html;
    }

    function renderMCOptions(uid, options, savedVal) {
        if (!options || options.length === 0) return '';
        var html = '<div class="options">';
        options.forEach(function(opt) {
            var val = opt.split(' ')[0];
            var checked = (savedVal === val) ? ' checked' : '';
            html += '<label><input type="radio" name="ans-' + uid + '" value="' + val + '"' + checked + '> ' + escapeHtml(opt) + '</label>';
        });
        html += '</div>';
        return html;
    }

    function renderFillBlank(uid, q, ex, savedVal) {
        if (ex.choices && ex.choices.length > 0) {
            var html = '<div class="options">';
            ex.choices.forEach(function(choice) {
                var val = choice.split(' ')[0];
                var checked = (savedVal === val) ? ' checked' : '';
                html += '<label><input type="radio" name="ans-' + uid + '" value="' + val + '"' + checked + '> ' + escapeHtml(choice) + '</label>';
            });
            html += '</div>';
            return html;
        } else {
            var savedStr = (typeof savedVal === 'string') ? savedVal : '';
            return '<p>Answer: <input type="text" id="input-' + uid + '" placeholder="Type answer" value="' + escapeHtml(savedStr) + '"></p>';
        }
    }

    function renderConjTableFill(uid, q, savedData) {
        if (!q.row_items || q.row_items.length === 0) return '';
        var defaultHeaders = ['ます形', '辞書形', 'ない形', 'た形', 'なかった形'];
        var numCols = q.row_items.length;
        var html = '<table class="conj-table" style="margin-top:6px;"><thead><tr>';
        for (var c = 0; c < numCols; c++) {
            html += '<th>' + (defaultHeaders[c] || '') + '</th>';
        }
        html += '</tr></thead><tbody><tr>';
        q.row_items.forEach(function(cellVal, colIdx) {
            var savedCell = savedData ? savedData[colIdx] : null;
            if (cellVal === '') {
                html += '<td><input type="text" id="ct-' + uid + '-' + colIdx + '" value="' + escapeHtml(savedCell || '') + '"></td>';
            } else {
                html += '<td class="prefilled">' + escapeHtml(cellVal) + '</td>';
            }
        });
        html += '</tr></tbody></table>';
        return html;
    }

    // ===== EXERCISES PAGE =====
    function renderExercises(route) {
        var chapter = data.find(function(c) { return c.chapter_id === route.chapterId; });
        if (!chapter) return notFound();
        var item = getItem(chapter, route.itemId);
        if (!item) return notFound();
        if (!item.exercises || item.exercises.length === 0) {
            root.innerHTML = '<h1>' + escapeHtml(item.title) + '</h1><p>No exercises available.</p>';
            return;
        }

        var html = '<h1>' + escapeHtml(item.title) + ' &mdash; Exercises</h1>';
        html += renderAllExercises(item.exercises, route.chapterId, route.itemId);
        html += '<div><a href="#' + route.chapterId + '/' + route.itemId + '" class="back-link">&larr; Back to ' + escapeHtml(item.title) + '</a></div>';
        root.innerHTML = html;

        renderBreadcrumbs([
            { label: chapter.chapter_title, url: '#' + route.chapterId },
            { label: item.title, url: '#' + route.chapterId + '/' + route.itemId },
            { label: 'Exercises' }
        ]);
    }

    // ===== ANSWER CHECKING =====
    function checkAnswers() {
        var route = getRoute();
        if (!route || !route.chapterId) return;
        var chapter = data.find(function(c) { return c.chapter_id === route.chapterId; });
        if (!chapter) return;
        var item = getItem(chapter, route.itemId);
        if (!item || !item.exercises) return;

        var totalQuestions = 0;
        var correctCount = 0;
        var results = {}; // for progress saving

        item.exercises.forEach(function(ex, idx) {
            (ex.questions || []).forEach(function(q, qIdx) {
                var uid = idx + '-' + qIdx;
                var fb = document.getElementById('fb-' + uid);
                if (!fb) return;

                var result = checkQuestion(ex, q, uid, qIdx);
                var qKey = q.id || qIdx;
                totalQuestions++;
                if (result.isCorrect) correctCount++;

                // Store result for progress
                if (!results[idx]) results[idx] = {};
                results[idx][qKey] = { answer: result.userAnswer, isCorrect: result.isCorrect };

                if (quizMode) {
                    // In quiz mode, show feedback only on result screen
                    fb.innerHTML = '';
                    return;
                }

                if (result.userAnswer === '') {
                    fb.innerHTML = 'Please answer the question.';
                    fb.className = 'feedback';
                } else if (result.isCorrect) {
                    fb.innerHTML = '✔ Correct!';
                    fb.className = 'feedback correct';
                } else {
                    var expected = getCorrectAnswer(q);
                    fb.innerHTML = '✘ Incorrect. The correct answer is: <strong>' + escapeHtml(String(expected)) + '</strong>';
                    fb.className = 'feedback incorrect';
                }
            });
        });

        // Save progress
        saveProgress(route.chapterId, route.itemId, results);

        // Quiz mode score
        var resultEl = document.getElementById('quiz-result');
        if (quizMode && resultEl) {
            var pct = totalQuestions > 0 ? Math.round(correctCount / totalQuestions * 100) : 0;
            var pctClass = pct >= 80 ? '' : (pct >= 50 ? 'mid' : 'low');
            resultEl.innerHTML = '<div class="quiz-score">' +
                '<h3>Quiz Result</h3>' +
                '<div class="pct ' + pctClass + '">' + correctCount + '/' + totalQuestions + ' (' + pct + '%)</div>' +
                '<div class="btn-group" style="justify-content:center;margin-top:10px;">' +
                '<button onclick="clearAnswers()">Clear All</button>' +
                '</div></div>';
        }

        // Save best quiz score
        if (quizMode) {
            saveBestScore(route.chapterId + '/' + route.itemId, correctCount, totalQuestions);
        }
    }

    function checkQuestion(ex, q, uid, qIdx) {
        var userAnswer = '';
        var isCorrect = false;
        var expected = getCorrectAnswer(q);

        if (ex.exercise_type === 'multiple_choice' || ex.exercise_type === 'multiple_choice_star' || ex.exercise_type === 'reading_comprehension') {
            var selected = document.querySelector('input[name="ans-' + uid + '"]:checked');
            userAnswer = selected ? selected.value : '';
            isCorrect = userAnswer !== '' && userAnswer === expected;
        } else if (ex.exercise_type === 'fill_in_the_blank') {
            if (ex.choices && ex.choices.length > 0) {
                var selected = document.querySelector('input[name="ans-' + uid + '"]:checked');
                userAnswer = selected ? selected.value : '';
                isCorrect = userAnswer !== '' && userAnswer === expected;
            } else {
                var inp = document.getElementById('input-' + uid);
                userAnswer = inp ? inp.value.trim() : '';
                isCorrect = userAnswer !== '' && userAnswer === expected;
            }
        } else if (ex.exercise_type === 'transformation') {
            var inp = document.getElementById('input-' + uid);
            userAnswer = inp ? inp.value.trim() : '';
            isCorrect = userAnswer !== '' && userAnswer === expected;
        } else if (ex.exercise_type === 'conjugation_table_fill') {
            var row = q.row_items || [];
            userAnswer = '';
            var anyFilled = false;
            for (var c = 0; c < row.length; c++) {
                if (row[c] === '') {
                    var inp = document.getElementById('ct-' + uid + '-' + c);
                    var v = inp ? inp.value.trim() : '';
                    if (v !== '') anyFilled = true;
                }
            }
            isCorrect = anyFilled;
        }

        return { userAnswer: userAnswer, isCorrect: isCorrect };
    }

    // ===== QUIZ MODE =====
    window.quizModeToggle = function() {
        quizMode = !quizMode;
        // Clear feedback
        document.querySelectorAll('.feedback').forEach(function(el) {
            el.innerHTML = '';
            el.className = 'feedback';
        });
        var resultEl = document.getElementById('quiz-result');
        if (resultEl) resultEl.innerHTML = '';
        if (quizMode) {
            var existing = document.getElementById('quiz-mode-badge');
            if (!existing) {
                var badge = document.createElement('div');
                badge.id = 'quiz-mode-badge';
                badge.style.cssText = 'background:#f39c12;color:#fff;padding:6px 14px;border-radius:4px;margin-bottom:12px;font-weight:bold;text-align:center;';
                badge.textContent = 'Quiz Mode — answers will be scored at the end';
                var firstBlock = document.querySelector('.exercise-block');
                if (firstBlock) {
                    firstBlock.parentNode.insertBefore(badge, firstBlock);
                }
            }
        } else {
            var badge = document.getElementById('quiz-mode-badge');
            if (badge) badge.remove();
        }
    };

    // ===== CLEAR ANSWERS =====
    window.clearAnswers = function() {
        document.querySelectorAll('.feedback').forEach(function(el) {
            el.innerHTML = '';
            el.className = 'feedback';
        });
        var resultEl = document.getElementById('quiz-result');
        if (resultEl) resultEl.innerHTML = '';
        document.querySelectorAll('input[type="text"]').forEach(function(inp) {
            inp.value = '';
        });
        document.querySelectorAll('input[type="radio"]').forEach(function(r) {
            r.checked = false;
        });
    };

    // ===== PROGRESS (localStorage) =====
    function getProgressKey(chapterId, itemId) {
        return 'kanzen_n4_' + chapterId + '_' + itemId;
    }
    function getScoreKey() {
        return 'kanzen_n4_quiz_scores';
    }

    function saveProgress(chapterId, itemId, results) {
        try {
            var key = getProgressKey(chapterId, itemId);
            localStorage.setItem(key, JSON.stringify(results));
        } catch(e) { /* quota exceeded, ignore */ }
    }

    function loadProgress(chapterId, itemId) {
        try {
            var key = getProgressKey(chapterId, itemId);
            var saved = localStorage.getItem(key);
            return saved ? JSON.parse(saved) : null;
        } catch(e) { return null; }
    }

    function saveBestScore(lessonKey, correct, total) {
        try {
            var scores = JSON.parse(localStorage.getItem(getScoreKey()) || '{}');
            var prev = scores[lessonKey];
            if (!prev || correct > prev.score || (correct === prev.score && total < prev.total)) {
                scores[lessonKey] = { score: correct, total: total, date: new Date().toISOString() };
                localStorage.setItem(getScoreKey(), JSON.stringify(scores));
            }
        } catch(e) { /* ignore */ }
    }

    function getBestScores() {
        try {
            return JSON.parse(localStorage.getItem(getScoreKey()) || '{}');
        } catch(e) { return {}; }
    }

    // ===== THEME TOGGLE =====
    document.getElementById('theme-toggle').addEventListener('click', function() {
        document.body.classList.toggle('dark');
        var isDark = document.body.classList.contains('dark');
        if (isDark) {
            document.body.style.background = '#1a1a2e';
            document.body.style.color = '#e0e0e0';
        } else {
            document.body.style.background = '';
            document.body.style.color = '';
        }
    });

    // ===== 404 =====
    function notFound() {
        root.innerHTML = '<h1>404</h1><p>Page not found.</p>';
        renderBreadcrumbs([]);
    }

    // ===== INIT =====
    fetch('data.json')
        .then(function(res) { return res.json(); })
        .then(function(json) {
            data = json;
            renderNav();
            renderPage();
        })
        .catch(function(err) {
            root.innerHTML = '<h1>Error</h1><p>Failed to load data: ' + err.message + '</p>';
        });

    // Handle initial load without hash
    if (!window.location.hash) {
        window.location.hash = '#';
    }
    </script>
</body>
</html>"""

if __name__ == "__main__":
    build_app()
