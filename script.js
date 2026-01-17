// --- CONFIG ---
const booksUrl = 'books.json';
let allBooks = [];
let currentBook = null;
let currentChapterIndex = 0;
let isPlaying = false;
let bookmarks = JSON.parse(localStorage.getItem('vibe_bookmarks')) || {};
let playHistory = JSON.parse(localStorage.getItem('vibe_history')) || [];

// Visualizer Variables
let audioContext, analyser, dataArray, canvas, ctx;

// --- ELEMENTS ---
const audio = document.getElementById('audio-element');
const views = {
    library: document.getElementById('library-view'),
    history: document.getElementById('history-view'),
    player: document.getElementById('chapter-view')
};
const tabs = {
    library: document.getElementById('tab-library'),
    history: document.getElementById('tab-history')
};
const currentTimeEl = document.getElementById('current-time');
const totalDurationEl = document.getElementById('total-duration');
const progressBar = document.getElementById('progress-bar');

// --- 🚀 INIT (App Start) ---
async function init() {
    try {
        const res = await fetch(booksUrl);
        allBooks = await res.json();
        
        renderBooks(allBooks); // Pehle sab books dikhao
        setupCategories();     // 🔥 Categories buttons banao
        renderHistory();
        
        // ✨ AUTO RESUME (Refresh Fix)
        const savedState = JSON.parse(localStorage.getItem('vibe_last_played'));
        
        if (savedState) {
            const book = allBooks.find(b => b.id === savedState.bookId);
            if (book) {
                currentBook = book;
                currentChapterIndex = savedState.chapterIndex;
                
                // Audio load without playing
                loadAudioSource(currentChapterIndex, false, savedState.time);
                
                openPlayerPage(book);
                updateMiniPlayerUI();
                console.log(`Resumed: ${book.title}`);
            }
        }
    } catch (err) {
        console.error("Error loading books:", err);
    }
}

// --- TABS LOGIC ---
function switchTab(tabName) {
    Object.values(views).forEach(el => el.classList.add('hidden'));
    Object.values(tabs).forEach(el => el.classList.remove('active-tab'));
    views[tabName].classList.remove('hidden');
    tabs[tabName].classList.add('active-tab');
    if (tabName === 'history') renderHistory();
}

// --- RENDER LIBRARY ---
function renderBooks(books) {
    const grid = document.getElementById('book-grid');
    grid.innerHTML = '';
    books.forEach(book => grid.appendChild(createCard(book)));
}

// --- 📂 CATEGORY FILTER ---
function setupCategories() {
    const categories = ['All', ...new Set(allBooks.map(b => b.category || 'Others'))];
    const container = document.getElementById('category-filters');
    container.innerHTML = '';
    
    categories.forEach(cat => {
        const btn = document.createElement('button');
        btn.innerText = cat;
        btn.className = 'filter-btn';
        if(cat === 'All') btn.classList.add('active');
        
        btn.onclick = () => {
            document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            
            if (cat === 'All') renderBooks(allBooks);
            else renderBooks(allBooks.filter(b => (b.category || 'Others') === cat));
        };
        container.appendChild(btn);
    });
}

function createCard(book) {
    const card = document.createElement('div');
    card.className = 'book-card';
    card.innerHTML = `
        <img src="${book.cover}" loading="lazy" alt="${book.title}">
        <h3>${book.title}</h3>
        <p>${book.author}</p>
    `;
    card.onclick = () => {
        const historyItem = playHistory.find(h => h.id === book.id);
        if(historyItem) {
            currentBook = book;
            currentChapterIndex = historyItem.lastChapter || 0;
            const startTime = historyItem.lastTime || 0;
            openPlayerPage(book);
            loadAudioSource(currentChapterIndex, true, startTime);
        } else {
            openPlayerPage(book);
        }
    };
    return card;
}

// --- HISTORY LOGIC ---
function addToHistory(book) {
    playHistory = playHistory.filter(b => b.id !== book.id);
    book.lastChapter = currentChapterIndex;
    book.lastTime = audio.currentTime;
    playHistory.unshift(book);
    if (playHistory.length > 10) playHistory.pop();
    localStorage.setItem('vibe_history', JSON.stringify(playHistory));
}

