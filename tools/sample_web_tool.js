#!/usr/bin/env node
// Example custom tool: fetch JSON from an HTTPS endpoint using Node built-ins.
const https = require('https');

const url = process.argv[2];
if (!url || !url.startsWith('https://')) {
  console.error('Usage: node tools/sample_web_tool.js https://example.com/data.json');
  process.exit(2);
}

https.get(url, (res) => {
  let data = '';
  res.on('data', (chunk) => { data += chunk; });
  res.on('end', () => {
    console.log(JSON.stringify({ statusCode: res.statusCode, bytes: data.length, preview: data.slice(0, 500) }, null, 2));
  });
}).on('error', (error) => {
  console.error(error.message);
  process.exit(1);
});
