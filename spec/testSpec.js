import childProcess from 'child_process';
import fs from 'fs';
import path from 'path';

import {readpng, ImageData} from '../lib/readpng';
import {dfs} from '../lib/dfs';

const FIXTURES_DIR = path.join(__dirname, 'fixtures');
// Use weird shades to prevent accidental detection.
const START_COLOR = [0, 0, 254];
const BOX_COLOR = [0, 254, 0];

function within(base, low, high, val) {
  return base * low <= val && val <= base * high;
}

function equals(pixel, color) {
  for (let i = 0; i < 3; i++) {
    if (pixel[i] !== color[i]) {
      return false;
    }
  }
  return true;
}

function findStartPixel(img) {
  for (let y = 0; y < img.height; y++) {
    for (let x = 0; x < img.width; x++) {
      if (equals(img.data[y][x], START_COLOR)) {
        return [x, y];
      }
    }
  }
  return null;
}

// Replace with the JS implementation eventually.
function findCharacters(imageFile, x, y) {
  const PYTHON_FILE = path.join(__dirname, '../char_extraction.py');
  const {status, stdout, stderr} = childProcess.spawnSync('python', [
    PYTHON_FILE,
    imageFile,
    x,
    y,
  ]);
  if (status !== 0) {
    console.err('could not find characters: %s', stderr);
    return null;
  }
  return JSON.parse(stdout);
}

function findExpected(image) {
  const vis = new Array(image.height);
  for (let y = 0; y < image.height; y++) {
    vis[y] = new Array(image.width);
  }
  const check = (y, x) => {
    return equals(image.data[y][x], BOX_COLOR);
  };
  let bounds = {};
  const callback = (y, x) => {
    if (x < bounds.xmin) bounds.xmin = x;
    if (x > bounds.xmax) bounds.xmax = x;
    if (y < bounds.ymin) bounds.ymin = y;
    if (y > bounds.ymax) bounds.ymax = y;
  };
  const boxes = [];
  for (let y = 0; y < image.height; y++) {
    for (let x = 0; x < image.width; x++) {
      bounds = {
        xmin: image.width,
        xmax: -1,
        ymin: image.height,
        ymax: -1,
      };
      dfs(image, y, x, vis, check, callback);
      if (bounds.xmax !== -1) {
        boxes.push(bounds);
      }
    }
  }
  return boxes;
}

async function waitsForPromise(done, cb) {
  try {
    await cb();
  } catch (e) {
    console.err(e);
  }
  done();
}

describe('basic tests', () => {
  const files = fs.readdirSync(FIXTURES_DIR);
  for (const file of files) {
    const {name, ext} = path.parse(file);
    const parts = name.split('_');
    if (parts.length > 1) {
      const testFile = path.join(FIXTURES_DIR, file);
      const baseFile = path.join(FIXTURES_DIR, parts[0] + ext);
      it(`passes ${file}`, (done) => {
        waitsForPromise(done, async () => {
          const img = new ImageData(await readpng(testFile));
          const pixel = findStartPixel(img);
          expect(pixel).not.toBe(null);
          const chars = findCharacters(baseFile, pixel[0], pixel[1]);
          const expected = findExpected(img);
          // Each expected box should be covered by a matched char.
          for (const box of expected) {
            let match = false;
            for (const char of chars) {
              const xmin = Math.max(char.xmin, box.xmin);
              const xmax = Math.min(char.xmax, box.xmax);
              const ymin = Math.max(char.ymin, box.ymin);
              const ymax = Math.min(char.ymax, box.ymax);
              if (within(box.xmax - box.xmin, 0.7, 1.3, xmax - xmin) &&
                  within(box.ymax - box.ymin, 0.7, 1.3, ymax - ymin)) {
                match = true;
                break;
              }
            }
            expect(match).toBe(
              true,
              'box at ' + JSON.stringify(box) + ' has no match',
            );
          }
        });
      });
    }
  }
});
