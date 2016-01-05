import sys, os
import Queue
from PIL import Image

WHITE_COLOR = 245
BLACK_COLOR = 10
MIN_WHITE_PIX = 625
THRES = 128
directions = [(0, 1), (0, -1), (1, 0), (-1, 0)]
matrix_bounds = None

def max_black_sq(matrix):
  return
  
  
def draw_grid_lines(matrix):
  xmin = len(matrix[0])
  xmax = -1
  ymin = len(matrix)
  ymax = -1
    
  for i in xrange(len(matrix)):
    for j in xrange(len(matrix[0])):
      if matrix[i][j] <= BLACK_COLOR:
        xmin = min(j, xmin)
        xmax = max(j, xmax)
        ymin = min(i, ymin)
        ymax = max(i, ymax)
  
  xmin = xmin - 2 if xmin >= 2 else 0
  xmax = xmax + 2 if xmax < len(matrix[0]) - 2 else -1
  ymin = ymin - 2 if ymin >= 2 else 0
  ymax = ymax + 2 if ymax < len(matrix) - 2 else -1
  
  # draw box for debug
  box = [[matrix[i][j] for j in xrange(len(matrix[0]))] for i in xrange(len(matrix))]
  for i in xrange(len(matrix)):
    box[i][xmin] = 0
    box[i][xmax] = 0
  for i in xrange(len(matrix[0])):
    box[ymin][i] = 0
    box[ymax][i] = 0
    
  print_image(box, 'box_lines')


'''
Returns the image within the text bubble that encloses the coordinate of the cursor

'''
def crop_bubble(matrix, ycoord, xcoord):
  # records the max and min of x/y for copying to another list later
  # ymin, ymax, xmin, xmax
  boundary = [ycoord, ycoord, xcoord, xcoord]
  
  # stores the coordinates of pixels that should be cropped
  white_space = set()
  white_space.add((ycoord, xcoord))
  
  white_pix_count = 0
  
  # 1st pass, find white pixels only
  # do bfs to search for white pixels around mouse
  # keep doing bfs and running flood fill until some minimum amount
  # of pixels are filled
  q = Queue.Queue()
  visited = set()
  q.put((ycoord, xcoord))
  visited.add((ycoord, xcoord))
  
  while not q.empty() and len(white_space) < MIN_WHITE_PIX:
    y, x = q.get()
    if matrix[y][x] >= WHITE_COLOR:
      flood_fill_white(matrix, white_space, y, x, boundary)
        
    for i, j in directions:
      next = (y + i, x + j)
      if in_bounds(next, matrix_bounds) and next in visited:
        continue
      q.put(next)
      visited.add(next)
  
  print boundary
  ymin, ymax, xmin, xmax = boundary
  
  # test point, save image for debug
  test_image = [[100 if (i, j) in white_space else matrix[i][j] 
                for j in xrange(xmin, xmax + 1)] \
                for i in xrange(ymin, ymax + 1)]
  print_image(test_image, 'text_block')
  
  # 2nd pass, find all enclosed areas
  # check all adjacent pixels that are filled, run another
  # flood fill to find if that area is enclosed by white space
  border_pixels = find_border(matrix, white_space, boundary)
  
  # 3rd pass
  # copy all pixels within text bubble to a new 2D list
  bubble = [[255 if (i, j) in border_pixels else matrix[i][j] for j in xrange(xmin, xmax + 1)] \
                for i in xrange(ymin, ymax + 1)]

  # print images for debug
  bord = [[0 if (i, j) in border_pixels else matrix[i][j] for j in xrange(xmin, xmax + 1)] \
                for i in xrange(ymin, ymax + 1)]
  print_image(bord, 'borders')
  apply_threshold(bubble, WHITE_COLOR)
  print_image(bubble, 'clean_block')
  
  return bubble

  
def find_border(matrix, white_space, boundary):
  ymin, ymax, xmin, xmax = boundary
  border = set()
  # do flood fill from the boundaries
  for i in xrange(xmin, xmax + 1):
    if (ymin, i) not in border and (ymin, i) not in white_space:
      flood_fill_non_white(white_space, border, boundary, ymin, i)
  
  for i in xrange(xmin, xmax + 1):
    if (ymax, i) not in border and (ymax, i) not in white_space:
      flood_fill_non_white(white_space, border, boundary, ymax, i)
      
  for i in xrange(ymin, ymax + 1):
    if (i, xmin) not in border and (i, xmin) not in white_space:
      flood_fill_non_white(white_space, border, boundary, i, xmin)
      
  for i in xrange(ymin, ymax + 1):
    if (i, xmax) not in border and (i, xmax) not in white_space:
      flood_fill_non_white(white_space, border, boundary, i, xmax)

  return border


def flood_fill_non_white(white_space, border, boundary, ycoord, xcoord):
  stack = [(ycoord, xcoord)]
  while stack:
    y, x = stack.pop()
    for i, j in directions:
      next = (y + i, x + j)
      if in_bounds(next, boundary) and next not in white_space and next not in border:
        stack.append(next)
        border.add(next)
    
  
def flood_fill_white(matrix, white_space, ycoord, xcoord, boundary):
  stack = [(ycoord, xcoord)]
  white_space.add((ycoord, xcoord))
  while stack:
    y, x = stack.pop()
    boundary[0] = min(boundary[0], y)
    boundary[1] = max(boundary[1], y)
    boundary[2] = min(boundary[2], x)
    boundary[3] = max(boundary[3], x)
    
    for i, j in directions:
      ynext, xnext = y + i, x + j
      next = (ynext, xnext)
      if in_bounds(next, matrix_bounds) and matrix[ynext][xnext] >= WHITE_COLOR and \
            next not in white_space:
        stack.append(next)
        white_space.add(next)

        
def in_bounds(coord, limits):
  i, j = coord
  ymin, ymax, xmin, xmax = limits
  return i >= ymin and i <= ymax and j >= xmin and j <= xmax
  
  
def apply_threshold(matrix, thres):
  for i in xrange(len(matrix)):
    for j in xrange(len(matrix[0])):
      if matrix[i][j] >= thres:
        matrix[i][j] = 255

      
def print_image(matrix, fname):
  blk = (0, 0, 0)           # color black
  wht = (255, 255, 255)     # color white
  
  pixels2 = [(matrix[i][j], matrix[i][j], matrix[i][j]) for i in xrange(len(matrix)) \
              for j in xrange(len(matrix[0]))]
  
  im2 = Image.new("RGB", (len(matrix[0]), len(matrix)))
  # im2 = im2.convert("RGB")
  im2.putdata(pixels2)
  im2.save(fname + '.png', "PNG")
  
  
def main():
  global matrix_bounds
  
  args = sys.argv[1:]
  filename = args[0]
  try:
    im = Image.open(filename)
  except IOError:
    print "Error in file name"
    print "Please place image in the same directory as the script and enter file name"
    sys.exit()
  
  # get pixel values and store to list
  im = im.convert("L")
  pixels = list(im.getdata())
  width, height = im.size
  # convert to list to 2D list
  pixels = [pixels[i * width:(i + 1) * width] for i in xrange(height)]
  
  matrix_bounds = [0, height - 1, 0, width - 1]
  
  # simulate mouse coordinate
  if len(args) < 2:
    x, y = 114, 319  # corresponds to a text bubble
  else:
    x, y = int(args[1]), int(args[2])
  
  # run flood fill algo
  bubble = crop_bubble(pixels, y, x)
  
  # tighten boundaries and try drawing grid lines
  draw_grid_lines(bubble)


if __name__ == '__main__':
  main()
