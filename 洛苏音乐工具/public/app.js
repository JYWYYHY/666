const API_BASE = '';
const PLATFORM_ENDPOINTS = {
  wymusic: '/api/wymusic/index.php',
  kgmusic:  '/api/kgmusic/index.php',
  qqmusic:  '/api/qqmusic/index.php'
};

// 读取设置
const defaultSettings = { limit: '20', quality: 'higher', downloadQuality: 'exhigh' };
let settings = JSON.parse(localStorage.getItem('luosu_settings')) || defaultSettings;

const state = {
  platform: 'wymusic',
  songs: [],
  currentIndex: -1,
  currentPlayUrl: '',
  lyricLines: [],
  lyricTimer: null
};

function $(id) { return document.getElementById(id); }
function setStatus(msg, isErr) {
  const el = $('status');
  el.textContent = msg;
  el.className = isErr ? 'err' : '';
}
function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, c =>
    ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}
function fmtTime(sec) {
  sec = Math.floor(Number(sec) || 0);
  return Math.floor(sec / 60) + ':' + String(sec % 60).padStart(2, '0');
}

/* ---------- 设置相关 ---------- */
function toggleSettings() {
  const modal = $('settingsModal');
  if (!modal.classList.contains('show')) {
    $('setLimit').value = settings.limit;
    $('setQuality').value = settings.quality;
    $('setDownloadQuality').value = settings.downloadQuality;
    modal.classList.add('show');
  } else {
    modal.classList.remove('show');
  }
}

function saveSettings() {
  settings.limit = $('setLimit').value;
  settings.quality = $('setQuality').value;
  settings.downloadQuality = $('setDownloadQuality').value;
  localStorage.setItem('luosu_settings', JSON.stringify(settings));
  $('settingsModal').classList.remove('show');
  setStatus('设置已保存');
}

/* ---------- 平台切换 ---------- */
$('platformTabs').addEventListener('click', e => {
  const btn = e.target.closest('button');
  if (!btn) return;
  document.querySelectorAll('.platform-tabs button').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  state.platform = btn.dataset.platform;
  state.songs = [];
  state.currentIndex = -1;
  $('resultList').innerHTML = '<div class="placeholder">切换平台，重新搜索</div>';
  $('nowName').textContent = '未播放';
  $('nowArtist').textContent = '—';
  $('audio').pause(); $('audio').removeAttribute('src'); $('audio').load();
  $('lyricArea').innerHTML = '<div class="placeholder">歌词将在这里显示</div>';
  clearLyricTimer();
  setStatus('已切换到 ' + btn.textContent);
});

/* ---------- 搜索 ---------- */
async function doSearch() {
  const kw = $('keyword').value.trim();
  if (!kw) { setStatus('请输入关键词', true); return; }

  $('searchBtn').disabled = true;
  $('resultList').innerHTML = '<div class="placeholder">搜索中…</div>';
  setStatus('搜索中…');

  try {
    const path = PLATFORM_ENDPOINTS[state.platform];
    // 应用设置的搜索数量 t
    const params = `ss=${encodeURIComponent(kw)}&format=json&t=${settings.limit}`;
    const url = API_BASE + path + '?' + params;
    
    const res = await fetch(url);
    if (!res.ok) throw new Error('HTTP ' + res.status);
    const json = await res.json();
    
    const list = extractSongArray(json);
    if (!list.length) {
      setStatus('无结果');
      $('resultList').innerHTML = '<div class="placeholder">没有找到结果</div>';
      return;
    }

    state.songs = list.map(normalizeSong);
    renderResults();
    setStatus(`找到 ${state.songs.length} 首 · ${state.platform}`);
  } catch (e) {
    setStatus('搜索失败：' + e.message, true);
    $('resultList').innerHTML = '<div class="placeholder err">搜索失败：' + escapeHtml(e.message) + '</div>';
    console.error(e);
  } finally {
    $('searchBtn').disabled = false;
  }
}

function extractSongArray(json) {
  if (Array.isArray(json)) return json;
  if (json.data && Array.isArray(json.data)) return json.data;
  if (json.data && Array.isArray(json.data.songs)) return json.data.songs;
  if (json.data && Array.isArray(json.data.list)) return json.data.list;
  if (json.data && Array.isArray(json.data.result)) return json.data.result;
  if (json.list && Array.isArray(json.list)) return json.list;
  if (json.songs && Array.isArray(json.songs)) return json.songs;
  return [];
}

