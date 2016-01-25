# character_extraction

Dependencies: Pillow/PIL (https://python-pillow.github.io/)

To run on command line in debug mode:
char_extraction.py image.png x_coordinate y_coordinate

Ex:
char_extraction.py test.png 734 166

To run on a full image:
char_extraction.py image.png

## Tests

Run `npm install` (just the first time), then `npm test`.

The test script looks for PNG images in `spec/fixtures`.

- `<base>.png` should be the source file
- `<base>_#.png` are the corresponding test cases. Each case should be the base image with the following additions:
  - a single pixel with the color [0, 0, 254] indicating the start point
  - several rectangles with the color [0, 254, 0] indicating the expected characters.
- The test script to see if each of the drawn rectangles matches an extracted character (with tolerance +- 30%).
