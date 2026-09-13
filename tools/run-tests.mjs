import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const rootDir = path.resolve(__dirname, '..');

const testSuites = [
    { name: 'Native Unit & Integration Tests', command: process.execPath, args: ['--test', 'tests/'] },
    { name: 'Phase 1 Reliability Tests', command: process.execPath, args: ['tools/test-reliability.mjs'] },
    { name: 'Phase 2 PWA Infrastructure Tests', command: process.execPath, args: ['tools/test-phase2-pwa.mjs'] }
];

console.log('🚀 Starting VibeAudio Test Consolidation Suite...\n');

let hasFailure = false;

for (const suite of testSuites) {
    console.log(`\n================================================================`);
    console.log(`▶ RUNNING: ${suite.name}`);
    console.log(`================================================================\n`);

    const result = spawnSync(suite.command, suite.args, {
        cwd: rootDir,
        stdio: 'inherit',
        shell: false
    });

    if (result.status !== 0) {
        console.error(`\n❌ FAILED: ${suite.name} (Exit code: ${result.status})`);
        hasFailure = true;
        break;
    } else {
        console.log(`\n✅ PASSED: ${suite.name}`);
    }
}

if (hasFailure) {
    console.error('\n🚨 Test suite run failed. See errors above.');
    process.exit(1);
} else {
    console.log('\n🎉 All test suites passed successfully!');
    process.exit(0);
}