function normalizeSong(s, i) {
  let artist = '未知歌手';
  let rawArtist = s.singer || s.singername || s.artist || s.ar || s.artists || s.author;
  if (rawArtist) {
    if (typeof rawArtist === 'string') artist = rawArtist.replace(/\//g, ' / ');
    else if (Array.isArray(rawArtist) && rawArtist.length > 0) {
      const names = rawArtist.map(a => a && a.name ? a.name : (typeof a === 'string' ? a : '')).filter(Boolean);
      if (names.length > 0) artist = names.join(' / ');
    }
  }
  let duration = s.duration || s.dt || s.interval || 0;
  if (duration > 10000) duration = duration / 1000;

  const url = s.play_url || s.url || s.playUrl || s.src || '';
  let pic = s.cover_url || s.pic || s.albumPic || s.img || '';
  if (!pic && s.al && s.al.picUrl) pic = s.al.picUrl;

  return {
    id: s.songmid || s.id || s.songid || String(i),
    name: s.name || s.songname || s.title || '未知歌曲',
    artist, album: s.album || '', duration, pic, url, raw: s
  };
}

function renderResults() {
  const box = $('resultList');
  if (!state.songs.length) { box.innerHTML = '<div class="placeholder">无结果</div>'; return; }
  box.innerHTML = state.songs.map((s, i) => `
    <div class="song-item ${i === state.currentIndex ? 'active' : ''}" onclick="playSong(${i})">
      <span class="idx">${i + 1}</span>
      <div class="meta">
        <div class="title">${escapeHtml(s.name)}</div>
        <div class="sub">${escapeHtml(s.artist)}</div>
      </div>
      ${s.duration ? `<span class="dur">${fmtTime(s.duration)}</span>` : ''}
    </div>
  `).join('');
}

/* ---------- 播放 ---------- */
async function playSong(index) {
  const song = state.songs[index];
  if (!song) return;

  state.currentIndex = index;
  renderResults();
  $('downloadBtn').disabled = true;
  state.currentPlayUrl = '';

  $('nowName').textContent = song.name;
  $('nowArtist').textContent = song.artist;
  
  const coverImg = $('cover');
  delete coverImg.dataset.retried;
  coverImg.src = song.pic || "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 48 48'%3E%3Crect fill='%23222' width='48' height='48'/%3E%3Ctext x='24' y='30' text-anchor='middle' fill='%23555' font-size='16'%3E♪%3C/text%3E%3C/svg%3E";

  setStatus('获取播放地址…');
  $('lyricArea').innerHTML = '<div class="placeholder">加载歌词…</div>';
  clearLyricTimer();

  const audio = $('audio');
  audio.pause(); audio.removeAttribute('src'); audio.load();

  try {
    let playUrl = '';
    let lyricText = extractLyric(song.raw);
    
    // 二次请求获取带设置音质的详情
    const path = PLATFORM_ENDPOINTS[state.platform];
    const keyword = song.name + (song.artist && song.artist !== '未知歌手' ? ' ' + song.artist : '');
    // 传入 yz 参数指定音质
    const params = `ss=${encodeURIComponent(keyword)}&n=1&format=json&yz=${settings.quality}`;
    const url = API_BASE + path + '?' + params;
    
    const res = await fetch(url);
    const json = await res.json();

    let detail = null;
    if (json.data && !Array.isArray(json.data) && (json.data.play_url || json.data.url)) {
      detail = json.data;
    } else {
      const list = extractSongArray(json);
      if (list.length) detail = list[0];
    }

    if (detail) {
      playUrl = detail.play_url || detail.url || detail.playUrl || detail.src || '';
      if (!lyricText) lyricText = extractLyric(detail);
      if (!song.pic && (detail.cover_url || detail.pic)) coverImg.src = detail.cover_url || detail.pic;
    }

    if (!playUrl) throw new Error('未获取到播放地址');

    state.currentPlayUrl = playUrl;
    state.lyricLines = parseLRC(lyricText);
    renderLyric();

    let finalSrc = playUrl.startsWith('http') ? '/audio-proxy?url=' + encodeURIComponent(playUrl) : playUrl;
    audio.src = finalSrc;
    await audio.play();
    setStatus('播放中 · ' + state.platform);
    $('downloadBtn').disabled = false;
    startLyricSync(audio);

  } catch (e) {
    setStatus('播放失败：' + e.message, true);
    $('lyricArea').innerHTML = '<div class="placeholder err">' + escapeHtml(e.message) + '</div>';
    console.error(e);
  }
}

/* ---------- 下载 ---------- */
async function downloadCurrent() {
  const song = state.songs[state.currentIndex];
  if (!song) return;

  $('downloadBtn').disabled = true;
  setStatus('正在获取下载链接…');

  try {
    // 用设置的下载音质去重新请求
    const path = PLATFORM_ENDPOINTS[state.platform];
    const keyword = song.name + (song.artist && song.artist !== '未知歌手' ? ' ' + song.artist : '');
    const params = `ss=${encodeURIComponent(keyword)}&n=1&format=json&yz=${settings.downloadQuality}`;
    const url = API_BASE + path + '?' + params;
    
    const res = await fetch(url);
    const json = await res.json();

    let detail = null;
    if (json.data && !Array.isArray(json.data) && (json.data.play_url || json.data.url)) {
      detail = json.data;
    } else {
      const list = extractSongArray(json);
      if (list.length) detail = list[0];
    }

    if (!detail) throw new Error('未获取到下载地址');
    const downloadUrl = detail.play_url || detail.url || detail.playUrl || detail.src || '';
    if (!downloadUrl) throw new Error('该音质无下载链接');

    // 获取文件后缀
    let ext = 'mp3';
    if (detail.extName) ext = detail.extName;
    else if (detail.encodeType) ext = detail.encodeType;
    else if (downloadUrl.includes('.flac')) ext = 'flac';
    else if (downloadUrl.includes('.m4a')) ext = 'm4a';

    const fileName = `${song.artist} - ${song.name}.${ext}`;
    
    // 通过代理下载，并传入 filename 强制附件下载
    const proxyUrl = `/audio-proxy?url=${encodeURIComponent(downloadUrl)}&download=1&filename=${encodeURIComponent(fileName)}`;
    
    // 使用隐藏的 a 标签触发下载
    const a = document.createElement('a');
    a.href = proxyUrl;
    a.download = fileName;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    
    setStatus('开始下载：' + fileName);
  } catch (e) {
    setStatus('下载失败：' + e.message, true);
  } finally {
    $('downloadBtn').disabled = false;
  }
}

/* ---------- 歌词 ---------- */
function extractLyric(raw) {
  if (!raw) return '';
  return raw.lyric || raw.lrc || raw.lyrics || '';
}

function parseLRC(text) {
  if (!text || typeof text !== 'string') return [];
  const lines = [];
  const re = /\[(\d{2}):(\d{2})\.(\d{2,3})\](.*)/g;
  let m;
  while ((m = re.exec(text)) !== null) {
    const t = parseInt(m[1], 10) * 60 + parseInt(m[2], 10) + parseInt(m[3].padEnd(3, '0'), 10) / 1000;
    const content = m[4].trim();
    if (content) lines.push({ time: t, content });
  }
  lines.sort((a, b) => a.time - b.time);
  return lines;
}

function renderLyric() {
  const box = $('lyricArea');
  if (!state.lyricLines.length) {
    box.innerHTML = '<div class="placeholder">该接口未返回歌词</div>';
    return;
  }
  box.innerHTML = state.lyricLines.map((l, i) =>
    `<div class="lyric-line" data-i="${i}">${escapeHtml(l.content)}</div>`
  ).join('');
}

function startLyricSync(audio) {
  clearLyricTimer();
  const lines = state.lyricLines;
  if (!lines.length) return;
  const els = $('lyricArea').querySelectorAll('.lyric-line');
  let last = -1;
  state.lyricTimer = setInterval(() => {
    const t = audio.currentTime;
    let idx = -1;
    for (let i = lines.length - 1; i >= 0; i--) {
      if (t >= lines[i].time) { idx = i; break; }
    }
    if (idx === last) return;
    last = idx;
    els.forEach((el, j) => el.classList.toggle('active', j === idx));
    if (idx >= 0 && els[idx]) els[idx].scrollIntoView({ block: 'center', behavior: 'smooth' });
  }, 200);
}

function clearLyricTimer() {
  if (state.lyricTimer) { clearInterval(state.lyricTimer); state.lyricTimer = null; }
}

window.addEventListener('beforeunload', clearLyricTimer);