const express = require('express');
const { createProxyMiddleware } = require('http-proxy-middleware');

const app = express();
const PORT = process.env.PORT || 3000;

app.use('/', createProxyMiddleware({
  target: 'https://brew-labs-ob-agent-dashboard.streamlit.app',
  changeOrigin: true,
  ws: true,
}));

app.listen(PORT, () => console.log(`Proxy on port ${PORT}`));
