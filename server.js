const express = require('express');
const { createProxyMiddleware } = require('http-proxy-middleware');
const app = express();
app.use('/', createProxyMiddleware({ target: 'https://brew-labs-ob-agent-dashboard.streamlit.app', changeOrigin: true, ws: true }));
app.listen(process.env.PORT || 3000);
