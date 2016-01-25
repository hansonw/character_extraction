export function dfs(image, oy, ox, vis, check, callback) {
  if (!check(oy, ox) || vis[oy][ox]) {
    return;
  }
  const stack = [];
  stack.push([oy, ox]);
  vis[oy][ox] = true;
  while (stack.length) {
    const [y, x] = stack.pop();
    callback(y, x);
    for (let dy = -1; dy <= 1; dy++) {
      for (let dx = -1; dx <= 1; dx++) {
        const ny = y + dy;
        const nx = x + dx;
        if (0 <= ny && ny < image.height && 0 <= nx && nx < image.width) {
          if (check(ny, nx) && !vis[ny][nx]) {
            stack.push([ny, nx]);
            vis[ny][nx] = true;
          }
        }
      }
    }
  }
}
