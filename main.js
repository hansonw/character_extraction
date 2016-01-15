const fs = require('fs');
const PNG = require('pngjs').PNG;

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

if (process.argv.length <= 2) {
  console.error('No input file.');
  return;
}

console.log('Reading PNG file..');
const png = new PNG({checkCRC: false});
png
  .on('parsed', function() {
    try {
      console.log('Processing image..');
      processImage(png);
      png.pack().pipe(fs.createWriteStream('out.png'));
      console.log('Done!');
    } catch (e) {
      console.error(e);
    }
  })
  .on('error', function(e) {
    console.error(e);
  });

const data = fs.readFileSync(process.argv[2])
png.write(data);
