const fs = require('fs');
const {readpng} = require('./lib/readpng');

function processImage(img) {
  // Each pixel is stored as 4 bytes, RGBA
  for (var y = 0; y < img.height; y++) {
    for (var x = 0; x < img.width; x++) {
      var idx = (img.width * y + x) << 2;

      // invert color
      img.data[idx] = 255 - img.data[idx];
      img.data[idx+1] = 255 - img.data[idx+1];
      img.data[idx+2] = 255 - img.data[idx+2];
    }
  }
}

async function main() {
  if (process.argv.length <= 2) {
    console.error('No input file.');
    return;
  }
  try {
    console.log('reading image..');
    const img = await readpng(process.argv[2]);
    console.log('processing...');
    processImage(img);
    img.pack().pipe(fs.createWriteStream('out.png'));
    console.log('output written to out.png');
  } catch (e) {
    console.err(e);
  }
}

main();