function renderHistory() {
    const grid = document.getElementById('history-grid');
    grid.innerHTML = '';
    if (playHistory.length === 0) {
        grid.innerHTML = '<p style="color:#aaa; text-align:center; width:100%;">No history yet.</p>';
        return;
    }
    playHistory.forEach(book => {
        grid.appendChild(createCard(book));
    });
}

// --- PLAYER PAGE UI ---
function openPlayerPage(book) {
    currentBook = book;
    Object.values(views).forEach(el => el.classList.add('hidden'));
    views.player.classList.remove('hidden');
    
    document.getElementById('detail-cover').src = book.cover;
    document.getElementById('blur-bg').style.backgroundImage = `url('${book.cover}')`;
    document.getElementById('detail-title').innerText = book.title;
    document.getElementById('detail-author').innerText = book.author;
    document.getElementById('total-chapters').innerText = `${book.chapters.length} Chapters`;

    renderChapters();
    renderBookmarksList(); // 🔥 Bookmarks bhi load karo
}

document.getElementById('back-btn').onclick = () => switchTab('library');

function renderChapters() {
    const list = document.getElementById('chapter-list');
    list.innerHTML = '';
    currentBook.chapters.forEach((chap, idx) => {
        const li = document.createElement('li');
        li.innerHTML = `
            <span>${idx + 1}. ${chap.name}</span> 
            ${idx === currentChapterIndex && isPlaying ? '<i class="fas fa-volume-up" style="color:var(--secondary)"></i>' : '<i class="far fa-play-circle"></i>'}
        `;
        li.onclick = () => playAudio(idx);
        if (idx === currentChapterIndex) li.classList.add('active');
        list.appendChild(li);
    });
}

// --- 🎧 AUDIO LOGIC ---

function getDirectLink(url) {
    if (url.includes('drive.google.com') || url.includes('docs.google.com')) {
        try {
            let id = "";
            if(url.includes('/d/')) id = url.split('/d/')[1].split('/')[0];
            else if(url.includes('id=')) id = url.split('id=')[1].split('&')[0];
            if (id) return `https://drive.google.com/uc?export=download&id=${id}`;
        } catch (e) { return url; }
    }
    return url;
}

function playAudio(index) {
    currentChapterIndex = index;
    loadAudioSource(index, true, 0);
    addToHistory(currentBook);
}

function loadAudioSource(index, autoPlay = true, resumeTime = 0) {
    const chapter = currentBook.chapters[index];
    const src = getDirectLink(chapter.url);
    
    if(audio.src !== src) {
        audio.src = src;
        audio.addEventListener('loadedmetadata', function onLoaded() {
            totalDurationEl.innerText = formatTime(audio.duration);
            if (resumeTime > 0) audio.currentTime = resumeTime;
            
            if (autoPlay) {
                initVisualizer(); // 🔥 Start Visualizer
                audio.play().catch(e => console.log("Autoplay blocked:", e));
                isPlaying = true;
            } else {
                isPlaying = false;
            }
            updatePlayBtn();
            renderChapters();
        }, { once: true });
    } else {
        if(autoPlay) { 
            initVisualizer(); 
            audio.play(); 
            isPlaying = true; 
        }
    }
    updateMiniPlayerUI();
}

function updateMiniPlayerUI() {
    document.getElementById('mini-player').classList.remove('hidden');
    document.getElementById('mini-title').innerText = currentBook.title;
    document.getElementById('mini-chapter').innerText = currentBook.chapters[currentChapterIndex].name;
    document.getElementById('mini-cover').src = currentBook.cover;
    updatePlayBtn();
}

function togglePlay() {
    initVisualizer(); // 🔥 Ensure context is ready
    if (audio.paused) {
        audio.play();
        isPlaying = true;
    } else {
        audio.pause();
        isPlaying = false;
    }
    updatePlayBtn();
    renderChapters();
}

function updatePlayBtn() {
    document.getElementById('play-btn').innerHTML = isPlaying ? '<i class="fas fa-pause"></i>' : '<i class="fas fa-play"></i>';
}

