const http = require('http');

const server = http.createServer((req, res) => {
  res.writeHead(200, { 'Content-Type': 'text/plain' });
  res.end('Hello from Node.js Docker over the NGINX HTTPS proxy!');
});

server.listen(3000, '0.0.0.0', () => {
  console.log('Node.js server listening on port 3000');
});
