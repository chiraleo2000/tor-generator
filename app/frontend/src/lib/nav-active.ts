/** Which sidebar item should use the orange active color. */

function withoutTrailingSlashes(path: string): string {
  let end = path.length;
  while (end > 0 && path[end - 1] === "/") end -= 1;
  return path.slice(0, end);
}

export function navItemIsActive(pathname: string, href: string): boolean {
  const path = withoutTrailingSlashes(pathname.split("?")[0] || "/") || "/";
  if (href === "/projects") {
    return path === "/projects";
  }
  if (href === "/draft") {
    if (path === "/draft" || path.startsWith("/draft/") || path.startsWith("/wizard")) {
      return true;
    }
    const project = /^\/projects\/[^/]+(?:\/(.*))?$/.exec(path);
    if (!project) {
      return false;
    }
    const rest = project[1] || "";
    return rest === "" || rest.startsWith("draft") || rest.startsWith("wizard");
  }
  return path === href || path.startsWith(`${href}/`);
}