// Controls
document.getElementById('play-btn').onclick = togglePlay;
document.getElementById('next-btn').onclick = () => {
    if (currentChapterIndex < currentBook.chapters.length - 1) playAudio(currentChapterIndex + 1);
};
document.getElementById('prev-btn').onclick = () => {
    if (currentChapterIndex > 0) playAudio(currentChapterIndex - 1);
};

// --- PROGRESS & UPDATES ---
function formatTime(seconds) {
    if (isNaN(seconds)) return "00:00";
    const min = Math.floor(seconds / 60);
    const sec = Math.floor(seconds % 60);
    return `${min < 10 ? '0' + min : min}:${sec < 10 ? '0' + sec : sec}`;
}

audio.addEventListener('timeupdate', () => {
    currentTimeEl.innerText = formatTime(audio.currentTime);
    if (audio.duration) {
        const percent = (audio.currentTime / audio.duration) * 100;
        progressBar.value = percent;
        progressBar.style.backgroundSize = `${percent}% 100%`;
    }
    
    // Save State
    if(currentBook && isPlaying && Math.floor(audio.currentTime) % 2 === 0) {
        localStorage.setItem('vibe_last_played', JSON.stringify({
            bookId: currentBook.id,
            chapterIndex: currentChapterIndex,
            time: audio.currentTime
        }));
        
        const historyIndex = playHistory.findIndex(b => b.id === currentBook.id);
        if(historyIndex > -1) {
            playHistory[historyIndex].lastTime = audio.currentTime;
            playHistory[historyIndex].lastChapter = currentChapterIndex;
            localStorage.setItem('vibe_history', JSON.stringify(playHistory));
        }
    }
});

progressBar.addEventListener('input', (e) => {
    const time = (e.target.value / 100) * audio.duration;
    audio.currentTime = time;
    e.target.style.backgroundSize = `${e.target.value}% 100%`;
});

audio.addEventListener('ended', () => {
    if (currentChapterIndex < currentBook.chapters.length - 1) playAudio(currentChapterIndex + 1);
    else { isPlaying = false; updatePlayBtn(); }
});

// Search
document.getElementById('search-input').addEventListener('input', (e) => {
    const term = e.target.value.toLowerCase();
    const filtered = allBooks.filter(b => b.title.toLowerCase().includes(term));
    if (!views.library.classList.contains('hidden')) renderBooks(filtered);
});

// PWA
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => navigator.serviceWorker.register('sw.js'));
}

// Speed & Timer
function changeSpeed() {
    const speeds = [1, 1.25, 1.5, 2];
    let newSpeed = speeds[(speeds.indexOf(audio.playbackRate) + 1) % speeds.length];
    audio.playbackRate = newSpeed;
    document.getElementById('speed-btn').innerText = newSpeed + 'x';
}

let sleepTimer = null;
function setSleepTimer() {
    const btn = document.getElementById('timer-btn');
    if (sleepTimer) {
        clearTimeout(sleepTimer); sleepTimer = null;
        btn.classList.remove('active-timer'); btn.innerText = '🌙';
        alert("Timer Cancelled"); return;
    }
    let mins = 30; 
    btn.classList.add('active-timer'); btn.innerText = '30m';
    sleepTimer = setTimeout(() => {
        audio.pause(); isPlaying = false; updatePlayBtn();
        btn.classList.remove('active-timer'); btn.innerText = '🌙';
    }, mins * 60 * 1000);
    alert(`Stopping in ${mins} mins. 😴`);
}

// --- 🔖 BOOKMARKS LOGIC ---
function addBookmark() {
    if (!currentBook) return;
    const note = prompt("Note for this timestamp:", "Good point");
    if (!note) return;
    
    const time = audio.currentTime;
    const bookId = currentBook.id;
    
    if (!bookmarks[bookId]) bookmarks[bookId] = [];
    bookmarks[bookId].push({ time, note, chapter: currentChapterIndex });
    
    localStorage.setItem('vibe_bookmarks', JSON.stringify(bookmarks));
    renderBookmarksList();
}

