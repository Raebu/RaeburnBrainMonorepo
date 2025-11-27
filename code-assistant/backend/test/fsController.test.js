import fs from 'fs-extra';
import path from 'path';
import { execSync } from 'child_process';
import {
  listDir,
  readFile,
  writeFile,
  createDir,
  renamePath,
  deletePath,
  gitStatus,
  gitAdd,
  gitCommit,
  gitPush,
} from '../fsController.js';

describe('fsController', () => {
  const originalCwd = process.cwd();
  const tmpDir = path.join(originalCwd, 'tmp-test');

  beforeAll(async () => {
    await fs.ensureDir(tmpDir);
    process.chdir(tmpDir);
    await fs.writeFile('a.txt', 'hello');
    await fs.writeFile('b.txt', 'world');
  });

  afterAll(async () => {
    process.chdir(originalCwd);
    await fs.remove(tmpDir);
  });

  test('listDir returns files', async () => {
    const files = await listDir('.');
    const names = files.map((f) => f.name).sort();
    expect(names).toEqual(['a.txt', 'b.txt']);
  });

  test('read and write file', async () => {
    await writeFile('c.txt', '123');
    const data = await readFile('c.txt');
    expect(data).toBe('123');
  });

  test('create, rename and delete directory', async () => {
    await createDir('sub');
    await writeFile('sub/file.txt', 'x');
    await renamePath('sub/file.txt', 'sub/renamed.txt');
    const content = await readFile('sub/renamed.txt');
    expect(content).toBe('x');
    await deletePath('sub');
    const exists = await fs.pathExists('sub');
    expect(exists).toBe(false);
  });

  test('gitStatus runs', () => {
    const status = gitStatus();
    expect(Array.isArray(status)).toBe(true);
  });

  describe('git operations', () => {
    const repoDir = path.join(tmpDir, 'repo');
    const remoteDir = path.join(tmpDir, 'remote.git');

    beforeAll(async () => {
      await fs.ensureDir(repoDir);
      await fs.ensureDir(remoteDir);
      process.chdir(repoDir);
      execSync('git init');
      execSync('git config user.email "test@example.com"');
      execSync('git config user.name "Test"');
      execSync(`git init --bare ${remoteDir}`);
      execSync(`git remote add origin ${remoteDir}`);
      await fs.writeFile('file.txt', 'hi');
    });

    afterAll(async () => {
      process.chdir(tmpDir);
      await fs.remove(repoDir);
      await fs.remove(remoteDir);
    });

    test('add commit push', () => {
      gitAdd(['file.txt']);
      gitCommit('init');
      const log = execSync('git log --oneline').toString();
      expect(log).toMatch('init');
      gitPush();
      const remoteLog = execSync(`git --git-dir=${remoteDir} log --oneline`).toString();
      expect(remoteLog).toMatch('init');
    });
  });
});
