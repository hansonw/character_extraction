import sys, os
import Queue
from PIL import Image

'''
Current flow
  1. detect bubble
  2. extract text from bubble
  3. crop extra white border
  4. apply threshold
  5. divide space into boxes based on black pixels
  6. further dissect boxes to deal with edge cases
  7. repeat 5, 6 one more time
  8. merge boxes to form squares

TO DO:
  Possible improvements:
    1. better filtering so light colored parts don't get cropped off
    2. clustering/grouping nearby words into connected components
    3. instead of using boxes, use vertical lines
    
    Notes on edge cases to improve for
      1. multiple text regions in one bubble, this is the main one
      2. punctuation marks
  Make comments, starting to forget lol

'''

DBG = 0
WHITE_COLOR = 245
BLACK_COLOR = 40
MIN_WHITE_PIX = 625
THRES = 128
BUBBLE_MARGIN = 5
CHAR_MARGIN = 2
RATIO_THRES = 0.85
MAX_BOX_NUM = 5
BLACK_PIX_THRES = 20
DISSECT_NUM = 2
DISSECT_RATIO_THRES = 0.6
WORD_BREAK_MIN_LEN = 30
MIN_BLK_PIX = 3
MIN_BOX_SIZE = 8
MAX_BOX_SIZE = 40000

directions = [(0, 1), (0, -1), (1, 0), (-1, 0)]
matrix_bounds = None

class Text_block():
  def __init__(self, ymin, ymax, xmin, xmax, ylen, xlen, ratio, blk_pix_cnt):
    self.ymin = ymin
    self.ymax = ymax
    self.xmin = xmin
    self.xmax = xmax
    self.ylen = ylen
    self.xlen = xlen
    self.ratio = ratio
    self.blk_pix_cnt = blk_pix_cnt
    self.down = None
    self.right = None
    self.matched = False
    
  def is_valid_block(self):
    enough_blk_pix = self.blk_pix_cnt >= MIN_BLK_PIX
    box_size = self.ylen * self.xlen
    valid_size = box_size < MAX_BOX_SIZE and box_size > MIN_BOX_SIZE
    return enough_blk_pix and valid_size
    
  def unpack(self):
    return (self.ymin, self.ymax, self.xmin, self.xmax, self.ylen, self.xlen,
            self.ratio, self.blk_pix_cnt)
            
  def has_word(self):
    return self.blk_pix_cnt > 0


def mark_text_blocks(matrix, idx=''):
  matrix_w_gaps = mark_gaps(matrix, idx)
  blocks = convert_img_to_blocks(matrix_w_gaps)
  processed_blocks = break_down_deformed_blocks(matrix_w_gaps, blocks)
  
  if DBG:
    boxes_img = [[100 if pix == -1 else pix for pix in row] for row in matrix_w_gaps]
    write_blocks_to_img(boxes_img, processed_blocks)
    print_image(boxes_img, 'bubbles_pre_merge')
  
  # merge blocks
  final_blocks = merge_blocks_to_form_squares(matrix_w_gaps, processed_blocks)
  
  # draw blocks on clean bubble
  if DBG:
    merged_blocks_img = [list(x) for x in matrix]
    write_blocks_to_img(merged_blocks_img, final_blocks)
    print_image(merged_blocks_img, 'final_merged_blocks' + idx)
  
  return final_blocks
  
  
def break_down_deformed_blocks(matrix_w_gaps, blocks):
  # break blocks down further if necessary
  for i in xrange(DISSECT_NUM):
    for block in blocks:
      if block.ratio <= DISSECT_RATIO_THRES:
        mark_gaps_within_block(matrix_w_gaps, block)
    blocks = convert_img_to_blocks(matrix_w_gaps, str(i))
  return blocks
  
  
def merge_blocks_to_form_squares(matrix_w_gaps, blocks):
  mark_adj_blocks(blocks, matrix_w_gaps)
  final_blocks = []
  for block in blocks:
    if block.matched or not block.has_word():
      continue
    if block.ratio < RATIO_THRES:
      block = merge_w_nearby_blocks(block)
    if block.is_valid_block():
      final_blocks.append(block)
  return final_blocks
  
  
