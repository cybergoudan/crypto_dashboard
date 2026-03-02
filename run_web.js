const http = require('http');
const fs = require('fs');
const path = require('path');

http.createServer((req, res) => {
    // 允许任何域调用前端页面的 API，这是为 LightweightCharts 本地执行保驾护航
    res.setHeader('Access-Control-Allow-Origin', '*');
    
    fs.readFile(path.join(__dirname, 'index.html'), (err, content) => {
        if (err) {
            res.writeHead(500);
            res.end(`Error: ${err.code}`);
        } else {
            res.writeHead(200, { 'Content-Type': 'text/html' });
            res.end(content, 'utf-8');
        }
    });
}).listen(28965, '::');
console.log('Static server for [::]:28965 ready');