function renderBookmarksList() {
    const list = document.getElementById('bookmarks-list');
    list.innerHTML = '';
    
    if (!currentBook || !bookmarks[currentBook.id]) {
        list.innerHTML = '<p style="color:#aaa; font-size:0.8rem;">No bookmarks yet.</p>';
        return;
    }
    
    bookmarks[currentBook.id].forEach((bm, index) => {
        const li = document.createElement('li');
        li.innerHTML = `
            <span onclick="playBookmark(${index})">
                <span class="bm-time">[${formatTime(bm.time)}]</span> ${bm.note}
            </span>
            <i class="fas fa-trash bm-delete" onclick="deleteBookmark(${index})"></i>
        `;
        list.appendChild(li);
    });
}

function playBookmark(index) {
    const bm = bookmarks[currentBook.id][index];
    if (currentChapterIndex !== bm.chapter) {
        playAudio(bm.chapter); 
        setTimeout(() => audio.currentTime = bm.time, 800); 
    } else {
        audio.currentTime = bm.time;
        audio.play();
    }
}

function deleteBookmark(index) {
    bookmarks[currentBook.id].splice(index, 1);
    localStorage.setItem('vibe_bookmarks', JSON.stringify(bookmarks));
    renderBookmarksList();
}

// --- 📊 MIRRORED VISUALIZER LOGIC ---

function initVisualizer() {
    if (!audioContext) {
        audioContext = new (window.AudioContext || window.webkitAudioContext)();
        analyser = audioContext.createAnalyser();
        const source = audioContext.createMediaElementSource(audio);
        source.connect(analyser);
        analyser.connect(audioContext.destination);
        
        // FFT Size 64 rakha hai taaki bars mote aur clean dikhein
        analyser.fftSize = 64; 
        const bufferLength = analyser.frequencyBinCount;
        dataArray = new Uint8Array(bufferLength);
        
        canvas = document.getElementById('visualizer');
        ctx = canvas.getContext('2d');
        
        // Resolution fix
        canvas.width = canvas.offsetWidth;
        canvas.height = canvas.offsetHeight;
        
        animateVisualizer();
    }
    if (audioContext.state === 'suspended') audioContext.resume();
}

function animateVisualizer() {
    requestAnimationFrame(animateVisualizer);

    if (!isPlaying) {
        // Pause hone par bars dheere dheere neeche aayein (Optional cleanup)
         ctx.clearRect(0, 0, canvas.width, canvas.height);
        return;
    }

    analyser.getByteFrequencyData(dataArray);
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    const bufferLength = analyser.frequencyBinCount;
    // Calculate bar width with some gap
    const barWidth = (canvas.width / bufferLength) * 0.8; 
    const gap = (canvas.width / bufferLength) * 0.2;
    let x = gap / 2; // Start with half gap

    for (let i = 0; i < bufferLength; i++) {
        let barHeight = dataArray[i] / 1.5; // Height adjust kar le
        
        // 🔥 NEON GRADIENT (Pink to Purple)
        const gradient = ctx.createLinearGradient(0, 0, 0, canvas.height);
        gradient.addColorStop(0, '#ff00cc'); // Neon Pink
        gradient.addColorStop(1, '#333399'); // Deep Purple

        ctx.fillStyle = gradient;

        // Center Point Calculation (Jahan se mirror hoga)
        const centerY = canvas.height / 1.5; 

        // 1. Upper Bar (Upar ja raha hai)
        // roundRect(x, y, width, height, radius)
        ctx.beginPath();
        ctx.roundRect(x, centerY - barHeight, barWidth, barHeight, [5, 5, 0, 0]);
        ctx.fill();

        // 2. Lower Bar (Reflection - Thoda transparent)
        ctx.fillStyle = 'rgba(255, 0, 204, 0.3)'; // Halka Pink Reflection
        ctx.beginPath();
        // Height thodi kam reflection ki (realism ke liye)
        ctx.roundRect(x, centerY + 2, barWidth, barHeight * 0.5, [0, 0, 5, 5]); 
        ctx.fill();

        x += barWidth + gap;
    }
}

// Start
init();