def mark_gaps(matrix, idx):
  print 'marking gaps...'
  matrix_w_gaps = [list(x) for x in matrix]
  vert_has_word = [0] * len(matrix)
  horz_has_word = [0] * len(matrix[0])
  
  for i, y in enumerate(matrix):
    for j, x in enumerate(y):
      if x <= BLACK_COLOR:
        vert_has_word[i] = 1
        horz_has_word[j] = 1
        
  for i in xrange(len(matrix)):
    for j in xrange(len(matrix[0])):
      if vert_has_word[i] == 0 or horz_has_word[j] == 0:
        matrix_w_gaps[i][j] = -1
  
  if DBG:
    gaps_marked = [list(x) for x in matrix]
    for i in xrange(len(matrix)):
      for j in xrange(len(matrix[0])):
        if vert_has_word[i] == 0 or horz_has_word[j] == 0:
          gaps_marked[i][j] = 100
    print_image(gaps_marked, 'gaps_marked' + idx)
    
  return matrix_w_gaps

  
def mark_gaps_within_block(matrix, block):
  ymin, ymax, xmin, xmax, ylen, xlen, ratio, blk_pix_cnt = block.unpack()
  vert_has_word = [0] * ylen
  horz_has_word = [0] * xlen
  
  for i in xrange(ymin, ymax + 1):
    for j in xrange(xmin, xmax + 1):
      if matrix[i][j] <= BLACK_COLOR and matrix[i][j] >= 0:
        vert_has_word[i - ymin] = 1
        horz_has_word[j - xmin] = 1
        
  if ylen > WORD_BREAK_MIN_LEN:
    for i in xrange(ymin, ymax + 1):
        if vert_has_word[i - ymin] == 0:
          for j in xrange(xmin, xmax + 1):
            matrix[i][j] = -1
  
  if xlen > WORD_BREAK_MIN_LEN:
    for j in xrange(xmin, xmax + 1):
        if horz_has_word[j - xmin] == 0:
          for i in xrange(ymin, ymax + 1):
            matrix[i][j] = -1
  
  
def convert_img_to_blocks(matrix_w_gaps, idx=''):
  processed = set()
  blocks = []
  for i, row in enumerate(matrix_w_gaps):
    for j, pix in enumerate(row):
      if pix != -1 and (i, j) not in processed:
        block = get_block_parameters(matrix_w_gaps, i, j, processed)
        blocks.append(block)
      
  if DBG:
    boxes_img = [[100 if pix == -1 else pix for pix in row] for row in matrix_w_gaps]
    write_blocks_to_img(boxes_img, blocks)
    print_image(boxes_img, 'boxes_preliminary' + idx)
      
  return blocks
  
  
def mark_adj_blocks(blocks, matrix_w_gaps):
  regions = [[-1] * len(matrix_w_gaps[0]) for x in xrange(len(matrix_w_gaps))]
  
  # first pass, mark idx for different blocks
  idx = 0
  for block in blocks:
    ymin, ymax, xmin, xmax, ylen, xlen, ratio, blk_pix_cnt = block.unpack()
    for i in xrange(ymin, ymax + 1):
      for j in xrange(xmin, xmax + 1):
        regions[i][j] = idx
    idx += 1
  
  # second pass, connect nodes/blocks
  for block in blocks:
    ymin, ymax, xmin, xmax, ylen, xlen, ratio, blk_pix_cnt = block.unpack()
    ymid = (ymin + ymax) / 2
    xmid = (xmin + xmax) / 2
    # search right
    right_idx = -1
    for j in xrange(xmax + 1, len(matrix_w_gaps[0])):
      if regions[ymid][j] != -1:
        right_idx = regions[ymid][j]
        break    
    if right_idx != -1:
      r_block = blocks[right_idx]
      if r_block.ymax == block.ymax and r_block.ymin == block.ymin:
        block.right = r_block
    # search down
    down_idx = -1
    for i in xrange(ymax + 1, len(matrix_w_gaps)):
      if regions[i][xmid] != -1:
        down_idx = regions[i][xmid]
        break    
    if down_idx != -1:
      d_blocks = blocks[down_idx]
      if d_blocks.xmax == block.xmax and d_blocks.xmin == block.xmin:
        block.down = d_blocks
  
  
