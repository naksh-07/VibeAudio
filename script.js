// --- CONFIG ---
const booksUrl = 'books.json';
let allBooks = [];
let currentBook = null;
let currentChapterIndex = 0;
let isPlaying = false;
// History ab Time aur Chapter bhi yaad rakhega
let playHistory = JSON.parse(localStorage.getItem('vibe_history')) || [];

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
        renderBooks(allBooks);
        renderHistory();
        
        // ✨ AUTO RESUME (Refresh Fix)
        const savedState = JSON.parse(localStorage.getItem('vibe_last_played'));
        
        if (savedState) {
            const book = allBooks.find(b => b.id === savedState.bookId);
            if (book) {
                // UI Set kar lo
                currentBook = book;
                currentChapterIndex = savedState.chapterIndex;
                
                // Audio load karo par play mat karo (false), aur Time pass karo
                loadAudioSource(currentChapterIndex, false, savedState.time);
                
                openPlayerPage(book, false); // false = Don't render chapters again if handled
                updateMiniPlayerUI();
                console.log(`Resumed: ${book.title} at ${formatTime(savedState.time)}`);
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

function createCard(book) {
    const card = document.createElement('div');
    card.className = 'book-card';
    card.innerHTML = `
        <img src="${book.cover}" loading="lazy" alt="${book.title}">
        <h3>${book.title}</h3>
        <p>${book.author}</p>
    `;
    card.onclick = () => {
        // Check History for Resume
        const historyItem = playHistory.find(h => h.id === book.id);
        if(historyItem) {
            // Agar history mein hai, wahi se chalao
            currentBook = book;
            currentChapterIndex = historyItem.lastChapter || 0;
            const startTime = historyItem.lastTime || 0;
            openPlayerPage(book);
            loadAudioSource(currentChapterIndex, true, startTime);
        } else {
            // New book
            openPlayerPage(book);
        }
    };
    return card;
}

// --- HISTORY LOGIC (Updated) ---
function addToHistory(book) {
    // Remove old entry of same book
    playHistory = playHistory.filter(b => b.id !== book.id);
    
    // Add new entry with extra data placeholders
    // (Actual time update loop mein save hoga)
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
        const card = createCard(book); // Reusing card logic
        // History card pe click karne se wo resume logic khud handle karega createCard mein
        grid.appendChild(card);
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
        li.onclick = () => playAudio(idx); // Clicking chapter always starts from 0
        if (idx === currentChapterIndex) li.classList.add('active');
        list.appendChild(li);
    });
}

// --- 🎧 AUDIO LOGIC (The Fix) ---

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
    loadAudioSource(index, true, 0); // Manual click starts from 0
    addToHistory(currentBook);
}

// 🔥 THIS IS THE MAGIC FUNCTION
function loadAudioSource(index, autoPlay = true, resumeTime = 0) {
    const chapter = currentBook.chapters[index];
    const src = getDirectLink(chapter.url);
    
    if(audio.src !== src) {
        audio.src = src;
        
        // 🛑 WAIT FOR METADATA BEFORE SEEKING
        audio.addEventListener('loadedmetadata', function onLoaded() {
            totalDurationEl.innerText = formatTime(audio.duration);
            
            if (resumeTime > 0) {
                audio.currentTime = resumeTime;
            }
            
            if (autoPlay) {
                audio.play().catch(e => console.log("Autoplay blocked:", e));
                isPlaying = true;
            } else {
                isPlaying = false;
            }
            updatePlayBtn();
            renderChapters();
            
        }, { once: true }); // Important: Run only once per load
    } else {
        // Agar same audio hai (pause/play case)
        if(autoPlay) { audio.play(); isPlaying = true; }
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
    if (currentChapterIndex < currentBook.chapters.length - 1) {
        playAudio(currentChapterIndex + 1);
    }
};
document.getElementById('prev-btn').onclick = () => {
    if (currentChapterIndex > 0) {
        playAudio(currentChapterIndex - 1);
    }
};

// --- PROGRESS & SAVE STATE ---

// Helper: Format Time
function formatTime(seconds) {
    if (isNaN(seconds)) return "00:00";
    const min = Math.floor(seconds / 60);
    const sec = Math.floor(seconds % 60);
    return `${min < 10 ? '0' + min : min}:${sec < 10 ? '0' + sec : sec}`;
}

// Update Loop
audio.addEventListener('timeupdate', () => {
    currentTimeEl.innerText = formatTime(audio.currentTime);
    
    if (audio.duration) {
        const percent = (audio.currentTime / audio.duration) * 100;
        progressBar.value = percent;
        progressBar.style.backgroundSize = `${percent}% 100%`;
    }
    
    // ✨ SAVE STATE EVERY 2 SECONDS
    if(currentBook && isPlaying && Math.floor(audio.currentTime) % 2 === 0) {
        
        // 1. Global (Refresh Resume)
        localStorage.setItem('vibe_last_played', JSON.stringify({
            bookId: currentBook.id,
            chapterIndex: currentChapterIndex,
            time: audio.currentTime
        }));

        // 2. History Specific (Book Resume)
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

init();