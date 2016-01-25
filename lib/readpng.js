const fs = require('fs');
const {PNG} = require('pngjs');

/**
 * Transform a PNG object into a 2D pixel grid.
 */
export class ImageData {
  constructor(png) {
    this.data = [];
    this.width = png.width;
    this.height = png.height;
    for (let y = 0; y < png.height; y++) {
      this.data.push([]);
      for (let x = 0; x < png.width; x++) {
        const idx = (y * png.width + x) * 4;
        this.data[y].push(png.data.slice(idx, idx + 4));
      }
    }
  }
}

export function readpng(filename) {
  return new Promise((resolve, reject) => {
    const png = new PNG();
    png
      .on('parsed', () => {
        resolve(png);
      })
      .on('error', function (e) {
        reject(e);
      });

    fs.readFile(filename, (error, result) => {
      if (error != null) {
        return reject(error);
      }
      png.write(result);
    });
  });
}