def merge_w_nearby_blocks(block):
  ymin, ymax, xmin, xmax, ylen, xlen, ratio, \
        blk_pix_cnt = block.unpack()
  
  if ylen > xlen:
    r_block = block.right
    for i in xrange(MAX_BOX_NUM):
      if not r_block:
        break
      ymin1, ymax1, xmin1, xmax1, ylen1, xlen1, ratio1, \
            blk_pix_cnt1 = r_block.unpack()
      new_ratio = box_ratio(ylen, xlen + xmax1 - xmax)
      if new_ratio > max(ratio, ratio1):
        ratio = new_ratio
        xlen += xmax1 - xmax
        xmax = xmax1
        blk_pix_cnt += blk_pix_cnt1
        r_block.matched = True
        r_block = r_block.right
      else:
        break
  else:
    d_block = block.down
    for i in xrange(MAX_BOX_NUM):
      if not d_block:
        break
      ymin1, ymax1, xmin1, xmax1, ylen1, xlen1, ratio1, \
            blk_pix_cnt1 = d_block.unpack()
      new_ratio = box_ratio(xlen, ylen + ymax1 - ymax)
      if new_ratio > max(ratio, ratio1):
        ratio = new_ratio
        ylen += ymax1 - ymax
        ymax = ymax1
        blk_pix_cnt += blk_pix_cnt1
        d_block.matched = True
        d_block = d_block.down
      else:
        break
  
  final_block = Text_block(ymin, ymax, xmin, xmax, ylen, xlen, ratio,
                      blk_pix_cnt)
  return final_block


def box_ratio(ylen, xlen):
  return float(min(xlen, ylen)) / max(xlen, ylen)

  
def write_blocks_to_img(matrix, blocks):
  for block in blocks:
    ymin, ymax, xmin, xmax, ylen, xlen, ratio, blk_pix_cnt = block.unpack()
    if block.has_word():
      ystart = max(0, ymin - CHAR_MARGIN)
      yend = min(len(matrix) - 1, ymax + CHAR_MARGIN)
      xstart = max(0, xmin - CHAR_MARGIN)
      xend = min(len(matrix[0]) - 1, xmax + CHAR_MARGIN)
      for i in xrange(ystart, yend + 1):
        matrix[i][xstart] = -1
        matrix[i][xend] = -1
      for j in xrange(xstart, xend + 1):
        matrix[ystart][j] = -1
        matrix[yend][j] = -1


def get_block_parameters(matrix, ycoord, xcoord, processed):
  blk_pix_cnt = 0
  i = ycoord
  while i + 1 < len(matrix) and (matrix[i][xcoord] != -1 
                              or matrix[i + 1][xcoord] != -1):
    j = xcoord
    while j + 1 < len(matrix[0]) and (matrix[i][j] != -1 
                                  or matrix[i][j + 1] != -1):
      processed.add((i, j))
      if matrix[i][j] <= BLACK_COLOR and matrix[i][j] >= 0:
        blk_pix_cnt += 1
      j += 1
    i += 1
  
  ymin, ymax, xmin, xmax = ycoord, i - 1, xcoord, j - 1
  ylen, xlen = i - ycoord, j - xcoord
  ratio = box_ratio(ylen, xlen)
  return Text_block(ymin, ymax, xmin, xmax, ylen, xlen, ratio, blk_pix_cnt)


def search_for_bubble_near_coord(matrix, ycoord, xcoord):
  print "Running BFS around (%d, %d) + flood fill..." % (ycoord, xcoord)
  visited_white_pix = set()
  q = Queue.Queue()
  q.put((ycoord, xcoord))
  visited = set()
  visited.add((ycoord, xcoord))
  boundary = [ycoord, ycoord, xcoord, xcoord]
  
  while not q.empty():
    y, x = q.get()
    if matrix[y][x] >= WHITE_COLOR:
      flood_fill_white(matrix, visited_white_pix, y, x, boundary)
      if len(visited_white_pix) > MIN_WHITE_PIX:
        break
    for i, j in directions:
      next_pix = (y + i, x + j)
      if in_bounds(next_pix, matrix_bounds) and next_pix not in visited:
        q.put(next_pix)
        visited.add(next_pix)
    
  bubble, blk_pix_cnt, offsets = extract_text(matrix, boundary, visited_white_pix)
  if bubble and blk_pix_cnt >= BLACK_PIX_THRES:
    mark_text_blocks(bubble)
  else:
    print 'No bubble found with given coordinates'

    
