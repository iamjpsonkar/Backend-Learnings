const http = require('http');

const server = http.createServer((req, res) => {
    res.writeHead(200, { 'Content-Type': 'text/plain' });
    res.end('Welcome to Server 1');
});

server.listen(3001, '0.0.0.0', () => {
    console.log('Welcome to Server 1');
});