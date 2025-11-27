import path from 'path';
import { execSync } from 'child_process';

function rootPath() {
  return process.cwd();
}

/**
 * Recursively list files and directories under a given path.
 * @param {string} dirPath
 * @returns {Promise<object>}
 */
export async function listDir(dirPath = '.') {
  const fullPath = path.join(rootPath(), dirPath);
  const entries = await fs.readdir(fullPath, { withFileTypes: true });
  const results = await Promise.all(entries.map(async (entry) => {
    const entryPath = path.join(dirPath, entry.name);
    if (entry.isDirectory()) {
      return { name: entry.name, path: entryPath, type: 'dir' };
    }
    const stats = await fs.stat(path.join(rootPath(), entryPath));
    return { name: entry.name, path: entryPath, type: 'file', size: stats.size };
  }));
  return results;
}

/**
 * Read a file as UTF-8 string.
 * @param {string} filePath
 */
export async function readFile(filePath) {
  const fullPath = path.join(rootPath(), filePath);
  return fs.readFile(fullPath, 'utf8');
}

/**
 * Write file contents, creating directories as needed.
 * @param {string} filePath
 * @param {string} content
 */
export async function writeFile(filePath, content) {
  const fullPath = path.join(rootPath(), filePath);
  await fs.ensureDir(path.dirname(fullPath));
  await fs.writeFile(fullPath, content, 'utf8');
}

/**
 * Create a new directory.
 * @param {string} dirPath
 */
export async function createDir(dirPath) {
  await fs.ensureDir(path.join(rootPath(), dirPath));
}

/**
 * Rename a file or directory.
 * @param {string} oldPath
 * @param {string} newPath
 */
export async function renamePath(oldPath, newPath) {
  await fs.move(path.join(rootPath(), oldPath), path.join(rootPath(), newPath), { overwrite: true });
}

/**
 * Remove a file or directory.
 * @param {string} targetPath
 */
export async function deletePath(targetPath) {
  await fs.remove(path.join(rootPath(), targetPath));
}

/**
 * Get git-style status for files under the repository.
 */
export function gitStatus() {
  try {
    const output = execSync('git status --porcelain', { cwd: rootPath() }).toString();
    return output.split('\n').filter(Boolean).map((line) => {
      const status = line.slice(0, 2).trim();
      const file = line.slice(3).trim();
      return { file, status };
    });
  } catch (err) {
    return [];
  }
}

/**
 * Stage files using git add.
 * @param {string[]} files
 */
export function gitAdd(files) {
  if (!files || files.length === 0) return;
  const quoted = files.map((f) => `'${f.replace(/'/g, "'\\''")}'`).join(' ');
  execSync(`git add ${quoted}`, { cwd: rootPath() });
}

/**
 * Commit staged files with a message.
 * @param {string} message
 */
export function gitCommit(message) {
  const msg = message.replace(/"/g, '\\"');
  execSync(`git commit -m "${msg}"`, { cwd: rootPath() });
}

/**
 * Push commits to the default remote.
 */
export function gitPush() {
  execSync('git push', { cwd: rootPath() });
}

export default {
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
};