def search_img_for_bubbles(matrix):
  final_img = [list(x) for x in matrix]
  visited = set()
  bubble_count = 0
  print 'Searching for bubbles...'
  for i, row in enumerate(matrix):
    for j, pix in enumerate(row):
      if pix >= WHITE_COLOR and (i, j) not in visited:
        visited_white_pix = set()
        boundary = [i, i, j, j]  # ymin, ymax, xmin, xmax
        flood_fill_white(matrix, visited_white_pix, i, j, boundary)
        visited |= visited_white_pix
        ymin, ymax, xmin, xmax = boundary
        if len(visited_white_pix) > MIN_WHITE_PIX:
          bubble, blk_pix_cnt, offsets = extract_text(matrix, boundary, \
                                          visited_white_pix, str(bubble_count))
          yoffset, xoffset = offsets
          if bubble and blk_pix_cnt >= BLACK_PIX_THRES:
            print '\n%dth bubble found' % (bubble_count + 1)
            print 'Bubble found at:', boundary
            bubble_count += 1
            blocks = mark_text_blocks(bubble, str(bubble_count))
            write_to_final_img(final_img, blocks, ymin + yoffset, 
                               xmin + xoffset, matrix)
  print_image(final_img, 'final_img')
  
  
def write_to_final_img(final_img, blocks, yoffset, xoffset, matrix):
  for block in blocks:
    ymin, ymax, xmin, xmax, ylen, xlen, ratio, blk_pix_count = block.unpack()
    if block.has_word():
      ystart = max(0, yoffset + ymin - CHAR_MARGIN)
      yend = min(len(matrix) - 1, yoffset + ymax + CHAR_MARGIN)
      xstart = max(0, xoffset + xmin - CHAR_MARGIN)
      xend = min(len(matrix[0]) - 1, xoffset + xmax + CHAR_MARGIN)
      for i in xrange(ystart, yend + 1):
        final_img[i][xstart] = -1
        final_img[i][xend] = -1
      for j in xrange(xstart, xend + 1):
        final_img[ystart][j] = -1
        final_img[yend][j] = -1


def extract_text(matrix, boundary, white_space, idx=''):
  print "Running 2nd flood fill from corners"
  
  background_pixels = mark_background(white_space, boundary)
  ymin, ymax, xmin, xmax = boundary
  clean_bubble = [[255 if (i, j) in background_pixels else matrix[i][j] \
                for j in xrange(xmin, xmax + 1)] \
                for i in xrange(ymin, ymax + 1)]
  apply_threshold(clean_bubble, WHITE_COLOR, BLACK_COLOR)
  
  if DBG:
    test_image1 = [[matrix[i][j] \
                  for j in xrange(xmin, xmax + 1)] \
                  for i in xrange(ymin, ymax + 1)]
    test_image2 = [[100 if (i, j) in white_space else matrix[i][j] 
                  for j in xrange(xmin, xmax + 1)] \
                  for i in xrange(ymin, ymax + 1)]
    bord = [[0 if (i, j) in background_pixels else matrix[i][j] \
                  for j in xrange(xmin, xmax + 1)] \
                  for i in xrange(ymin, ymax + 1)]
    print_image(test_image1, 'original_text_block' + idx)
    print_image(test_image2, 'text_block' + idx)
    print_image(bord, 'borders' + idx)
    print_image(clean_bubble, 'clean_block' + idx)
  
  return tighten_bubble(clean_bubble, idx)

  
def tighten_bubble(matrix, idx):
  print "Cropping extra white space..."
  xmin = len(matrix[0])
  xmax = -1
  ymin = len(matrix)
  ymax = -1
  black_pix_count = 0
  
  for i in xrange(len(matrix)):
    for j in xrange(len(matrix[0])):
      if matrix[i][j] <= BLACK_COLOR:
        black_pix_count += 1
        xmin = min(j, xmin)
        xmax = max(j, xmax)
        ymin = min(i, ymin)
        ymax = max(i, ymax)
  
  xmin = xmin - BUBBLE_MARGIN if xmin >= BUBBLE_MARGIN else 0
  xmax = xmax + BUBBLE_MARGIN if xmax < len(matrix[0]) - BUBBLE_MARGIN else 0
  ymin = ymin - BUBBLE_MARGIN if ymin >= BUBBLE_MARGIN else 0
  ymax = ymax + BUBBLE_MARGIN if ymax < len(matrix) - BUBBLE_MARGIN else 0
  
  if DBG:
    box = [list(x) for x in matrix]
    for i in xrange(len(matrix)):
      box[i][xmin] = 0
      box[i][xmax] = 0
    for i in xrange(len(matrix[0])):
      box[ymin][i] = 0
      box[ymax][i] = 0
    print_image(box, 'box_lines' + idx)
  
  tightened_bubble = [[matrix[i][j] for j in xrange(xmin, xmax + 1)] \
                      for i in xrange(ymin, ymax + 1)]
  return tightened_bubble, black_pix_count, (ymin, xmin)
  
  
