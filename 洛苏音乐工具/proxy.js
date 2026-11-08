const http = require('http');
const https = require('https');
const fs = require('fs');
const path = require('path');
const { exec } = require('child_process');

const PORT = 3000;
const TARGET_HOST = 'api.luosu.top';
const PUBLIC_DIR = path.join(__dirname, 'public');

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.js': 'application/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.ico': 'image/x-icon'
};

function getRefererFor(url) {
  if (url.includes('music.126.net') || url.includes('music.163.com')) return 'https://music.163.com/';
  if (url.includes('qqmusic') || url.includes('y.qq.com') || url.includes('stream.qq.com')) return 'https://y.qq.com/';
  if (url.includes('kugou.com')) return 'https://www.kugou.com/';
  return null;
}

function requestUrl(url, options, callback) {
  const client = url.startsWith('https') ? https : http;
  return client.get(url, options, callback);
}

const server = http.createServer((req, res) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', '*');

  if (req.method === 'OPTIONS') { res.writeHead(204); res.end(); return; }
  if (req.url === '/favicon.ico') { res.writeHead(204); res.end(); return; }

  /* ---------- 1. API 代理 ---------- */
  if (req.url.indexOf('/api/') === 0) {
    const targetUrl = 'https://' + TARGET_HOST + req.url;
    console.log('[API代理]', targetUrl);
    requestUrl(targetUrl, {}, (proxyRes) => {
      res.writeHead(proxyRes.statusCode, proxyRes.headers);
      proxyRes.pipe(res);
    }).on('error', (err) => {
      console.error('[API代理错误]', err.message);
      res.writeHead(502, { 'Content-Type': 'application/json; charset=utf-8' });
      res.end(JSON.stringify({ error: 'Proxy error: ' + err.message }));
    });
    return;
  }

  /* ---------- 2. 音频流/下载代理 ---------- */
  if (req.url.indexOf('/audio-proxy?url=') === 0) {
    // 解析 url 和 下载相关参数
    const urlParams = new URLSearchParams(req.url.split('?')[1]);
    const audioUrl = decodeURIComponent(urlParams.get('url'));
    const isDownload = urlParams.get('download') === '1';
    const fileName = urlParams.get('filename') || 'music.mp3';

    console.log(`[音频代理${isDownload ? ' (下载)' : ''}]`, audioUrl);

    const headers = {
      'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
      'Accept': '*/*'
    };
    const referer = getRefererFor(audioUrl);
    if (referer) headers['Referer'] = referer;
    // 如果是播放，带上 Range 头支持拖动
    if (!isDownload && req.headers.range) headers['Range'] = req.headers.range;

    requestUrl(audioUrl, { headers }, (audioRes) => {
      if (audioRes.statusCode >= 400) {
        console.error('[音频代理] CDN 返回', audioRes.statusCode);
      }
      
      const outHeaders = { ...audioRes.headers };
      // 如果是下载请求，强制浏览器保存文件，而不是尝试播放
      if (isDownload) {
        outHeaders['Content-Disposition'] = `attachment; filename*=UTF-8''${encodeURIComponent(fileName)}`;
        delete outHeaders['content-range']; // 下载不需要分段
      }
      
      res.writeHead(audioRes.statusCode, outHeaders);
      audioRes.pipe(res);
    }).on('error', (err) => {
      console.error('[音频代理错误]', err.message);
      res.writeHead(502); res.end('Audio proxy error');
    });
    return;
  }

  /* ---------- 3. 图片代理 ---------- */
  if (req.url.indexOf('/img-proxy?url=') === 0) {
    const imgUrl = decodeURIComponent(req.url.split('url=')[1]);
    console.log('[图片代理]', imgUrl);

    const headers = {
      'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
      'Accept': 'image/avif,image/webp,image/apng,image/*,*/*;q=0.8'
    };
    const referer = getRefererFor(imgUrl);
    if (referer) headers['Referer'] = referer;

    requestUrl(imgUrl, { headers }, (imgRes) => {
      if (imgRes.statusCode >= 300 && imgRes.statusCode < 400 && imgRes.headers.location) {
        const redirectUrl = imgRes.headers.location.startsWith('http')
          ? imgRes.headers.location
          : new URL(imgRes.headers.location, imgUrl).href;
        const ref2 = getRefererFor(redirectUrl);
        if (ref2) headers['Referer'] = ref2;
        
        requestUrl(redirectUrl, { headers }, (r2) => {
          res.writeHead(r2.statusCode, r2.headers);
          r2.pipe(res);
        }).on('error', () => { res.writeHead(502); res.end(); });
        return;
      }
      res.writeHead(imgRes.statusCode, imgRes.headers);
      imgRes.pipe(res);
    }).on('error', (err) => {
      console.error('[图片代理错误]', err.message);
      res.writeHead(502); res.end();
    });
    return;
  }

  /* ---------- 4. 静态文件 ---------- */
  let filePath = req.url === '/' ? '/index.html' : req.url;
  filePath = filePath.split('?')[0];

  const fullPath = path.normalize(path.join(PUBLIC_DIR, filePath));
  const safeRoot = PUBLIC_DIR.endsWith(path.sep) ? PUBLIC_DIR : PUBLIC_DIR + path.sep;
  if (!fullPath.startsWith(safeRoot) && fullPath !== PUBLIC_DIR) {
    res.writeHead(403); res.end('Forbidden'); return;
  }

  fs.readFile(fullPath, (err, data) => {
    if (err) {
      res.writeHead(404, { 'Content-Type': 'text/plain; charset=utf-8' });
      res.end('Not Found: ' + filePath + '\n请确认文件与 proxy.js 在同一目录。');
      return;
    }
    const ext = path.extname(fullPath).toLowerCase();
    res.writeHead(200, { 'Content-Type': MIME[ext] || 'application/octet-stream' });
    res.end(data);
  });
});

server.listen(PORT, () => {
  const url = 'http://localhost:' + PORT;
  console.log('========================================');
  console.log('  洛苏音乐工具已启动');
  console.log('  访问地址: ' + url);
  console.log('========================================');

  const platform = process.platform;
  let cmd;
  if (platform === 'win32') cmd = 'start "" "' + url + '"';
  else if (platform === 'darwin') cmd = 'open "' + url + '"';
  else cmd = 'xdg-open "' + url + '"';
  exec(cmd, (err) => { if (err) console.log('请手动打开: ' + url); });
});