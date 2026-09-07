/** Which sidebar item should use the orange active color. */

export function navItemIsActive(pathname: string, href: string): boolean {
  const path = (pathname.split("?")[0] || "/").replace(/\/+$/, "") || "/";
  if (href === "/projects") {
    return path === "/projects";
  }
  if (href === "/draft") {
    if (path === "/draft" || path.startsWith("/draft/") || path.startsWith("/wizard")) {
      return true;
    }
    const project = path.match(/^\/projects\/[^/]+(?:\/(.*))?$/);
    if (!project) {
      return false;
    }
    const rest = project[1] || "";
    return rest === "" || rest.startsWith("draft") || rest.startsWith("wizard");
  }
  return path === href || path.startsWith(`${href}/`);
}