def mark_background(visited_white_pix, boundary):
  ymin, ymax, xmin, xmax = boundary
  border = set()
  # do flood fill from the boundaries
  for i in xrange(xmin, xmax + 1):
    if (ymin, i) not in border and (ymin, i) not in visited_white_pix:
      flood_fill_non_white(visited_white_pix, border, boundary, ymin, i)
    if (ymax, i) not in border and (ymax, i) not in visited_white_pix:
      flood_fill_non_white(visited_white_pix, border, boundary, ymax, i)
      
  for i in xrange(ymin, ymax + 1):
    if (i, xmin) not in border and (i, xmin) not in visited_white_pix:
      flood_fill_non_white(visited_white_pix, border, boundary, i, xmin)
    if (i, xmax) not in border and (i, xmax) not in visited_white_pix:
      flood_fill_non_white(visited_white_pix, border, boundary, i, xmax)  

  return border

  
def flood_fill_non_white(visited_white_pix, border, boundary, ycoord, xcoord):
  stack = [(ycoord, xcoord)]
  while stack:
    y, x = stack.pop()
    for i, j in directions:
      next_pix = (y + i, x + j)
      if in_bounds(next_pix, boundary) and next_pix not in visited_white_pix \
                                       and next_pix not in border:
        stack.append(next_pix)
        border.add(next_pix)
    
  
def flood_fill_white(matrix, visited_white_pix, ycoord, xcoord, boundary):
  stack = [(ycoord, xcoord)]
  visited_white_pix.add((ycoord, xcoord))
  while stack:
    y, x = stack.pop()
    if y < boundary[0]:
      boundary[0] = y
    if y > boundary[1]:
      boundary[1] = y
    if x < boundary[2]:
      boundary[2] = x
    if x > boundary[3]:
      boundary[3] = x
    
    for i, j in directions:
      yn, xn = y + i, x + j
      next_pix = (yn, xn)
      if in_bounds(next_pix, matrix_bounds) and matrix[yn][xn] >= WHITE_COLOR \
            and next_pix not in visited_white_pix:
        stack.append(next_pix)
        visited_white_pix.add(next_pix)

        
def in_bounds(coord, limits):
  i, j = coord
  ymin, ymax, xmin, xmax = limits
  return i >= ymin and i <= ymax and j >= xmin and j <= xmax
  
  
def apply_threshold(matrix, white_thres=255, black_thres=0):
  for i in xrange(len(matrix)):
    for j in xrange(len(matrix[0])):
      if matrix[i][j] >= white_thres:
        matrix[i][j] = 255
      if matrix[i][j] <= black_thres:
        matrix[i][j] = 0

      
def print_image(matrix, fname):
  blk = (0, 0, 0)           # color black
  wht = (255, 255, 255)     # color white
  grn = (0, 255, 0)
  red = (255, 0, 0)
  
  pixels2 = [grn if x == -1 else red if x == -2 else (x, x, x) 
              for row in matrix for x in row]
  
  im2 = Image.new("RGB", (len(matrix[0]), len(matrix)))
  im2.putdata(pixels2)
  im2.save(fname + '.png', "PNG")
  
  
def main():
  global matrix_bounds
  global DBG
  
  args = sys.argv[1:]
  filename = args[0]
  print "Reading image file..."
  try:
    im = Image.open(filename)
  except IOError:
    print "Error in file name"
    sys.exit()
  
  # get pixel values and store to list
  im = im.convert("L")
  pixels = list(im.getdata())
  width, height = im.size
  # convert to list to 2D list
  pixels = [pixels[i * width:(i + 1) * width] for i in xrange(height)]
  matrix_bounds = [0, height - 1, 0, width - 1]
  
  if len(args) >= 3:
    DBG = 1
    x, y = int(args[1]), int(args[2])
    search_for_bubble_near_coord(pixels, y, x)
  else:
    search_img_for_bubbles(pixels)


if __name__ == '__main__':
  main()
