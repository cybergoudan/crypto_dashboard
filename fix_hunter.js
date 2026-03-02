const fs = require('fs');
let py = fs.readFileSync('agent_squeeze_hunter.py', 'utf8');

const tStart = py.indexOf('payload = {');
const tEnd = py.indexOf('}', tStart);

if (tStart > -1 && tEnd > -1) {
    const oldPayload = py.substring(tStart, tEnd+1);
    const newPayload = oldPayload.replace('"type": "FUNDING_SQUEEZE"', '"type": "FUNDING_SQUEEZE",\n        "funding_rate": target[\'fundingRate\']');
    py = py.replace(oldPayload, newPayload);
    fs.writeFileSync('agent_squeeze_hunter.py', py);
}
